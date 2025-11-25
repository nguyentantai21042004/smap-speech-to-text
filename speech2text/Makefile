.PHONY: help install dev-install run-api run-queue run-scheduler setup-models setup-model setup-model-tiny setup-model-base setup-model-small setup-model-medium setup-model-large setup-whisper setup-whisper-custom docker-build docker-up docker-down docker-logs clean test format lint upgrade

# ==============================================================================
# HELPERS
# ==============================================================================
help:
	@echo "Available commands (Managed by uv):"
	@echo "  make install            - Install dependencies (Sync environment)"
	@echo "  make dev-install        - Install all dependencies including dev tools"
	@echo "  make upgrade            - Upgrade all packages in lock file"
	@echo "  make run-api            - Run API service"
	@echo "  make run-consumer       - Run Consumer service"
	@echo "  make setup-models       - Download all Whisper models from MinIO"
	@echo "  make setup-model-medium - Download specific model (tiny/base/small/medium/large)"
	@echo "  make setup-whisper      - Build whisper.cpp binary from source"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start all services"
	@echo "  make docker-down        - Stop all services"
	@echo "  make test               - Run tests"
	@echo "  make format             - Format code (black)"
	@echo "  make lint               - Lint code (flake8)"
	@echo "  make clean              - Clean up compiled files and caches"

# ==============================================================================
# DEPENDENCY MANAGEMENT (UV)
# ==============================================================================
# Cài đặt môi trường (mặc định uv sync cài cả dev deps, thêm --no-dev nếu chỉ muốn prod)
install:
	uv sync

# Nếu bạn chia group dev trong pyproject.toml, uv sync mặc định đã cài dev. 
# Target này giữ lại để tương thích thói quen cũ.
dev-install:
	uv sync

# Cập nhật các gói lên phiên bản mới nhất
upgrade:
	uv lock --upgrade

# Thêm thư viện mới (Ví dụ: make add pkg=requests)
add:
	uv add $(pkg)

# ==============================================================================
# RUN SERVICES
# ==============================================================================
# "uv run" tự động load .venv và environment, không cần trỏ đường dẫn python thủ công
# PYTHONPATH=. vẫn giữ để đảm bảo import các module gốc hoạt động đúng
run-api:
	PYTHONPATH=. uv run cmd/api/main.py

run-api-refactored:
	PYTHONPATH=. uv run cmd/api/main.py

run-consumer:
	PYTHONPATH=. uv run cmd/consumer/main.py

# ==============================================================================
# WHISPER SETUP
# ==============================================================================
# Download Whisper models from MinIO (for local development)
# Requires MinIO connection configured in .env
setup-models:
	@echo "Downloading Whisper models from MinIO..."
	PYTHONPATH=. uv run scripts/setup_models.py

# Download specific model (e.g., make setup-model MODEL=medium)
setup-model:
	@echo "Downloading model: $(MODEL)..."
	PYTHONPATH=. uv run scripts/setup_models.py $(MODEL)

# Quick shortcuts for common models
setup-model-tiny:
	@echo "Downloading tiny model..."
	PYTHONPATH=. uv run scripts/setup_models.py tiny

setup-model-base:
	@echo "Downloading base model..."
	PYTHONPATH=. uv run scripts/setup_models.py base

setup-model-small:
	@echo "Downloading small model..."
	PYTHONPATH=. uv run scripts/setup_models.py small

setup-model-medium:
	@echo "Downloading medium model..."
	PYTHONPATH=. uv run scripts/setup_models.py medium

setup-model-large:
	@echo "Downloading large model..."
	PYTHONPATH=. uv run scripts/setup_models.py large

# Build whisper.cpp binary from source (for local development)
# Requires: cmake, make, and whisper.cpp repo cloned
setup-whisper:
	@echo "Building whisper.cpp binary..."
	bash scripts/setup_whisper.sh

# Build whisper.cpp with specific models
setup-whisper-custom:
	@echo "Building whisper.cpp with models: $(MODELS)..."
	bash scripts/setup_whisper.sh --models "$(MODELS)"

# ==============================================================================
# DOCKER OPERATIONS
# ==============================================================================
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

docker-clean:
	docker-compose down -v

# ==============================================================================
# CODE QUALITY & TESTING
# ==============================================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	# Dọn dẹp cache của uv (tuỳ chọn)
	uv clean

test:
	uv run pytest -v

format:
	uv run black core/ repositories/ services/ cmd/

lint:
	uv run flake8 core/ repositories/ services/ cmd/ --max-line-length=100

# ==============================================================================
# LOGS & SCALING
# ==============================================================================
scale-queue:
	docker-compose up -d --scale queue=3

logs-api:
	docker-compose logs -f api

logs-queue:
	docker-compose logs -f queue

logs-mongodb:
	docker-compose logs -f mongodb

logs-rabbitmq:
	docker-compose logs -f rabbitmq