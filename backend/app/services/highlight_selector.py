from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import HIGHLIGHT_PROVIDER, OPENAI_HIGHLIGHT_MODEL, SHORT_CLIP_SECONDS


@dataclass
class Highlight:
    start: float
    end: float
    reason: str


def select_highlight(segments: list[dict[str, Any]], transcript: str) -> Highlight | None:
    if not segments:
        return None

    provider = os.getenv("HIGHLIGHT_PROVIDER", HIGHLIGHT_PROVIDER).lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            return select_with_openai(segments)
        except Exception:
            return select_with_heuristic(segments, transcript)
    return select_with_heuristic(segments, transcript)


def select_with_openai(segments: list[dict[str, Any]]) -> Highlight:
    duration = int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_HIGHLIGHT_MODEL", OPENAI_HIGHLIGHT_MODEL)
    compact_segments = [
        {
            "start": round(float(segment["start"]), 2),
            "end": round(float(segment["end"]), 2),
            "text": segment["text"],
        }
        for segment in segments[:160]
    ]
    body = {
        "model": model,
        "instructions": (
            "Choose the strongest short-video highlight from timestamped transcript segments. "
            "Prefer emotionally strong, surprising, useful, funny, controversial, or self-contained moments. "
            f"Return only JSON with start, end, and reason. Keep the clip at or under {duration} seconds."
        ),
        "input": json.dumps(compact_segments, ensure_ascii=False),
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    text = extract_response_text(payload)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError("Highlight selector returned no JSON.")
    selected = json.loads(match.group(0))
    return normalize_highlight(
        float(selected["start"]),
        float(selected["end"]),
        str(selected.get("reason", "AI-selected highlight")),
        segments,
    )


def select_with_heuristic(segments: list[dict[str, Any]], transcript: str) -> Highlight:
    duration = int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    keywords = {
        "truth",
        "secret",
        "best",
        "worst",
        "never",
        "always",
        "why",
        "how",
        "mistake",
        "money",
        "love",
        "betrayal",
        "problem",
        "solution",
        "important",
        "እውነት",
        "ችግር",
        "ፍቅር",
    }
    best_index = 0
    best_score = -1
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "")).lower()
        word_count = len(text.split())
        keyword_score = sum(3 for keyword in keywords if keyword in text)
        punctuation_score = text.count("?") * 2 + text.count("!") * 2
        position_score = 1 if index > 0 else 0
        score = word_count + keyword_score + punctuation_score + position_score
        if score > best_score:
            best_index = index
            best_score = score

    start = max(0.0, float(segments[best_index]["start"]) - 2)
    end = start
    for segment in segments[best_index:]:
        end = float(segment["end"])
        if end - start >= duration:
            break
    return normalize_highlight(start, end, "Selected by local highlight scoring", segments)


def normalize_highlight(start: float, end: float, reason: str, segments: list[dict[str, Any]]) -> Highlight:
    duration = int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    video_end = max(float(segment["end"]) for segment in segments)
    start = max(0.0, min(start, video_end))
    end = max(start + 3, min(end, start + duration, video_end))
    return Highlight(start=start, end=end, reason=reason)


def extract_response_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct

    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts)
