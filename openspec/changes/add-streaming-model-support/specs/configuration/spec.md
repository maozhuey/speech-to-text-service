# Configuration Spec Delta

## ADDED Requirements

### Requirement: Model Configuration
The configuration system SHALL support defining multiple speech recognition models with their properties.

#### Scenario: Models configuration structure
- **WHEN** configuring models in the system
- **THEN** each model SHALL be defined with: name, path, type, description, enabled flag
- **AND** the system SHALL support configuring multiple models simultaneously
- **AND** the system SHALL validate that each model has a unique name

#### Scenario: Configuration file format
- **WHEN** models are configured via environment variables or config file
- **THEN** the configuration SHALL be in a structured format (dict/tomap)
- **AND** the system SHALL parse the configuration at startup

### Requirement: Model Path Configuration
The system SHALL allow configuration of model file paths for each model.

#### Scenario: Offline model path
- **WHEN** the offline model path is configured via OFFLINE_MODEL_PATH
- **THEN** the system SHALL use that path to load the offline model
- **AND** the default value SHALL be "./models/speech_paraformer-large-v2-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"

#### Scenario: Streaming model path
- **WHEN** the streaming model path is configured via STREAMING_MODEL_PATH
- **THEN** the system SHALL use that path to load the streaming model
- **AND** the default value SHALL be "./models/paraformer-zh-streaming"

### Requirement: Default Model Configuration
The system SHALL allow configuration of the default recognition model.

#### Scenario: Configure default model
- **WHEN** the DEFAULT_MODEL environment variable is set
- **THEN** the system SHALL use that model as the default when no model parameter is provided
- **AND** the default value SHALL be "offline"

#### Scenario: Invalid default model
- **WHEN** the configured default model is not in the models configuration
- **THEN** the system SHALL log a warning at startup
- **AND** the system SHALL fall back to "offline" if available

### Requirement: Model Caching Configuration
The system SHALL allow configuration of model caching behavior.

#### Scenario: Maximum cached models
- **WHEN** MAX_CACHED_MODELS is configured
- **THEN** the system SHALL cache at most that many models simultaneously
- **AND** the default value SHALL be 2

#### Scenario: Disable model caching
- **WHEN** MAX_CACHED_MODELS is set to 1
- **THEN** the system SHALL only keep one model loaded at a time
- **AND** loading a new model SHALL cause the previous model to be unloaded

### Requirement: Model Availability Configuration
The system SHALL support enabling/disabling models without removing their configuration.

#### Scenario: Enable specific models
- **WHEN** a model has enabled: true in configuration
- **THEN** the model SHALL be available for use
- **AND** the model SHALL appear in the /api/v1/models response

#### Scenario: Disable specific models
- **WHEN** a model has enabled: false in configuration
- **THEN** the model SHALL NOT be available for use
- **AND** requesting the disabled model SHALL return an error
- **AND** the model SHALL still appear in /api/v1/models with enabled: false
