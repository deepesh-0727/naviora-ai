# Naviora AI Engineering Manifesto

## 🚀 Vision
Naviora AI is a mission-critical coordination platform for clinical environments. We prioritize **Reliability**, **Traceability**, and **Accessibility**.

## 🛡️ Reliability & Resilience
Every code contribution must adhere to the **Failure-Is-Certain** principle:
1.  **Circuit Breakers:** All AI and external service calls must be wrapped in circuit breakers.
2.  **Graceful Fallbacks:** If the AI fails, the system must revert to safe, deterministic rule-based logic.
3.  **Idempotency:** All state-changing API operations (e.g., SOS trigger) must be idempotent to prevent duplicate events during network retries.

## 🔒 Security & HIPAA Alignment
1.  **PII Encryption:** All patient-identifiable data (Name, Phone, Medical History) must be encrypted at rest using AES-256.
2.  **Audit Logs:** Every clinician and admin action must be logged with the `request_id`, user ID, and timestamp.
3.  **Strict Schema Validation:** No clinical data enters the database without passing Pydantic regex and range validation.

## 📱 User Experience & Accessibility
1.  **High Contrast:** Use the primary Brand Palette (Sky-500/Slate-900) to ensure readability for patients with visual impairments.
2.  **Zero-Typing Philosophy:** Every feature must be accessible via voice.
3.  **Visual Feedback:** Every async operation (loading, AI thinking) must have an accompanying animation to reduce perceived latency.

## 🛠 Backend Engineering
1.  **Modular Monolith:** Maintain clear separation between `Agents`, `Services`, and `Core` modules to ensure vertical scalability.
2.  **Async/Await:** Blocking calls are strictly prohibited in the main request loop. Use `BackgroundTasks` for high-latency operations.
3.  **Structured Logging:** Log only contextually relevant data. PII must be masked in logs.
