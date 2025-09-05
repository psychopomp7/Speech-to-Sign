import { useState, useRef } from "react";

export default function LiveSTT() {
  const [text, setText] = useState("Click start to record...");
  const [recording, setRecording] = useState(false);

  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const startRecording = async () => {
    // Setup WebSocket
    wsRef.current = new WebSocket("ws://localhost:8000/stt/ws/transcribe");

    wsRef.current.onopen = () => {
      console.log("✅ WebSocket connected");
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📩 From backend:", data);

      if (data.partial) {
        setText((prevText) => prevText + " " + data.partial); // Append partial results
      }
      if (data.final) {
        console.log("📝 Final transcription:", data.final);
        setText(data.final);
        wsRef.current.close(); // ✅ Now close the connection
      }
    };

    wsRef.current.onclose = () => {
      console.log("🔌 WebSocket closed");
    };

    // Setup audio capture
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaStreamRef.current = stream;
    audioContextRef.current = new AudioContext({ sampleRate: 16000 });

    // Load the worklet from public/processor.js
    await audioContextRef.current.audioWorklet.addModule("/processor.js");

    const source = audioContextRef.current.createMediaStreamSource(stream);

    workletNodeRef.current = new AudioWorkletNode(
      audioContextRef.current,
      "pcm16-worklet"
    );

    // Send audio buffers to backend
    workletNodeRef.current.port.onmessage = (event) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(event.data);
      }
    };

    source.connect(workletNodeRef.current);

    setRecording(true);
    setText("🎤 Listening...");
  };

  const stopRecording = () => {
  // ... (disconnect worklet, stop mic tracks, close audio context) ...

  // Tell backend we're done, BUT DON'T CLOSE THE CONNECTION HERE
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    // We need to send a JSON object, not a plain string, to be consistent
    wsRef.current.send(JSON.stringify({ text: "STOP" }));
  }

  setRecording(false);
};

  return (
    <div className="p-6 flex flex-col items-center">
      <h2 className="text-xl font-bold mb-4">🎤 Speech-to-Text</h2>

      <div className="flex gap-4 mb-6">
        {!recording ? (
          <button
            onClick={startRecording}
            className="px-4 py-2 bg-green-600 text-white rounded-lg shadow hover:bg-green-700"
          >
            Start Recording
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="px-4 py-2 bg-red-600 text-white rounded-lg shadow hover:bg-red-700"
          >
            Stop Recording
          </button>
        )}
      </div>

      {/* transcript area aligned to the right */}
      <div className="flex justify-end w-full">
        <div className="bg-gray-100 p-4 rounded-lg shadow-md w-96 min-h-[100px] text-right">
          {text}
        </div>
      </div>
    </div>
  );
}
