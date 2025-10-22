import cv2
import mediapipe as mp
import numpy as np
import os
import json
import pandas as pd

# --- Configuration ---
# Get the directory where this script is located (i.e., the 'backend' folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Point this to the root directory of your ASLLVD video files
ASLLVD_ROOT_DIR = r"D:\Speech to Sign\ASLLVD" # <-- This path stays the same

# 2. This is the metadata file.
METADATA_FILENAME = "asllvd_signs_2024_06_27.csv"
METADATA_FILE = os.path.join(SCRIPT_DIR, METADATA_FILENAME)

# 3. This is where the final dictionary will be saved
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "pose_dictionary.json")

# --- MediaPipe Initialization ---
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(
    static_image_mode=False, 
    model_complexity=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def extract_keypoints(results):
    """
    Extracts keypoints from MediaPipe results into a flat array.
    """
    pose_flat = np.array([[res.x, res.y, res.z] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*3)
    lh_flat = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh_flat = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose_flat, lh_flat, rh_flat]).tolist()

# --- MODIFIED FUNCTION ---
def process_videos(dataset_path, metadata_path, output_json_path):
    
    # --- 1. LOAD EXISTING DICTIONARY (THE CRUCIAL CHANGE) ---
    if os.path.exists(output_json_path):
        print(f"Loading existing dictionary from {output_json_path}...")
        try:
            with open(output_json_path, 'r') as f:
                pose_dictionary = json.load(f)
            print(f"Loaded {len(pose_dictionary)} existing sign poses.")
        except json.JSONDecodeError:
            print("Warning: pose_dictionary.json is corrupted. Starting fresh.")
            pose_dictionary = {}
    else:
        print("No existing dictionary found. Starting fresh.")
        pose_dictionary = {}
    # --- END OF CHANGE ---

    # --- 2. Load metadata ---
    try:
        df = pd.read_csv(metadata_path)
        df_unique = df[["full video file", "Class Label"]].drop_duplicates()
        metadata = pd.Series(df_unique["Class Label"].values, index=df_unique["full video file"]).to_dict()
    except Exception as e:
        print(f"Error: Could not load metadata file from {metadata_path}")
        return

    print(f"Loaded metadata. Found {len(metadata)} unique video files in master list.")
    
    video_files = list(metadata.keys())
    new_signs_found_this_session = 0
    
    for i, video_filename in enumerate(video_files):
        gloss_label = str(metadata[video_filename]).upper().split('(')[0].strip()

        # --- 3. CHECK IF WE ALREADY HAVE THIS SIGN ---
        # If this gloss is *already* in our JSON, we can skip it.
        # This speeds up processing hugely.
        if gloss_label in pose_dictionary:
            continue
            
        video_path = os.path.join(dataset_path, video_filename)
        
        # --- 4. CHECK IF WE HAVE THE VIDEO FILE ---
        # If the file doesn't exist (because it's deleted or not downloaded),
        # skip it.
        if not os.path.exists(video_path):
            # This is no longer a "Warning", just a normal skip.
            # We can comment this out to reduce log spam:
            # print(f"File not found (normal): {video_path}. Skipping.")
            continue
            
        # --- 5. PROCESS THE NEW VIDEO ---
        cap = cv2.VideoCapture(video_path)
        frame_keypoints = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            try:
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = holistic.process(image)
                keypoints = extract_keypoints(results)
                frame_keypoints.append(keypoints)
            except Exception as e:
                print(f"Error processing frame in {video_filename}: {e}. Skipping video.")
                frame_keypoints = [] # Clear any partial data
                break # Stop processing this video
            
        cap.release()
        
        if frame_keypoints:
            pose_dictionary[gloss_label] = frame_keypoints
            new_signs_found_this_session += 1
            print(f"Processed ({i+1}/{len(video_files)}): {video_filename} -> ADDED NEW Gloss: {gloss_label} ({len(frame_keypoints)} frames)")

    print(f"\nFound {new_signs_found_this_session} new signs in this session.")
    return pose_dictionary

# --- Main execution (MODIFIED) ---
if __name__ == "__main__":
    print("Starting incremental video processing...")
    
    # We now pass OUTPUT_JSON as an argument so the function can read it
    final_poses = process_videos(ASLLVD_ROOT_DIR, METADATA_FILE, OUTPUT_JSON)
    
    if final_poses:
        print(f"\nProcessing complete. Total signs in dictionary: {len(final_poses)}")
        
        # Save the dictionary to JSON
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(final_poses, f) # Save without indent for smaller file size
            
        print(f"✅ Successfully updated pose dictionary: {OUTPUT_JSON}")
    else:
        print("No poses were processed. Please check your paths and metadata.")