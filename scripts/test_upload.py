#!/usr/bin/env python3
"""
Test script for the complete STT pipeline.
Tests the end-to-end flow: upload → queue → process → retrieve results.

Usage:
    python scripts/test_upload.py <audio_file_path> [--language vi] [--model medium]

Example:
    python scripts/test_upload.py tests/sample.mp3 --language vi --model medium

This script will:
1. Upload an audio file to the API
2. Poll for job status until completion
3. Retrieve and display the transcription result
4. Save results to a file
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 2  # seconds
MAX_POLL_TIME = 3600  # 1 hour


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(message: str):
    """Print a header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}{message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.CYAN}🔍 {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")


async def upload_audio(
    file_path: Path, language: str = "vi", model: str = "medium"
) -> Optional[dict]:
    """
    Upload an audio file to the API.

    Args:
        file_path: Path to audio file
        language: Language code
        model: Whisper model to use

    Returns:
        Response dictionary with job_id, or None on error
    """
    try:
        print_info(f"Uploading audio file: {file_path}")
        print_info(f"Language: {language}, Model: {model}")

        # Check if file exists
        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            return None

        # Get file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        print_info(f"File size: {file_size_mb:.2f}MB")

        # Prepare multipart form data
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "audio/mpeg")}
                data = {"language": language, "model": model}

                print_info(f"Sending request to {API_BASE_URL}/api/v1/tasks/upload...")

                response = await client.post(
                    f"{API_BASE_URL}/api/v1/tasks/upload", files=files, data=data
                )

                if response.status_code == 201:
                    result = response.json()
                    print_success(f"Upload successful!")
                    print_success(f"Job ID: {result['job_id']}")
                    return result
                else:
                    print_error(f"Upload failed with status {response.status_code}")
                    print_error(f"Response: {response.text}")
                    return None

    except httpx.RequestError as e:
        print_error(f"Request failed: {e}")
        print_warning("Make sure the API server is running at http://localhost:8000")
        return None
    except Exception as e:
        print_error(f"Upload error: {e}")
        import traceback

        traceback.print_exc()
        return None


async def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get the status of a job.

    Args:
        job_id: Job identifier

    Returns:
        Status dictionary, or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{job_id}/status")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print_error(f"Job not found: {job_id}")
                return None
            else:
                print_error(f"Status check failed with status {response.status_code}")
                print_error(f"Response: {response.text}")
                return None

    except httpx.RequestError as e:
        print_error(f"Request failed: {e}")
        return None
    except Exception as e:
        print_error(f"Status check error: {e}")
        return None


async def get_job_result(job_id: str) -> Optional[dict]:
    """
    Get the result of a completed job.

    Args:
        job_id: Job identifier

    Returns:
        Result dictionary, or None on error
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{job_id}/result")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print_error(f"Job not found: {job_id}")
                return None
            else:
                print_error(
                    f"Result retrieval failed with status {response.status_code}"
                )
                print_error(f"Response: {response.text}")
                return None

    except httpx.RequestError as e:
        print_error(f"Request failed: {e}")
        return None
    except Exception as e:
        print_error(f"Result retrieval error: {e}")
        return None


async def poll_until_complete(job_id: str) -> bool:
    """
    Poll job status until it's completed or failed.

    Args:
        job_id: Job identifier

    Returns:
        True if completed successfully, False otherwise
    """
    start_time = time.time()
    last_progress = -1

    print_header("Polling Job Status")
    print_info(f"Job ID: {job_id}")
    print_info(f"Polling every {POLL_INTERVAL} seconds...")

    while True:
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > MAX_POLL_TIME:
            print_error(f"Timeout after {MAX_POLL_TIME} seconds")
            return False

        # Get status
        status_data = await get_job_status(job_id)
        if not status_data:
            print_error("Failed to get job status")
            return False

        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        chunks_completed = status_data.get("chunks_completed", 0)
        chunks_total = status_data.get("chunks_total", 0)

        # Print progress if changed
        if progress != last_progress:
            if chunks_total > 0:
                print_info(
                    f"Status: {status} | Progress: {progress:.1f}% | "
                    f"Chunks: {chunks_completed}/{chunks_total} | "
                    f"Elapsed: {elapsed:.1f}s"
                )
            else:
                print_info(f"Status: {status} | Elapsed: {elapsed:.1f}s")
            last_progress = progress

        # Check if completed
        if status == "COMPLETED":
            print_success(f"Job completed in {elapsed:.1f} seconds!")
            return True

        # Check if failed
        if status == "FAILED":
            error_message = status_data.get("error_message", "Unknown error")
            print_error(f"Job failed: {error_message}")
            return False

        # Wait before next poll
        await asyncio.sleep(POLL_INTERVAL)


async def save_results(job_id: str, result_data: dict, output_dir: Path):
    """
    Save transcription results to files.

    Args:
        job_id: Job identifier
        result_data: Result dictionary
        output_dir: Output directory
    """
    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save full JSON response
        json_path = output_dir / f"{job_id}_result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        print_success(f"Saved JSON result to: {json_path}")

        # Save transcription text only
        transcription = result_data.get("transcription", "")
        if transcription:
            text_path = output_dir / f"{job_id}_transcription.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(transcription)
            print_success(f"Saved transcription to: {text_path}")

    except Exception as e:
        print_error(f"Failed to save results: {e}")


async def main():
    """Main test function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test the STT pipeline by uploading an audio file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_upload.py tests/sample.mp3
  python scripts/test_upload.py tests/sample.wav --language en --model small
  python scripts/test_upload.py tests/sample.m4a --language vi --model medium
        """,
    )
    parser.add_argument("audio_file", type=Path, help="Path to audio file to upload")
    parser.add_argument(
        "--language", type=str, default="vi", help="Language code (default: vi)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="medium",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model to use (default: medium)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_results"),
        help="Output directory for results (default: test_results)",
    )

    args = parser.parse_args()

    print_header("SMAP STT Pipeline Test")
    print_info(f"Audio file: {args.audio_file}")
    print_info(f"Language: {args.language}")
    print_info(f"Model: {args.model}")
    print_info(f"Output directory: {args.output_dir}")

    # Step 1: Upload audio
    print_header("Step 1: Upload Audio")
    upload_result = await upload_audio(
        file_path=args.audio_file, language=args.language, model=args.model
    )

    if not upload_result:
        print_error("Upload failed. Exiting.")
        sys.exit(1)

    job_id = upload_result["job_id"]

    # Step 2: Poll until complete
    print_header("Step 2: Wait for Processing")
    success = await poll_until_complete(job_id)

    if not success:
        print_error("Job did not complete successfully. Exiting.")
        sys.exit(1)

    # Step 3: Get results
    print_header("Step 3: Retrieve Results")
    result_data = await get_job_result(job_id)

    if not result_data:
        print_error("Failed to retrieve results. Exiting.")
        sys.exit(1)

    # Display results
    print_header("Transcription Result")
    transcription = result_data.get("transcription", "")
    print(f"\n{Colors.CYAN}{transcription}{Colors.ENDC}\n")

    # Display metadata
    print_header("Job Metadata")
    print_info(f"Job ID: {result_data.get('job_id')}")
    print_info(f"Status: {result_data.get('status')}")
    print_info(f"Filename: {result_data.get('filename')}")
    print_info(f"Language: {result_data.get('language')}")
    print_info(f"Duration: {result_data.get('duration_seconds', 0):.2f}s")
    print_info(f"Processing time: {result_data.get('processing_time_seconds', 0):.2f}s")

    # Save results
    print_header("Step 4: Save Results")
    await save_results(job_id, result_data, args.output_dir)

    print_header("Test Completed Successfully!")
    print_success("All steps completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
