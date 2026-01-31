import { useState, useEffect } from "react";

// Load ALL sign images (word signs + alphabet)
const signImages = import.meta.glob("./assets/signs/**/*.png", { eager: true });

function App() {
  const [audioFile, setAudioFile] = useState(null);
  const [text, setText] = useState("");
  const [gloss, setGloss] = useState("");
  const [signs, setSigns] = useState([]);

  const [loading, setLoading] = useState(false);

  // Sequencing states
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(800);

  // Mic states
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);

  const [socket, setSocket] = useState(null);
  const [liveMode, setLiveMode] = useState(false);


  // =========================
  // Upload + process pipeline
  // =========================
  const uploadAudioFile = async (file) => {
    setLoading(true);
    setText("");
    setGloss("");
    setSigns([]);
    setCurrentIndex(0);
    setPlaying(false);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Speech → Text + Gloss
      const response = await fetch("http://127.0.0.1:8000/asr/translate", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setText(data.text);
      setGloss(data.gloss);

      // Gloss → Signs
      const signRes = await fetch("http://127.0.0.1:8000/sign/map", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gloss: data.gloss }),
      });

      const signData = await signRes.json();
      setSigns(signData.signs);

      setPlaying(true);
    } catch (err) {
      console.error(err);
      alert("Error processing audio");
    } finally {
      setLoading(false);
    }
  };

  // =====================
  // File upload handler
  // =====================
  const handleUpload = () => {
    if (!audioFile) {
      alert("Please select an audio file");
      return;
    }
    uploadAudioFile(audioFile);
  };

  // =====================
  // Mic recording logic
  // =====================
  const startRecording = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  const recorder = new MediaRecorder(stream, {
    mimeType: "audio/webm;codecs=opus",
  });

  let chunks = [];

  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) {
      chunks.push(e.data);
    }
  };

  recorder.onstop = async () => {
    const audioBlob = new Blob(chunks, { type: "audio/webm" });
    const audioFile = new File([audioBlob], "mic.webm", {
      type: "audio/webm",
    });

    uploadAudioFile(audioFile);
  };

  recorder.start();
  setMediaRecorder(recorder);
  setRecording(true);
};


  const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    setRecording(false);
  }
};

 // ===================
 // live mode
 // ===================

  const startLiveMode = async () => {
  const ws = new WebSocket("ws://127.0.0.1:8000/ws/asr");
  setSocket(ws);

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream, {
    mimeType: "audio/webm;codecs=opus",
  });

  recorder.ondataavailable = (e) => {
    if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
      e.data.arrayBuffer().then(buffer => ws.send(buffer));
    }
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setText(data.text);
    setGloss(data.gloss);
    setSigns(data.signs);
    setCurrentIndex(0);
    setPlaying(true);
  };

  recorder.start(1500); //  chunk every 1.5 sec
  setMediaRecorder(recorder);
  setLiveMode(true);
};

const stopLiveMode = () => {
  if (mediaRecorder) mediaRecorder.stop();
  if (socket) socket.close();
  setLiveMode(false);
};


  // ======================
  // Sign sequencing engine
  // ======================
  useEffect(() => {
    if (!playing || signs.length === 0) return;

    if (currentIndex >= signs.length - 1) {
      setPlaying(false);
      return;
    }

    const timer = setTimeout(() => {
      setCurrentIndex((prev) => prev + 1);
    }, speed);

    return () => clearTimeout(timer);
  }, [playing, currentIndex, signs, speed]);

  // ======================
  // Render
  // ======================
  return (
    <div
      style={{
        padding: "40px",
        fontSize: "18px",
        background: "#1e1e1e",
        color: "#fff",
        minHeight: "100vh",
      }}
    >
      <h1>Speech → Sign Language</h1>

      {/* File upload */}
      <input
        type="file"
        accept="audio/*"
        onChange={(e) => setAudioFile(e.target.files[0])}
      />

      <br /><br />

      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Processing..." : "Upload & Convert"}
      </button>

      <br /><br />

      {/* Mic controls */}
      <button onClick={startRecording} disabled={recording}>
        🎤 Start Mic
      </button>

      <button onClick={stopRecording} disabled={!recording}>
        ⏹ Stop Mic
      </button>

      <br /><br />
      <button onClick={startLiveMode} disabled={liveMode}>
        🔴 Start Live
      </button>
      <button onClick={stopLiveMode} disabled={!liveMode}>
        ⏹ Stop Live
      </button>

      <br /><br />

      {text && (
        <>
          <h3>Speech → Text</h3>
          <p>{text}</p>
        </>
      )}

      {gloss && (
        <>
          <h3>ASL Gloss</h3>
          <p style={{ fontWeight: "bold" }}>{gloss}</p>
        </>
      )}

      {signs.length > 0 && (
        <>
          <h3>Sign Output</h3>

          <div
            style={{
              display: "flex",
              gap: "15px",
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            {signs.slice(0, currentIndex + 1).map((sign, index) => {
              // Word sign
              if (sign.startsWith("SIGN_")) {
                const imgPath = `./assets/signs/${sign}.png`;
                return (
                  <img
                    key={index}
                    src={signImages[imgPath]?.default}
                    alt={sign}
                    width="120"
                  />
                );
              }

              // Fingerspelling
              if (sign.startsWith("FINGER_")) {
                const letter = sign.replace("FINGER_", "");
                const imgPath = `./assets/signs/alphabet/${letter}.png`;
                return (
                  <img
                    key={index}
                    src={signImages[imgPath]?.default}
                    alt={letter}
                    width="80"
                  />
                );
              }

              return null;
            })}
          </div>

          <br />

          {/* Controls */}
          <button onClick={() => setPlaying(true)}>▶ Play</button>
          <button onClick={() => setPlaying(false)}>⏸ Pause</button>
          <button
            onClick={() => {
              setCurrentIndex(0);
              setPlaying(true);
            }}
          >
            🔁 Replay
          </button>

          <br /><br />

          <label>Speed (ms per sign): </label>
          <input
            type="range"
            min="300"
            max="1500"
            step="100"
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
          />
          <span> {speed} ms</span>
        </>
      )}
    </div>
  );
}



export default App;
