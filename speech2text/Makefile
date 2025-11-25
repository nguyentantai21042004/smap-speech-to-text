.PHONY: help install dev-install run-api run-queue run-scheduler docker-build docker-up docker-down docker-logs clean test format lint upgrade

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