import os
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "models", "t5-asl-translator")
PREFIX = "translate English to ASL: "
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def main():
    # --- Load Model and Tokenizer ---
    print(f"Loading model from: {MODEL_PATH}")
    try:
        tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH, legacy=False)
        model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
        model.to(DEVICE)
        model.eval()
        print(f"✅ Model loaded successfully on {DEVICE}.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not load model from {MODEL_PATH}")
        return

    # --- Interactive Test Loop ---
    print("\n--- ASL Gloss Translator Test ---")
    print("Type an English sentence and press Enter.")
    print("Type 'q' or 'quit' to exit.")
    
    while True:
        try:
            text = input("\nEnglish: ")
            
            if text.lower() in ['q', 'quit']:
                break
                
            if not text:
                continue

            clean_text = text.lower().strip()
            input_text = PREFIX + clean_text
            
            inputs = tokenizer(input_text, return_tensors="pt", max_length=128, truncation=True)
            input_ids = inputs.input_ids.to(DEVICE)
            
            with torch.no_grad():
                output_ids = model.generate(
                    input_ids,
                    max_length=128,
                    num_beams=4,
                    min_length=2,          # Force it to generate at least 2 tokens
                    no_repeat_ngram_size=2 # Prevent repeating pairs of words
                )
            
            # --- UPDATED DECODE SECTION ---
            
            # 1. Decode WITHOUT skipping special tokens
            gloss_raw = tokenizer.decode(output_ids[0], skip_special_tokens=False)
            
            # 2. Decode WITH skipping special tokens (the original)
            gloss_clean = tokenizer.decode(output_ids[0], skip_special_tokens=True)
            
            print(f"ASL Gloss (Raw):   {gloss_raw}")
            print(f"ASL Gloss (Clean): {gloss_clean}")
            # --- END OF UPDATE ---

        except Exception as e:
            print(f"An error occurred: {e}")

    print("Exiting translator test.")

if __name__ == "__main__":
    main()