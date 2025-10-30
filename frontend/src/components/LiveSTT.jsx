// src/LiveSTT.jsx (Simplified for Demo)
import React, { useState } from "react";
import { Play, Square } from "lucide-react";
import AvatarAnimation from './AvatarAnimation'; // Import the animation component

export default function HelloDemo() {
  const [isPlayingDemo, setIsPlayingDemo] = useState(false); // State to control playback

  // Function to toggle the demo animation
  const toggleHelloDemo = () => {
    setIsPlayingDemo(prev => !prev); // Toggle playing state
    console.log(isPlayingDemo ? "Stopping HELLO demo" : "Playing HELLO demo");
  };

  return (
    <div className="w-full h-[80vh] md:h-[calc(100vh-4rem)] max-h-[900px] bg-slate-800 flex flex-col rounded-lg shadow-2xl overflow-hidden my-8 mx-auto max-w-4xl">

      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 sm:px-6 py-3 flex items-center justify-between border-b border-blue-600/50 flex-shrink-0">
        <h2 className="text-lg font-semibold text-white">ASL Animation Demo - HELLO</h2>
        <div className={`w-3 h-3 rounded-full transition-all ${
            isPlayingDemo ? "bg-green-400 animate-pulse" : "bg-gray-400"
          }`} title={isPlayingDemo ? "Playing" : "Stopped"} />
      </div>

      {/* Main Area: Avatar occupies most space */}
      <div className="flex-1 relative border-b border-slate-700">
        {/* Pass isPlaying state to control animation */}
        <AvatarAnimation isPlaying={isPlayingDemo} />
      </div>

      {/* Footer: Control Button */}
      <div className="bg-slate-900/80 backdrop-blur-sm px-4 py-3 border-t border-slate-700 flex items-center justify-center gap-3 flex-shrink-0">
        <button
          onClick={toggleHelloDemo}
          className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 font-semibold flex-shrink-0 shadow-lg ${
              isPlayingDemo
               ? 'bg-red-500 hover:bg-red-600 shadow-red-500/50'
               : 'bg-blue-500 hover:bg-blue-600 shadow-blue-500/50'
          }`}
          title={isPlayingDemo ? "Stop Animation" : "Play 'HELLO'"}
        >
          {isPlayingDemo ? <Square size={24} className="text-white" /> : <Play size={24} className="text-white" />}
        </button>
      </div>

      {/* Optional Styles if needed */}
      <style>{`
        /* Add any specific styles here */
      `}</style>
    </div>
  );
}