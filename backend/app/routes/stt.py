import asyncio
import collections
import numpy as np
import webrtcvad
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

# --- Imports for the pipeline ---
from app import translator
from app import renderer

router = APIRouter()

# --- Configuration ---
MODEL_SIZE = "medium.en"  # Or "small.en", "base.en" etc.
DEVICE = "cuda"         # Use "cuda" for GPU, "cpu" for CPU
COMPUTE_TYPE = "float16"  # Use "float16" or "int8_float16" for GPU, "int8" for CPU

# VAD Configurations
VAD_AGGRESSIVENESS = 1      # 0 (least aggressive) to 3 (most aggressive)
FRAME_DURATION_MS = 30      # Recommended frame duration for VAD
RATE = 16000                # Sample rate expected by Whisper and VAD
VAD_CHUNK_SIZE = int(RATE * FRAME_DURATION_MS / 1000) * 2 # Bytes for 30ms of 16-bit audio
SILENCE_DURATION_S = 2      # How many seconds of silence triggers transcription

# --- Global State ---
print("Initializing Whisper model (STT)...")
try:
    stt_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("✅ Whisper model initialized.")
except Exception as e:
    print(f"❌ CRITICAL ERROR: Failed to initialize Whisper model.")
    print(f"   Check model size, device, compute type, and CUDA/cuDNN installation.")
    print(f"   Error details: {e}")
    stt_model = None # Ensure model is None if init fails

# --- Synchronous Transcription Function ---
# IMPORTANT: This should NOT be async def
def transcribe_chunk(audio_chunk: bytes) -> str:
    """
    Transcribes an audio chunk using the faster-whisper model.
    (This is a blocking CPU/GPU call, run in a thread)
    """
    if not stt_model:
        print("Error: STT model not loaded.")
        return "" # Return empty if model failed to load

    try:
        # Convert buffer from int16 bytes to float32 numpy array
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # Transcribe using faster-whisper
        segments, _ = stt_model.transcribe(audio_float32, beam_size=5)

        # Concatenate segments
        transcription = "".join(segment.text for segment in segments).strip()
        return transcription
    except Exception as e:
        print(f"Error during transcription: {e}")
        return "" # Return empty on error


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """Handles WebSocket connection for real-time transcription and translation."""
    await websocket.accept()
    print("✅ WebSocket connection accepted.")

    if not stt_model or not translator.model or not renderer.pose_dictionary:
         print("❌ Closing connection: Required models or data not loaded.")
         await websocket.close(code=1011, reason="Backend models not ready")
         return

    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    # Per-connection state variables
    ring_buffer = collections.deque(maxlen=int((SILENCE_DURATION_S * 1000) / FRAME_DURATION_MS))
    speech_buffer = bytearray()
    unprocessed_audio = bytearray()
    triggered = False
    is_transcribing = False # Mutex to prevent overlapping pipeline runs

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                audio_data = message["bytes"]
                unprocessed_audio.extend(audio_data)

                # Process audio in VAD-sized chunks
                while len(unprocessed_audio) >= VAD_CHUNK_SIZE:
                    chunk = unprocessed_audio[:VAD_CHUNK_SIZE]
                    unprocessed_audio = unprocessed_audio[VAD_CHUNK_SIZE:]

                    try:
                        is_speech = vad.is_speech(chunk, RATE)
                    except Exception as e:
                        # VAD can sometimes fail on invalid data
                        print(f"VAD error: {e}. Skipping chunk.")
                        continue

                    if is_speech:
                        triggered = True
                        speech_buffer.extend(chunk)

                    ring_buffer.append((chunk, is_speech))

                    # Check for end of speech (silence duration met)
                    if triggered and not is_transcribing:
                        num_unvoiced = len([f for f, speech in ring_buffer if not speech])

                        if num_unvoiced == ring_buffer.maxlen:
                            # --- PAUSE DETECTED, RUN FULL PIPELINE ---
                            is_transcribing = True # Acquire lock
                            print("Pause detected, running full pipeline...")

                            audio_to_transcribe = bytes(speech_buffer) # Copy buffer

                            # Reset buffers immediately
                            triggered = False
                            speech_buffer.clear()
                            ring_buffer.clear()

                            if not audio_to_transcribe:
                                print("Skipping empty audio buffer.")
                                is_transcribing = False # Release lock
                                continue

                            # --- 1. SPEECH TO TEXT (Run blocking func in thread) ---
                            transcription = await asyncio.to_thread(
                                transcribe_chunk, audio_to_transcribe
                            )
                            if not transcription:
                                print("STT resulted in empty transcription.")
                                is_transcribing = False # Release lock
                                continue
                            print(f"📝 STT: {transcription}")
                            # Send transcription to frontend
                            await websocket.send_json({"final": transcription})

                            # --- 2. TRANSLATE (Run blocking func in thread) ---
                            asl_gloss = await asyncio.to_thread(
                                translator.translate_to_gloss, transcription
                            )
                            print(f"↪️ Gloss: {asl_gloss}")

                            # --- 3. RENDER POSES (Fast, no thread needed) ---
                            pose_array = renderer.get_poses_from_gloss(asl_gloss)
                            print(f"🤸 Poses: Found {len(pose_array)} frames.")

                            # --- 4. SEND POSES TO FRONTEND ---
                            if pose_array:
                                await websocket.send_json({"poses": pose_array})
                            else:
                                # Send empty array if no poses found? Or just skip?
                                # Sending empty might signal frontend to clear animation
                                await websocket.send_json({"poses": []})


                            is_transcribing = False # Release lock

            elif "text" in message:
                # --- STOP MESSAGE RECEIVED, RUN FINAL PIPELINE ---
                try:
                    control_data = json.loads(message["text"])
                    if control_data.get("text") == "STOP":
                        print("🛑 STOP message received.")

                        if speech_buffer and not is_transcribing:
                            is_transcribing = True # Acquire lock
                            print("Processing remaining audio buffer...")
                            audio_to_transcribe = bytes(speech_buffer) # Copy buffer
                            speech_buffer.clear() # Clear buffer now

                            if not audio_to_transcribe:
                                print("Skipping empty audio buffer on STOP.")
                                # If buffer was empty, still need to break
                                break # <--- Break here if buffer was empty

                            else:
                                # --- Run full pipeline one last time ---
                                transcription = await asyncio.to_thread(
                                    transcribe_chunk, audio_to_transcribe
                                )
                                if transcription:
                                    print(f"📝 STT: {transcription}")
                                    await websocket.send_json({"final": transcription})

                                    asl_gloss = await asyncio.to_thread(
                                        translator.translate_to_gloss, transcription
                                    )
                                    print(f"↪️ Gloss: {asl_gloss}") # Will run now

                                    pose_array = renderer.get_poses_from_gloss(asl_gloss)
                                    print(f"🤸 Poses: Found {len(pose_array)} frames.") # Will run now

                                    if pose_array:
                                        await websocket.send_json({"poses": pose_array}) # Might run now
                                    else:
                                         await websocket.send_json({"poses": []})

                                # --- MOVE BREAK HERE ---
                                # Break only *after* processing is done
                                break # Exit the while loop to close connection
                        else:
                            # --- ADD ELSE BREAK ---
                            # If STOP received but no buffer or already processing, just break.
                            print("STOP received, but no audio buffer to process or already processing.")
                            break # Exit the while loop to close connection

                except json.JSONDecodeError:
                     print(f"Received non-JSON text message: {message['text']}")
                     break # Exit on bad message
                except Exception as e:
                     print(f"Error processing text message: {e}")
                     break # Exit on unexpected error

            # --- REMOVE BREAK FROM THE OUTER LEVEL ---
            # Make sure there is no 'break' statement directly under the 'elif "text" in message:' line

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket handler: {e}")
    finally:
        # Cleanup can go here if needed, although resources are per-connection
        print("🔌 Connection closed.")