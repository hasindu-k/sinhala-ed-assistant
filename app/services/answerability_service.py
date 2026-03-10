# app/services/answerability_service.py
import logging
import re
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)

class AnswerabilityService:
    """
    Determines whether a question can be answered
    using the retrieved context only.
    """

    # Stopwords for Sinhala and English
    STOPWORDS = {
        # Sinhala stopwords
        "යනු", "කුමක්ද", "ද", "මොනවාද", "පිළිබඳ", "පිලිබඳ",
        "කරුණාකර", "පැහැදිලි", "කරන්න", "සඳහා", "මෙම", "මෙහි", "මෙහී",
        "එම", "ඒ", "මේ", "සහ", "හා", "තුළ", "අනුව",
        "ලෙස", "වන", "වූ", "බව", "සිට", "දක්වා",
        "පමණ", "හැකි", "විය", "ය", "මගින්", "සමග",
        "වැනි", "පිළිබඳව", "ගැන", "අතර", "සඳහන්",
        "දෙන්න", "ගන්න", "වෙන්න",
        # English stopwords
        "what", "is", "are", "the", "of", "in", "on", "at",
        "to", "for", "with", "by", "about", "as", "an",
        "hello", "hi", "hey", "good", "morning", "afternoon", "evening",
        "give", "get", "me", "summary"
    }

    # Greeting terms for special handling
    GREETING_TERMS = {
        "හායි", "හලෝ", "ආයුබෝවන්", "කොහොමද", 
        "ගුඩ් මෝනින්", "good morning", "good afternoon", 
        "good evening", "hello", "hi", "hey"
    }

    # Content generation intents - these should always be answerable if content exists
    CONTENT_GENERATION_INTENTS = {
        "summary", "qa_generate", "explanation"
    }

    @staticmethod
    def extract_key_terms(text: str) -> List[str]:
        """
        Extract meaningful content words from text.
        Handles both Sinhala and English.
        """
        # Extract words (Sinhala Unicode range + English letters)
        words = re.findall(r"[a-zA-Zඅ-෴]+", text.lower())
        
        # Filter out stopwords and very short words
        key_terms = [
            word for word in words 
            if word not in AnswerabilityService.STOPWORDS 
            and len(word) > 2
        ]
        
        return key_terms

    @staticmethod
    def calculate_relevance_score(question: str, context: str, chunks: List[Dict]) -> float:
        """
        Calculate a comprehensive relevance score between question and context.
        Returns a score between 0 and 1.
        """
        if not context or not context.strip():
            return 0.0

        # Extract question terms
        question_terms = set(AnswerabilityService.extract_key_terms(question))
        context_lower = context.lower()
        
        # If question has no content terms, rely on chunk similarity
        if not question_terms:
            logger.debug("No content terms in question, relying on chunk similarity")
            chunk_similarities = []
            if chunks:
                for chunk in chunks[:3]:
                    sim_score = chunk.get("similarity")
                    if sim_score is not None:
                        chunk_similarities.append(sim_score)
            
            avg_chunk_similarity = np.mean(chunk_similarities) if chunk_similarities else 0
            return avg_chunk_similarity
        
        # Method 1: Key term overlap
        term_matches = 0
        matched_terms = []
        for term in question_terms:
            if term in context_lower:
                term_matches += 1
                matched_terms.append(term)
        
        # If no terms match at all, score should be low
        if term_matches == 0:
            logger.debug(f"No question terms found in context: {question_terms}")
            return 0.1  # Return a very low score instead of 0
        
        term_overlap_ratio = term_matches / len(question_terms)
        
        # Method 2: Use chunk similarity scores
        chunk_similarities = []
        if chunks:
            for chunk in chunks[:3]:
                sim_score = chunk.get("similarity")
                if sim_score is not None:
                    chunk_similarities.append(sim_score)
        
        avg_chunk_similarity = np.mean(chunk_similarities) if chunk_similarities else 0
        
        # Method 3: Check for exact phrase matches
        phrases = AnswerabilityService._extract_phrases(question)
        phrase_matches = 0
        for phrase in phrases:
            if phrase.lower() in context_lower:
                phrase_matches += 1
        
        phrase_score = min(phrase_matches / max(len(phrases), 1), 1.0) if phrases else 0
        
        # Combine scores with weights
        relevance_score = (
            term_overlap_ratio * 0.4 +      # Term overlap
            avg_chunk_similarity * 0.4 +     # Semantic similarity
            phrase_score * 0.2                # Phrase matches
        )
        
        # Cap at 1.0
        relevance_score = min(relevance_score, 1.0)
        
        logger.debug(f"Relevance breakdown - Terms matched: {matched_terms}, "
                    f"Term overlap: {term_overlap_ratio:.3f}, "
                    f"Chunk similarity: {avg_chunk_similarity:.3f}, "
                    f"Phrase matches: {phrase_score:.3f} → Final: {relevance_score:.3f}")
        
        return relevance_score

    @staticmethod
    def _extract_phrases(text: str, max_phrase_length: int = 4) -> List[str]:
        """
        Extract meaningful phrases (n-grams) from text.
        """
        words = re.findall(r"[a-zA-Zඅ-෴]+", text.lower())
        phrases = []
        
        # Extract bigrams and trigrams
        for n in range(2, min(max_phrase_length + 1, len(words) + 1)):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                # Filter out phrases with stopwords at boundaries
                if phrase.split()[0] not in AnswerabilityService.STOPWORDS and \
                   phrase.split()[-1] not in AnswerabilityService.STOPWORDS:
                    phrases.append(phrase)
        
        return phrases

    @staticmethod
    def has_relevant_content(
        question: str, 
        context: str, 
        chunks: List[Dict], 
        intent: str = "qa_answer",  # Add intent parameter
        threshold: float = 0.3
    ) -> bool:
        """
        Determine if the context contains content relevant to the question.
        Returns True if relevance score exceeds threshold.
        Intent-aware: Content generation intents are always answerable if chunks exist.
        """
        # Handle empty cases
        if not context or not context.strip():
            logger.info("Empty context - no relevant content")
            return False
        
        # Check for greetings
        normalized = question.lower().strip()
        if any(greeting in normalized for greeting in AnswerabilityService.GREETING_TERMS):
            logger.info("Greeting detected - treating as answerable")
            return True
        
        # INTENT-AWARE HANDLING:
        # For content generation intents (summary, qa_generate, explanation),
        # if we have chunks, the question is answerable regardless of term matching
        if intent in AnswerabilityService.CONTENT_GENERATION_INTENTS:
            if chunks and len(chunks) > 0:
                logger.info(f"Content generation intent '{intent}' with chunks available - treating as answerable")
                return True
            else:
                logger.info(f"Content generation intent '{intent}' but no chunks - unanswerable")
                return False
        
        # For QA_ANSWER intents, we need stricter relevance checking
        # Extract question terms
        question_terms = AnswerabilityService.extract_key_terms(question)
        
        # If the question has no meaningful content terms, treat as unanswerable
        if not question_terms:
            logger.info("Question has no meaningful content terms - treating as unanswerable")
            return False
        
        # Check if at least one key term appears in context
        context_lower = context.lower()
        has_term_match = any(term in context_lower for term in question_terms)
        
        if not has_term_match:
            logger.info(f"No key terms from question found in context: {question_terms[:5]}")
            return False
        
        # Calculate relevance score
        relevance_score = AnswerabilityService.calculate_relevance_score(question, context, chunks)
        
        # Determine if content is relevant
        is_relevant = relevance_score >= threshold
        
        logger.info(f"Content relevance: score={relevance_score:.3f}, "
                   f"threshold={threshold}, has_term_match={has_term_match}, "
                   f"relevant={is_relevant}")
        
        return is_relevant

    @staticmethod
    def is_answerable(question: str, context: str, intent: str = "qa_answer") -> bool:
        """
        Legacy method with intent awareness.
        """
        # Handle greetings
        normalized = question.lower().strip()
        if any(greeting in normalized for greeting in AnswerabilityService.GREETING_TERMS):
            return True
        
        # For content generation intents, if context exists, it's answerable
        if intent in AnswerabilityService.CONTENT_GENERATION_INTENTS:
            return bool(context and context.strip())
        
        key_terms = AnswerabilityService.extract_key_terms(question)

        if not key_terms:
            return False

        context_lower = context.lower()
        hits = sum(1 for t in key_terms if t.lower() in context_lower)

        # require at least one strong overlap
        return hits > 0