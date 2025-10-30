## 1. Whisper.cpp (Cơ Chế)

**Whisper.cpp** là **cơ chế thực thi** (_execution engine_) hay **phần mềm/chương trình** (_program_) được viết bằng **C/C++**.

**Vai trò:**  
- Chứa logic và mã nguồn để chạy mô hình AI Whisper một cách **nhanh chóng** và **hiệu quả** trên CPU (thường có các phiên bản tối ưu hóa).
- Xử lý việc **nạp (load)** tệp model, nhận **đầu vào (input)** là âm thanh và xuất ra **đầu ra (output)** là văn bản.
- Có thể so sánh với **khung xe và động cơ** của một chiếc ô tô: khung xe có thể chạy nhưng cần “nhiên liệu” và “bản đồ” để vận hành đúng.

**Tóm lại:**  
> *Whisper.cpp là bộ công cụ giúp bạn chạy thuật toán Whisper.*
> Whisper.cpp is the execution engine that runs the Whisper algorithm.

---

## 2. Model (Dữ Liệu Trí Tuệ)

**Model** (các tệp `.bin` hoặc `.ggml`) là **dữ liệu đã được huấn luyện** (_trained data_) chứa “trí tuệ” của AI.

**Vai trò:**  
- Chứa các **trọng số** (_weights_) và **tham số** (_parameters_) đã được học từ hàng triệu giờ dữ liệu âm thanh & văn bản.
- Đây là phần **thực sự hiểu** cách chuyển sóng âm thành các từ ngữ có nghĩa.  
- **Model** càng lớn (ví dụ: `large-v3`) thì càng “thông minh”, kết quả nhận dạng càng **chính xác** hơn.
- Có thể ví như **bản đồ** (hiểu cấu trúc ngôn ngữ) và **kinh nghiệm lái xe** (trọng số) của chiếc ô tô.

**Tóm lại:**  
> *Model là “bộ não”, là nơi chứa mọi kiến thức để thực hiện việc chuyển giọng nói thành văn bản.*
> The model is the "brain" that holds learned weights to convert speech into text.

## 3. Model Download and Portable Bundle (English)

Phần dưới đây (tiếng Anh) hướng dẫn cách đóng gói và chạy `whisper-cli` cùng các model `ggml` như một bundle có thể sao chép sang dự án/máy khác.

This bundle packages the `whisper-cli` executable together with selected `ggml` models into a self-contained folder you can copy to another project or machine (same OS/arch) and run immediately.

### What it creates
- `whisper/bin/whisper-cli`
- `whisper/models/ggml-<model>.bin` (default: `medium`)
- `whisper/samples/jfk.wav`
- `whisper/run_whisper.sh`

### Build and package
From the repository root:

```bash
scripts/setup_whisper.sh
# or specify models and output dir
scripts/setup_whisper.sh --models "medium small.en" --out ./dist/whisper
```

Requirements:
- CMake toolchain available
- macOS or Linux environment compatible with your target

The script will:
1) Build `whisper-cli` in `./build/bin` (Release)
2) Download requested models into `./models`
3) Assemble a `whisper/` folder ready to copy

### Run

Quick test:

```bash
whisper/run_whisper.sh -f whisper/samples/jfk.wav
```

Use a specific model or pass extra arguments to `whisper-cli`:

```bash
whisper/run_whisper.sh -m ggml-medium.bin -f /path/to/audio.wav --print-colors
```

Notes:
- Audio should be 16-bit PCM WAV mono at 16kHz for best results. Convert with:

```bash
ffmpeg -i input.mp3 -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

### Copy to another source/project

You can copy the entire `whisper/` folder into another repository and invoke `run_whisper.sh` from there. No re-build is needed as long as the target environment is compatible with the built binary (same OS/architecture and compatible system libs/frameworks).


