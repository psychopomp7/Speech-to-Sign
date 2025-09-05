from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes import stt

app = FastAPI()

# Allow frontend (React) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # or ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include STT router
app.include_router(stt.router, prefix="/stt", tags=["speech-to-text"])


@app.get("/")
async def root():
    return {"message": "Backend is running!"}
