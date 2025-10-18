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
    
    # --- THIS IS THE FIX ---
    # We add a flag to prevent two transcriptions from running at once.
    is_transcribing = False

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
                        continue

                    if is_speech:
                        triggered = True
                        speech_buffer.extend(chunk)
                    
                    ring_buffer.append((chunk, is_speech))

                    if triggered and not is_transcribing: # <-- Check the flag
                        num_unvoiced = len([f for f, speech in ring_buffer if not speech])
                        
                        if num_unvoiced == ring_buffer.maxlen:
                            # --- SET THE FLAG ---
                            is_transcribing = True 
                            print("Pause detected, transcribing...")
                            
                            # Get audio from buffer *before* starting async task
                            audio_to_transcribe = bytes(speech_buffer)
                            
                            # Reset buffers *immediately*
                            triggered = False
                            speech_buffer.clear()
                            ring_buffer.clear()
                            
                            transcription = await transcribe_chunk(audio_to_transcribe)

                            if transcription:
                                print(f"📝 Transcription: {transcription}")
                                print(f"📤 Sending to frontend: {transcription}")
                                await websocket.send_json({"final": transcription})

                            # --- CLEAR THE FLAG ---
                            is_transcribing = False
            
            elif "text" in message:
                control_data = json.loads(message["text"])
                if control_data.get("text") == "STOP":
                    print("🛑 STOP message received.")
                    
                    # --- CHECK THE FLAG ---
                    # Only transcribe on STOP if a VAD transcription isn't already running
                    if speech_buffer and not is_transcribing:
                        print("Processing remaining audio buffer...")
                        transcription = await transcribe_chunk(bytes(speech_buffer))
                        
                        if transcription:
                            print(f"📝 Final (STOP) Transcription: {transcription}")
                            print(f"📤 Sending final to frontend: {transcription}")
                            try:
                                await websocket.send_json({"final": transcription})
                            except Exception as e:
                                print(f"❌ Failed to send: {e}")
                    
                    break # Exit the loop to close the connection

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("🔌 Connection closed.")