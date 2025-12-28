# WebSocket API Spec Delta

## ADDED Requirements

### Requirement: Model Selection Parameter
The WebSocket endpoint SHALL accept a `model` query parameter to specify which recognition model to use.

#### Scenario: Connect with streaming model
- **WHEN** a client connects to ws://host/ws?model=streaming
- **THEN** the server SHALL use the streaming model for recognition
- **AND** the connection SHALL be established if the streaming model is available

#### Scenario: Connect with offline model
- **WHEN** a client connects to ws://host/ws?model=offline
- **THEN** the server SHALL use the offline model for recognition
- **AND** the connection SHALL be established if the offline model is available

#### Scenario: Connect without model parameter
- **WHEN** a client connects to ws://host/ws without a model parameter
- **THEN** the server SHALL use the default model (offline)
- **AND** the connection SHALL be established

#### Scenario: Invalid model parameter
- **WHEN** a client connects with an invalid model parameter (e.g., model=invalid)
- **THEN** the server SHALL reject the connection
- **AND** the server SHALL close the WebSocket with code 4002
- **AND** the close reason SHALL contain "Invalid model: invalid"

### Requirement: Model Loading Error Handling
The WebSocket endpoint SHALL handle errors that occur during model loading.

#### Scenario: Model file not found
- **WHEN** a client requests a model and the model files are not found
- **THEN** the server SHALL close the connection with error code 4003
- **AND** the close reason SHALL contain "Failed to load model" and the model name

#### Scenario: Model load timeout
- **WHEN** model loading takes longer than 30 seconds
- **THEN** the server SHALL close the connection with error code 4003
- **AND** the system SHALL log the timeout event

#### Scenario: Insufficient memory
- **WHEN** the system cannot load the model due to insufficient memory
- **THEN** the server SHALL close the connection with error code 4003
- **AND** the system SHALL log the out-of-memory event

### Requirement: Model Information Endpoint
The API SHALL provide an endpoint to query available models.

#### Scenario: Query available models
- **WHEN** a client sends GET /api/v1/models
- **THEN** the system SHALL return JSON with success: true
- **AND** the response SHALL contain a "models" array
- **AND** each model SHALL include: name, display_name, type, description, enabled
- **AND** the response SHALL include the "default" model name

#### Scenario: Model list includes all configured models
- **WHEN** multiple models are configured in the system
- **THEN** the /api/v1/models endpoint SHALL return all configured models
- **AND** disabled models SHALL be included with enabled: false
