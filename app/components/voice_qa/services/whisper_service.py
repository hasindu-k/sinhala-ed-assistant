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

# Hybrid retrieval helpers (lexical + dense + cross-encoder rerank)
from app.components.voice_qa.services.hybrid_retrieval import (
    retrieve_top_k,
    dense_retrieval,
)

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

    @staticmethod
    def qa_from_audio(file_path: str, top_k: int = 3) -> Dict:
        """Run the end-to-end pipeline given a local audio file path.

        Returns a dict with keys: question, retrieved_chunks, answer
        """
        raw_text = VoiceService.transcribe_audio(file_path)
        normalized, standard = VoiceService.standardize_southern_sinhala(raw_text)
        question_text = standard or normalized or raw_text
        # Use the hybrid retrieval pipeline which performs lexical + dense retrieval
        # and cross-encoder re-ranking to return the final top-K contexts.
        top_chunks = retrieve_top_k(question_text, top_k=top_k)
        prompt = VoiceQAService.build_prompt(question_text, top_chunks)
        answer = VoiceQAService.llm_generate(prompt)

        return {
            "question": question_text,
            "retrieved_chunks": top_chunks,
            "answer": answer,
        }
