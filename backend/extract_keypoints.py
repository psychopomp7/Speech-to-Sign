import sqlite3
import json
import sys
import os

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# This MUST match the DB file created by your process_videos_grouped.py script
DB_FILENAME = "pose_dictionary_v2_world.db"
DB_PATH = os.path.join(SCRIPT_DIR, DB_FILENAME)
# ---

def extract_gloss_to_json(gloss_name):
    """
    Fetches pose data for a specific gloss from the SQLite database
    and saves it to a new JSON file.
    """
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        print("Please run `process_videos_grouped.py` first to create the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Fetch the data for the requested gloss
        cursor.execute("SELECT pose_data FROM poses WHERE gloss = ?", (gloss_name.upper(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            # The data is stored as a JSON string, so we load it
            pose_data = json.loads(row[0])
            
            # Define the output filename
            output_filename = f"{gloss_name.lower()}_keypoints.json"
            output_path = os.path.join(SCRIPT_DIR, output_filename)

            # Save the loaded data to a new JSON file
            with open(output_path, 'w') as f:
                json.dump(pose_data, f, indent=2)
            
            print(f"\n✅ Success!")
            print(f"Extracted '{gloss_name.upper()}' ({len(pose_data)} frames) and saved to {output_path}")

        else:
            print(f"\n❌ Error: Gloss '{gloss_name.upper()}' not found in the database.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        gloss_name = sys.argv[1]
    else:
        gloss_name = input("Enter the gloss name to extract (e.g., CAR): ")
    
    if gloss_name:
        extract_gloss_to_json(gloss_name)
    else:
        print("No gloss name provided.")
