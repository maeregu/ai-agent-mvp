from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import app.config  # Loads backend/.env


def main() -> int:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("api_key_available false")
        return 1

    request = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print("status", response.status)
            print("api_key_valid true")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print("status", exc.code)
        print("api_key_valid false")
        try:
            payload = json.loads(body)
            error = payload.get("error", {})
            print("error_code", error.get("code"))
            print("error_type", error.get("type"))
            print("message", error.get("message"))
        except json.JSONDecodeError:
            print(body[:300])
        return 1
    except Exception as exc:
        print(type(exc).__name__, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
