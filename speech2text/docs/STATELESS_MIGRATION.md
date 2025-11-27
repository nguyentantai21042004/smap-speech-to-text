# PROPOSAL: TỐI ƯU HÓA STT SERVICE (STATELESS MIGRATION)

## 1\. Mục tiêu (Objectives)

  * **Decoupling (Tách rời):** Loại bỏ hoàn toàn sự phụ thuộc của STT Service vào MongoDB, RabbitMQ và MinIO Credentials.
  * **Simplification (Đơn giản hóa):** Giảm 60-70% lượng code thừa (boilerplate code) liên quan đến kết nối hạ tầng.
  * **Focus (Tập trung):** Service chỉ làm đúng 1 nhiệm vụ: Chuyển Audio từ URL thành Text.

## 2\. So sánh Kiến trúc (Architecture Shift)

| Đặc điểm | Hiện tại (Legacy) | Đề xuất (Target MVP) | Lợi ích |
| :--- | :--- | :--- | :--- |
| **Vai trò** | Stateful Worker (Consumer) | Stateless API (Utility) | Dễ scale, không lo race condition. |
| **Input** | Message từ RabbitMQ | HTTP POST Request (chứa URL) | Crawler chủ động điều phối flow. |
| **Data Fetch** | Dùng MinIO Client + Key để tải | Dùng `requests.get()` với Presigned URL | Không cần quản lý MinIO Key bảo mật. |
| **Output** | Tự ghi vào MongoDB | Trả về JSON trong HTTP Response | Đảm bảo tính Atomic cho Crawler. |
| **Config** | \~40 biến môi trường | \~10 biến môi trường | Dễ deploy, ít lỗi cấu hình. |

-----

## 3\. Kế hoạch Tinh gọn Cấu hình (`.env` Cleanup)

Đây là bước hành động cụ thể. Bạn hãy **XÓA** các biến bên trái và **GIỮ** các biến bên phải.

### 🗑️ CẦN XÓA (DEPRECATED)

  * \~\~`MONGODB_URL`, `MONGODB_DATABASE`, `MONGODB_USER`...\~\~ (STT không được chạm vào DB).
  * \~\~`RABBITMQ_HOST`, `RABBITMQ_QUEUE_NAME`...\~\~ (STT không nhận message nữa).
  * \~\~`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`...\~\~ (STT không cần quyền admin storage).
  * \~\~`CHUNK_DURATION`, `USE_PARALLEL_TRANSCRIPTION`...\~\~ (MVP chưa cần chunking phức tạp, Whisper xử lý file \<5 phút rất tốt nguyên khối).

### ✅ GIỮ LẠI & TỐI ƯU (KEEP)

```properties
# App Core
APP_NAME=smap-stt-core
ENVIRONMENT=production
LOG_LEVEL=INFO

# API Server
API_PORT=8000
API_WORKERS=1          # Giới hạn 1 worker/pod để tránh tranh chấp CPU với Model AI
MAX_UPLOAD_SIZE_MB=500 # Giới hạn cứng để bảo vệ RAM

# Whisper Engine
WHISPER_MODEL=small    # Model tối ưu cho MVP (nhanh/nhẹ)
WHISPER_LANGUAGE=vi    # Hardcode tiếng Việt để skip detect language
TEMP_DIR=/tmp/stt      # Nơi lưu file tạm khi stream về
```

-----

## 4\. Logic Code Tái cấu trúc (Code Logic Redefinition)

Logic của Service sẽ chuyển từ mô hình "Event Loop" sang mô hình "Request-Response".

### Luồng xử lý mới (New Workflow):

1.  **Endpoint:** `POST /transcribe`
2.  **Payload:** `{ "audio_url": "http://minio.../file.mp3?token=..." }`
3.  **Bước 1 - Stream:** Service dùng thư viện HTTP Client download file từ `audio_url` về thư mục `/tmp`.
      * *Lưu ý:* Nếu file \> 500MB $\rightarrow$ Trả lỗi 413 ngay.
4.  **Bước 2 - Inference:** Gọi Whisper Engine đọc file từ `/tmp` và sinh text.
5.  **Bước 3 - Cleanup:** Xóa ngay file trong `/tmp`.
6.  **Response:** Trả về `{ "text": "...", "duration": 120.5 }`.

### Cấu trúc thư mục code đề xuất (Folder Structure):

Bạn nên xóa các folder `consumers`, `db`, `repositories`. Cấu trúc mới sẽ cực phẳng.

## 5\. Chiến lược Triển khai (Deployment Strategy)

Để đảm bảo hiệu năng và cô lập lỗi theo nguyên tắc thiết kế:

  * **Docker Image:** Build một image riêng, base từ `python:3.10-slim`. Cài sẵn `ffmpeg`.
  * **Resource Limits (K8s):**
      * CPU Request: 2 core (Whisper cần tính toán ma trận).
      * RAM Request: 4GB (Model load vào RAM).
  * **Scaling:** Sử dụng HPA (Horizontal Pod Autoscaler) dựa trên **CPU Utilization**.
      * Nếu CPU \> 80% $\rightarrow$ Tự động bật thêm Pod STT mới.