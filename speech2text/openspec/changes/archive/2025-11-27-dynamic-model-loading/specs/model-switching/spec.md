# Model Switching Spec

## ADDED Requirements

### Requirement: Environment-Based Model Selection
The system SHALL support dynamic model selection via environment variable without requiring code changes or Docker rebuild.

#### Scenario: Select small model via ENV
**Given** WHISPER_MODEL_SIZE environment variable is set to "small"  
**When** the API service starts  
**Then** it SHALL load artifacts from whisper_small_xeon directory  
**And** it SHALL use ggml-small-q5_1.bin model file  
**And** it SHALL allocate approximately 500MB RAM

#### Scenario: Select medium model via ENV
**Given** WHISPER_MODEL_SIZE environment variable is set to "medium"  
**When** the API service starts  
**Then** it SHALL load artifacts from whisper_medium_xeon directory  
**And** it SHALL use ggml-medium-q5_1.bin model file  
**And** it SHALL allocate approximately 2GB RAM

#### Scenario: Default to small model
**Given** WHISPER_MODEL_SIZE environment variable is not set  
**When** the API service starts  
**Then** it SHALL default to "small" model  
**And** it SHALL log the default selection

#### Scenario: Reject invalid model size
**Given** WHISPER_MODEL_SIZE is set to an invalid value (not "small" or "medium")  
**When** the API service starts  
**Then** it SHALL raise a configuration error  
**And** it SHALL log the invalid value and valid options

### Requirement: Automatic Artifact Download
The system SHALL automatically download required Whisper artifacts if not present locally.

#### Scenario: Download artifacts on first run
**Given** the selected model artifacts are not present locally  
**When** the entrypoint script runs  
**Then** it SHALL detect the missing artifacts  
**And** it SHALL call the download script with the correct model size  
**And** it SHALL wait for download to complete before starting the service

#### Scenario: Skip download if artifacts exist
**Given** the selected model artifacts are already present locally  
**When** the entrypoint script runs  
**Then** it SHALL detect existing artifacts  
**And** it SHALL skip the download step  
**And** it SHALL proceed directly to starting the service

#### Scenario: Handle download failure
**Given** artifact download fails (network error, MinIO unavailable)  
**When** the entrypoint script attempts download  
**Then** it SHALL log the error with details  
**And** it SHALL exit with non-zero status  
**And** it SHALL NOT start the service with missing artifacts

### Requirement: Unified Docker Image
The system SHALL use a single Docker image that supports both small and medium models via runtime configuration.

#### Scenario: Run same image with different models
**Given** a Docker image is built without hardcoded model  
**When** the container starts with WHISPER_MODEL_SIZE=small  
**Then** it SHALL use the small model  
**And** when the container is restarted with WHISPER_MODEL_SIZE=medium  
**Then** it SHALL use the medium model  
**And** no image rebuild SHALL be required

#### Scenario: Model switching in docker-compose
**Given** docker-compose.yml defines WHISPER_MODEL_SIZE  
**When** the environment variable is changed  
**And** the service is restarted  
**Then** it SHALL load the new model  
**And** it SHALL NOT require docker-compose build

### Requirement: Model Configuration Validation
The system SHALL validate model configuration at startup and provide clear error messages.

#### Scenario: Validate model files exist
**Given** the model size is configured  
**When** WhisperLibraryAdapter initializes  
**Then** it SHALL verify all required .so files exist  
**And** it SHALL verify the .bin model file exists  
**And** it SHALL raise ModelInitError if any files are missing

#### Scenario: Validate library compatibility
**Given** the .so files are loaded  
**When** initializing the Whisper context  
**Then** it SHALL verify whisper_init_from_file() returns a valid context  
**And** it SHALL raise ModelInitError if initialization fails  
**And** it SHALL include the model path in the error message

#### Scenario: Log model configuration
**Given** the service starts successfully  
**When** WhisperLibraryAdapter is initialized  
**Then** it SHALL log the selected model size  
**And** it SHALL log the model file path  
**And** it SHALL log the artifacts directory  
**And** it SHALL log estimated memory usage
