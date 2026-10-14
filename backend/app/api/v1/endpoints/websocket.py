from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
import jwt
import logging
import json
import secrets
from redis.asyncio import Redis
from app.core import security
from app.core.config import settings
from app.services.ws_manager import ws_manager
from app.services.voice.voice_orchestrator import voice_orchestrator
from app.db.session import SessionLocal
from sqlalchemy.future import select
from app.models.user import User
from sqlalchemy.orm import selectinload

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Authentication Token"),
    session_id: str | None = Query(None, description="Redis-backed conversation session"),
):
    """
    Real-time WebSocket Gateway for voice assistant streams and notifications
    """
    user_id = None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        user_id = payload.get("sub")
        if payload.get("type") != "access":
            raise ValueError("Access token required")
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=4003)
        return

    if not user_id:
        await websocket.close(code=4003)
        return

    if not str(user_id).isdigit():
        await websocket.close(code=4003)
        return

    session_key = session_id or secrets.token_urlsafe(24)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_key = f"naviora:session:{user_id}:{session_key}"
    try:
        await redis.ping()
    except Exception:
        await redis.aclose()
        await websocket.close(code=1013, reason="Session storage unavailable")
        return

    await ws_manager.connect(websocket, str(user_id), claims=payload)

    try:
        while True:
            # Handle both JSON commands and Binary audio chunks
            message = await websocket.receive()
            
            if "bytes" in message:
                # Binary audio chunk received
                audio_data = message["bytes"]

                async with SessionLocal() as db:
                    # Fetch user with patient profile for context
                    result = await db.execute(
                        select(User)
                        .options(selectinload(User.patient_profile))
                        .filter(User.id == int(user_id))
                    )
                    user = result.scalars().first()

                    if user:
                        result = await voice_orchestrator.process_audio_command(
                            db, user, audio_data, await _load_session_context(redis, redis_key, user_id, session_key)
                        )

                        # Send back the metadata and audio response
                        await websocket.send_json({
                            "type": "voice_response",
                            "query": result.get("query"),
                            "intent": result.get("intent"),
                            "response_text": result.get("response_text")
                        })
                        target_room = (
                            f"patient:{payload.get('patient_id') or user_id}"
                            if payload.get("role") == "patient"
                            else f"doctor:{payload.get('staff_id') or user_id}"
                            if payload.get("role") == "doctor"
                            else f"nurse:{payload.get('staff_id') or user_id}"
                            if payload.get("role") == "nurse"
                            else f"staff:{user_id}"
                        )
                        await ws_manager.broadcast_event(target_room, "voice_result", {
                            "intent": result.get("intent"),
                            "response_text": result.get("response_text"),
                        })
                        await _save_session_context(redis, redis_key, user_id, session_key)

                        if result.get("audio_response"):
                            await websocket.send_bytes(result["audio_response"])

            elif "text" in message:
                import json
                data = json.loads(message["text"])
                action = data.get("action")

                if action == "ping":
                    await websocket.send_json({"action": "pong"})
                elif action == "pong":
                    ws_manager.handle_pong(websocket)
                elif action == "join_room":
                    room = data.get("room")
                    if isinstance(room, str) and await ws_manager.join_room(websocket, room):
                        await websocket.send_json({"action": "joined_room", "room": room})
                    elif isinstance(room, str):
                        await websocket.send_json({"type": "error", "message": "Not authorized to join room"})
                elif action == "leave_room":
                    room = data.get("room")
                    if room:
                        await ws_manager.leave_room(websocket, room)
                        await websocket.send_json({"action": "left_room", "room": room})

                elif action == "process_voice":
                    base64_audio = data.get("audio")
                    if base64_audio:
                        import base64
                        try:
                            audio_data = base64.b64decode(base64_audio)
                            async with SessionLocal() as db:
                                result = await db.execute(
                                    select(User)
                                    .options(selectinload(User.patient_profile))
                                    .filter(User.id == int(user_id))
                                )
                                user = result.scalars().first()

                                if user:
                                    process_result = await voice_orchestrator.process_audio_command(
                                        db, user, audio_data,
                                        await _load_session_context(redis, redis_key, user_id, session_key),
                                    )

                                    await websocket.send_json({
                                        "type": "voice_response",
                                        "query": process_result.get("query"),
                                        "intent": process_result.get("intent"),
                                        "response_text": process_result.get("response_text")
                                    })
                                    target_room = (
                                        f"patient:{payload.get('patient_id') or user_id}"
                                        if payload.get("role") == "patient"
                                        else f"doctor:{payload.get('staff_id') or user_id}"
                                        if payload.get("role") == "doctor"
                                        else f"nurse:{payload.get('staff_id') or user_id}"
                                        if payload.get("role") == "nurse"
                                        else f"staff:{user_id}"
                                    )
                                    await ws_manager.broadcast_event(target_room, "voice_result", {
                                        "intent": process_result.get("intent"),
                                        "response_text": process_result.get("response_text"),
                                    })
                                    await _save_session_context(redis, redis_key, user_id, session_key)

                                    if process_result.get("audio_response"):
                                        await websocket.send_bytes(process_result["audio_response"])
                        except Exception as e:
                            logger.error(f"Error processing base64 voice: {e}")
                            await websocket.send_json({"type": "error", "message": "Failed to process audio stream"})

                # WebRTC Signaling Bridge
                elif action in ["rtc_offer", "rtc_answer", "rtc_candidate"]:
                    target_id = data.get("target_id")
                    if target_id:
                        # Forward the signaling packet to the target user
                        await ws_manager.send_personal_message(
                            {
                                "type": action,
                                "sender_id": str(user_id),
                                "data": data.get("data")
                            },
                            str(target_id)
                        )

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, str(user_id))
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await ws_manager.disconnect(websocket, str(user_id))
    finally:
        await redis.aclose()


async def _load_session_context(redis: Redis, key: str, user_id: str, session_id: str) -> dict:
    stored = await redis.get(key)
    context = json.loads(stored) if stored else {}
    context.update({"session_id": session_id, "user_id": int(user_id)})
    return context


async def _save_session_context(redis: Redis, key: str, user_id: str, session_id: str) -> None:
    await redis.set(
        key,
        json.dumps({"session_id": session_id, "user_id": int(user_id)}),
        ex=settings.CACHE_TTL,
    )


