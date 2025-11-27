# Stateless API

## ADDED Requirements

### Requirement: Transcribe Endpoint
The system MUST provide an HTTP endpoint to transcribe audio from a URL.

#### Scenario: Successful Transcription
Given a valid audio URL pointing to a file < 500MB
When a POST request is made to `/transcribe` with the URL
Then the system downloads the file
And transcribes it using Whisper
And returns the transcription text and duration in JSON format
And deletes the temporary file.

#### Scenario: File Too Large
Given an audio URL pointing to a file > 500MB
When a POST request is made to `/transcribe`
Then the system returns a 413 Payload Too Large error
And does not process the file.

#### Scenario: Invalid URL
Given an invalid or inaccessible audio URL
When a POST request is made to `/transcribe`
Then the system returns a 400 Bad Request error.
