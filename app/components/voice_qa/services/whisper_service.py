import librosa
import torch
from typing import List, Dict

from app.core.whisper_loader import WhisperLoader
from app.core.utils import normalize_sinhala
from app.core.gemini_client import GeminiClient

# Reuse the project's embedding + LLM helpers
from app.components.document_processing.services.embedding_service import (
    generate_text_embedding as _generate_text_embedding,
)
from app.shared.ai.gemini_client import gemini_generate
from app.core.database import engine
from sqlalchemy import text

from jiwer import wer, cer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

# Hybrid retrieval helpers (lexical + dense + cross-encoder rerank)
from app.components.voice_qa.services.hybrid_retrieval import (
    retrieve_top_k,
    dense_retrieval,
)

class VoiceService:
    
    _embedding_tokenizer = None
    _embedding_model = None

    @staticmethod
    def transcribe_audio(file_path: str):
        processor, model, device = WhisperLoader.load()

        # Enable mixed precision (FP16) for GPU
        model.half()  # Use FP16 (mixed precision)

        # Load & resample audio
        audio, sr = librosa.load(file_path, sr=16000)

        # Process the audio file with WhisperProcessor
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt").to(device)

        # Convert the input features to FP16 (mixed precision)
        inputs = {k: v.half() for k, v in inputs.items()}

        with torch.no_grad():
            # Use the model for generating transcriptions
            ids = model.generate(inputs["input_features"])

        # Decode the generated token IDs to get the transcription text
        text = processor.batch_decode(ids, skip_special_tokens=True)[0]
        return text

    @staticmethod
    def standardize_southern_sinhala(text: str):
        normalized = normalize_sinhala(text)

        prompt = f"""
            As an expert Sinhala linguist, transform the following transcribed text into Standard Literary Sinhala (ලිඛිත සිංහල).

            Tasks:
            1. Fix transcription errors: Correct phonetic misinterpretations (e.g., if 'මකේ' appears where 'මගේ' is intended).
            2. Normalize Dialect: Convert Southern-specific idioms and pronunciations into standard forms.
            3. Grammar: Ensure proper Sinhala sentence structure.

            Input Text:
            {normalized}

            Return ONLY the corrected Standard Sinhala text. Do not include explanations.
            """

        gemini = GeminiClient()
        response = gemini.generate_content(prompt)

        result = (response.get("text") or "").strip()

        return normalized, result

    @staticmethod
    def _load_embedding_model():
        if VoiceService._embedding_model is None:
            VoiceService._embedding_tokenizer = AutoTokenizer.from_pretrained(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            VoiceService._embedding_model = AutoModel.from_pretrained(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            
    @staticmethod
    def _get_embedding(text: str):
        VoiceService._load_embedding_model()

        inputs = VoiceService._embedding_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        )

        with torch.no_grad():
            outputs = VoiceService._embedding_model(**inputs)

        # Mean pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.numpy()
    
    
    @staticmethod
    def evaluate_audio(audio_path: str, reference_text: str):

        # 1️⃣ Transcribe using your existing Whisper logic
        predicted = VoiceService.transcribe_audio(audio_path)

        # 2️⃣ Normalize both texts
        # reference_text = normalize_sinhala(reference_text)
        # predicted = normalize_sinhala(predicted)

        # 3️⃣ Compute WER & CER
        word_error = wer(reference_text, predicted)
        char_error = cer(reference_text, predicted)

        # 4️⃣ Semantic similarity
        pred_emb = VoiceService._get_embedding(predicted)
        ref_emb = VoiceService._get_embedding(reference_text)

        semantic_score = cosine_similarity(pred_emb, ref_emb)[0][0]

        return {
            "prediction": predicted,
            "reference": reference_text,
            "wer": round(word_error, 4),
            "cer": round(char_error, 4),
            "semantic_similarity": round(float(semantic_score), 4)
        }

class VoiceQAService:
    """Collection of helpers for the voice → RAG → LLM pipeline.

    These functions were moved here so `voice_router` can remain small and
    simply call high-level helpers.
    """

    @staticmethod
    def generate_text_embedding(text: str) -> List[float]:
        return _generate_text_embedding(text)

    @staticmethod
    def find_similar_chunks(question_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """Dense-only retrieval wrapper.

        This method preserves the original signature (takes an embedding) but
        delegates to the safe, parameterized `dense_retrieval` implemented in
        `hybrid_retrieval.py`.
        """

        if not question_embedding:
            return []

        # delegate to hybrid.dense_retrieval which uses parameterized queries
        return dense_retrieval(question_embedding, top_k=top_k)

    @staticmethod
    def build_prompt(question: str, chunks: List[Dict]) -> str:
        system = (
            "Use the following retrieved educational content to answer the question. "
            "Answer only using the provided context. Respond in Sinhala."
        )

        chunk_texts = "\n\n".join([f"{i+1}. {c.get('text','')}" for i, c in enumerate(chunks)])

        user = f"Question: \"{question}\"\n\nRelevant content:\n{chunk_texts}"

        prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        return prompt

    @staticmethod
    def llm_generate(prompt: str) -> str:
        try:
            return gemini_generate(prompt)
        except Exception as e:
            print(f"[VoiceQAService] LLM generation failed: {e}")
            return ""
        