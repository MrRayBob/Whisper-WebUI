import pytest

from modules.whisper.data_classes import Segment, WhisperParams
from modules.whisper.faster_whisper_inference import FasterWhisperInference


class DummyProgress:
    def __call__(self, *_args, **_kwargs):
        return None


def build_inferencer(monkeypatch, tmp_path):
    inferencer = FasterWhisperInference.__new__(FasterWhisperInference)
    inferencer.model = None
    inferencer.model_dir = str(tmp_path)
    inferencer.output_dir = str(tmp_path)
    inferencer.model_paths = {"tiny": "tiny-model"}
    inferencer.current_model_size = None
    inferencer.current_compute_type = "float16"
    inferencer.preferred_device = "cuda"
    inferencer.device = "cuda"
    inferencer.loaded_device = None
    inferencer.available_models = inferencer.model_paths.keys()

    monkeypatch.setattr(
        inferencer,
        "get_supported_compute_types_for_device",
        lambda device: ["float16", "float32"] if device == "cuda" else ["float32", "int8"],
    )
    return inferencer


def test_update_model_falls_back_to_cpu_on_cuda_oom(monkeypatch, tmp_path):
    inferencer = build_inferencer(monkeypatch, tmp_path)
    attempts = []

    def fake_ensure_model_loaded(model_size, compute_type, device, progress):
        attempts.append((model_size, compute_type, device))
        if device == "cuda":
            raise RuntimeError("CUDA failed with error out of memory")
        inferencer.loaded_device = device
        inferencer.current_compute_type = compute_type
        inferencer.current_model_size = model_size
        inferencer.model = object()
        return inferencer.model

    monkeypatch.setattr(inferencer, "_ensure_model_loaded", fake_ensure_model_loaded)

    runtime = inferencer.update_model("tiny", "float16", DummyProgress())

    assert attempts == [
        ("tiny", "float16", "cuda"),
        ("tiny", "float32", "cpu"),
    ]
    assert runtime.fell_back is True
    assert runtime.actual_device == "cpu"
    assert runtime.actual_compute_type == "float32"


def test_transcribe_falls_back_to_cpu_on_cuda_oom(monkeypatch, tmp_path):
    inferencer = build_inferencer(monkeypatch, tmp_path)
    load_attempts = []
    transcribe_attempts = []

    def fake_ensure_model_loaded(model_size, compute_type, device, progress):
        load_attempts.append((model_size, compute_type, device))
        inferencer.loaded_device = device
        inferencer.current_compute_type = compute_type
        inferencer.current_model_size = model_size
        inferencer.model = object()
        return inferencer.model

    def fake_transcribe_on_device(audio, params, device, compute_type, progress, progress_callback):
        fake_ensure_model_loaded(params.model_size, compute_type, device, progress)
        transcribe_attempts.append((device, compute_type))
        if device == "cuda":
            raise RuntimeError("CUDA out of memory")
        return [Segment(text="cpu transcript", start=0.0, end=1.0)]

    monkeypatch.setattr(inferencer, "_ensure_model_loaded", fake_ensure_model_loaded)
    monkeypatch.setattr(inferencer, "_transcribe_on_device", fake_transcribe_on_device)

    params = WhisperParams(model_size="tiny", compute_type="float16")
    segments, _elapsed, runtime = inferencer.transcribe_with_runtime(
        "audio.wav",
        DummyProgress(),
        None,
        *params.to_list(),
    )

    assert load_attempts == [
        ("tiny", "float16", "cuda"),
        ("tiny", "float32", "cpu"),
    ]
    assert transcribe_attempts == [
        ("cuda", "float16"),
        ("cpu", "float32"),
    ]
    assert segments[0].text == "cpu transcript"
    assert runtime.fell_back is True
    assert runtime.actual_device == "cpu"


def test_transcribe_does_not_retry_non_oom_errors(monkeypatch, tmp_path):
    inferencer = build_inferencer(monkeypatch, tmp_path)
    attempts = []

    def fake_transcribe_on_device(audio, params, device, compute_type, progress, progress_callback):
        attempts.append((device, compute_type))
        raise RuntimeError("decoder exploded")

    monkeypatch.setattr(inferencer, "_transcribe_on_device", fake_transcribe_on_device)

    params = WhisperParams(model_size="tiny", compute_type="float16")
    with pytest.raises(RuntimeError, match="decoder exploded"):
        inferencer.transcribe_with_runtime(
            "audio.wav",
            DummyProgress(),
            None,
            *params.to_list(),
        )

    assert attempts == [("cuda", "float16")]


def test_next_job_retries_cuda_after_cpu_fallback(monkeypatch, tmp_path):
    inferencer = build_inferencer(monkeypatch, tmp_path)
    load_attempts = []
    job_counter = {"value": 0}

    def fake_ensure_model_loaded(model_size, compute_type, device, progress):
        load_attempts.append((job_counter["value"], model_size, compute_type, device))
        inferencer.loaded_device = device
        inferencer.current_compute_type = compute_type
        inferencer.current_model_size = model_size
        inferencer.model = object()
        return inferencer.model

    def fake_transcribe_on_device(audio, params, device, compute_type, progress, progress_callback):
        fake_ensure_model_loaded(params.model_size, compute_type, device, progress)
        if job_counter["value"] == 0 and device == "cuda":
            raise RuntimeError("CUDA failed with error out of memory")
        return [Segment(text=f"{device} transcript", start=0.0, end=1.0)]

    monkeypatch.setattr(inferencer, "_ensure_model_loaded", fake_ensure_model_loaded)
    monkeypatch.setattr(inferencer, "_transcribe_on_device", fake_transcribe_on_device)

    params = WhisperParams(model_size="tiny", compute_type="float16")
    first_segments, _first_elapsed, first_runtime = inferencer.transcribe_with_runtime(
        "audio.wav",
        DummyProgress(),
        None,
        *params.to_list(),
    )

    job_counter["value"] = 1
    second_segments, _second_elapsed, second_runtime = inferencer.transcribe_with_runtime(
        "audio.wav",
        DummyProgress(),
        None,
        *params.to_list(),
    )

    assert first_segments[0].text == "cpu transcript"
    assert first_runtime.fell_back is True
    assert second_segments[0].text == "cuda transcript"
    assert second_runtime.fell_back is False
    assert load_attempts[0] == (0, "tiny", "float16", "cuda")
    assert load_attempts[1] == (0, "tiny", "float32", "cpu")
    assert load_attempts[2] == (1, "tiny", "float16", "cuda")
