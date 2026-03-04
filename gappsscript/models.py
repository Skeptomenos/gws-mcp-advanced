"""Pydantic models for Apps Script tool DTOs."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScriptProject(BaseModel):
    """Normalized Apps Script project metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    script_id: str = Field(alias="scriptId")
    title: str | None = None
    create_time: str | None = Field(default=None, alias="createTime")
    update_time: str | None = Field(default=None, alias="updateTime")
    parent_id: str | None = Field(default=None, alias="parentId")


class ProcessStatus(str, Enum):
    """Supported Apps Script process statuses."""

    PROCESS_STATUS_UNSPECIFIED = "PROCESS_STATUS_UNSPECIFIED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    UNKNOWN = "UNKNOWN"
    DELAYED = "DELAYED"
    EXECUTION_DISABLED = "EXECUTION_DISABLED"


class ProcessType(str, Enum):
    """Supported Apps Script process types."""

    PROCESS_TYPE_UNSPECIFIED = "PROCESS_TYPE_UNSPECIFIED"
    ADD_ON = "ADD_ON"
    EXECUTION_API = "EXECUTION_API"
    TIME_DRIVEN = "TIME_DRIVEN"
    TRIGGER = "TRIGGER"
    WEBAPP = "WEBAPP"
    EDITOR = "EDITOR"
    SIMPLE_TRIGGER = "SIMPLE_TRIGGER"
    MENU = "MENU"
    BATCH_TASK = "BATCH_TASK"


class UserAccessLevel(str, Enum):
    """Supported Apps Script process user access levels."""

    USER_ACCESS_LEVEL_UNSPECIFIED = "USER_ACCESS_LEVEL_UNSPECIFIED"
    NONE = "NONE"
    READ = "READ"
    WRITE = "WRITE"
    OWNER = "OWNER"


class MetricsGranularity(str, Enum):
    """Supported Apps Script metrics granularities."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class ScriptProcessFilter(BaseModel):
    """Filter contract for `processes.listScriptProcesses`."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    deployment_id: str | None = Field(default=None, alias="deploymentId")
    function_name: str | None = Field(default=None, alias="functionName")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    statuses: list[ProcessStatus] | None = None
    types: list[ProcessType] | None = None
    user_access_levels: list[UserAccessLevel] | None = Field(default=None, alias="userAccessLevels")

    @field_validator("start_time", "end_time")
    @classmethod
    def _validate_rfc3339_datetime(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("must be an RFC3339 datetime string.") from exc
        return value


class UserProcessFilter(BaseModel):
    """Filter contract for `processes.list`."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    script_id: str | None = Field(default=None, alias="scriptId")
    project_name: str | None = Field(default=None, alias="projectName")
    deployment_id: str | None = Field(default=None, alias="deploymentId")
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")
    statuses: list[ProcessStatus] | None = None
    types: list[ProcessType] | None = None
    user_access_levels: list[UserAccessLevel] | None = Field(default=None, alias="userAccessLevels")

    @field_validator("start_time", "end_time")
    @classmethod
    def _validate_rfc3339_datetime(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("must be an RFC3339 datetime string.") from exc
        return value


class MetricsFilter(BaseModel):
    """Filter contract for `projects.getMetrics`."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    deployment_id: str | None = Field(default=None, alias="deploymentId")


MAX_SCRIPT_FILES = 50
MAX_SINGLE_FILE_BYTES = 250 * 1024
MAX_TOTAL_FILE_BYTES = 1024 * 1024


class ScriptFileType(str, Enum):
    """Supported Apps Script file types for source updates."""

    SERVER_JS = "SERVER_JS"
    HTML = "HTML"
    JSON = "JSON"


class ScriptFilePayload(BaseModel):
    """Single Apps Script file payload for content updates."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1)
    type: ScriptFileType
    source: str

    @field_validator("name")
    @classmethod
    def _validate_name_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("file name cannot be blank.")
        return normalized

    @field_validator("source")
    @classmethod
    def _validate_source_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_SINGLE_FILE_BYTES:
            raise ValueError(f"file source exceeds max size of {MAX_SINGLE_FILE_BYTES} bytes.")
        return value


class UpdateScriptContentPayload(BaseModel):
    """DTO for `update_script_content` payload validation."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    files: list[ScriptFilePayload] = Field(min_length=1, max_length=MAX_SCRIPT_FILES)

    @field_validator("files")
    @classmethod
    def _validate_total_size_and_manifest(cls, files: list[ScriptFilePayload]) -> list[ScriptFilePayload]:
        total_bytes = sum(len(file.source.encode("utf-8")) for file in files)
        if total_bytes > MAX_TOTAL_FILE_BYTES:
            raise ValueError(f"total files payload exceeds max size of {MAX_TOTAL_FILE_BYTES} bytes.")

        has_manifest = any(file.name == "appsscript" and file.type == ScriptFileType.JSON for file in files)
        if not has_manifest:
            raise ValueError("payload must include an appsscript manifest file (name='appsscript', type='JSON').")
        return files


class CreateScriptProjectPayload(BaseModel):
    """DTO for script project creation requests."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str = Field(min_length=1)
    parent_id: str | None = Field(default=None, alias="parentId")

    @field_validator("title")
    @classmethod
    def _validate_title_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title cannot be blank.")
        return normalized


class DeploymentMutationPayload(BaseModel):
    """Shared DTO for deployment create/update mutation inputs."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    description: str = Field(min_length=1)
    version_number: int | None = Field(default=None, alias="versionNumber")

    @field_validator("description")
    @classmethod
    def _validate_description_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("description cannot be blank.")
        return normalized

    @field_validator("version_number")
    @classmethod
    def _validate_version_number(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("versionNumber must be >= 1.")
        return value


class RunFunctionPayload(BaseModel):
    """DTO for script function execution input validation."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    function_name: str = Field(min_length=1, alias="functionName")
    parameters: list[object] | None = None
    dev_mode: bool = Field(default=False, alias="devMode")

    @field_validator("function_name")
    @classmethod
    def _validate_function_name_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("functionName cannot be blank.")
        return normalized
