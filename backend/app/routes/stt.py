from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from vosk import Model, KaldiRecognizer
import json

router = APIRouter()

# 🧠 Load the Vosk model. Ensure the path is correct.
# The model is loaded only once when the application starts.
try:
    model = Model("./model/vosk-model-small-en-us-0.15")
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    print("Please make sure you have downloaded the model and placed it in the 'model' directory.")
    model = None

# We expect audio to be 16kHz, single-channel PCM
SAMPLE_RATE = 16000

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    
    if not model:
        await websocket.send_json({"error": "Vosk model not loaded."})
        await websocket.close()
        return

    # Create a recognizer instance for this specific client connection
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    
    print("✅ WebSocket connection accepted. Recognizer created.")

    try:
        while True:
            # Receive audio data from the client
            message = await websocket.receive()

            if "bytes" in message:
                # This is the audio chunk
                if recognizer.AcceptWaveform(message["bytes"]):
                    # recognizer.Result() gives the final result of an utterance
                    result_json = recognizer.Result()
                    result_text = json.loads(result_json).get("text", "")
                    if result_text: # Only send if there's text
                        print(f"📝 Final result: {result_text}")
                        await websocket.send_json({"final": result_text})
                else:
                    # recognizer.PartialResult() gives a partial result
                    partial_json = recognizer.PartialResult()
                    partial_text = json.loads(partial_json).get("partial", "")
                    if partial_text: # Only send if there's partial text
                         await websocket.send_json({"partial": partial_text})
            
            elif "text" in message:
                # This is a control message
                if message["text"] == "STOP":
                    print("🛑 STOP message received. Processing final result.")
                    # Get the final result for any remaining audio
                    final_json = recognizer.FinalResult()
                    final_text = json.loads(final_json).get("text", "")
                    if final_text:
                        await websocket.send_json({"final": final_text})
                    break # End the loop and close connection

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("🔌 Connection closed.")