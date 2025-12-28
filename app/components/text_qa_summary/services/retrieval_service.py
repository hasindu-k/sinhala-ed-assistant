# app/components/text_qa_summary/services/retrieval_service.py
import uuid
import re
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import numpy as np
from rank_bm25 import BM25Okapi

from app.shared.models.text_chunk import TextChunk
from app.components.text_qa_summary.services.embedding_service import EmbeddingService
from app.components.text_qa_summary.utils.sinhala_processor import (
    tokenize_sinhala,
    calculate_bm25_score
)


class RetrievalService:
    @staticmethod
    def _parse_query_intent(query: str) -> Dict[str, Any]:
        """
        Parse user query to understand intent
        """
        intent = {
            "type": "unknown",
            "lesson_numbers": [],
            "key_terms": [],
            "grade_level": None,
            "content_type": None  # "qa" or "summary"
        }
        
        # Extract lesson numbers
        lesson_patterns = [
            r'පාඩම\s*(\d+(?:-\d+)?)',
            r'පාඩම්\s*(\d+(?:-\d+)?)',
            r'lesson\s*(\d+(?:-\d+)?)',
            r'lessons\s*(\d+(?:-\d+)?)',
        ]
        
        for pattern in lesson_patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                if match not in intent["lesson_numbers"]:
                    intent["lesson_numbers"].append(match)
        
        # Determine content type
        if any(term in query.lower() for term in ["qa", "q&a", "ප්‍රශ්න", "පිළිතුරු"]):
            intent["content_type"] = "qa"
        elif any(term in query.lower() for term in ["සාරාංශය", "summary", "සංක්ෂිප්ත"]):
            intent["content_type"] = "summary"
        
        # Extract grade level
        grade_patterns = [
            (r'grade\s*(\d+(?:-\d+)?)', "english"),
            (r'ශ්‍රේණිය\s*(\d+(?:-\d+)?)', "sinhala"),
            (r'(\d+(?:-\d+)?)\s*ශ්‍රේණිය', "sinhala"),
        ]
        
        for pattern, lang in grade_patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                intent["grade_level"] = match
                break
            if intent["grade_level"]:
                break
        
        # Tokenize query for key terms
        intent["key_terms"] = tokenize_sinhala(query)
        
        return intent
    
    @staticmethod
    def retrieve_relevant_chunks(
        db: Session,
        chat_id: uuid.UUID,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 0.6,
        semantic_weight: float = 0.4
    ) -> List[Tuple[TextChunk, float, Dict[str, float]]]:
        """
        Retrieve relevant chunks using hybrid retrieval
        """
        # Parse query intent
        intent = RetrievalService._parse_query_intent(query)
        
        # Get all chunks for this chat
        all_chunks = db.query(TextChunk).filter(
            TextChunk.chat_id == chat_id
        ).all()
        
        if not all_chunks:
            return []
        
        # Prepare query
        query_tokens = tokenize_sinhala(query)
        
        # Create BM25 index for all chunks
        corpus_tokens = []
        for chunk in all_chunks:
            if chunk.tokens:
                corpus_tokens.append(chunk.tokens)
            else:
                # If tokens are None, tokenize now
                chunk_tokens = tokenize_sinhala(chunk.content)
                chunk.tokens = chunk_tokens
                corpus_tokens.append(chunk_tokens)
        
        bm25_index = BM25Okapi(corpus_tokens)
        
        # Get query embedding
        query_embedding = EmbeddingService.get_embeddings([query])[0]
        
        # Score each chunk
        scored_chunks = []
        
        for idx, chunk in enumerate(all_chunks):
            scores = {
                "bm25": 0.0,
                "semantic": 0.0,
                "lesson_match": 0.0,
                "keyphrase_match": 0.0,
                "final": 0.0
            }
            
            # 1. BM25 Score (Lexical)
            if query_tokens and corpus_tokens[idx]:
                scores["bm25"] = calculate_bm25_score(
                    query_tokens=query_tokens,
                    document_tokens=corpus_tokens[idx],
                    bm25_index=bm25_index,
                    doc_index=idx
                )
            
            # 2. Semantic Score (XLM-R)
            if chunk.embedding and query_embedding:
                try:
                    scores["semantic"] = EmbeddingService.cosine_similarity(
                        chunk.embedding,
                        query_embedding
                    )
                except:
                    scores["semantic"] = 0.0
            
            # 3. Lesson Number Match
            if chunk.lesson_numbers and intent["lesson_numbers"]:
                for lesson in intent["lesson_numbers"]:
                    if any(lesson in str(chunk_lesson) for chunk_lesson in chunk.lesson_numbers):
                        scores["lesson_match"] = 1.0
                        break
            
            # 4. Keyphrase Match
            if chunk.key_phrases and intent["key_terms"]:
                chunk_phrase_set = set()
                for phrase in chunk.key_phrases:
                    if phrase:
                        chunk_phrase_set.update(phrase.split())
                
                query_term_set = set(intent["key_terms"])
                overlap = len(chunk_phrase_set.intersection(query_term_set))
                if overlap > 0 and len(query_term_set) > 0:
                    scores["keyphrase_match"] = min(overlap / len(query_term_set), 1.0)
            
            # 5. Combine scores
            # Base combination: BM25 + Semantic
            combined_score = (
                bm25_weight * scores["bm25"] +
                semantic_weight * scores["semantic"]
            )
            
            # Boost for specific matches
            if scores["lesson_match"] > 0:
                combined_score *= 1.5  # Boost for exact lesson match
            
            if scores["keyphrase_match"] > 0.5:
                combined_score *= 1.3  # Boost for keyphrase overlap
            
            scores["final"] = combined_score
            
            scored_chunks.append((chunk, combined_score, scores))
        
        # Sort by final score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k chunks
        return scored_chunks[:top_k]
    
    @staticmethod
    def generate_context_from_chunks(
        scored_chunks: List[Tuple[TextChunk, float, Dict[str, float]]],
        max_context_length: int = 4000
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate context from retrieved chunks
        """
        context_parts = []
        metadata = {
            "total_chunks": len(scored_chunks),
            "used_chunks": 0,
            "avg_score": 0.0,
            "retrieval_scores": []
        }
        
        total_length = 0
        used_chunks = 0
        
        for chunk, score, score_details in scored_chunks:
            chunk_text = chunk.content
            chunk_length = len(chunk_text)
            
            if total_length + chunk_length <= max_context_length:
                context_parts.append(chunk_text)
                total_length += chunk_length
                used_chunks += 1
                metadata["retrieval_scores"].append({
                    "chunk_id": str(chunk.id),
                    "score": score,
                    "details": score_details,
                    "lesson_numbers": chunk.lesson_numbers,
                    "key_phrases": chunk.key_phrases[:3] if chunk.key_phrases else []
                })
            else:
                break
        
        if context_parts:
            metadata["used_chunks"] = used_chunks
            if used_chunks > 0:
                metadata["avg_score"] = sum(s[1] for s in scored_chunks[:used_chunks]) / used_chunks
        
        context = "\n\n".join(context_parts)
        return context, metadata