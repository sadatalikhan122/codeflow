"""FastAPI backend for a local Ollama chatbot."""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="FastAPI + Ollama CI/CD Chatbot", version="1.0.0")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
HTML_FILE = Path(__file__).resolve().parent / "static" / "index.html"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    model: str


async def ask_ollama(message: str) -> str:
    """Call the Ollama generation API; tests replace this function with a mock."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": message, "stream": False},
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("response")
        if not isinstance(answer, str):
            raise ValueError("Ollama returned a response without answer text")
        return answer


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(HTML_FILE)


@app.get("/health")
async def health():
    """Liveness only; does not guarantee the Ollama model is downloaded."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        answer = await ask_ollama(body.message)
    except httpx.HTTPStatusError as exc:
        # Example: Ollama returns 404 if the model has not been pulled yet.
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an error. Check that the model is downloaded.",
        ) from exc
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Ollama. Check whether Ollama is running.",
        ) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail="Invalid Ollama response") from exc

    return ChatResponse(answer=answer, model=OLLAMA_MODEL)
