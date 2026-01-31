import subprocess
import os
from faster_whisper import WhisperModel

model = WhisperModel("base", compute_type="int8")

def convert_to_wav(input_path: str) -> str:
    os.makedirs("temp", exist_ok=True)

    wav_path = input_path.replace(".webm", ".wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        wav_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if not os.path.exists(wav_path):
        print("❌ FFmpeg failed")
        print(result.stderr)
        raise RuntimeError("FFmpeg conversion failed")

    return wav_path

def transcribe_audio(audio_path: str) -> str:
    if audio_path.endswith(".webm"):
        audio_path = convert_to_wav(audio_path)

    segments, info = model.transcribe(audio_path)
    text = " ".join(segment.text.strip() for segment in segments)
    return text
