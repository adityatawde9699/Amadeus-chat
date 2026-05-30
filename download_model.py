#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

# Load variables from .env file
load_dotenv()

repo_id = os.getenv("HF_REPO_ID")
filename = os.getenv("HF_FILENAME")

if not repo_id or not filename:
    print("Error: Please set HF_REPO_ID and HF_FILENAME in your .env file.")
    exit(1)

# Ensure the Models directory exists in the current folder
base_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(base_dir, "Models")
os.makedirs(models_dir, exist_ok=True)

print(f"Downloading model '{filename}' from repository '{repo_id}'...")
print(f"Destination: {models_dir}")
print("This may take a while depending on your internet connection.\n")

try:
    # Download the model. local_dir_use_symlinks=False ensures the actual file is placed in Models/
    model_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=models_dir,
        local_dir_use_symlinks=False
    )
    print(f"\n✅ Successfully downloaded model to:\n{model_path}")
    print(f"\nYou can now start your chat with this model using:")
    print(f"uv run chat.py --model {model_path}")
except Exception as e:
    print(f"\n❌ Error downloading model: {e}")
