import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

MODEL_PATH = "app/models/whisper-sinhala-accent-model"

class WhisperLoader:
    _processor = None
    _model = None
    _device = "cuda" if torch.cuda.is_available() else "cpu"

    @classmethod
    def load(cls):
        if cls._processor is None or cls._model is None:
            cls._processor = WhisperProcessor.from_pretrained(MODEL_PATH)
            cls._model = WhisperForConditionalGeneration.from_pretrained(MODEL_PATH)
            cls._model.to(cls._device)
        return cls._processor, cls._model, cls._device
