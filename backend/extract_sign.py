import json
import os
import sqlite3 # Use SQLite
import sys

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "pose_dictionary.db") # <-- Path to your database
SIGN_TO_EXTRACT = "HELLO"  # <-- Change this to the sign you want!
OUTPUT_FILENAME = "hello_poses.json" # <-- Output file name
# --- END CONFIGURATION ---

print(f"Connecting to {DB_PATH} to extract '{SIGN_TO_EXTRACT}'...")

if not os.path.exists(DB_PATH):
    print(f"❌ ERROR: Database file '{DB_PATH}' not found.")
    print("   Please run process_videos.py to create it.")
    sys.exit(1)

pose_data = None
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query the database for the specific gloss
    cursor.execute("SELECT pose_data FROM poses WHERE gloss = ?", (SIGN_TO_EXTRACT,))
    result = cursor.fetchone() # Get the first (and only) result

    if result:
        # The pose_data is stored as a JSON string, so we need to parse it
        pose_data_json_string = result[0]
        pose_data = json.loads(pose_data_json_string) # Convert JSON string back to Python list
        print(f"   Found sign '{SIGN_TO_EXTRACT}' in the database.")
    else:
        print(f"❌ Error: Sign '{SIGN_TO_EXTRACT}' not found in the database.")
        # Optionally, list some available signs
        cursor.execute("SELECT gloss FROM poses LIMIT 20")
        available = cursor.fetchall()
        if available:
            print("\n   Available signs (first 20):")
            for sign in available:
                print(f"    - {sign[0]}")

    conn.close()

except sqlite3.Error as e:
    print(f"❌ Database Error: {e}")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"❌ Error: Could not parse pose data for '{SIGN_TO_EXTRACT}'. Data might be corrupted in DB.")
    print(f"   Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")
    sys.exit(1)

# --- Save the extracted data to a new JSON file ---
if pose_data:
    output_path = os.path.join(SCRIPT_DIR, OUTPUT_FILENAME)
    try:
        with open(output_path, 'w') as out_f:
            json.dump(pose_data, out_f) # Save just the list of poses

        print(f"\n✅ Success! Extracted {len(pose_data)} frames for '{SIGN_TO_EXTRACT}'.")
        print(f"   Saved to: {output_path}")
        print(f"   Now copy this file ({OUTPUT_FILENAME}) to your frontend project (e.g., inside the 'src' folder).")

    except Exception as e:
        print(f"❌ Error saving extracted data to {output_path}: {e}")