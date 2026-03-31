from pytubefix import YouTube
import subprocess
import os
import tempfile

from modules.utils.paths import BACKEND_CACHE_DIR


def get_ytdata(link):
    return YouTube(link)


def get_ytmetas(link):
    yt = YouTube(link)
    return yt.thumbnail_url, yt.title, yt.description


def get_ytaudio(ytdata: YouTube):
    # Somehow the audio is corrupted so need to convert to valid audio file.
    # Fix for : https://github.com/jhj0517/Whisper-WebUI/issues/304

    temp_dir = tempfile.mkdtemp(prefix="yt_", dir=BACKEND_CACHE_DIR)
    audio_stream = ytdata.streams.get_audio_only()
    audio_path = audio_stream.download(
        output_path=temp_dir,
        filename="yt_tmp",
    )
    temp_audio_path = os.path.join(temp_dir, "yt_tmp_fixed.wav")

    try:
        subprocess.run([
            'ffmpeg', '-y',
            '-i', audio_path,
            temp_audio_path
        ], check=True)

        os.replace(temp_audio_path, audio_path)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg conversion: {e}")
        return None
