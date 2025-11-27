#!/usr/bin/env python3
"""
Download Whisper artifacts from MinIO based on model size.
Usage: python scripts/download_whisper_artifacts.py [small|medium]
"""
import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.client import Config
except ImportError:
    print("Error: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)

# MinIO Configuration (from environment or defaults)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://172.16.19.115:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "smap")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "hcmut2025")
BUCKET_NAME = "whisper-artifacts"


def download_artifacts(model_size="small"):
    """Download Whisper artifacts for specified model size"""

    # Create output directory
    output_dir = Path(f"whisper_{model_size}_xeon")
    output_dir.mkdir(exist_ok=True)

    print(f"📦 Downloading Whisper {model_size.upper()} artifacts...")
    print(f"   From: {MINIO_ENDPOINT}/{BUCKET_NAME}")
    print(f"   To: {output_dir}/")
    print()

    # Create S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    # List of files to download
    prefix = f"whisper_{model_size}_xeon/"

    try:
        # List objects in bucket
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)

        if 'Contents' not in response:
            print(f"❌ No artifacts found for {model_size} model")
            return False

        # Download each file
        for obj in response['Contents']:
            key = obj['Key']
            filename = key.split('/')[-1]

            if not filename:  # Skip directory entries
                continue

            local_path = output_dir / filename
            file_size_mb = obj['Size'] / (1024 * 1024)

            print(f"⬇️  {filename} ({file_size_mb:.1f} MB)...", end=" ", flush=True)

            try:
                s3_client.download_file(BUCKET_NAME, key, str(local_path))
                print("✓")
            except ClientError as e:
                print(f"✗ Error: {e}")
                return False

        print()
        print(f"✅ Downloaded to: {output_dir}/")

        # Verify critical files exist
        required_files = [
            "libwhisper.so",
            "libggml.so.0",
            "libggml-base.so.0",
            "libggml-cpu.so.0",
            f"ggml-{model_size}-q5_1.bin"
        ]

        for file in required_files:
            if not (output_dir / file).exists():
                print(f"❌ Missing required file: {file}")
                return False

        print("✅ All required files verified")
        return True

    except ClientError as e:
        print(f"❌ Error accessing MinIO: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        model_size = sys.argv[1].lower()
    else:
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")

    if model_size not in ["small", "medium"]:
        print("Usage: python download_whisper_artifacts.py [small|medium]")
        print(f"Or set WHISPER_MODEL_SIZE environment variable")
        sys.exit(1)

    success = download_artifacts(model_size)
    sys.exit(0 if success else 1)
