# GitHub Actions deployment secrets

The `Deploy` workflow needs these repository Actions secrets before it can request a Render deployment:

| Secret | Used by | Where to get it | Required? |
|---|---|---|---|
| `RENDER_DEPLOY_HOOK` | `.github/workflows/deploy.yml` | Render dashboard → `naviora-backend` service → Settings → Deploy Hook | Yes |
| `RENDER_BACKEND_URL` | `.github/workflows/deploy.yml` health check | The public URL shown for the Render `naviora-backend` service, for example `https://naviora-backend.onrender.com` | Yes |

Add each value to GitHub without committing it:

1. Open the repository on GitHub and go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Enter the exact secret name from the table and its value from Render.
4. Click **Add secret** / **Save**.

`RENDER_BACKEND_URL` must be the HTTPS base URL of the backend service. The workflow checks its `/health` endpoint after triggering the deploy hook. If either secret is missing, the deploy job fails with an explicit error.

Never put deploy-hook URLs or production credentials in workflow YAML, source files, or commit messages.
