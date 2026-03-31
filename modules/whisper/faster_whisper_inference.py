import gc
import os
import time
import huggingface_hub
import numpy as np
import torch
from typing import BinaryIO, Union, Tuple, List, Callable, Optional
import faster_whisper
from faster_whisper.vad import VadOptions
import ast
import ctranslate2
import whisper
import gradio as gr
from argparse import Namespace

from modules.utils.paths import (FASTER_WHISPER_MODELS_DIR, DIARIZATION_MODELS_DIR, UVR_MODELS_DIR, OUTPUT_DIR)
from modules.whisper.data_classes import *
from modules.whisper.base_transcription_pipeline import BaseTranscriptionPipeline
from modules.utils.logger import get_logger


logger = get_logger()


class FasterWhisperInference(BaseTranscriptionPipeline):
    CUDA_OOM_PATTERNS = (
        "cuda out of memory",
        "out of memory",
        "cuda failed with error out of memory",
        "cuda failed with error 2",
        "cublas_status_alloc_failed",
        "cudnn_status_alloc_failed",
        "cuda_error_out_of_memory",
        "cuda driver error 2",
        "not enough memory",
        "failed to allocate memory",
    )
    CPU_FALLBACK_MESSAGE = "Whisper retried on CPU because GPU memory was full."

    def __init__(self,
                 model_dir: str = FASTER_WHISPER_MODELS_DIR,
                 diarization_model_dir: str = DIARIZATION_MODELS_DIR,
                 uvr_model_dir: str = UVR_MODELS_DIR,
                 output_dir: str = OUTPUT_DIR,
                 ):
        super().__init__(
            model_dir=model_dir,
            diarization_model_dir=diarization_model_dir,
            uvr_model_dir=uvr_model_dir,
            output_dir=output_dir
        )
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

        self.model_paths = self.get_model_paths()
        self.preferred_device = self.device
        self.loaded_device = None
        self.available_models = self.model_paths.keys()

    def transcribe(self,
                   audio: Union[str, BinaryIO, np.ndarray],
                   progress: gr.Progress = gr.Progress(),
                   progress_callback: Optional[Callable] = None,
                   *whisper_params,
                   ) -> Tuple[List[Segment], float]:
        segments_result, elapsed_time, _ = self.transcribe_with_runtime(
            audio,
            progress,
            progress_callback,
            *whisper_params,
        )
        return segments_result, elapsed_time

    def transcribe_with_runtime(self,
                                audio: Union[str, BinaryIO, np.ndarray],
                                progress: gr.Progress = gr.Progress(),
                                progress_callback: Optional[Callable] = None,
                                *whisper_params,
                                ) -> Tuple[List[Segment], float, WhisperRuntimeInfo]:
        """
        transcribe method for faster-whisper.

        Parameters
        ----------
        audio: Union[str, BinaryIO, np.ndarray]
            Audio path or file binary or Audio numpy array
        progress: gr.Progress
            Indicator to show progress directly in gradio.
        progress_callback: Optional[Callable]
            callback function to show progress. Can be used to update progress in the backend.
        *whisper_params: tuple
            Parameters related with whisper. This will be dealt with "WhisperParameters" data class

        Returns
        ----------
        segments_result: List[Segment]
            list of Segment that includes start, end timestamps and transcribed text
        elapsed_time: float
            elapsed time for transcription
        """
        start_time = time.time()

        params = WhisperParams.from_list(list(whisper_params))
        segments_result, runtime_info = self._run_with_device_fallback(
            model_size=params.model_size,
            compute_type=params.compute_type,
            progress=progress,
            operation=lambda device, resolved_compute_type: self._transcribe_on_device(
                audio=audio,
                params=params,
                device=device,
                compute_type=resolved_compute_type,
                progress=progress,
                progress_callback=progress_callback,
            ),
        )

        elapsed_time = time.time() - start_time
        return segments_result, elapsed_time, runtime_info

    def update_model(self,
                     model_size: str,
                     compute_type: str,
                     progress: gr.Progress = gr.Progress()
                     ):
        """
        Update current model setting

        Parameters
        ----------
        model_size: str
            Size of whisper model. If you enter the huggingface repo id, it will try to download the model
            automatically from huggingface.
        compute_type: str
            Compute type for transcription.
            see more info : https://opennmt.net/CTranslate2/quantization.html
        progress: gr.Progress
            Indicator to show progress directly in gradio.
        """
        _, runtime_info = self._run_with_device_fallback(
            model_size=model_size,
            compute_type=compute_type,
            progress=progress,
            operation=lambda device, resolved_compute_type: self._ensure_model_loaded(
                model_size=model_size,
                compute_type=resolved_compute_type,
                device=device,
                progress=progress,
            ),
        )
        return runtime_info

    def get_model_paths(self):
        """
        Get available models from models path including fine-tuned model.

        Returns
        ----------
        Name list of models
        """
        model_paths = {model:model for model in faster_whisper.available_models()}
        faster_whisper_prefix = "models--Systran--faster-whisper-"

        existing_models = os.listdir(self.model_dir)
        wrong_dirs = [".locks", "faster_whisper_models_will_be_saved_here"]
        existing_models = list(set(existing_models) - set(wrong_dirs))

        for model_name in existing_models:
            if faster_whisper_prefix in model_name:
                model_name = model_name[len(faster_whisper_prefix):]

            if model_name not in whisper.available_models():
                model_paths[model_name] = os.path.join(self.model_dir, model_name)
        return model_paths

    @staticmethod
    def get_device():
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    @staticmethod
    def format_suppress_tokens_str(suppress_tokens_str: str) -> List[int]:
        try:
            suppress_tokens = ast.literal_eval(suppress_tokens_str)
            if not isinstance(suppress_tokens, list) or not all(isinstance(item, int) for item in suppress_tokens):
                raise ValueError("Invalid Suppress Tokens. The value must be type of List[int]")
            return suppress_tokens
        except Exception as e:
            raise ValueError("Invalid Suppress Tokens. The value must be type of List[int]")

    def offload(self):
        self._release_model(clear_device=self.loaded_device or self.preferred_device)

    def get_supported_compute_types_for_device(self, device: str) -> List[str]:
        target_device = "cuda" if device == "cuda" else "cpu"
        return list(ctranslate2.get_supported_compute_types(target_device))

    def _resolve_cpu_compute_type(self, requested_compute_type: str) -> str:
        available_compute_types = self.get_supported_compute_types_for_device("cpu")
        if requested_compute_type in available_compute_types:
            return requested_compute_type
        if "float32" in available_compute_types:
            return "float32"
        return available_compute_types[0]

    def _resolve_model_artifacts(self, model_size: str) -> Tuple[str, bool]:
        model_size_dirname = model_size.replace("/", "--") if "/" in model_size else model_size
        if model_size not in self.model_paths and model_size_dirname not in self.model_paths:
            print(f"Model is not detected. Trying to download \"{model_size}\" from huggingface to "
                  f"\"{os.path.join(self.model_dir, model_size_dirname)} ...")
            huggingface_hub.snapshot_download(
                model_size,
                local_dir=os.path.join(self.model_dir, model_size_dirname),
            )
            self.model_paths = self.get_model_paths()
            gr.Info(f"Model is downloaded with the name \"{model_size_dirname}\"")

        resolved_model_path = self.model_paths[model_size_dirname]
        local_files_only = False
        hf_prefix = "models--Systran--faster-whisper-"
        official_model_path = os.path.join(self.model_dir, hf_prefix + model_size)
        if ((os.path.isdir(resolved_model_path) and os.path.exists(resolved_model_path)) or
            (model_size in faster_whisper.available_models() and os.path.exists(official_model_path))):
            local_files_only = True
        return resolved_model_path, local_files_only

    def _ensure_model_loaded(self,
                             model_size: str,
                             compute_type: str,
                             device: str,
                             progress: gr.Progress = gr.Progress()):
        resolved_model_path, local_files_only = self._resolve_model_artifacts(model_size)
        needs_reload = (
            self.model is None or
            self.current_model_size != resolved_model_path or
            self.current_compute_type != compute_type or
            self.loaded_device != device
        )
        if not needs_reload:
            return self.model

        self._release_model(clear_device=self.loaded_device or device)
        progress(0, desc="Initializing Model..")

        model = faster_whisper.WhisperModel(
            device=device,
            model_size_or_path=resolved_model_path,
            download_root=self.model_dir,
            compute_type=compute_type,
            local_files_only=local_files_only
        )

        self.model = model
        self.current_model_size = resolved_model_path
        self.current_compute_type = compute_type
        self.loaded_device = device
        return self.model

    def _transcribe_on_device(self,
                              audio: Union[str, BinaryIO, np.ndarray],
                              params: WhisperParams,
                              device: str,
                              compute_type: str,
                              progress: gr.Progress = gr.Progress(),
                              progress_callback: Optional[Callable] = None) -> List[Segment]:
        self._ensure_model_loaded(
            model_size=params.model_size,
            compute_type=compute_type,
            device=device,
            progress=progress,
        )

        segments, info = self.model.transcribe(
            audio=audio,
            language=params.lang,
            task="translate" if params.is_translate else "transcribe",
            beam_size=params.beam_size,
            log_prob_threshold=params.log_prob_threshold,
            no_speech_threshold=params.no_speech_threshold,
            best_of=params.best_of,
            patience=params.patience,
            temperature=params.temperature,
            initial_prompt=params.initial_prompt,
            compression_ratio_threshold=params.compression_ratio_threshold,
            length_penalty=params.length_penalty,
            repetition_penalty=params.repetition_penalty,
            no_repeat_ngram_size=params.no_repeat_ngram_size,
            prefix=params.prefix,
            suppress_blank=params.suppress_blank,
            suppress_tokens=params.suppress_tokens,
            max_initial_timestamp=params.max_initial_timestamp,
            word_timestamps=True,  # Set it to always True as it reduces hallucinations
            prepend_punctuations=params.prepend_punctuations,
            append_punctuations=params.append_punctuations,
            max_new_tokens=params.max_new_tokens,
            chunk_length=params.chunk_length,
            hallucination_silence_threshold=params.hallucination_silence_threshold,
            hotwords=params.hotwords,
            language_detection_threshold=params.language_detection_threshold,
            language_detection_segments=params.language_detection_segments,
            prompt_reset_on_temperature=params.prompt_reset_on_temperature,
        )
        progress(0, desc="Loading audio..")

        segments_result = []
        for segment in segments:
            progress_n = segment.start / info.duration if info.duration else 0
            progress(progress_n, desc="Transcribing..")
            if progress_callback is not None:
                progress_callback(progress_n)
            segments_result.append(Segment.from_faster_whisper(segment))
        return segments_result

    def _run_with_device_fallback(self,
                                  model_size: str,
                                  compute_type: str,
                                  progress: gr.Progress,
                                  operation: Callable[[str, str], Union[List[Segment], faster_whisper.WhisperModel]],
                                  ) -> Tuple[Union[List[Segment], faster_whisper.WhisperModel], WhisperRuntimeInfo]:
        requested_device = self.preferred_device
        requested_compute_type = compute_type
        attempts = [(requested_device, requested_compute_type, False)]
        if requested_device == "cuda":
            attempts.append(("cpu", self._resolve_cpu_compute_type(requested_compute_type), True))

        last_exception = None
        for attempt_index, (device, resolved_compute_type, is_fallback) in enumerate(attempts):
            try:
                result = operation(device, resolved_compute_type)
                runtime_info = WhisperRuntimeInfo(
                    requested_device=requested_device,
                    requested_compute_type=requested_compute_type,
                    actual_device=device,
                    actual_compute_type=resolved_compute_type,
                    fell_back=is_fallback,
                    fallback_reason=str(last_exception) if is_fallback and last_exception is not None else None,
                    fallback_message=self.CPU_FALLBACK_MESSAGE if is_fallback else None,
                )
                return result, runtime_info
            except Exception as exc:
                last_exception = exc
                should_retry_on_cpu = (
                    device == "cuda" and
                    attempt_index < len(attempts) - 1 and
                    self._is_cuda_oom_error(exc)
                )
                if not should_retry_on_cpu:
                    raise
                logger.warning(
                    "Whisper ran out of CUDA memory while using compute type %s. Retrying on CPU. Error: %s",
                    requested_compute_type,
                    exc,
                )
                self._release_model(clear_device=device)

        raise last_exception

    def _release_model(self, clear_device: Optional[str] = None):
        if self.model is not None:
            del self.model
            self.model = None

        device_to_clear = clear_device or self.loaded_device
        if device_to_clear == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_max_memory_allocated()

        self.loaded_device = None
        gc.collect()

    @classmethod
    def _is_cuda_oom_error(cls, exc: Exception) -> bool:
        if isinstance(exc, torch.cuda.OutOfMemoryError):
            return True

        error_text = str(exc).lower()
        if any(pattern in error_text for pattern in cls.CUDA_OOM_PATTERNS):
            return True

        mentions_cuda_stack = any(token in error_text for token in ("cuda", "cublas", "cudnn"))
        mentions_memory_failure = any(token in error_text for token in ("out of memory", "not enough memory", "alloc_failed", "failed to allocate"))
        return mentions_cuda_stack and mentions_memory_failure
