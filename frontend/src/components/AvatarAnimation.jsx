// src/components/AvatarAnimation.jsx
import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, useGLTF } from '@react-three/drei';
import * as THREE from 'three';

// --- IMPORT THE EXTRACTED POSE DATA ---
import HELLO_POSE_DATA from '../hello_poses.json'; // Assumes hello_poses.json is in src/

// --- Bone Mapping (EXAMPLE - NEEDS ADJUSTMENT FOR YOUR AVATAR) ---
// Maps MediaPipe landmark indices to potential Mixamo bone names
const mediapipe_to_avatar_bones = {
    // Body
    'mixamorigHips': { index: [23, 24], type: 'hips' },
    'mixamorigSpine': { index: [11, 12], type: 'spine' }, // Approx using shoulders
    'mixamorigNeck': { index: [9, 10], type: 'neck' }, // Approx using mouth corners/ears
    'mixamorigHead': { index: 0, type: 'head' }, // Nose

    // Left Arm
    'mixamorigLeftShoulder': { index: 11, type: 'joint' },
    'mixamorigLeftArm': { index: 13, type: 'target' }, // Upper arm points to Elbow
    'mixamorigLeftForeArm': { index: 15, type: 'target' }, // Forearm points to Wrist
    'mixamorigLeftHand': { index: 15, type: 'joint' }, // Wrist itself

    // Right Arm
    'mixamorigRightShoulder': { index: 12, type: 'joint' },
    'mixamorigRightArm': { index: 14, type: 'target' },
    'mixamorigRightForeArm': { index: 16, type: 'target' },
    'mixamorigRightHand': { index: 16, type: 'joint' },
    // Add more bones (legs, fingers) if needed and available in your model/data
};

// Helper to get Vector3 from flat pose array (225 floats: 33*3 pose + 21*3 LH + 21*3 RH)
const getKeypoint = (poseFrame, landmarkIndex) => {
    const baseIndex = landmarkIndex * 3;
    if (!poseFrame || baseIndex + 2 >= poseFrame.length) {
        return new THREE.Vector3(0, 0, 0); // Return zero vector safely
    }
    // Adjust coordinate system: MediaPipe Y-down -> Three.js Y-up
    return new THREE.Vector3(
        poseFrame[baseIndex],      // x
        poseFrame[baseIndex + 1],  // -y (Invert Y)
        poseFrame[baseIndex + 2]   // z
    );
};

// --- Avatar Model Component ---
function AvatarModel({ poseData, isPlaying }) {
    const group = useRef();
    const { scene } = useGLTF('/avatar.glb');
    const bones = useRef({});
    const initialBoneRotations = useRef({});

    // Use the original scene directly
    useEffect(() => {
        if (scene) {
            bones.current = {};
            initialBoneRotations.current = {};
            scene.traverse((object) => {
                if (object.isBone) {
                    bones.current[object.name] = object;
                    initialBoneRotations.current[object.name] = object.quaternion.clone();
                }
            });
            scene.scale.set(1.5, 1.5, 1.5);
            scene.position.set(0, -1.5, 0);
            console.log("Avatar bones extracted:", Object.keys(bones.current).length);
        }
    }, [scene]);

    const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
    const clock = useRef(new THREE.Clock(false));
    const timeAccumulator = useRef(0);

    // Control playback state (same as before)
    useEffect(() => {
        if (isPlaying) {
            setCurrentFrameIndex(0);
            timeAccumulator.current = 0;
            if (!clock.current.running) clock.current.start();
        } else {
            if (clock.current.running) clock.current.stop();
            resetToInitialPose();
        }
    }, [isPlaying]);

    // Reset pose function (same as before)
    const resetToInitialPose = () => {
         if (!Object.keys(bones.current).length) return;
         for (const boneName in initialBoneRotations.current) {
             if (bones.current[boneName]) {
                 bones.current[boneName].quaternion.copy(initialBoneRotations.current[boneName]);
             }
         }
         if (bones.current['mixamorigHips']) {
            bones.current['mixamorigHips'].position.set(0,0,0);
         }
    };
    
    // --- Pre-calculate common rotation offsets ---
    const OFFSET_X_POS_90 = new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, 0));
    const OFFSET_X_NEG_90 = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
    const OFFSET_Y_POS_90 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI / 2, 0)); // Your "closest" one
    const OFFSET_Y_NEG_90 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -Math.PI / 2, 0));
    // ... (other offsets) ...


    // --- USEFRAME HOOK (MODIFIED FOR DEBUGGING) ---
    useFrame(() => {
        if (!isPlaying || !poseData || poseData.length === 0 || !Object.keys(bones.current).length || !clock.current.running) {
            return;
        }

        const delta = clock.current.getDelta();
        const targetFps = 30;
        const frameDuration = 1 / targetFps;
        timeAccumulator.current += delta;

        let framesToAdvance = Math.floor(timeAccumulator.current / frameDuration);

        if (framesToAdvance > 0) {
             timeAccumulator.current -= framesToAdvance * frameDuration;
             const nextFrameIndex = (currentFrameIndex + framesToAdvance) % poseData.length;
             setCurrentFrameIndex(nextFrameIndex);
             const frameData = poseData[nextFrameIndex];
             if (!frameData) return;

            // --- 1. HIPS POSITION (Working) ---
            const hipsWorldPos = new THREE.Vector3();
            const leftHipKP = getKeypoint(frameData, 23);
            const rightHipKP = getKeypoint(frameData, 24);
            hipsWorldPos.copy(leftHipKP).add(rightHipKP).multiplyScalar(0.5);
            const hipsBone = bones.current['mixamorigHips'];
            if (hipsBone) {
                hipsBone.position.copy(hipsWorldPos);
            }

            // --- 2. BONE ROTATIONS (MODIFIED) ---
            for (const boneName in mediapipe_to_avatar_bones) {
                const bone = bones.current[boneName];
                if (!bone || !bone.parent || !bone.parent.isBone) continue;
                if (boneName.includes('Spine') || boneName.includes('Neck') || boneName.includes('Head')) continue;

                const mapping = mediapipe_to_avatar_bones[boneName];
                if (mapping.type !== 'target') continue;

                const targetKeypointIndex = mapping.index;
                if (targetKeypointIndex < 0) continue;

                const targetKP = getKeypoint(frameData, targetKeypointIndex);
                const targetWorldEst = new THREE.Vector3().copy(targetKP).add(hipsBone ? hipsBone.position : hipsWorldPos);

                const parentWorldInv = new THREE.Matrix4();
                bone.parent.updateWorldMatrix(true, false);
                parentWorldInv.copy(bone.parent.matrixWorld).invert();
                const targetLocal = targetWorldEst.clone().applyMatrix4(parentWorldInv);

                const lookAtMatrix = new THREE.Matrix4().lookAt(bone.position, targetLocal, new THREE.Vector3(0, 1, 0));
                bone.quaternion.setFromRotationMatrix(lookAtMatrix);

                // --- 3. APPLY ASYMMETRICAL OFFSETS ---
                
                // RIGHT SIDE (The one that looked good)
                if (boneName.includes('mixamorigRightArm')) bone.quaternion.multiply(OFFSET_Y_POS_90);
                if (boneName.includes('mixamorigRightForeArm')) bone.quaternion.multiply(OFFSET_Y_POS_90);
                
                // LEFT SIDE (Apply NO offset)
                // if (boneName.includes('mixamorigLeftArm')) ... (do nothing)
                // if (boneName.includes('mixamorigLeftForeArm')) ... (do nothing)
                
                // --- END MODIFICATION ---
            }
        }
    }); // End useFrame

    return <primitive object={scene} dispose={null} />;
} // End AvatarModel

// --- Main AvatarAnimation component (No changes) ---
export default function AvatarAnimation({ isPlaying }) {
    // ... (Canvas, Lights, Controls, Floor... same as before) ...
    // ... Make sure floor position is set to [0, -4.75, 0] ...
    return (
        <Canvas camera={{ position: [0, 0.5, 3], fov: 50 }} shadows style={{ background: '#374151' }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[5, 10, 7]} intensity={1.5} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024}/>
            <directionalLight position={[-5, 5, -5]} intensity={0.5} />
            <hemisphereLight skyColor={"#cceeff"} groundColor={"#666666"} intensity={0.4} />

            <AvatarModel poseData={HELLO_POSE_DATA} isPlaying={isPlaying} />

            <OrbitControls target={[0, 0.5, 0]} enablePan={true} enableZoom={true} />

            <mesh
                rotation={[-Math.PI / 2, 0, 0]}
                position={[0, -4.75, 0]} // Your working floor position
                receiveShadow
            >
                <planeGeometry args={[20, 20]} />
                <meshStandardMaterial color="#4A5568" roughness={0.7} metalness={0.2} />
            </mesh>
        </Canvas>
    );
}