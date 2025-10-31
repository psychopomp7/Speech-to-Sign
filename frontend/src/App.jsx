import React, { useState } from 'react';
import LiveSTT from "./components/LiveSTT";
import CarPlayerPage from "./components/CarPlayerPage"; // Import the new page

function App() {
  const [currentPage, setCurrentPage] = useState('home'); // 'home' or 'car_test'

  // Simple header with navigation
  const Header = () => (
    <div className="w-full max-w-3xl mb-6">
      <div className="text-center mb-4">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-emerald-400 to-emerald-600 bg-clip-text text-transparent">
          AI Sign Translator
        </h1>
        <p className="text-gray-400 text-sm mt-2">
          {currentPage === 'home' ? "Real-time speech to text chat" : "Sign Animation Test"}
        </p>
      </div>
      <nav className="flex justify-center gap-4">
        <button
          onClick={() => setCurrentPage('home')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            currentPage === 'home' 
              ? 'bg-emerald-600 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Live Transcription
        </button>
        <button
          onClick={() => setCurrentPage('car_test')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            currentPage === 'car_test' 
              ? 'bg-emerald-600 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          Test "CAR" Sign
        </button>
      </nav>
    </div>
  );

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
      <Header />
      
      {/* Page Content - Takes remaining space */}
      <div className="w-full max-w-3xl flex-1 rounded-xl overflow-hidden mb-8">
        {currentPage === 'home' ? (
          <LiveSTT />
        ) : (
          <CarPlayerPage />
        )}
      </div>
    </div>
  );
}

export default App;