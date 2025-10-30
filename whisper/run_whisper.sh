#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$SCRIPT_DIR/bin/whisper-cli"
MODELS_DIR="$SCRIPT_DIR/models"

MODEL_NAME="ggml-medium.bin"
INPUT_FILE=""j

usage() {
  echo "Usage: $0 [-m model_filename] -f audio_file [extra whisper-cli args...]"
  echo "  Defaults: -m $MODEL_NAME"
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--model)
      MODEL_NAME="$2"; shift 2 ;;
    -f|--file)
      INPUT_FILE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      ARGS+=("$1"); shift ;;
  esac
done

if [[ -z "$INPUT_FILE" ]]; then
  echo "Missing input file: use -f <audio>" >&2
  usage
  exit 1
fi

MODEL_PATH="$MODELS_DIR/$MODEL_NAME"
if [[ ! -f "$MODEL_PATH" ]]; then
  echo "Model not found: $MODEL_PATH" >&2
  echo "Available models:" >&2
  ls -lah "$MODELS_DIR" >&2 || true
  exit 1
fi

exec "$BIN" -m "$MODEL_PATH" -f "$INPUT_FILE" "${ARGS[@]}"
