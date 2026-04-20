import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

# Path to the saved model
MODEL_PATH = "app/models/whisper-small-sinhala-robust-FINAL"

class WhisperLoader:
    _processor = None
    _model = None
    _device = "cuda" if torch.cuda.is_available() else "cpu"

    @classmethod
    def load(cls):
        # Check if model and processor are already loaded
        if cls._processor is None or cls._model is None:
            # Load the Whisper processor and model
            cls._processor = WhisperProcessor.from_pretrained(MODEL_PATH)
            cls._model = WhisperForConditionalGeneration.from_pretrained(MODEL_PATH)

            # Move the model to the appropriate device (GPU if available)
            cls._model.to(cls._device)

            # Enable mixed precision for faster inference if on GPU
            cls._model.half()  # Use FP16 (mixed precision)
            
        return cls._processor, cls._model, cls._device