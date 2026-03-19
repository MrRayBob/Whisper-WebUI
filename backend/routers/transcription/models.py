from pydantic import BaseModel, Field, field_validator
from typing import List


class TranscriptionOutputParams(BaseModel):
    file_format: str = Field(default="SRT", description="Subtitle file format to generate.")
    add_timestamp: bool = Field(default=False, description="Whether to append a timestamp to the output filename.")

    @field_validator("file_format")
    def validate_file_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            "srt": "srt",
            "webvtt": "vtt",
            "vtt": "vtt",
            "txt": "txt",
            "lrc": "lrc",
        }
        if normalized not in allowed:
            raise ValueError("Supported formats are SRT, WebVTT, txt, and LRC")
        return allowed[normalized]


class TranscriptionDownloadArtifact(BaseModel):
    hash: str = Field(..., description="Content hash of the generated subtitle file.")
    filename: str = Field(..., description="Filename of the generated subtitle file.")
    file_format: str = Field(..., description="Normalized output format of the generated subtitle file.")


class TranscriptionResult(BaseModel):
    segments: List[dict] = Field(..., description="Transcription segments returned by the pipeline.")
    output: TranscriptionDownloadArtifact = Field(..., description="Generated subtitle artifact metadata.")
