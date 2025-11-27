ARCHITECTURAL PROPOSAL — DYNAMIC WHISPER MODEL LOADING

Date: 2025-11-27
Author: Architecture Senior
Status: Draft

⸻

1. Hiện trạng (Current State Assessment)

Hiện tại, STT Service đang sử dụng kiến trúc CLI Wrapper (subprocess.run() gọi whisper-cli). Đây là mô hình mang nặng tính scripting và gây ra nhiều vấn đề hiệu năng & vận hành:

1.1. Vấn đề hiệu năng — Cold Start nặng
	•	Mỗi API Request → Python tạo process mới → load lại model 181MB từ disk → inference → hủy process.
	•	Nếu có 100 request → model bị load 100 lần.
	•	Tổng độ trễ cao & không phù hợp với workloads real-time.

1.2. Vấn đề kiến trúc — Hardcode & thiếu linh hoạt
	•	Model (small/medium) được hardcode trong script hoặc Dockerfile.
	•	Muốn đổi model phải sửa code + rebuild image.
	•	Không tối ưu theo hardware (Xeon/GPU/CUDA).
	•	Parser stdout từ CLI → dễ lỗi, không robust.

1.3. Vấn đề vận hành — Static & thiếu Dynamic Control
	•	Artifacts được download static theo Option 1 (Python Script).
	•	Không có cơ chế chuyển đổi model theo ENV khi Runtime.
	•	LD_LIBRARY_PATH và thư mục .so bị cố định.

⸻

2. Kiến trúc mới (New Architecture Overview)

Bạn đã phát triển cách tiếp cận mới: Shared Library Integration (.so) + Whisper Xeon Artifacts.

Với tư cách Architecture Senior, tôi đánh giá đây là bước nhảy mang tính hệ thống, chuyển từ “Scripting” → “System Programming”, tạo nền tảng để xây dựng một Long-running, High-performance STT Service.

⸻

3. Phân tích ưu điểm của kiến trúc mới

3.1. Hiệu năng vượt trội — Load model 1 lần duy nhất

Cách cũ: CLI
	•	Model load từ disk mỗi request → tốn 1–2s/request.
	•	CPU bị tạo & hủy Process liên tục → overhead lớn.

Cách mới: Shared Library
	•	FastAPI khởi động → load .so và model .bin một lần.
	•	Tất cả request gọi hàm whisper_full() trực tiếp trên RAM.
	•	Latency giảm mạnh, phù hợp real-time, concurrent workloads.

⸻

3.2. Kiến trúc phần cứng tối ưu — CPU/GPU backend modular

Cách build hiện tại của bạn tạo ra:
	•	libggml-cpu.so.0
	•	libggml-base.so.0
	•	libwhisper.so

Cấu trúc này cho phép:
	•	Tối ưu theo AVX/AVX2/AVX512 của Xeon mà không động vào code Python.
	•	Sau này đổi sang GPU chỉ cần swap file backend (libggml-cuda.so).

⸻

3.3. Tích hợp Python chuẩn — không còn “parse text”

Cách cũ (CLI)
	•	Python parse stdout → dễ lỗi → không chuẩn.

Cách mới (Shared Library)
	•	Python gọi trực tiếp function C qua memory pointers.
	•	Nhận về string sạch + error code rõ ràng.

⸻

4. Vấn đề còn tồn tại trong kiến trúc mới (trước khi merge proposal)

Dù đã cải thiện lớn, kiến trúc mới vẫn còn 2 hạn chế chính:

4.1. Model Path & Backend Path vẫn còn static
	•	Chưa có cơ chế ENV-based switching giữa small/medium.
	•	LD_LIBRARY_PATH phải set thủ công.

4.2. Artifacts download theo Option 1 vẫn là static
	•	Nếu muốn đổi model → cần sửa code/script → restart.

Đây là lý do cần một proposal hoàn chỉnh để đưa hệ thống lên trạng thái “Dynamic & Production-ready”.

⸻

5. PROPOSAL NÂNG CẤP KIẾN TRÚC (FINAL MERGED PROPOSAL)

5.1. Mục tiêu
	•	Dynamic Model Switching:
Chuyển đổi small/medium bằng ENV tại runtime:

WHISPER_MODEL_SIZE=small | medium


	•	Dynamic Library Binding:
Khởi chạy container → auto detect model → auto load .so tương ứng.
	•	No Rebuild Required:
Cùng 1 Docker Image cho cả Dev (small) & Prod (medium).

⸻

6. Giải pháp tổng hợp

6.1. Introduce “Smart Entrypoint” Layer

Tạo file entrypoint.sh để:
	1.	Đọc biến môi trường WHISPER_MODEL_SIZE.
	2.	Gọi Python script download artifacts tương ứng nếu chưa có.
	3.	Thiết lập LD_LIBRARY_PATH đúng thư mục .so.
	4.	Khởi động ứng dụng STT.

⸻

6.2. Python Wrapper tự động hóa

WhisperTranscriber sẽ:
	•	Đọc lại ENV:

model_size = os.getenv("WHISPER_MODEL_SIZE", "small")


	•	Map file .bin đúng theo từng folder:
	•	whisper_small_xeon/ggml-small-q5_1.bin
	•	whisper_medium_xeon/ggml-medium-q5_1.bin
	•	Load dependency .so theo thứ tự chính xác.
	•	Initialize context với whisper_init_from_file().

⸻

6.3. Dockerfile unified

Không hardcode model tại build-time.
Chỉ copy scripts và kích hoạt entrypoint.sh.

⸻

7. Lợi ích sau khi triển khai

Lợi ích	Mô tả
0-rebuild switching	Chỉ đổi ENV để đổi model
Tối ưu tài nguyên	Mỗi lần chạy chỉ tải model cần thiết
Tách biệt logic - deployment	Dev/Prod xài cùng image
High performance	Model load 1 lần, inference tức thì
Portable & scalable	Dễ cluster hóa và autoscale


⸻

8. Kết luận

Kiến trúc mới (Shared Library + Dynamic Switching) là bản nâng cấp mạnh mẽ từ mô hình CLI truyền thống, chuyển hệ thống từ dạng “chạy lệnh” sang một System-level, High-performance Microservice.

Đề xuất này khi triển khai sẽ giúp:
	•	Giảm latency, tăng throughput rõ rệt.
	•	Đơn giản hóa CI/CD & vận hành.
	•	Tối ưu phần cứng theo đúng kiến trúc Xeon server.
	•	Đáp ứng tiêu chuẩn Production-grade của SMAP.
