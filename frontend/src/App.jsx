import LiveSTT from "./components/LiveSTT";

function App() {
  return (
    <div
      className="w-screen h-screen flex flex-col items-center justify-start pt-8 px-4 font-sans"
      style={{
        backgroundColor: '#0a1014',
        backgroundImage: 'radial-gradient(#1c2a35 0.5px, transparent 0.5px), radial-gradient(#1c2a35 0.5px, #0a1014 0.5px)',
        backgroundSize: '20px 20px',
        backgroundPosition: '0 0, 10px 10px',
      }}
    >
      {/* Title */}
      <div className="text-center mb-6">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-emerald-400 to-emerald-600 bg-clip-text text-transparent">
          AI Transcription
        </h1>
        <p className="text-gray-400 text-sm mt-2">Real-time speech to text chat</p>
      </div>
      
      {/* Chat Component - Takes remaining space */}
      <div className="w-full max-w-3xl flex-1 rounded-xl overflow-hidden">
        <LiveSTT />
      </div>
    </div>
  );
}

export default App;