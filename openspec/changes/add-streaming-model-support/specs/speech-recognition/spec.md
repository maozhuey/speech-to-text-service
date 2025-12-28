# Speech Recognition Spec Delta

## ADDED Requirements

### Requirement: Multiple Model Support
The system SHALL support multiple speech recognition models with different characteristics (latency, accuracy, resource usage).

#### Scenario: List available models
- **WHEN** a client requests the list of available models via GET /api/v1/models
- **THEN** the system SHALL return a list of all configured models with their names, display names, types, descriptions, and enabled status
- **AND** the response SHALL indicate which model is the default

#### Scenario: Model has required attributes
- **WHEN** a model is configured in the system
- **THEN** the model SHALL have a unique name identifier
- **AND** the model SHALL have a human-readable display name
- **AND** the model SHALL have a type (offline or streaming)
- **AND** the model SHALL have a description explaining its use case

### Requirement: Streaming Model Recognition
The system SHALL support streaming speech recognition model for low-latency real-time transcription.

#### Scenario: Streaming model provides faster response
- **WHEN** a client uses the streaming model for recognition
- **THEN** the recognition latency SHALL be less than 800ms
- **AND** the system SHALL provide partial/intermediate results as audio is being processed

#### Scenario: Streaming model accuracy
- **WHEN** a client uses the streaming model
- **THEN** the system SHALL maintain Chinese character recognition accuracy above 90%

### Requirement: Model Selection
The system SHALL allow clients to select which recognition model to use for a WebSocket connection.

#### Scenario: Client selects streaming model
- **WHEN** a client establishes a WebSocket connection with model=streaming parameter
- **THEN** the system SHALL load the streaming model if not already loaded
- **AND** all recognition requests for that connection SHALL use the streaming model

#### Scenario: Client selects offline model
- **WHEN** a client establishes a WebSocket connection with model=offline parameter
- **THEN** the system SHALL load the offline model if not already loaded
- **AND** all recognition requests for that connection SHALL use the offline model

#### Scenario: Default model when not specified
- **WHEN** a client establishes a WebSocket connection without specifying a model parameter
- **THEN** the system SHALL use the default model (offline)

#### Scenario: Invalid model name
- **WHEN** a client specifies an invalid or non-existent model name
- **THEN** the system SHALL close the WebSocket connection with error code 4002
- **AND** the reason SHALL include the text "Invalid model" and the provided model name

### Requirement: Model Lifecycle Management
The system SHALL manage model loading, caching, and unloading to balance memory usage and performance.

#### Scenario: LRU model caching
- **WHEN** the number of loaded models exceeds the maximum cache size (2)
- **THEN** the system SHALL unload the least recently used model
- **AND** the system SHALL free the associated memory resources

#### Scenario: Default model pre-loading
- **WHEN** the system starts up
- **THEN** the system SHALL pre-load the default model (offline)
- **AND** the model SHALL be available immediately for the first connection

#### Scenario: Model loading on demand
- **WHEN** a client requests a model that is not currently loaded
- **THEN** the system SHALL load the model from disk
- **AND** the system SHALL cache the model for future use
- **AND** the loading process SHALL be thread-safe

#### Scenario: Model already loaded
- **WHEN** a client requests a model that is already in the cache
- **THEN** the system SHALL use the cached model instance
- **AND** the system SHALL update the model's LRU timestamp
- **AND** the system SHALL NOT reload the model from disk

### Requirement: Model Resource Management
The system SHALL properly manage and release model resources when models are unloaded.

#### Scenario: Model memory release
- **WHEN** a model is unloaded from the cache
- **THEN** the system SHALL release all memory resources associated with the model
- **AND** the system SHALL remove any references to the model object

#### Scenario: Graceful shutdown
- **WHEN** the system shuts down
- **THEN** the system SHALL unload all loaded models
- **AND** the system SHALL release all associated resources
