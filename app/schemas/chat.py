from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Message(StrictModel):
    role: Literal["system", "developer", "user", "assistant"]
    content: str
    name: str | None = None


class StreamOptions(StrictModel):
    include_usage: bool = False


class ChatRequest(StrictModel):
    model: str = Field(min_length=1, max_length=200)
    messages: list[Message] = Field(min_length=1, max_length=1000)
    stream: bool = False
    stream_options: StreamOptions | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, gt=0)
    max_completion_tokens: int | None = Field(default=None, gt=0)
    stop: str | list[str] | None = None
    seed: int | None = None
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    n: int | None = Field(default=None, ge=1, le=8)

    @model_validator(mode="after")
    def validate_stream_options(self) -> "ChatRequest":
        if self.stream_options is not None and not self.stream:
            raise ValueError("stream_options requires stream=true")
        return self
