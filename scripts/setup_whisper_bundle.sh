#!/bin/bash
set -euo pipefail

###############################################################################
# Portable bundle builder for whisper.cpp
# - Builds whisper-cli (Release)
# - Downloads requested ggml models (default: medium)
# - Packages into whisper/ with a run script
#
# Usage:
#   scripts/setup_whisper.sh [--models "medium small.en"] [--out DIR]
#
# Examples:
#   scripts/setup_whisper.sh
#   scripts/setup_whisper.sh --models "medium small" --out ./dist/whisper
###############################################################################

MODELS="medium"
OUT_DIR="$(pwd)/whisper"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --models)
      MODELS="$2"
      shift 2
      ;;
    --out)
      OUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
BIN_DIR="$BUILD_DIR/bin"
WHISPER_CLI="$BIN_DIR/whisper-cli"
MODELS_DIR="$ROOT_DIR/models"

if ! command -v cmake >/dev/null 2>&1; then
  echo "Error: cmake not found on PATH." >&2
  echo "macOS quick fix:" >&2
  echo "  xcode-select --install" >&2
  echo "  brew install cmake   # if Homebrew is installed" >&2
  echo "If Homebrew is not installed: https://brew.sh" >&2
  exit 127
fi

echo "[1/4] Ensuring build (Release) ..."
if [[ ! -x "$WHISPER_CLI" ]]; then
  cmake -B "$BUILD_DIR"
  cmake --build "$BUILD_DIR" -j --config Release
fi

if [[ ! -x "$WHISPER_CLI" ]]; then
  echo "Failed to build whisper-cli" >&2
  exit 1
fi

echo "[2/4] Downloading models: $MODELS ..."
pushd "$ROOT_DIR" >/dev/null
for m in $MODELS; do
  bash ./models/download-ggml-model.sh "$m"
done
popd >/dev/null

echo "[3/4] Creating bundle at: $OUT_DIR ..."
mkdir -p "$OUT_DIR/bin" "$OUT_DIR/models" "$OUT_DIR/samples"

cp "$WHISPER_CLI" "$OUT_DIR/bin/"

for m in $MODELS; do
  # Resulting filename pattern: models/ggml-<model>.bin
  src="$MODELS_DIR/ggml-$m.bin"
  if [[ ! -f "$src" ]]; then
    echo "Expected model not found: $src" >&2
    exit 1
  fi
  cp "$src" "$OUT_DIR/models/"
done

# Include a known sample for quick testing
if [[ -f "$ROOT_DIR/samples/jfk.wav" ]]; then
  cp "$ROOT_DIR/samples/jfk.wav" "$OUT_DIR/samples/"
fi

echo "[4/4] Writing run script ..."
cat > "$OUT_DIR/run_whisper.sh" <<'RUN'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$SCRIPT_DIR/bin/whisper-cli"
MODELS_DIR="$SCRIPT_DIR/models"

MODEL_NAME="ggml-medium.bin"
INPUT_FILE=""

usage() {
  echo "Usage: $0 [-m model_filename] -f audio_file [extra whisper-cli args...]"
  echo "  Defaults: -m $MODEL_NAME"
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--model)
      MODEL_NAME="$2"
      shift 2
      ;;
    -f|--file)
      INPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
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
RUN

chmod +x "$OUT_DIR/run_whisper.sh"

echo
echo "✅ Bundle ready: $OUT_DIR"
echo "   Try:"
echo "   $OUT_DIR/run_whisper.sh -f $OUT_DIR/samples/jfk.wav"

