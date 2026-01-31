from fastapi import WebSocket
import tempfile
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from asr.service import transcribe_audio
from gloss.translator import english_to_asl_gloss
from signs.mapper import gloss_to_signs
import shutil
import os

from asr.service import transcribe_audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend running"}

@app.post("/asr/transcribe")
async def transcribe(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = transcribe_audio(file_path)

    return {
        "text": text
    }

@app.post("/translate/gloss")
async def translate_gloss(text: str):
    gloss = english_to_asl_gloss(text)
    return {
        "gloss": gloss
    }

from fastapi import UploadFile, File
import shutil, os

@app.post("/asr/translate")
async def asr_and_translate(file: UploadFile = File(...)):
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = transcribe_audio(file_path)
    gloss = english_to_asl_gloss(text)

    return {
        "text": text,
        "gloss": gloss
    }

from pydantic import BaseModel

class GlossRequest(BaseModel):
    gloss: str

@app.post("/sign/map")
async def map_signs(request: GlossRequest):
    signs = gloss_to_signs(request.gloss)
    return {
        "gloss": request.gloss,
        "signs": signs
    }

@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            audio_bytes = await websocket.receive_bytes()

            # Save chunk temporarily
            temp_file = f"temp/{uuid.uuid4()}.webm"
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)

            # ASR
            text = transcribe_audio(temp_file)
            gloss = english_to_asl_gloss(text)
            signs = gloss_to_signs(gloss)

            await websocket.send_json({
                "text": text,
                "gloss": gloss,
                "signs": signs
            })
    except Exception as e:
        print("WebSocket closed:", e)
