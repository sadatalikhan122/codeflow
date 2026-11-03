"""Tests deliberately avoid starting or downloading Ollama."""

import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import app


class TestChatbot(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_frontend(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("FastAPI Ollama Chatbot", response.text)

    def test_chat_uses_mocked_ollama(self):
        async def fake_ollama(message):
            return f"Hello! You said: {message}"

        with patch("app.main.ask_ollama", new=fake_ollama):
            response = self.client.post("/chat", json={"message": "Hi"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Hello! You said: Hi")
        self.assertEqual(response.json()["model"], "llama3.2")

    def test_empty_message_is_rejected(self):
        response = self.client.post("/chat", json={"message": ""})
        self.assertEqual(response.status_code, 422)

    def test_ollama_offline_is_handled(self):
        async def offline(_message):
            raise httpx.ConnectError(
                "Cannot connect", request=httpx.Request("POST", "http://localhost:11434/api/generate")
            )

        with patch("app.main.ask_ollama", new=offline):
            response = self.client.post("/chat", json={"message": "Hi"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("Cannot reach Ollama", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
