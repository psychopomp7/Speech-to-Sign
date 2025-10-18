import { useState, useRef, useEffect } from "react";
import { Mic, Send, AlertCircle, CheckCheck, Clock } from "lucide-react";

export default function LiveSTT() {
  const [recording, setRecording] = useState(false);
  const [messages, setMessages] = useState([
    { id: 0, sender: "system", text: "👋 Welcome! Click the mic button to start chatting.", timestamp: new Date() }
  ]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const chatWindowRef = useRef(null);
  const messageCountRef = useRef(1);

  const addMessage = (sender, text) => {
    if (!text) return;
    setMessages(prev => [
      ...prev,
      { 
        id: messageCountRef.current++, 
        sender, 
        text,
        timestamp: new Date(),
        status: sender === "user" ? "sending" : "received"
      }
    ]);
  };

  useEffect(() => {
    if (chatWindowRef.current) {
      setTimeout(() => {
        chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
      }, 0);
    }
  }, [messages]);

  const startRecording = async () => {
    setError(null);
    setIsConnecting(true);
    addMessage("system", "🎤 Connecting to microphone...");

    wsRef.current = new WebSocket("ws://localhost:8000/stt/ws/transcribe");

    wsRef.current.onopen = () => {
      addMessage("system", "✅ Listening... Speak clearly into your microphone");
      setRecording(true);
      setIsConnecting(false);
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📩 From backend:", data);
        
        if (data.final && data.final.trim()) {
          setMessages(prev => {
            const updated = [...prev];
            // Look for the last "Processing" message or create a new user message
            const lastIdx = updated.length - 1;
            
            // Check if the last message is a system message about processing
            if (lastIdx >= 0 && updated[lastIdx].sender === "system" && updated[lastIdx].text.includes("Processing")) {
              // Replace it with the transcribed text
              updated[lastIdx] = {
                id: messageCountRef.current++,
                sender: "user",
                text: data.final,
                timestamp: new Date(),
                status: "sent"
              };
            } else {
              // Add as new user message
              updated.push({
                id: messageCountRef.current++,
                sender: "user",
                text: data.final,
                timestamp: new Date(),
                status: "sent"
              });
            }
            return updated;
          });
        }
      } catch (error) {
        console.error("Error parsing message:", error);
      }
    };

    wsRef.current.onclose = () => {
      console.log("🔌 WebSocket closed");
      setRecording(false);
      setIsConnecting(false);
    };

    wsRef.current.onerror = () => {
      console.error("WebSocket error");
      const errorMsg = "❌ Connection error. Please check your backend is running.";
      addMessage("system", errorMsg);
      setError(errorMsg);
      setRecording(false);
      setIsConnecting(false);
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      
      await audioContextRef.current.audioWorklet.addModule("/recorder-worklet.js");
      const source = audioContextRef.current.createMediaStreamSource(stream);
      workletNodeRef.current = new AudioWorkletNode(audioContextRef.current, "recorder-processor");

      workletNodeRef.current.port.onmessage = (event) => {
        if (wsRef.current?.readyState === 1) {
          wsRef.current.send(event.data);
        }
      };

      source.connect(workletNodeRef.current).connect(audioContextRef.current.destination);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      const errorMsg = "🚫 Microphone access denied. Please allow microphone access and try again.";
      addMessage("system", errorMsg);
      setError(errorMsg);
      setIsConnecting(false);
    }
  };

  const stopRecording = () => {
    addMessage("system", "⏹️ Processing your message...");
    
    if (wsRef.current?.readyState === 1) {
      wsRef.current.send(JSON.stringify({ text: "STOP" }));
      // Don't close immediately - let the backend send the response first
      // The connection will close on its own when the backend closes it
    }

    // Clean up audio resources after a delay to ensure message is sent
    setTimeout(() => {
      if (workletNodeRef.current) {
        workletNodeRef.current.port.close();
        workletNodeRef.current.disconnect();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    }, 500);

    setRecording(false);
  };

  const getStatusIcon = (status) => {
    if (status === "sending") return <Clock size={14} className="text-gray-400" />;
    if (status === "sent") return <CheckCheck size={14} className="text-blue-400" />;
    return null;
  };

  return (
    <div className="w-full h-full bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col rounded-lg shadow-2xl overflow-hidden">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 px-6 py-4 flex items-center justify-between border-b border-emerald-600/50">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-emerald-600 font-bold text-lg">
            A
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Aura AI</h2>
            <p className={`text-xs font-medium transition-colors ${
              recording ? "text-emerald-100 animate-pulse" : "text-emerald-200"
            }`}>
              {recording ? "🎤 Recording..." : isConnecting ? "Connecting..." : "Ready to chat"}
            </p>
          </div>
        </div>
        <div className={`w-3 h-3 rounded-full transition-all ${
          recording ? "bg-red-400 animate-pulse" : "bg-emerald-300"
        }`} />
      </div>

      {/* Messages Window */}
      <div
        ref={chatWindowRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 bg-gradient-to-b from-slate-900 to-slate-800 scrollbar-hide"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2 animate-fadeIn ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.sender === "system" && (
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                <AlertCircle size={16} className="text-yellow-400" />
              </div>
            )}
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow-md text-sm transition-all duration-200 ${
                msg.sender === "user"
                  ? "bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-br-none"
                  : "bg-slate-700 text-gray-100 rounded-bl-none"
              }`}
            >
              <p className="break-words">{msg.text}</p>
              <div className={`text-xs mt-1 flex items-center gap-1 ${
                msg.sender === "user" ? "text-emerald-100" : "text-gray-400"
              }`}>
                <span>{msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                {msg.sender === "user" && getStatusIcon(msg.status)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer & Input */}
      <div className="bg-slate-900 px-4 py-3 border-t border-slate-700 flex items-center gap-3">
        <input
          type="text"
          placeholder={recording ? "Listening..." : "Tap mic to speak..."}
          disabled
          className="flex-1 bg-slate-800 text-gray-300 rounded-full px-5 py-3 text-sm border border-slate-700 placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors disabled:opacity-60"
        />
        
        <button
          onClick={recording ? stopRecording : startRecording}
          disabled={isConnecting}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 font-semibold flex-shrink-0 ${
            isConnecting
              ? "bg-gray-600 cursor-not-allowed"
              : recording
              ? "bg-red-500 hover:bg-red-600 active:scale-95 shadow-lg shadow-red-500/50"
              : "bg-emerald-500 hover:bg-emerald-600 active:scale-95 shadow-lg shadow-emerald-500/50"
          }`}
          title={recording ? "Stop recording" : "Start recording"}
        >
          {isConnecting ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : recording ? (
            <div className="w-4 h-4 bg-white rounded-sm" />
          ) : (
            <Mic size={20} className="text-white" />
          )}
        </button>
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }

        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}