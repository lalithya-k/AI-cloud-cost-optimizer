import os
import requests
from dotenv import load_dotenv


class LLMClientError(Exception):
    pass


class HuggingFaceLLMClient:

    def __init__(self, model_id: str):
        load_dotenv()

        api_key = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
        if not api_key:
            raise LLMClientError("Missing HF token. Set HF_API_KEY (or HF_TOKEN) in your .env")

        self.api_key = api_key
        self.model_id = model_id

        # IMPORTANT: new endpoint
        self.url = "https://router.huggingface.co/v1/chat/completions"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, max_new_tokens: int = 800, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_new_tokens,
        }

        try:
            r = requests.post(self.url, headers=self.headers, json=payload, timeout=90)
        except requests.RequestException as e:
            raise LLMClientError(f"Network error calling LLM: {e}") from e

        if r.status_code != 200:
            raise LLMClientError(f"LLM request failed (status {r.status_code}): {r.text}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMClientError(f"Unexpected response format: {data}") from e
