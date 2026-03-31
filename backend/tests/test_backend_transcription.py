from io import BytesIO
from types import SimpleNamespace
import math
import wave

import pytest

from backend.db.task.models import TaskStatus
from backend.tests.test_backend_config import get_client
from backend.tests.test_task_status import fetch_file_response, wait_for_task_completion
from modules.whisper.data_classes import (
    BGMSeparationParams,
    DiarizationParams,
    Segment,
    VadParams,
    WhisperParams,
    WhisperRuntimeInfo,
)


BASE_PIPELINE_PARAMS = {
    **WhisperParams(model_size="tiny", compute_type="float32").model_dump(exclude_none=True),
    **VadParams().model_dump(exclude_none=True),
    **BGMSeparationParams().model_dump(exclude_none=True),
    **DiarizationParams().model_dump(exclude_none=True),
}


def build_test_wav_bytes(duration_seconds: float = 0.25, sample_rate: int = 16000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    wav_io = BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        samples = bytearray()
        for index in range(frame_count):
            amplitude = int(8000 * math.sin(2 * math.pi * 220 * (index / sample_rate)))
            samples.extend(amplitude.to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(samples))
    return wav_io.getvalue()


class FakePipeline:
    def run(self, audio, progress, file_format, add_timestamp, progress_callback, include_runtime_info=False, *pipeline_params):
        progress_callback(0.5)
        progress(1.0, desc="Finished")
        runtime = WhisperRuntimeInfo(
            requested_device="cuda",
            requested_compute_type="float16",
            actual_device="cpu",
            actual_compute_type="float32",
            fell_back=True,
            fallback_reason="CUDA failed with error out of memory",
            fallback_message="Whisper retried on CPU because GPU memory was full.",
        )
        result = [
            Segment(
                id=0,
                start=0.0,
                end=1.0,
                text="Synthetic transcription result",
            )
        ], 0.01
        if include_runtime_info:
            return result[0], result[1], runtime
        return result


@pytest.fixture
def fake_pipeline(monkeypatch):
    import backend.routers.transcription.router as transcription_router

    monkeypatch.setattr(transcription_router, "get_pipeline", lambda: FakePipeline())


@pytest.mark.parametrize(
    ("endpoint", "filename"),
    [
        ("/transcription", "alias.wav"),
        ("/transcription/file", "file.wav"),
        ("/transcription/mic", "mic.wav"),
    ],
)
def test_transcription_upload_endpoints_queue_and_download(fake_pipeline, endpoint: str, filename: str):
    client = get_client()
    response = client.post(
        endpoint,
        files={"file": (filename, build_test_wav_bytes(), "audio/wav")},
        params={**BASE_PIPELINE_PARAMS, "file_format": "srt", "add_timestamp": False},
    )

    assert response.status_code == 201
    assert response.json()["status"] == TaskStatus.QUEUED

    identifier = response.json()["identifier"]
    completed_task = wait_for_task_completion(identifier=identifier, max_attempts=5, frequency=0.01)
    assert completed_task is not None

    result = completed_task.json()["result"]
    assert result["segments"][0]["text"] == "Synthetic transcription result"
    assert result["output"]["filename"].endswith(".srt")
    assert result["output"]["file_format"] == "srt"
    assert result["runtime"]["fell_back"] is True
    assert result["runtime"]["actual_device"] == "cpu"
    assert result["runtime"]["actual_compute_type"] == "float32"

    file_response = fetch_file_response(identifier)
    assert file_response is not None
    assert result["output"]["filename"] in file_response.headers["content-disposition"]


@pytest.mark.parametrize(
    ("file_format", "expected_extension"),
    [
        ("SRT", ".srt"),
        ("WebVTT", ".vtt"),
        ("txt", ".txt"),
        ("LRC", ".lrc"),
    ],
)
def test_transcription_output_formats(fake_pipeline, file_format: str, expected_extension: str):
    client = get_client()
    response = client.post(
        "/transcription/file",
        files={"file": ("format.wav", build_test_wav_bytes(), "audio/wav")},
        params={**BASE_PIPELINE_PARAMS, "file_format": file_format, "add_timestamp": False},
    )

    assert response.status_code == 201
    identifier = response.json()["identifier"]

    completed_task = wait_for_task_completion(identifier=identifier, max_attempts=5, frequency=0.01)
    assert completed_task is not None

    result = completed_task.json()["result"]
    assert result["output"]["filename"].endswith(expected_extension)

    file_response = fetch_file_response(identifier)
    assert file_response is not None
    assert result["output"]["filename"] in file_response.headers["content-disposition"]


def test_transcription_youtube_endpoint(fake_pipeline, monkeypatch):
    import backend.routers.transcription.router as transcription_router

    monkeypatch.setattr(transcription_router, "get_ytdata", lambda url: SimpleNamespace(title="Clip/Test"))
    monkeypatch.setattr(transcription_router, "get_ytaudio", lambda yt: "backend/tests/fake-youtube.wav")
    monkeypatch.setattr(transcription_router, "cleanup_temp_file", lambda file_path: None)

    client = get_client()
    response = client.post(
        "/transcription/youtube",
        params={**BASE_PIPELINE_PARAMS, "url": "https://example.test/watch?v=123", "file_format": "txt", "add_timestamp": False},
    )

    assert response.status_code == 201
    identifier = response.json()["identifier"]

    completed_task = wait_for_task_completion(identifier=identifier, max_attempts=5, frequency=0.01)
    assert completed_task is not None

    result = completed_task.json()["result"]
    assert result["output"]["filename"] == "Clip_Test.txt"
    assert result["segments"][0]["text"] == "Synthetic transcription result"
