import functools
import os
from datetime import datetime
from typing import Optional, Union

import gradio as gr
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status

from backend.common.audio import read_audio
from backend.common.compresser import get_file_hash
from backend.common.config_loader import load_server_config
from backend.common.models import QueueResponse
from backend.db.task.dao import add_task_to_db, update_task_status_in_db
from backend.db.task.models import TaskStatus, TaskType
from modules.utils.paths import BACKEND_CACHE_DIR
from modules.utils.subtitle_manager import generate_file, safe_filename
from modules.utils.youtube_manager import get_ytdata, get_ytaudio
from modules.whisper.data_classes import (
    BGMSeparationParams,
    DiarizationParams,
    Segment,
    TranscriptionPipelineParams,
    VadParams,
    WhisperParams,
)
from modules.whisper.faster_whisper_inference import FasterWhisperInference

from .models import TranscriptionDownloadArtifact, TranscriptionOutputParams, TranscriptionResult

transcription_router = APIRouter(prefix="/transcription", tags=["Transcription"])


def create_progress_callback(identifier: str):
    def progress_callback(progress_value: float):
        update_task_status_in_db(
            identifier=identifier,
            update_data={
                "uuid": identifier,
                "status": TaskStatus.IN_PROGRESS,
                "progress": round(progress_value, 2),
                "updated_at": datetime.utcnow(),
            },
        )

    return progress_callback


@functools.lru_cache
def get_pipeline() -> FasterWhisperInference:
    config = load_server_config()["whisper"]
    inferencer = FasterWhisperInference(
        output_dir=BACKEND_CACHE_DIR
    )
    inferencer.update_model(
        model_size=config["model_size"],
        compute_type=config["compute_type"]
    )
    return inferencer


def build_task_params(
    params: TranscriptionPipelineParams,
    output_params: TranscriptionOutputParams,
) -> dict:
    return {
        **params.to_dict(),
        "output": output_params.model_dump(),
    }


def get_run_output_format(output_params: TranscriptionOutputParams) -> str:
    if output_params.file_format == "vtt":
        return "WebVTT"
    return output_params.file_format.upper()


def build_transcription_result(
    *,
    segments: list[Segment],
    output_name: str,
    params: TranscriptionPipelineParams,
    output_params: TranscriptionOutputParams,
) -> TranscriptionResult:
    writer_options = {
        "highlight_words": True if params.whisper.word_timestamps else False,
    }
    _, file_path = generate_file(
        output_dir=BACKEND_CACHE_DIR,
        output_file_name=output_name,
        output_format=output_params.file_format,
        result=segments,
        add_timestamp=output_params.add_timestamp,
        **writer_options,
    )
    artifact = TranscriptionDownloadArtifact(
        hash=get_file_hash(file_path),
        filename=os.path.basename(file_path),
        file_format=output_params.file_format,
    )
    return TranscriptionResult(
        segments=[segment.model_dump() for segment in segments],
        output=artifact,
    )


def mark_task_failed(identifier: str, exc: Exception):
    update_task_status_in_db(
        identifier=identifier,
        update_data={
            "uuid": identifier,
            "status": TaskStatus.FAILED,
            "error": str(exc),
            "updated_at": datetime.utcnow(),
        },
    )


def cleanup_temp_file(file_path: Optional[str]):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def run_transcription_job(
    *,
    audio: Union[np.ndarray, str],
    params: TranscriptionPipelineParams,
    output_params: TranscriptionOutputParams,
    identifier: str,
    output_name: str,
    cleanup_path: Optional[str] = None,
):
    update_task_status_in_db(
        identifier=identifier,
        update_data={
            "uuid": identifier,
            "status": TaskStatus.IN_PROGRESS,
            "updated_at": datetime.utcnow(),
        },
    )

    try:
        progress_callback = create_progress_callback(identifier)
        segments, elapsed_time = get_pipeline().run(
            audio,
            gr.Progress(),
            get_run_output_format(output_params),
            output_params.add_timestamp,
            progress_callback,
            *params.to_list(),
        )
        result = build_transcription_result(
            segments=segments,
            output_name=output_name,
            params=params,
            output_params=output_params,
        )
        update_task_status_in_db(
            identifier=identifier,
            update_data={
                "uuid": identifier,
                "status": TaskStatus.COMPLETED,
                "result": result.model_dump(),
                "updated_at": datetime.utcnow(),
                "duration": elapsed_time,
                "progress": 1.0,
            },
        )
        return result
    except Exception as exc:
        mark_task_failed(identifier, exc)
        raise
    finally:
        cleanup_temp_file(cleanup_path)


def run_youtube_transcription(
    *,
    url: str,
    params: TranscriptionPipelineParams,
    output_params: TranscriptionOutputParams,
    identifier: str,
):
    try:
        yt = get_ytdata(url)
        audio_path = get_ytaudio(yt)
        if not audio_path:
            raise RuntimeError("Could not download audio from the YouTube URL")
        output_name = safe_filename(getattr(yt, "title", "youtube"))
        return run_transcription_job(
            audio=audio_path,
            params=params,
            output_params=output_params,
            identifier=identifier,
            output_name=output_name,
            cleanup_path=audio_path,
        )
    except Exception as exc:
        mark_task_failed(identifier, exc)
        raise


def enqueue_transcription_job(
    *,
    background_tasks: BackgroundTasks,
    params: TranscriptionPipelineParams,
    output_params: TranscriptionOutputParams,
    output_name: str,
    file_name: Optional[str],
    audio_duration: Optional[float],
    url: Optional[str] = None,
    job_fn,
    job_kwargs: dict,
    message: str = "Transcription task has queued",
) -> QueueResponse:
    identifier = add_task_to_db(
        status=TaskStatus.QUEUED,
        file_name=file_name,
        url=url,
        audio_duration=audio_duration,
        language=params.whisper.lang,
        task_type=TaskType.TRANSCRIPTION,
        task_params=build_task_params(params, output_params),
    )

    background_tasks.add_task(
        job_fn,
        identifier=identifier,
        **job_kwargs,
    )
    return QueueResponse(identifier=identifier, status=TaskStatus.QUEUED, message=message)


@transcription_router.post(
    "/",
    response_model=QueueResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@transcription_router.post(
    "/file",
    response_model=QueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transcribe Uploaded Audio",
    description="Queue transcription for an uploaded audio or video file.",
)
async def transcription_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio or video file to transcribe."),
    output_params: TranscriptionOutputParams = Depends(),
    whisper_params: WhisperParams = Depends(),
    vad_params: VadParams = Depends(),
    bgm_separation_params: BGMSeparationParams = Depends(),
    diarization_params: DiarizationParams = Depends(),
) -> QueueResponse:
    audio, info = await read_audio(file=file)
    params = TranscriptionPipelineParams(
        whisper=whisper_params,
        vad=vad_params,
        bgm_separation=bgm_separation_params,
        diarization=diarization_params,
    )
    output_name = safe_filename(os.path.splitext(file.filename)[0] if file.filename else "transcription")
    return enqueue_transcription_job(
        background_tasks=background_tasks,
        params=params,
        output_params=output_params,
        output_name=output_name,
        file_name=file.filename,
        audio_duration=info.duration if info else None,
        job_fn=run_transcription_job,
        job_kwargs={
            "audio": audio,
            "params": params,
            "output_params": output_params,
            "output_name": output_name,
        },
    )


@transcription_router.post(
    "/mic",
    response_model=QueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transcribe Microphone Recording",
    description="Queue transcription for microphone audio uploaded by the browser.",
)
async def transcription_mic(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Recorded microphone audio to transcribe."),
    output_params: TranscriptionOutputParams = Depends(),
    whisper_params: WhisperParams = Depends(),
    vad_params: VadParams = Depends(),
    bgm_separation_params: BGMSeparationParams = Depends(),
    diarization_params: DiarizationParams = Depends(),
) -> QueueResponse:
    audio, info = await read_audio(file=file)
    params = TranscriptionPipelineParams(
        whisper=whisper_params,
        vad=vad_params,
        bgm_separation=bgm_separation_params,
        diarization=diarization_params,
    )
    output_name = safe_filename(os.path.splitext(file.filename)[0] if file.filename else "mic")
    return enqueue_transcription_job(
        background_tasks=background_tasks,
        params=params,
        output_params=output_params,
        output_name=output_name,
        file_name=file.filename or "mic-recording",
        audio_duration=info.duration if info else None,
        job_fn=run_transcription_job,
        job_kwargs={
            "audio": audio,
            "params": params,
            "output_params": output_params,
            "output_name": output_name,
        },
        message="Microphone transcription task has queued",
    )


@transcription_router.post(
    "/youtube",
    response_model=QueueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transcribe YouTube Audio",
    description="Queue transcription for audio fetched from a YouTube URL.",
)
async def transcription_youtube(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube URL to transcribe."),
    output_params: TranscriptionOutputParams = Depends(),
    whisper_params: WhisperParams = Depends(),
    vad_params: VadParams = Depends(),
    bgm_separation_params: BGMSeparationParams = Depends(),
    diarization_params: DiarizationParams = Depends(),
) -> QueueResponse:
    params = TranscriptionPipelineParams(
        whisper=whisper_params,
        vad=vad_params,
        bgm_separation=bgm_separation_params,
        diarization=diarization_params,
    )
    return enqueue_transcription_job(
        background_tasks=background_tasks,
        params=params,
        output_params=output_params,
        output_name="youtube",
        file_name=None,
        audio_duration=None,
        url=url,
        job_fn=run_youtube_transcription,
        job_kwargs={
            "url": url,
            "params": params,
            "output_params": output_params,
        },
        message="YouTube transcription task has queued",
    )
