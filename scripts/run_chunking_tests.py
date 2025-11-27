#!/usr/bin/env python3
"""
Run transcription tests for multiple audio files defined in speech2text/file.json
and collect timing/response metadata for reporting.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000/transcribe")
API_KEY = os.environ.get("API_KEY", "your-api-key-here")
INPUT_FILE = Path("speech2text/file.json")
OUTPUT_DIR = Path("/tmp/base_chunking_tests")
RESULTS_JSON = OUTPUT_DIR / "results.json"

# Preferred language hints per duration (minutes). Falls back to Vietnamese.
LANGUAGE_HINTS = {
    4: "vi",
    9: "vi",
    13: "en",
    18: "vi",
}


@dataclass
class TestResult:
    index: int
    duration_label: str
    duration_minutes: int
    media_url: str
    language: str
    status_code: int
    success: bool
    api_status: str | None
    processing_time: float | None
    audio_duration: float | None
    error_message: str | None
    total_wall_time: float
    response_path: str


def load_test_cases() -> list[dict[str, Any]]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Test input file not found: {INPUT_FILE}")
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("file.json must contain a list of test cases")
    return data


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def infer_language(duration_label: str) -> tuple[int, str]:
    """Parse '4 minutes' -> (4, 'vi'|'en')."""
    parts = duration_label.split()
    try:
        minutes = int(parts[0])
    except (ValueError, IndexError):
        minutes = -1
    language = LANGUAGE_HINTS.get(minutes, "vi")
    return minutes, language


def run_test_case(index: int, case: dict[str, Any]) -> TestResult:
    duration_label = case.get("duration", f"{index}")
    minutes, language = infer_language(duration_label)
    media_url = case["url"]

    payload = {"media_url": media_url}
    if language:
        payload["language"] = language

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }

    start = time.perf_counter()
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=1200)
        wall_time = time.perf_counter() - start
        response_text = resp.text
    except Exception as exc:
        wall_time = time.perf_counter() - start
        response_text = json.dumps(
            {"status": "error", "message": str(exc)}, ensure_ascii=False
        )
        resp = None

    response_path = (
        OUTPUT_DIR / f"test{index}_{minutes if minutes > 0 else 'unknown'}min.json"
    )
    response_path.write_text(response_text, encoding="utf-8")

    api_status = None
    processing_time = None
    audio_duration = None
    error_message = None

    if resp is not None:
        try:
            data = resp.json()
            api_status = data.get("status")
            if isinstance(data.get("data"), dict):
                processing_time = data["data"].get("processing_time")
                audio_duration = data["data"].get("duration") or data["data"].get(
                    "audio_duration"
                )
            if api_status != "success":
                error_message = data.get("message")
        except ValueError:
            error_message = "Invalid JSON response"

    return TestResult(
        index=index,
        duration_label=duration_label,
        duration_minutes=minutes,
        media_url=media_url,
        language=language,
        status_code=resp.status_code if resp is not None else -1,
        success=(resp is not None and resp.ok),
        api_status=api_status,
        processing_time=processing_time,
        audio_duration=audio_duration,
        error_message=error_message,
        total_wall_time=wall_time,
        response_path=str(response_path),
    )


def main() -> None:
    ensure_output_dir()
    cases = load_test_cases()
    results: list[TestResult] = []

    for idx, case in enumerate(cases, start=1):
        print(
            f"=== Running test {idx}/{len(cases)}: {case.get('duration')} ===",
            flush=True,
        )
        result = run_test_case(idx, case)
        results.append(result)
        print(
            f"[{idx}] status={result.status_code}, success={result.success}, "
            f"wall={result.total_wall_time:.2f}s, api_status={result.api_status}",
            flush=True,
        )

    with RESULTS_JSON.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)

    print("\n=== Summary ===")
    for r in results:
        print(
            f"Test {r.index}: {r.duration_label} | success={r.success} "
            f"| status={r.status_code} | api={r.api_status} "
            f"| wall={r.total_wall_time:.2f}s",
            flush=True,
        )
    print(f"\nResults saved to: {RESULTS_JSON}")


if __name__ == "__main__":
    main()
