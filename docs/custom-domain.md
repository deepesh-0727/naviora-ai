# Custom API domain on Render

This guide prepares `api.naviora.ai` as the API hostname. You must own and control the `naviora.ai` domain before making DNS changes.

## Add the hostname in Render

1. Open the backend web service in the Render Dashboard.
2. Under **Settings → Custom Domains**, add `api.naviora.ai` and save it.
3. Copy the exact DNS target Render shows for this service. Do not guess the target from an old deployment or copy a target from another service.

## Configure DNS

At the DNS provider for `naviora.ai`, create a `CNAME` record with name `api` and the target shown by Render. Remove conflicting records for `api`, including any `AAAA` record, then wait for DNS propagation. Return to Render and select **Verify**. Render provisions and renews TLS certificates for custom domains and redirects HTTP to HTTPS. See [Render custom domains](https://render.com/docs/custom-domains) and [managed TLS](https://render.com/docs/tls) for provider-specific details.

## Configure the backend

In Render's backend environment, set:

```text
ALLOWED_ORIGINS=https://naviora.ai,https://www.naviora.ai
```

`ALLOWED_ORIGINS` is a comma-separated list of browser origins, including scheme and optional port. Add only the frontend origins that should call the API. The backend also accepts the legacy `BACKEND_CORS_ORIGINS` setting; both lists are merged. `api.naviora.ai` is included in the built-in trusted-host list. Save the environment change and wait for Render to redeploy.

## Configure the frontend

Set this build-time Expo variable in the frontend hosting/build environment, then create a new frontend build:

```text
EXPO_PUBLIC_API_URL=https://api.naviora.ai
```

The shared frontend config appends `/api/v1` for REST calls and derives `wss://api.naviora.ai/api/v1/stream` for WebSockets. Do not include `/api/v1` in the environment value unless you have verified the config's suffix handling in the target build.

## Verify the cutover

Check DNS resolution and the Render dashboard's domain verification first. Then verify:

```text
https://api.naviora.ai/health
https://api.naviora.ai/api/v1/departments
```

Both should use valid HTTPS certificates. `/health` should return `200` with `{"status":"ok"}`. The public department list should return `200` and the configured database rows. Finally, open the rebuilt frontend and check sign-in, department loading, and WebSocket flows before changing any remaining clients. Keep the Render hostname available for rollback until the new hostname has been observed healthy.
