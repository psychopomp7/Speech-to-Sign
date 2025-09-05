import LiveSTT from "./components/LiveSTT";

function App() {
  return (
    // Add a subtle gradient background and center the component
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-200 flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl font-bold text-gray-800 mb-2">
        Real-Time Transcription
      </h1>
      <p className="text-gray-600 mb-8">Powered by Vosk & FastAPI</p>
      <LiveSTT />
    </div>
  );
}

export default App;