import cv2
import mediapipe as mp
import numpy as np
import os
import json
import pandas as pd
import sqlite3 # Import SQLite
import sys
import time # For timing

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASLLVD_ROOT_DIR = r"C:\Mridul Project\Speech-to-Sign\ASLLVD" # <-- Your video folder path
METADATA_FILENAME = "asllvd_signs_2024_06_27.csv"
METADATA_FILE = os.path.join(SCRIPT_DIR, METADATA_FILENAME)
# --- NEW: Database Configuration ---
DB_FILENAME = "pose_dictionary_v2_world.db" # <-- Changed DB name to reflect new data
DB_PATH = os.path.join(SCRIPT_DIR, DB_FILENAME)

# --- MediaPipe Initialization ---
mp_holistic = mp.solutions.holistic
holistic = mp_holistic.Holistic(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    enable_segmentation=False,      # <-- Explicitly disable
    refine_face_landmarks=False   # <-- Explicitly disable
)

#
# --- !!! CRITICAL CORRECTION HERE !!! ---
#
def extract_keypoints(results):
    """
    Extracts 3D POSE_WORLD_LANDMARKS only.
    
    This is the corrected function. We MUST use 'pose_world_landmarks' 
    to get true 3D coordinates (in meters) centered at the hips.
    
    We CANNOT use 'left_hand_landmarks' or 'right_hand_landmarks' here,
    as they are in 2.5D *image-space* and are not compatible with
    the 3D world-space coordinates.
    
    TRADE-OFF: This provides 3D-accurate body/arm/head data, but
    you will have NO finger/hand animation.
    """
    
    # 1. Get 3D World Pose (33 landmarks * 3 coords = 99 floats)
    # These are in meters, centered at the hips (0,0,0).
    if results.pose_world_landmarks:
        pose_flat = np.array([[res.x, res.y, res.z] 
                              for res in results.pose_world_landmarks.landmark]).flatten()
    else:
        pose_flat = np.zeros(33*3) # 33 * 3 = 99 floats
        
    # 2. DO NOT INCLUDE HANDS OR FACE
    # lh_flat and rh_flat are in 2.5D image-space and will corrupt the 3D data.
    
    # Convert numpy array to list for JSON serialization later
    return pose_flat.tolist()

# --- Database Functions ---
def setup_database(db_path):
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poses (
            gloss TEXT PRIMARY KEY,
            pose_data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database setup complete at {db_path}")

def get_existing_glosses(db_path):
    """Gets a set of glosses already present in the database."""
    existing_glosses = set()
    if not os.path.exists(db_path):
        return existing_glosses
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT gloss FROM poses")
        rows = cursor.fetchall()
        existing_glosses = {row[0] for row in rows}
        conn.close()
    except Exception as e:
        print(f"Warning: Could not read existing glosses from database. Error: {e}")
    return existing_glosses

def insert_pose_data(db_path, gloss, pose_data):
    """Inserts or replaces pose data for a given gloss."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Serialize pose_data list into a JSON string for storage
    pose_data_json = json.dumps(pose_data)
    # Use INSERT OR REPLACE to handle potential duplicates cleanly
    cursor.execute("INSERT OR REPLACE INTO poses (gloss, pose_data) VALUES (?, ?)",
                   (gloss, pose_data_json))
    conn.commit()
    conn.close()

# --- Main Processing Function (No logic changes needed) ---
def process_videos_grouped(dataset_path, metadata_path, db_path):

    # --- 1. Setup DB and get existing glosses ---
    setup_database(db_path)
    existing_glosses = get_existing_glosses(db_path)
    print(f"Found {len(existing_glosses)} existing signs in the database.")

    # --- 2. Load and Group Metadata ---
    try:
        df = pd.read_csv(metadata_path)
        df.rename(columns={
            'full video file': 'video_filename',
            'Class Label': 'gloss_label',
            'start frame of the sign (relative to full videos)': 'start_frame',
            'end frame of the sign (relative to full videos)': 'end_frame'
        }, inplace=True)

        # Keep only necessary columns and drop rows with missing values
        df_filtered = df[['video_filename', 'gloss_label', 'start_frame', 'end_frame']].dropna()

        # Clean gloss labels
        df_filtered['gloss_label'] = df_filtered['gloss_label'].astype(str).str.upper().str.split('(', expand=True)[0].str.strip()

        # Convert frame numbers to integers, drop invalid rows
        df_filtered = df_filtered[pd.to_numeric(df_filtered['start_frame'], errors='coerce').notnull()]
        df_filtered = df_filtered[pd.to_numeric(df_filtered['end_frame'], errors='coerce').notnull()]
        df_filtered['start_frame'] = df_filtered['start_frame'].astype(int)
        df_filtered['end_frame'] = df_filtered['end_frame'].astype(int)

        # Filter out invalid frame ranges
        df_filtered = df_filtered[df_filtered['end_frame'] > df_filtered['start_frame']]
        df_filtered = df_filtered[df_filtered['start_frame'] >= 0]


        # **GROUPING**: Group rows by video filename
        grouped_metadata = df_filtered.groupby('video_filename')

        print(f"Loaded and grouped metadata. Processing {len(grouped_metadata)} unique videos.")

    except Exception as e:
        print(f"Error: Could not load or process metadata file from {metadata_path}")
        print(f"Details: {e}")
        sys.exit("Exiting due to metadata error.")

    processed_signs_total = len(existing_glosses)
    processed_this_session = 0
    start_time = time.time()

    # --- 3. Iterate through Videos ---
    for video_filename, group in grouped_metadata:
        video_path = os.path.join(dataset_path, video_filename)

        if not os.path.exists(video_path):
            # print(f"Skipping video (not found): {video_path}")
            continue # Skip if the whole video file is missing

        # Check if ALL signs in this video group are already processed
        signs_in_group = set(group['gloss_label'])
        if signs_in_group.issubset(existing_glosses):
            # print(f"Skipping video (all signs processed): {video_filename}")
            continue

        # --- Open Video ONCE ---
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Warning: Could not open video file {video_path}. Skipping group.")
            continue

        print(f"\nProcessing video: {video_filename} ({len(group)} sign instances)")

        # --- Iterate through Sign Segments within this Video ---
        # Sort group by start_frame to process segments mostly sequentially
        group_sorted = group.sort_values('start_frame')

        for index, row in group_sorted.iterrows():
            gloss_label = row['gloss_label']
            start_frame = row['start_frame']
            end_frame = row['end_frame']

            # Skip if this specific gloss is already done
            if gloss_label in existing_glosses:
                continue

            frame_keypoints = []
            success_reading = True
            try:
                # --- Seek and Read Segment ---
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                current_frame = start_frame

                while current_frame <= end_frame:
                    ret, frame = cap.read()
                    if not ret:
                        print(f"  Warning: Failed to read frame {current_frame} for {gloss_label}. Stopping segment.")
                        success_reading = False
                        break

                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    
                    # --- This now calls the CORRECTED function ---
                    keypoints = extract_keypoints(results) 
                    
                    frame_keypoints.append(keypoints)
                    current_frame += 1

                # --- Store Result in DB ---
                if frame_keypoints and success_reading:
                        insert_pose_data(db_path, gloss_label, frame_keypoints)
                        existing_glosses.add(gloss_label) # Update set to avoid reprocessing
                        processed_signs_total += 1
                        processed_this_session += 1
                        print(f"  -> Added Gloss: {gloss_label} [{start_frame}-{end_frame}] ({len(frame_keypoints)} frames). Total: {processed_signs_total}")

                elif not success_reading:
                    print(f"  Skipping storage for {gloss_label} due to frame reading errors.")

            except Exception as e:
                print(f"  ERROR processing segment for {gloss_label} [{start_frame}-{end_frame}]: {e}. Skipping.")
                # Continue to the next segment in the video

        # --- Close Video ---
        cap.release()

    end_time = time.time()
    print(f"\nFinished processing all videos.")
    print(f" - New signs added this session: {processed_this_session}")
    print(f" - Total signs in database: {processed_signs_total}")
    print(f" - Total time: {end_time - start_time:.2f} seconds")
    return processed_signs_total # Return total count

# --- Main execution ---
if __name__ == "__main__":
    print("Starting grouped video processing with SQLite...")
    print("!!! INFO: This script now saves 3D POSE_WORLD_LANDMARKS (Body/Arms only) !!!")
    print("!!! INFO: Finger/Hand data is NOT included to maintain 3D accuracy. !!!")
    total_signs = process_videos_grouped(ASLLVD_ROOT_DIR, METADATA_FILE, DB_PATH)

    if total_signs is not None:
        print(f"\n✅ Processing complete. Database '{DB_FILENAME}' contains {total_signs} signs.")
    else:
        print("\n❌ Processing failed due to errors.")