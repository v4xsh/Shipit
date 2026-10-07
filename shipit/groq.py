"""Minimal Groq chat client over urllib. Raises GroqError with a friendly message."""
import json
import os
import urllib.error
import urllib.request

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"


class GroqError(Exception):
    def __init__(self, msg, bad_json=False):
        super().__init__(msg)
        self.bad_json = bad_json


def post(url, headers, body, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"), headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(messages, transport=post, timeout=30):
    """Send messages, return the reply text (a JSON string)."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise GroqError("No GROQ_API_KEY in .env")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "User-Agent": "shipit/0.1"}  # default urllib agent gets blocked
    body = {"model": os.environ.get("GROQ_MODEL", MODEL), "temperature": 0,
            "response_format": {"type": "json_object"}, "messages": messages}
    try:
        data = transport(URL, headers, body, timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise GroqError(f"Groq said {e.code}", bad_json="json_validate_failed" in detail)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise GroqError(f"Couldn't reach Groq ({e.__class__.__name__})")
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise GroqError("Groq sent an empty answer", bad_json=True)
