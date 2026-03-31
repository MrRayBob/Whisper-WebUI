import os
import subprocess

import pytest


pytest.importorskip("pytubefix")

from modules.utils import youtube_manager


class FakeAudioStream:
    def download(self, output_path, filename):
        audio_path = os.path.join(output_path, f"{filename}.wav")
        os.makedirs(output_path, exist_ok=True)
        with open(audio_path, "wb") as file:
            file.write(b"raw-audio")
        return audio_path


class FakeStreams:
    def get_audio_only(self):
        return FakeAudioStream()


class FakeYouTube:
    streams = FakeStreams()


def test_get_ytaudio_uses_temp_directory_and_returns_valid_path(monkeypatch, tmp_path):
    monkeypatch.setattr(youtube_manager, "BACKEND_CACHE_DIR", str(tmp_path))

    def fake_run(command, check):
        output_path = command[-1]
        with open(output_path, "wb") as file:
            file.write(b"fixed-audio")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(youtube_manager.subprocess, "run", fake_run)

    audio_path = youtube_manager.get_ytaudio(FakeYouTube())

    assert audio_path is not None
    assert os.path.exists(audio_path)
    assert os.path.dirname(audio_path).startswith(str(tmp_path))
    assert os.path.basename(audio_path) == "yt_tmp.wav"
    assert not os.path.exists(os.path.join(os.path.dirname(audio_path), "yt_tmp_fixed.wav"))
