# app/components/evaluation/services/semantic_model.py

from sentence_transformers import SentenceTransformer

# ------------------------------------------------------------
# Load XLM-R once at startup
# ------------------------------------------------------------

xlmr = SentenceTransformer(
    "sentence-transformers/paraphrase-xlm-r-multilingual-v1"
)
