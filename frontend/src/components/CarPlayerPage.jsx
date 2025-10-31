import React, { useState, useRef, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useGLTF, Html } from '@react-three/drei';
import * as THREE from 'three';

// --- Configuration ---
const PLAYBACK_FPS = 30; // This should match the source video's FPS
const FRAME_DURATION = 1 / PLAYBACK_FPS;

/**
 * This component is a "dumb player."
 * It loads an avatar and applies pre-baked rotation data to its bones.
 * It has NO IK logic.
 */
function AvatarModel({ modelUrl, animationData, isPlaying }) {
  const { scene } = useGLTF(modelUrl);

  // Get a stable, ordered list of all bones
  const bones = useMemo(() => {
    if (!scene) return [];
    // Traverse the scene to find the SkinnedMesh and its bones
    let skinnedMesh = null;
    scene.traverse((object) => {
      if (object.isSkinnedMesh) {
        skinnedMesh = object;
      }
    });
    // The bones are stored in the skeleton
    return skinnedMesh ? skinnedMesh.skeleton.bones : [];
  }, [scene]);

  // Refs for controlling playback
  const frameIndexRef = useRef(0);
  const timeAccumulatorRef = useRef(0);

  // Reset animation when data or play state changes
  useEffect(() => {
    frameIndexRef.current = 0;
    timeAccumulatorRef.current = 0;
  }, [animationData, isPlaying]);

  useFrame((state, delta) => {
    // Stop if not playing or if data isn't ready
    if (!isPlaying || !animationData || !animationData.length || !bones.length) {
      return;
    }

    // 1. Advance the frame index based on time
    timeAccumulatorRef.current += delta;

    if (timeAccumulatorRef.current >= FRAME_DURATION) {
      // Enough time has passed to move to the next frame
      timeAccumulatorRef.current -= FRAME_DURATION;
      frameIndexRef.current = (frameIndexRef.current + 1) % animationData.length;
    }

    // 2. Get the pose data for the current frame
    const currentFrameData = animationData[frameIndexRef.current];
    if (!currentFrameData || !currentFrameData.bones) return;

    // 3. APPLY the pre-calculated rotations
    bones.forEach((bone, index) => {
      // Check if data exists for this bone index
      if (index < currentFrameData.bones.length) {
        const rotationData = currentFrameData.bones[index];
        
        if (rotationData) {
          // `rotationData` is an array [w, x, y, z]
          // We apply it directly to the bone's quaternion.
          bone.quaternion.fromArray(rotationData);
        }
      }
    });
  });

  // Return the entire scene, positioned and scaled
  return <primitive object={scene} position={[0, -1.5, 0]} scale={[1.5, 1.5, 1.5]} />;
}

// A simple loading component
function Loader() {
  return (
    <Html center>
      <span className="text-white font-semibold">Loading Avatar...</span>
    </Html>
  );
}

/**
 * This is the main page component with the Play/Pause button.
 */
export default function CarPlayerPage() {
  const [isPlaying, setIsPlaying] = useState(true);
  
  // --- Load JSON data using fetch ---
  const [animationData, setAnimationData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // This fetches the file from your /public folder
    // *** Make sure you have run bake_animation.py and placed
    // *** the output 'car_rotations.json' file in your /public/ folder.
    fetch('/car_rotations.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok. Make sure car_rotations.json is in the /public folder.');
        }
        return response.json();
      })
      .then((data) => {
        setAnimationData(data);
      })
      .catch((err) => {
        console.error("Failed to load animation data:", err);
        setError(err.message);
      });
  }, []); // Empty array means this runs once on mount

  return (
    // We remove the w-screen/h-screen to make it fit inside the App.jsx layout
    <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900 text-white font-sans rounded-lg">
      
      {/* 3D Canvas */}
      <div className="w-full h-96 rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
        <Canvas camera={{ position: [0, 0.5, 2.5], fov: 50 }} shadows>
          <ambientLight intensity={0.8} />
          <directionalLight 
            position={[5, 10, 7]} 
            intensity={1.5} 
            castShadow 
          />
          <hemisphereLight skyColor={"#aaddff"} groundColor={"#666666"} intensity={0.5} />

          {/* Suspense is needed to handle the loading of the GLB model */}
          <Suspense fallback={<Loader />}>
            {/* Only render the model if the animation data has loaded */}
            {animationData && (
              <AvatarModel 
                modelUrl="/avatar.glb" // Make sure your avatar.glb is in the /public/ folder
                animationData={animationData} 
                isPlaying={isPlaying} 
              />
            )}
          </Suspense>
          
          <OrbitControls target={[0, 0.5, 0]} />
          
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.5, 0]} receiveShadow>
            <planeGeometry args={[20, 20]} />
            <meshStandardMaterial color="#334155" />
          </mesh>

          {/* Show an error message if JSON loading fails */}
          {error && (
            <Html center>
              <div className="text-red-400 bg-black/50 p-4 rounded-lg">
                <p className="font-bold">Error loading animation:</p>
                <p>{error}</p>
              </div>
            </Html>
          )}
        </Canvas>
      </div>

      {/* Play/Pause Button */}
      <button 
        onClick={() => setIsPlaying(!isPlaying)}
        disabled={!animationData} // Disable button until data is loaded
        className="mt-6 px-6 py-3 bg-emerald-600 text-white font-semibold rounded-lg shadow-md hover:bg-emerald-500 transition-all focus:outline-none focus:ring-2 focus:ring-emerald-400 disabled:bg-gray-500"
      >
        {isPlaying ? "Pause" : "Play"}
      </button>
    </div>
  );
}