from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import HIGHLIGHT_PROVIDER, OPENAI_HIGHLIGHT_MODEL, SHORT_CLIP_COUNT, SHORT_CLIP_SECONDS


@dataclass
class Highlight:
    start: float
    end: float
    reason: str


def select_highlight(segments: list[dict[str, Any]], transcript: str) -> Highlight | None:
    highlights = select_highlights(segments, transcript, count=1)
    return highlights[0] if highlights else None


def select_highlights(
    segments: list[dict[str, Any]],
    transcript: str,
    count: int | None = None,
    duration_seconds: int | None = None,
) -> list[Highlight]:
    if not segments:
        return []

    count = count or int(os.getenv("SHORT_CLIP_COUNT", str(SHORT_CLIP_COUNT)))
    duration_seconds = duration_seconds or int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    provider = os.getenv("HIGHLIGHT_PROVIDER", HIGHLIGHT_PROVIDER).lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            return select_many_with_openai(segments, count, duration_seconds)
        except Exception:
            return select_many_with_heuristic(segments, transcript, count, duration_seconds)
    return select_many_with_heuristic(segments, transcript, count, duration_seconds)


def select_with_openai(segments: list[dict[str, Any]]) -> Highlight:
    highlights = select_many_with_openai(
        segments,
        count=1,
        duration_seconds=int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS))),
    )
    if not highlights:
        raise RuntimeError("Highlight selector returned no highlights.")
    return highlights[0]


def select_many_with_openai(
    segments: list[dict[str, Any]],
    count: int,
    duration_seconds: int,
) -> list[Highlight]:
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
            f"Return only JSON as an array of up to {count} objects with start, end, and reason. "
            f"Keep each clip at or under {duration_seconds} seconds. Avoid duplicate or overlapping clips."
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
    match = re.search(r"\[.*\]|\{.*\}", text, re.S)
    if not match:
        raise RuntimeError("Highlight selector returned no JSON.")
    selected = json.loads(match.group(0))
    if isinstance(selected, dict):
        selected = [selected]
    return [
        normalize_highlight(
            float(item["start"]),
            float(item["end"]),
            str(item.get("reason", "AI-selected highlight")),
            segments,
            duration_seconds,
        )
        for item in selected[:count]
    ]


def select_with_heuristic(segments: list[dict[str, Any]], transcript: str) -> Highlight:
    highlights = select_many_with_heuristic(
        segments,
        transcript,
        count=1,
        duration_seconds=int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS))),
    )
    return highlights[0]


def select_many_with_heuristic(
    segments: list[dict[str, Any]],
    transcript: str,
    count: int,
    duration_seconds: int,
) -> list[Highlight]:
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
    scored: list[tuple[int, int]] = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "")).lower()
        word_count = len(text.split())
        keyword_score = sum(3 for keyword in keywords if keyword in text)
        punctuation_score = text.count("?") * 2 + text.count("!") * 2
        position_score = 1 if index > 0 else 0
        score = word_count + keyword_score + punctuation_score + position_score
        scored.append((score, index))

    highlights: list[Highlight] = []
    used_ranges: list[tuple[float, float]] = []
    for _, index in sorted(scored, reverse=True):
        start = max(0.0, float(segments[index]["start"]) - 2)
        end = start
        for segment in segments[index:]:
            end = float(segment["end"])
            if end - start >= duration_seconds:
                break
        highlight = normalize_highlight(
            start,
            end,
            "Selected by local highlight scoring",
            segments,
            duration_seconds,
        )
        if any(ranges_overlap((highlight.start, highlight.end), used) for used in used_ranges):
            continue
        highlights.append(highlight)
        used_ranges.append((highlight.start, highlight.end))
        if len(highlights) >= count:
            break
    return highlights


def normalize_highlight(
    start: float,
    end: float,
    reason: str,
    segments: list[dict[str, Any]],
    duration_seconds: int | None = None,
) -> Highlight:
    duration = duration_seconds or int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    video_end = max(float(segment["end"]) for segment in segments)
    start = max(0.0, min(start, video_end))
    end = max(start + 3, min(end, start + duration, video_end))
    return Highlight(start=start, end=end, reason=reason)


def ranges_overlap(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return max(first[0], second[0]) < min(first[1], second[1])


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
