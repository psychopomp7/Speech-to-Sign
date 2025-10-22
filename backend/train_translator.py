import pandas as pd
import os  # <-- Import OS
from sklearn.model_selection import train_test_split
from datasets import Dataset
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq
)

# --- Configuration (UPDATED) ---

# Get the directory where this script is located (i.e., the 'backend' folder)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Build absolute paths based on the script's location
TRAINING_FILE = os.path.join(SCRIPT_DIR, "train.csv")
MODEL_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "models", "t5-asl-translator")
CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, "models", "t5-asl-translator_checkpoints")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")

MODEL_NAME = "t5-small"
PREFIX = "translate English to ASL: " # T5 prefix

# --- Module 3: Text Preprocessing (SIMPLIFIED) ---
def preprocess_text(text: str) -> str:
    return str(text).lower().strip()

# --- Module 4: T5 Training ---

def main():
    # 1. Load and prepare data
    print(f"Loading and preprocessing data from {TRAINING_FILE}...")
    try:
        df = pd.read_csv(TRAINING_FILE)
    except FileNotFoundError:
        print(f"Error: Training file not found at {TRAINING_FILE}")
        return
        
    df['english_clean'] = df['english'].apply(preprocess_text)
    df['input_text'] = PREFIX + df['english_clean']
    df['target_text'] = df['gloss'].astype(str)

    train_df, val_df = train_test_split(df, test_size=0.1, random_state=42)
    
    train_dataset = Dataset.from_pandas(train_df[['input_text', 'target_text']])
    val_dataset = Dataset.from_pandas(val_df[['input_text', 'target_text']])

    # 2. Load Tokenizer and Model
    print(f"Loading tokenizer and model '{MODEL_NAME}'...")
    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME, legacy=False)
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)

    # 3. Tokenize Datasets
    print("Tokenizing datasets...")
    def tokenize_function(examples):
        inputs = tokenizer(examples['input_text'], max_length=128, truncation=True, padding="max_length")
        labels = tokenizer(text_target=examples['target_text'], max_length=128, truncation=True, padding="max_length")
        inputs['labels'] = labels['input_ids']
        return inputs

    tokenized_train_ds = train_dataset.map(tokenize_function, batched=True)
    tokenized_val_ds = val_dataset.map(tokenize_function, batched=True)

    # 4. Set up Training
    data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

    training_args = TrainingArguments(
        output_dir=CHECKPOINT_DIR,  # <-- Use new path
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=20,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_dir=LOG_DIR,  # <-- Use new path
        logging_steps=10,
        # Change this to False:
        load_best_model_at_end=False,
        # metric_for_best_model="eval_loss", # No longer needed
        # greater_is_better=False, # No longer needed
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_ds,
        eval_dataset=tokenized_val_ds,
        data_collator=data_collator,
    )

    # 5. Start Training
    print("--- Starting Model Training ---")
    trainer.train()
    print("--- Training Complete ---")

    # 6. Save the final model
    print(f"Saving model to {MODEL_OUTPUT_DIR}...")
    trainer.save_model(MODEL_OUTPUT_DIR)
    tokenizer.save_pretrained(MODEL_OUTPUT_DIR)
    print("✅ Model saved successfully.")
    
    # 7. Test the saved model
    print("\n--- Testing model on TRAINING data ---")
    
    for i in range(min(5, len(train_df))):
        test_row = train_df.iloc[i]
        clean_text = preprocess_text(test_row['english']) 
        input_text = PREFIX + clean_text
        
        inputs = tokenizer(input_text, return_tensors="pt", max_length=128, truncation=True)
        # Move tensor to the model's device (CPU or GPU)
        output_ids = model.generate(inputs.input_ids.to(model.device), max_length=128)
        prediction = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        print(f"\nEnglish:   {test_row['english']}")
        print(f"Expected:  {test_row['target_text']}")
        print(f"Predicted: {prediction}")

if __name__ == "__main__":
    main()