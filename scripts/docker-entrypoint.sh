#!/bin/bash
set -e

# ============================================
# Docker Entrypoint for SMAP Speech-to-Text
# ============================================
# This script runs before the main application starts
# It ensures Whisper models are downloaded from MinIO if not present

echo "================================================"
echo "SMAP Speech-to-Text - Starting..."
echo "================================================"

# Check if SKIP_MODEL_DOWNLOAD is set
if [ "${SKIP_MODEL_DOWNLOAD}" = "true" ]; then
    echo " Skipping model download (SKIP_MODEL_DOWNLOAD=true)"
else
    echo "Checking Whisper models..."
    
    # Run model setup script
    if [ -f "/app/scripts/setup_models.py" ]; then
        # Download only required models (save space and time)
        # Default to 'medium' model if MODEL_TO_DOWNLOAD not set
        MODEL=${MODEL_TO_DOWNLOAD:-${DEFAULT_MODEL:-medium}}
        
        echo "📥 Downloading model: $MODEL"
        python /app/scripts/setup_models.py $MODEL || {
            echo "Failed to download model. Please check:"
            echo "   1. MinIO is running and accessible"
            echo "   2. Model exists in MinIO at 'whisper-models/ggml-$MODEL.bin'"
            echo "   3. MinIO credentials are correct"
            echo ""
            echo "💡 To skip model download, set: SKIP_MODEL_DOWNLOAD=true"
            exit 1
        }
        
        echo "Model ready!"
    else
        echo " setup_models.py not found, skipping model download"
    fi
fi

echo "================================================"
echo "🚀 Starting application..."
echo "================================================"
echo ""

# Execute the main command (passed as arguments to this script)
exec "$@"

