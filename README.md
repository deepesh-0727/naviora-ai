# Naviora AI

Naviora AI is a hospital operations platform with a FastAPI backend and an Expo / React Native frontend.

## Development checks

Install Git pre-commit hooks after cloning:

```bash
python -m pip install pre-commit
pre-commit install
```

Run all configured hooks against the repository:

```bash
pre-commit run --all-files
```

Backend and frontend test instructions are in [docs/testing.md](docs/testing.md). CI and deployment secret setup is in [docs/ci-secrets.md](docs/ci-secrets.md).

<!-- First automated deploy -->
