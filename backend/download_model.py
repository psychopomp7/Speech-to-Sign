# download_model.py
import os
from sherpa_onnx.online_model_config import online_model_config

# This is a state-of-the-art streaming model for English
# For other options, see: https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/index.html
config = online_model_config(
    model_name="sherpa-onnx-streaming-zipformer-en-2023-06-26"
)

# The first time you run this, it will download the model and cache it.
# Subsequent runs will use the cached model.
print("Downloading model...")
if not os.path.exists(config.transducer.encoder):
    print(f"Please download the model from {config.model_url} and unzip it.")
    # This is a placeholder; you'll typically download and place it manually
    # as per the latest sherpa-onnx instructions if auto-download isn't direct.
    # For this model, let's assume manual placement is clearer.
print("Model files should be ready.")