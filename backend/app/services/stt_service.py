import whisper
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=device)

def transcribe_audio(path: str):
    return model.transcribe(path, condition_on_previous_text=False)
