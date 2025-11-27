# Speech Transcription Capability - Chunking Process Delta

## ADDED Requirements

### Requirement: Sequential Audio Chunking for Long Audio
The system SHALL support transcribing audio files longer than 30 seconds by automatically splitting them into chunks and processing sequentially.

#### Scenario: Long audio automatic chunking
- **WHEN** audio duration is greater than 30 seconds
- **THEN** the system SHALL split audio into 30-second chunks with 1-second overlap
- **AND** process each chunk sequentially
- **AND** merge results into final transcription

#### Scenario: Short audio fast path
- **WHEN** audio duration is 30 seconds or less
- **THEN** the system SHALL transcribe directly without chunking
- **AND** processing time SHALL be equivalent to current implementation

#### Scenario: Progress tracking for chunked audio
- **WHEN** processing chunked audio
- **THEN** the system SHALL log progress as "Processing chunk X/Y"
- **AND** include chunk metadata in API response

### Requirement: FFmpeg-Based Audio Splitting
The system SHALL use FFmpeg to split audio files into chunks for efficient processing.

#### Scenario: Fast audio splitting
- **WHEN** splitting audio into chunks
- **THEN** the system SHALL use FFmpeg with 16kHz mono WAV output
- **AND** splitting SHALL complete in less than 1 second for 5-minute audio

#### Scenario: Audio duration detection
- **WHEN** receiving audio file for transcription
- **THEN** the system SHALL use ffprobe to detect duration
- **AND** duration detection SHALL complete in less than 500ms

### Requirement: Smart Chunk Merging
The system SHALL merge chunk transcriptions intelligently to handle word boundaries at chunk edges.

#### Scenario: Basic chunk merging
- **WHEN** merging chunk transcriptions (MVP)
- **THEN** the system SHALL concatenate with space separators
- **AND** strip leading/trailing whitespace

#### Scenario: Overlap handling (Phase 2)
- **WHEN** chunks have overlap regions
- **THEN** the system SHALL detect duplicate words in overlap
- **AND** remove duplicates from final transcription

### Requirement: Flat Memory Usage
The system SHALL maintain constant memory usage regardless of audio length when using chunking.

#### Scenario: Memory stability for long audio
- **WHEN** transcribing 10-minute audio with chunking
- **THEN** peak memory usage SHALL NOT exceed 800MB
- **AND** memory SHALL be flat (not growing with audio length)

#### Scenario: Immediate chunk cleanup
- **WHEN** chunk transcription completes
- **THEN** the system SHALL immediately delete chunk file
- **AND** disk usage SHALL remain under 50MB during processing

### Requirement: Configurable Chunking Behavior
The system SHALL allow configuration of chunking parameters via environment variables.

#### Scenario: Chunk duration configuration
- **WHEN** `WHISPER_CHUNK_DURATION` is set
- **THEN** the system SHALL use specified duration for chunks
- **AND** default SHALL be 30 seconds if not specified

#### Scenario: Overlap configuration
- **WHEN** `WHISPER_CHUNK_OVERLAP` is set
- **THEN** the system SHALL use specified overlap duration
- **AND** default SHALL be 1 second if not specified

#### Scenario: Feature toggle
- **WHEN** `WHISPER_CHUNK_ENABLED=false`
- **THEN** the system SHALL use direct transcription for all audio
- **AND** long audio may timeout (acceptable for rollback)

### Requirement: Adaptive Transcription Timeout
The system SHALL calculate adaptive timeout based on audio duration when chunking is enabled.

#### Scenario: Adaptive timeout for chunked audio
- **WHEN** transcribing audio with chunking
- **THEN** timeout SHALL be `max(90, audio_duration * 1.5)` seconds
- **AND** individual chunks SHALL use 60-second timeout

#### Scenario: Timeout for direct transcription
- **WHEN** transcribing audio without chunking (< 30s)
- **THEN** timeout SHALL be fixed at 90 seconds
- **AND** behavior SHALL match standard fast path

### Requirement: Chunking Metadata in API Response
The system SHALL include chunking metadata in transcription responses when chunking was used (Phase 2 enhancement).

#### Scenario: Chunked transcription response
- **WHEN** transcription used chunking
- **THEN** response MAY include:
  - `chunks_processed`: number of chunks
  - `chunk_times`: array of per-chunk processing times
  - `chunking_enabled`: true
- **AND** maintain backward compatibility for existing fields

#### Scenario: Direct transcription response
- **WHEN** transcription used direct method (no chunking)
- **THEN** response SHALL NOT include chunk metadata
- **AND** format SHALL match standard transcription response

## Performance Requirements

### Requirement: Chunking Overhead Limit
Chunking overhead (splitting + merging) SHALL NOT exceed 5% of total processing time.

#### Scenario: Splitting performance
- **WHEN** splitting 5-minute audio
- **THEN** splitting SHALL complete in less than 1 second
- **AND** not impact total processing time significantly

#### Scenario: Merging performance
- **WHEN** merging 20 chunks
- **THEN** merging SHALL complete in less than 100ms
- **AND** be negligible compared to inference time

### Requirement: Quality Preservation
Transcription quality with chunking SHALL maintain at least 95% accuracy compared to direct transcription.

#### Scenario: Quality comparison for short audio
- **WHEN** comparing chunked vs direct transcription for 60s audio
- **THEN** transcription text SHALL be substantially similar
- **AND** major content SHALL match (allowing minor punctuation differences)

#### Scenario: Overlap quality improvement
- **WHEN** using 1-second overlap
- **THEN** word-level errors at boundaries SHALL be minimized
- **AND** no incomplete words in final transcription

