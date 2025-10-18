import { useState, useRef } from "react";

// --- Icons (no changes) ---
const MicIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" fill="currentColor"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2h2v2a5 5 0 0 0 10 0v-2h2z" fill="currentColor"/>
    <path d="M12 19.5a.5.5 0 0 1-.5-.5v-2a.5.5 0 0 1 1 0v2a.5.5 0 0 1-.5-.5z" fill="currentColor"/>
    <path d="M8 22a.5.5 0 0 1-.5-.5v-2a.5.5 0 0 1 1 0v2a.5.5 0 0 1-.5-.5z" fill="currentColor"/>
    <path d="M16 22a.5.5 0 0 1-.5-.5v-2a.5.5 0 0 1 1 0v2a.5.5 0 0 1-.5-.5z" fill="currentColor"/>
  </svg>
);
const StopIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="12" height="12" x="6" y="6" fill="currentColor" rx="1"/>
  </svg>
);
const AudioVisualizer = ({ isRecording }) => {
  const barCount = 32;
  return (
    <div className="flex items-center justify-center gap-1 w-full h-12">
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className={`w-1 rounded-full bg-cyan-400/50 ${isRecording ? 'animate-visualizer-bar' : 'h-1'}`}
          style={{
            animationDelay: isRecording ? `${Math.random() * 0.5}s` : undefined,
            animationDuration: isRecording ? `${(Math.random() * 0.5) + 1}s` : undefined,
            height: isRecording ? '100%' : '0.25rem'
          }}
        />
      ))}
    </div>
  );
};
// --- End Icons ---


export default function LiveSTT() {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState({ final: "", partial: "" });
  const [statusText, setStatusText] = useState("Click the icon to start recording");

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const displayText = (transcript.final + " " + transcript.partial).trim();

  const startRecording = async () => {
    setTranscript({ final: "", partial: "" });
    setStatusText("Connecting to server...");

    wsRef.current = new WebSocket("ws://localhost:8000/stt/ws/transcribe");

    wsRef.current.onopen = () => {
      setStatusText("Listening... speak into your microphone");
      setRecording(true);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📩 From backend:", data);

      if (data.final) {
        setTranscript({ final: data.final, partial: "" });
      }
      if (data.partial) {
        setTranscript((prev) => ({ ...prev, partial: data.partial }));
      }
    };
    
    wsRef.current.onclose = () => {
      setStatusText("Connection closed. Click to start again.");
      setRecording(false);
    };
    wsRef.current.onerror = () => {
      setStatusText("Connection error. Please try again.");
      setRecording(false);
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      await audioContextRef.current.audioWorklet.addModule("/recorder-worklet.js");
      const source = audioContextRef.current.createMediaStreamSource(stream);
      workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, "recorder-processor");
      
      // --- THIS IS THE FIX ---
      // We check the WebSocket state *before* sending.
      workletNodeRef.current.port.onmessage = (event) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(event.data);
        }
      };
      
      source.connect(workletNodeRef.current).connect(audioContextRef.current.destination);
    } catch (error) {
      console.error("Error starting recording:", error);
      setStatusText("Microphone access denied. Please allow and try again.");
    }
  };

  const stopRecording = () => {
    setStatusText("Processing final audio...");
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text: "STOP" }));
    }
    
    // Gracefully shut down audio components
    if (workletNodeRef.current) {
        workletNodeRef.current.port.close();
        workletNodeRef.current.disconnect();
    }
    if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (audioContextRef.current) {
        audioContextRef.current.close();
    }
    // The wsRef.current.onclose event will handle setting recording to false
  };

  return (
    <div className="w-full max-w-3xl mx-auto bg-gray-800/30 backdrop-blur-xl border border-cyan-400/20 rounded-2xl shadow-2xl p-8 text-white">
      
      {/* Transcript Display Area */}
      <div className="w-full h-60 bg-black/30 rounded-lg p-6 mb-6 font-mono text-lg leading-relaxed text-gray-200 overflow-y-auto border border-gray-700">
        {displayText || <span className="text-gray-500">{statusText}</span>}
      </div>

      {/* Visualizer */}
      <AudioVisualizer isRecording={recording} />

      {/* Controls */}
      <div className="flex flex-col items-center mt-6">
        <button
          onClick={recording ? stopRecording : startRecording}
          className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ease-in-out border-2 border-cyan-400/50
            ${recording 
              ? 'bg-red-500/80 text-white animate-pulse-glow' 
              : 'bg-cyan-500/80 text-white hover:bg-cyan-400'
            }`
          }
        >
          {recording ? <StopIcon /> : <MicIcon />}
        </button>
        <p className="text-center text-cyan-300/70 h-6 mt-5 tracking-wide">
          {recording ? "Click to Stop" : statusText}
        </p>
      </div>

    </div>
  );
}