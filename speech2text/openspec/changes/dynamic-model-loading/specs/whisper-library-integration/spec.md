# Whisper Library Integration Spec

## ADDED Requirements

### Requirement: Shared Library Loading
The system SHALL load Whisper.cpp as shared libraries (.so files) instead of spawning subprocess for each transcription request.

#### Scenario: Load libraries at startup
**Given** the API service is starting up  
**And** Whisper artifacts are available in the configured directory  
**When** the WhisperLibraryAdapter initializes  
**Then** it SHALL load libggml-base.so.0, libggml-cpu.so.0, libggml.so.0, and libwhisper.so in correct dependency order  
**And** it SHALL initialize the Whisper context using whisper_init_from_file()  
**And** it SHALL keep the context in memory for reuse across requests

#### Scenario: Transcribe using library
**Given** the Whisper library is loaded and context is initialized  
**When** a transcription request is received  
**Then** the system SHALL call whisper_full() directly via ctypes  
**And** it SHALL NOT spawn a subprocess  
**And** it SHALL return the transcribed text from the C function

#### Scenario: Handle library load failure
**Given** the required .so files are missing or incompatible  
**When** WhisperLibraryAdapter attempts to load libraries  
**Then** it SHALL raise LibraryLoadError with details about which library failed  
**And** it SHALL log the error with LD_LIBRARY_PATH and file locations

### Requirement: Context Lifecycle Management
The system SHALL manage Whisper context lifecycle to prevent memory leaks and ensure proper cleanup.

#### Scenario: Initialize context once
**Given** the API service starts  
**When** WhisperLibraryAdapter is instantiated  
**Then** it SHALL call whisper_init_from_file() exactly once  
**And** it SHALL store the context pointer for reuse

#### Scenario: Reuse context across requests
**Given** the Whisper context is initialized  
**When** multiple transcription requests are processed  
**Then** the system SHALL reuse the same context for all requests  
**And** it SHALL NOT reinitialize the context between requests

#### Scenario: Free context on shutdown
**Given** the API service is shutting down  
**When** WhisperLibraryAdapter is destroyed  
**Then** it SHALL call whisper_free() to release the context  
**And** it SHALL prevent memory leaks

### Requirement: Library Dependency Resolution
The system SHALL correctly resolve and load library dependencies in the proper order.

#### Scenario: Load dependencies before main library
**Given** Whisper libraries have dependency chain  
**When** loading libraries  
**Then** it SHALL load libggml-base.so.0 first  
**And** it SHALL load libggml-cpu.so.0 second  
**And** it SHALL load libggml.so.0 third  
**And** it SHALL load libwhisper.so last  
**And** it SHALL use RTLD_GLOBAL for dependency libraries

#### Scenario: Set LD_LIBRARY_PATH correctly
**Given** libraries are in a non-standard location  
**When** the entrypoint script runs  
**Then** it SHALL set LD_LIBRARY_PATH to include the artifacts directory  
**And** it SHALL preserve existing LD_LIBRARY_PATH values
