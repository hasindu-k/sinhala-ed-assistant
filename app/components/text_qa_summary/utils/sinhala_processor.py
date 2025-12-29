# app/components/text_qa_summary/utils/sinhala_processor.py
import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np

# Sinhala stopwords
SINHALA_STOPWORDS = {
    "කරන", "යන්න", "සඳහන්", "පිළිබඳ", "කෙරෙයි", "වන්නේ", "ඇත", "වැනි",
    "මෙම", "පමණක්", "දක්වයි", "හෝ", "සමඟ", "කටයුතු", "ඉතා", "බව",
    "ගෙන", "සඳහා", "විස්තර", "කියවීමට", "එක", "දෙක", "තුන", "හතර",
    "පහ", "හය", "හත", "අට", "නවය", "දහය"
}


def tokenize_sinhala(text: str) -> List[str]:
    """
    Tokenize Sinhala text into words
    """
    # Remove punctuation and numbers
    text = re.sub(r'[^\u0D80-\u0DFF\s]', ' ', text)
    
    # Split by whitespace
    tokens = text.split()
    
    # Filter stopwords and short tokens
    tokens = [
        token.strip() 
        for token in tokens 
        if len(token) >= 2 and token not in SINHALA_STOPWORDS
    ]
    
    return tokens


def extract_lesson_numbers(text: str) -> List[str]:
    """
    Extract lesson numbers from text (e.g., "පාඩම 1", "පාඩම් 5-7")
    """
    patterns = [
        r'පාඩම\s*(\d+)',
        r'පාඩම්\s*(\d+(?:-\d+)?)',
        r'Lesson\s*(\d+)',
        r'LESSON\s*(\d+)',
        r'පාඩම\s+([\u0D66-\u0D6F]+)',  # Sinhala numerals
    ]
    
    lesson_numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match not in lesson_numbers:
                lesson_numbers.append(str(match))
    
    return lesson_numbers


def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """
    Extract key phrases from Sinhala text
    """
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    
    key_phrases = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue
            
        # Find noun phrases (simplified - look for sequences of 2-4 Sinhala words)
        tokens = tokenize_sinhala(sentence)
        
        # Create bi-grams and tri-grams
        if len(tokens) >= 2:
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]} {tokens[i+1]}"
                if len(bigram) >= 4 and bigram not in key_phrases:
                    key_phrases.append(bigram)
        
        if len(tokens) >= 3:
            for i in range(len(tokens) - 2):
                trigram = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
                if len(trigram) >= 6 and trigram not in key_phrases:
                    key_phrases.append(trigram)
    
    return key_phrases[:max_phrases]


def calculate_bm25_score(
    query_tokens: List[str],
    document_tokens: List[str],
    bm25_index: BM25Okapi = None,
    doc_index: int = 0
) -> float:
    """
    Calculate BM25 score using proper BM25 implementation
    """
    if bm25_index is None:
        # Create a temporary BM25 index
        corpus = [document_tokens]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
        return float(scores[0])
    else:
        scores = bm25_index.get_scores(query_tokens)
        return float(scores[doc_index])