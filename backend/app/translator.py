import os
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# --- Configuration ---
# Get the directory where this script is located (should be the 'app' folder)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the model directory (backend/models/t5-asl-translator)
MODEL_PATH = os.path.join(APP_DIR, "..", "models", "t5-asl-translator")
PREFIX = "translate English to ASL: " # The prefix used during training
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Load Model (Module 4) ---
print("Initializing T5 ASL translator model...")
tokenizer = None
model = None
try:
    if os.path.exists(MODEL_PATH):
        tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH, legacy=False)
        model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
        # Move model to the selected device (GPU or CPU) for fast inference
        model.to(DEVICE)
        model.eval() # Set model to evaluation mode (disables dropout etc.)
        print(f"✅ T5 model loaded successfully from {MODEL_PATH} onto {DEVICE}.")
    else:
         print(f"❌ WARNING: Model directory not found at {MODEL_PATH}.")
         print("   Translator will not work. Did you run train_translator.py?")

except Exception as e:
    print(f"❌ CRITICAL ERROR: Could not load T5 model from {MODEL_PATH}.")
    print(f"   Error details: {e}")
    tokenizer = None
    model = None

# --- Preprocessing (Module 3) ---
def preprocess_text(text: str) -> str:
    """Cleans English text for T5 input."""
    if not text:
        return ""
    # Simple cleaning: lowercase and strip whitespace
    return str(text).lower().strip()

# --- Translation Function ---
def translate_to_gloss(text: str) -> str:
    """Translates English text to ASL Gloss using the loaded T5 model."""
    if model is None or tokenizer is None:
        print("Error: T5 model or tokenizer not loaded. Cannot translate.")
        return "ERROR: MODEL NOT LOADED"

    # 1. Preprocess and add prefix
    clean_text = preprocess_text(text)
    if not clean_text:
        return "" # Return empty if input is empty after cleaning
    input_text = PREFIX + clean_text

    try:
        # 2. Tokenize the input text
        inputs = tokenizer(input_text, return_tensors="pt", max_length=128, truncation=True)
        input_ids = inputs.input_ids.to(DEVICE) # Move input tensor to the same device as the model

        # 3. Run inference (blocking CPU/GPU call, run in thread)
        with torch.no_grad(): # Disable gradient calculations for inference
            output_ids = model.generate(
                input_ids,
                max_length=128,        # Max length of the generated gloss
                num_beams=4,           # Use beam search for potentially better results
                # min_length=1,        # Optional: Force generation of at least 1 token
                no_repeat_ngram_size=2 # Optional: Prevent repetitive phrases
                )

        # 4. Decode the generated token IDs back to a string
        gloss_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return gloss_text.strip()

    except Exception as e:
        print(f"Error during T5 translation for input '{text}': {e}")
        return "ERROR: TRANSLATION FAILED"