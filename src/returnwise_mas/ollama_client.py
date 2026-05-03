from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaClient:
    """Small HTTP client for local Ollama text generation."""

    model: str = "phi3"
    host: str = "http://localhost:11434"
    timeout_seconds: int = 45

    def generate(self, system_prompt: str, task_prompt: str) -> str:
        """Generate a response from a local Ollama model.

        Raises:
            RuntimeError: If Ollama is unavailable or returns an invalid response.
        """
        body = json.dumps(
            {
                "model": self.model,
                "prompt": f"{system_prompt.strip()}\n\nTask:\n{task_prompt.strip()}",
                "stream": False,
                "options": {"temperature": 0.1},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc

        text = payload.get("response")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Ollama returned an empty response.")
        return text.strip()

