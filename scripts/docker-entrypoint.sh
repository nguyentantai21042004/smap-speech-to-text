#!/bin/bash
set -e

# ============================================
# Docker Entrypoint for SMAP Speech-to-Text
# ============================================
# This script runs before the main application starts
# It ensures Whisper models are downloaded from MinIO private storage if not present

echo "================================================"
echo "SMAP Speech-to-Text - Docker Entrypoint"
echo "================================================"

# Check if SKIP_MODEL_DOWNLOAD is set
if [ "${SKIP_MODEL_DOWNLOAD}" = "true" ]; then
    echo "⏭️  Skipping model download (SKIP_MODEL_DOWNLOAD=true)"
else
    echo "🔍 Checking Whisper models..."
    
    # Ensure models directory exists
    mkdir -p /app/whisper/models
    
    # Run model setup script to download from MinIO
    if [ -f "/app/scripts/setup_models.py" ]; then
        # Download only required models (save space and time)
        # Default to 'medium' model if MODEL_TO_DOWNLOAD not set
        MODEL=${MODEL_TO_DOWNLOAD:-${DEFAULT_WHISPER_MODEL:-medium}}
        
        echo "📥 Downloading model '$MODEL' from MinIO private storage..."
        echo "   MinIO Endpoint: ${MINIO_ENDPOINT:-<not set>}"
        echo "   MinIO Bucket: ${MINIO_BUCKET:-<not set>}"
        
        # Download model from MinIO
        python /app/scripts/setup_models.py "$MODEL" || {
            echo ""
            echo "❌ Failed to download model from MinIO!"
            echo ""
            echo "Please check:"
            echo "   1. MinIO is running and accessible at: ${MINIO_ENDPOINT:-<not set>}"
            echo "   2. Model exists in MinIO bucket '${MINIO_BUCKET:-<not set>}' at path: whisper-models/ggml-$MODEL.bin"
            echo "   3. MinIO credentials are correct (MINIO_ACCESS_KEY, MINIO_SECRET_KEY)"
            echo "   4. Network connectivity to MinIO server"
            echo ""
            echo "💡 To skip model download, set: SKIP_MODEL_DOWNLOAD=true"
            exit 1
        }
        
        echo "✅ Model '$MODEL' ready!"
    else
        echo "⚠️  setup_models.py not found, skipping model download"
    fi
fi

echo "================================================"
echo "🚀 Starting application..."
echo "================================================"
echo ""

# Execute the main command (passed as arguments to this script)
exec "$@"

