## 1. Specification
- [ ] 1.1 Draft `stt-api` capability delta covering swagger hosting + transcription API contract.
- [ ] 1.2 Validate change with `openspec validate add-stt-swagger-transcribe --strict`.

## 2. Implementation
- [ ] 2.1 Add swagger UI routing so `/swagger/index.html` serves FastAPI docs and assets.
- [ ] 2.2 Implement POST `/transcribe` request models, API key auth, and response schema.
- [ ] 2.3 Stream media download via presigned URL, optional ffmpeg demux/resample, and whisper inference with timeout.
- [ ] 2.4 Return structured payload (`status`, `transcription`, `duration`, `confidence`, `processing_time`) and ensure temp files cleaned.
- [ ] 2.5 Add unit/integration tests covering success, invalid auth, invalid URL, inference timeout.

## 3. Verification
- [ ] 3.1 Run full test suite.
- [ ] 3.2 Update docs/README with swagger path + API usage.

