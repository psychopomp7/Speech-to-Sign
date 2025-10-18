import asyncio
import collections
import numpy as np
import webrtcvad
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

router = APIRouter()

# --- Configuration ---
MODEL_SIZE = "medium.en"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# VAD Configurations
VAD_AGGRESSIVENESS = 1      # How aggressive VAD is (0-3). 1 is less aggressive.
FRAME_DURATION_MS = 30      # Duration of each audio frame in ms
RATE = 16000
VAD_CHUNK_SIZE = int(RATE * FRAME_DURATION_MS / 1000) * 2 # 960 bytes (30ms of 16-bit audio)
SILENCE_DURATION_S = 2

# --- Global State ---
print("Initializing transcription model...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("Model initialized.")


async def transcribe_chunk(audio_chunk: bytes) -> str:
    """
    Transcribes an audio chunk using the faster-whisper model.
    This runs in a separate thread to avoid blocking the main asyncio event loop.
    """
    audio_float32 = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
    
    segments, _ = await asyncio.to_thread(model.transcribe, audio_float32, beam_size=5)
    
    transcription = "".join(segment.text for segment in segments).strip()
    return transcription

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket connection accepted.")

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    
    # Per-connection state
    ring_buffer = collections.deque(maxlen=int((SILENCE_DURATION_S * 1000) / FRAME_DURATION_MS))
    speech_buffer = bytearray()
    unprocessed_audio = bytearray()
    triggered = False
    full_transcript = []

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                audio_data = message["bytes"]
                unprocessed_audio.extend(audio_data)

                # Process audio in VAD-required chunk sizes
                while len(unprocessed_audio) >= VAD_CHUNK_SIZE:
                    chunk = unprocessed_audio[:VAD_CHUNK_SIZE]
                    unprocessed_audio = unprocessed_audio[VAD_CHUNK_SIZE:]

                    try:
                        is_speech = vad.is_speech(chunk, RATE)
                    except Exception:
                        # VAD can fail on silence chunks, just skip it
                        continue

                    if is_speech:
                        triggered = True
                        speech_buffer.extend(chunk)
                    
                    ring_buffer.append((chunk, is_speech))

                    if triggered:
                        num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                        if num_unvoiced == ring_buffer.maxlen:
                            print("Pause detected, transcribing...")
                            
                            transcription = await transcribe_chunk(bytes(speech_buffer))

                            if transcription:
                                print(f"📝 Transcription: {transcription}")
                                full_transcript.append(transcription)
                                # Send the *entire* transcript so far
                                await websocket.send_json({"final": " ".join(full_transcript).lower()})

                            # Reset for the next utterance
                            triggered = False
                            speech_buffer.clear()
                            ring_buffer.clear()
            
            elif "text" in message:
                control_data = json.loads(message["text"])
                if control_data.get("text") == "STOP":
                    print("🛑 STOP message received.")
                    
                    # --- THIS IS THE CRUCIAL FIX ---
                    # If there's audio in the buffer, transcribe it one last time.
                    if speech_buffer:
                        print("Processing remaining audio buffer...")
                        transcription = await transcribe_chunk(bytes(speech_buffer))
                        if transcription:
                            print(f"📝 Final (STOP) Transcription: {transcription}")
                            full_transcript.append(transcription)
                            await websocket.send_json({"final": " ".join(full_transcript).lower()})
                    
                    break # Exit the loop to close the connection

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("🔌 Connection closed.")