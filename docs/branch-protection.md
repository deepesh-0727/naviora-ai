# Protecting `main`

Configure branch protection in GitHub; repository files cannot enforce these repository settings.

## Recommended rule

For `main`, configure:

- Require a pull request before merging.
- Require 1 approving review.
- Require the `backend` and `frontend` status checks from the `Test` workflow.
- Require branches to be up to date before merging.
- Do not allow force pushes.
- Do not allow branch deletions.
- Optionally require signed commits if contributors have signing keys configured.

## Configure in GitHub

1. Open `deepesh-0727/naviora-ai` on GitHub.
2. Go to **Settings → Branches**.
3. Choose **Add branch protection rule** (or add a ruleset), and set the branch name pattern to `main`.
4. Enable the required pull request, reviewer, status check, and up-to-date options above.
5. Select `backend` and `frontend` as required status checks after the `Test` workflow has reported them at least once.
6. Leave force pushes and deletions disabled. Enable signed commits only if the team is ready to sign every commit.
7. Save the rule and confirm it appears for `main`.
