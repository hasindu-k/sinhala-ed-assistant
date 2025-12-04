import librosa
import torch
from app.core.whisper_loader import WhisperLoader
from app.core.utils import normalize_sinhala
from app.core.gemini_client import GeminiClient

class VoiceService:

    @staticmethod
    def transcribe_audio(file_path: str):
        processor, model, device = WhisperLoader.load()

        # Load & resample audio
        audio, sr = librosa.load(file_path, sr=16000)

        inputs = processor(audio, sampling_rate=16000, return_tensors="pt").to(device)

        with torch.no_grad():
            ids = model.generate(inputs["input_features"])

        text = processor.batch_decode(ids, skip_special_tokens=True)[0]
        return text

    @staticmethod
    def standardize_southern_sinhala(text: str):
        normalized = normalize_sinhala(text)

        prompt = f"""
        Convert Southern-accent Sinhala into Standard Sinhala.
        Do NOT translate.

        Southern Sinhala:
        {normalized}

        Return only the Standard Sinhala version.
        """

        gemini = GeminiClient.load()
        result = gemini.generate_content(prompt).text.strip()

        return normalized, result
