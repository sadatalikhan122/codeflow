# FastAPI + Ollama + GitHub Actions CI/CD

A hands-on project: HTML chat page -> FastAPI -> Ollama (`llama3.2`). Every push to `main` triggers **CI** (unit tests, Compose validation, Docker image build). After CI passes, **CD** automatically uploads source over SSH and runs Docker Compose on an Ubuntu VPS / AWS EC2 server.

> **Important:** GitHub Pages cannot host FastAPI or Ollama. CD requires a real Linux server with Docker, SSH, and enough RAM/disk for the model. The repo contains a working CD workflow, but it cannot deploy until you configure your server and four GitHub secrets.

## Project structure

```
fastapi-ollama-cicd/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── static/index.html
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .github/workflows/ci-cd.yml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── compose.yaml
├── .dockerignore
└── .gitignore
```

## 1. Run locally on Windows (no Docker required)

Install [Python 3.13](https://www.python.org/downloads/) and [Ollama](https://ollama.com/download). Open PowerShell from the **project root** (the directory containing `app` and `tests`).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
ollama pull llama3.2
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload
```

Ollama typically starts automatically when its Windows application runs; otherwise start `ollama serve` in another terminal. Open http://127.0.0.1:8000 for chat and http://127.0.0.1:8000/docs for API docs.

The `/chat` endpoint accepts `{"message":"Hello"}` and returns `{"answer":"...","model":"llama3.2"}`. The `/health` endpoint tests only FastAPI, not model readiness. CI mocks the Ollama call, so no model is needed during tests.

## 2. Create a new GitHub repository (avoid nested Git folders)

Create an **empty** GitHub repository named `fastapi-ollama-cicd` (do not add a README or license on GitHub when creating it). Open PowerShell *inside this extracted project folder*:

```powershell
git init
git add .
git commit -m "Initial FastAPI Ollama CI/CD project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fastapi-ollama-cicd.git
git push -u origin main
```

Replace `YOUR_USERNAME`. If `git commit` requests your identity, set `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"` first.

At this point **CI** runs automatically from GitHub > Actions. **CD** will not succeed until you complete the server and secrets configuration below.

## 3. One-time Ubuntu VPS / AWS EC2 setup

Use a Linux host with enough RAM and disk to run `llama3.2` on CPU (8 GB+ RAM is a useful starting point, actual requirements vary). SSH to the server using your own credentials. Install Docker Engine **and Docker Compose plugin** according to the official Docker Ubuntu instructions:

https://docs.docker.com/engine/install/ubuntu/

Then:

```bash
sudo apt update
sudo apt install -y rsync curl
sudo usermod -aG docker "$USER"
```

Log out of SSH and reconnect so Docker group membership applies. Check:

```bash
docker --version
docker compose version
mkdir -p "$HOME/fastapi-ollama-cicd"
```

**Security:** Docker group membership grants near-root privileges. Use a dedicated trusted deployment account with no more access than needed. Do **not** make port 11434 public. The Compose configuration binds the FastAPI app to `127.0.0.1:8000` on the server, so it is not exposed publicly without a proxy/tunnel. This is intentional.

### SSH key for GitHub Actions

Generate a **dedicated deployment key pair on your own trusted machine** (not inside the GitHub workflow). Example:

```bash
ssh-keygen -t ed25519 -f github-actions-deploy -C github-actions-deploy
```

Install the **public** key (`github-actions-deploy.pub`) into the deployment account's `~/.ssh/authorized_keys` on the server. Keep the **private** key safe and put its contents in a GitHub Actions secret. Verify the server's SSH host fingerprint out of band before trusting a `known_hosts` entry (do not blindly trust SSH keyscan output).

In GitHub repository -> Settings -> Secrets and variables -> Actions, add these **four Repository secrets**:

| Name | Value |
| --- | --- |
| `DEPLOY_HOST` | Server public IPv4 or DNS name |
| `DEPLOY_USER` | SSH username, e.g. `ubuntu` |
| `DEPLOY_SSH_KEY` | Entire private OpenSSH key, with BEGIN/END lines |
| `DEPLOY_KNOWN_HOSTS` | Verified SSH host key entry for your server (OpenSSH `known_hosts` format) |

If you use a GitHub **production environment** with approval rules, deployment waits for those approvals. Otherwise the CD job starts automatically after CI.

A server that SSHes via a nonstandard port will need extra customization (the sample assumes port 22). Ensure firewall/security-group allows SSH from GitHub-hosted runners; GitHub runner IPs are dynamic, so use a suitable secure deployment strategy for production.

## 4. Deploy automatically

Push any change to `main`:

```powershell
git add .
git commit -m "Update chatbot"
git push origin main
```

Workflow: CI runs 5 tests, validates Compose, builds the API image. CD uses SSH + rsync to copy files into `~/fastapi-ollama-cicd` on your server, runs `docker compose up -d --build`, downloads `llama3.2` only if missing, and checks `GET /health`. If tests fail, CD doesn't run.

For a remote private demo, access the app with an **SSH tunnel from your computer**:

```bash
ssh -L 8000:127.0.0.1:8000 DEPLOY_USER@DEPLOY_HOST
```

Keep the SSH session open, and visit http://127.0.0.1:8000 on your computer. If running FastAPI locally too, free local port 8000 or use another local tunnel port.

For a public domain, configure HTTPS reverse proxy (Caddy or Nginx), authentication, rate-limiting, monitoring, and appropriate network access. This starter repo deliberately does not publish the Ollama backend or expose the API openly.

## Troubleshooting

- `ImportError: Start directory is not importable: 'tests'` -> run tests from the folder that actually has the `tests` directory; this repo includes `tests/__init__.py`.
- `error: src refspec main does not match any` -> create the first commit, then `git branch -M main` and push.
- `'origin' does not appear to be a git repository` -> `git remote -v` and add the actual repository URL with `git remote add origin ...`.
- `502` on `/chat` -> model missing: `ollama pull llama3.2` (local) or `docker compose exec ollama ollama pull llama3.2` (server).
- `503` on `/chat` -> Ollama unavailable; check running process/container and `OLLAMA_BASE_URL`.
- CD job fails on SSH -> verify secrets, server firewall, `authorized_keys`, server fingerprint, and server Docker/rsync installation.
- Docker on Windows requires working WSL2/virtualization, but local Python + Ollama mode does not require Docker.

## Notes

This is a learning/reference project, not a fully production-hardened public chatbot. It does not implement user authentication, request quotas, model safety controls, HTTPS reverse proxy, persistent conversation history, or rollback. For serious use, pin and scan your image dependencies, restrict SSH/network access, implement authentication, and use a controlled deployment account.
