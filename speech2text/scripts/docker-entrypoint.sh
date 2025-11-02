#!/bin/bash
set -euo pipefail

# ============================================
# Docker Entrypoint for SMAP Speech-to-Text
# ============================================
# This script runs before the main application starts
# It ensures Whisper models are downloaded from MinIO private storage if not present

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# Validate required environment variables for MinIO connection
validate_minio_config() {
    local missing_vars=()
    
    if [ -z "${MINIO_ENDPOINT:-}" ]; then
        missing_vars+=("MINIO_ENDPOINT")
    fi
    
    if [ -z "${MINIO_ACCESS_KEY:-}" ]; then
        missing_vars+=("MINIO_ACCESS_KEY")
    fi
    
    if [ -z "${MINIO_SECRET_KEY:-}" ]; then
        missing_vars+=("MINIO_SECRET_KEY")
    fi
    
    if [ -z "${MINIO_BUCKET_MODEL:-}" ]; then
        missing_vars+=("MINIO_BUCKET_MODEL")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required MinIO environment variables:"
        printf '%s\n' "${missing_vars[@]}" | sed 's/^/  - /'
        return 1
    fi
    
    return 0
}

# Validate model name
validate_model_name() {
    local model=$1
    local valid_models=("tiny" "base" "small" "medium" "large")
    
    for valid_model in "${valid_models[@]}"; do
        if [ "$model" = "$valid_model" ]; then
            return 0
        fi
    done
    
    log_error "Invalid model name: '$model'"
    log_info "Valid models: ${valid_models[*]}"
    return 1
}

# Check if setup script exists and is executable
check_setup_script() {
    if [ ! -f "/app/scripts/setup_models.py" ]; then
        log_warning "setup_models.py not found at /app/scripts/setup_models.py"
        return 1
    fi
    
    if [ ! -x "/app/scripts/setup_models.py" ]; then
        log_warning "setup_models.py is not executable, making it executable..."
        chmod +x /app/scripts/setup_models.py || {
            log_error "Failed to make setup_models.py executable"
            return 1
        }
    fi
    
    return 0
}

# Main entrypoint
main() {
    echo "================================================"
    echo "SMAP Speech-to-Text - Docker Entrypoint"
    echo "================================================"
    echo ""
    
    # Check if model download should be skipped
    if [ "${SKIP_MODEL_DOWNLOAD:-false}" = "true" ]; then
        log_info "Skipping model download (SKIP_MODEL_DOWNLOAD=true)"
    else
        log_info "Preparing Whisper models..."
        
        # Validate MinIO configuration
        if ! validate_minio_config; then
            log_error "MinIO configuration is incomplete"
            log_info "Set SKIP_MODEL_DOWNLOAD=true to skip model download"
            exit 1
        fi
        
        # Ensure models directory exists with correct permissions
        local models_dir="/app/whisper/models"
        mkdir -p "$models_dir" || {
            log_error "Failed to create models directory: $models_dir"
            exit 1
        }
        
        # Set proper permissions (readable/writable by app user)
        chmod 755 "$models_dir" || {
            log_warning "Failed to set permissions on models directory"
        }
        
        # Check setup script
        if ! check_setup_script; then
            log_warning "Cannot download models without setup script"
        else
            # Determine which model to download
            local model="${MODEL_TO_DOWNLOAD:-${DEFAULT_WHISPER_MODEL:-medium}}"
            
            # Validate model name
            if ! validate_model_name "$model"; then
                log_error "Invalid model specified"
                exit 1
            fi
            
            log_info "Downloading model: $model"
            log_info "MinIO Endpoint: ${MINIO_ENDPOINT}"
            log_info "MinIO Bucket: ${MINIO_BUCKET_MODEL}"
            log_info "MinIO Path: models/ggml-$model.bin"
            
            # Download model from MinIO
            if python /app/scripts/setup_models.py "$model"; then
                log_success "Model '$model' downloaded and validated successfully"
            else
                log_error "Failed to download model '$model' from MinIO"
                echo ""
                log_info "Troubleshooting:"
                echo "  1. Verify MinIO is running and accessible"
                echo "  2. Check network connectivity to: ${MINIO_ENDPOINT}"
                echo "  3. Verify credentials (MINIO_ACCESS_KEY, MINIO_SECRET_KEY)"
                echo "  4. Ensure model exists in bucket '${MINIO_BUCKET_MODEL}' at path: models/ggml-$model.bin"
                echo "  5. Check bucket permissions for read access"
                echo ""
                log_info "To skip model download, set: SKIP_MODEL_DOWNLOAD=true"
                exit 1
            fi
        fi
    fi
    
    echo ""
    echo "================================================"
    log_success "Starting application..."
    echo "================================================"
    echo ""
    
    # Execute the main command (passed as arguments to this script)
    exec "$@"
}

# Run main function
main "$@"

