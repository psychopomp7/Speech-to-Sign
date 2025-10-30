import json
import os
import sqlite3 # Use SQLite
import sys

# --- Configuration ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Path to the SQLite database file
DB_FILENAME = "pose_dictionary.db"
DB_PATH = os.path.join(APP_DIR, "..", DB_FILENAME) # Assumes DB is in the 'backend' folder

# --- Check if Database Exists at Startup ---
if not os.path.exists(DB_PATH):
    print(f"❌ CRITICAL ERROR: Database file '{DB_PATH}' not found.")
    print("   Please run process_videos.py to create it.")
    # You might want to exit or prevent the app from fully starting here
    # sys.exit(1)
else:
    print(f"✅ Database file found at: {DB_PATH}")

# --- No global dictionary load needed anymore ---

def get_poses_from_gloss(gloss_string: str) -> list:
    """
    Connects to the SQLite DB and retrieves pose data for a given gloss string.
    """
    if not gloss_string:
        return []

    # Ensure DB exists before trying to connect in a request
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH} during request.")
        return []

    conn = None # Initialize connection variable
    sentence_poses = []
    tokens = gloss_string.upper().split()

    try:
        # Connect to the database (read-only is often sufficient here)
        conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
        cursor = conn.cursor()

        for token in tokens:
            pose_data = None # Reset for each token
            if token.startswith("FS-"):
                # Handle fingerspelling, e.g., "fs-SAM"
                name = token.split("-", 1)[1]
                for char in name:
                    cursor.execute("SELECT pose_data FROM poses WHERE gloss = ?", (char,))
                    result = cursor.fetchone()
                    if result:
                        pose_data_json = result[0]
                        pose_data = json.loads(pose_data_json)
                        sentence_poses.extend(pose_data)
                    else:
                        print(f"Warning: Fingerspelling char '{char}' not found in database.")
            else:
                # Normal gloss lookup
                cursor.execute("SELECT pose_data FROM poses WHERE gloss = ?", (token,))
                result = cursor.fetchone()
                if result:
                    # The pose_data is stored as a JSON string, parse it
                    pose_data_json = result[0]
                    pose_data = json.loads(pose_data_json)
                    sentence_poses.extend(pose_data)
                else:
                    # Fallback: Word not found
                    print(f"Warning: Gloss '{token}' not found in database. Skipping.")

            # (Optional) Add a small pause after each sign/char if data was found
            # if pose_data and sentence_poses:
            #     num_pause_frames = 5
            #     last_pose = sentence_poses[-1]
            #     for _ in range(num_pause_frames):
            #         sentence_poses.append(last_pose)

    except sqlite3.Error as e:
        print(f"❌ Database error during lookup for '{gloss_string}': {e}")
        return [] # Return empty list on DB error
    except json.JSONDecodeError as e:
         print(f"❌ Error parsing pose data from DB for token '{token}': {e}")
         # Continue processing other tokens, but this sign might be missing/corrupt
    except Exception as e:
        print(f"❌ Unexpected error during get_poses_from_gloss: {e}")
        return []
    finally:
        # Ensure the connection is always closed
        if conn:
            conn.close()

    return sentence_poses