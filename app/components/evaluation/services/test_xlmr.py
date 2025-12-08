# test_xlmr.py

from app.components.evaluation.services.semantic_model import xlmr
import torch


def cosine_sim(a, b):
    """Compute cosine similarity manually"""
    return float((a @ b.T) / (a.norm() * b.norm()))


def test_xlmr():
    print("=== XLM-R TEST START ===")

    # Sample Sinhala sentences
    text1 = "පුනරුදය යනු යුරෝපයේ සිදු වූ සංස්කෘතික පරිවර්තනයකි."
    text2 = "යුරෝපීය පුනරුදය යනු නව සංස්කෘතික දියුණුවකි."
    text3 = "ශ්‍රී ලංකාවේ වැව් පද්ධතිය කෘෂිකර්මයට වැදගත්ය."

    print("\nLoading embeddings...")
    emb1 = xlmr.encode(text1, convert_to_tensor=True)
    emb2 = xlmr.encode(text2, convert_to_tensor=True)
    emb3 = xlmr.encode(text3, convert_to_tensor=True)

    print("\nComputing cosine similarities...")
    sim12 = cosine_sim(emb1, emb2)
    sim13 = cosine_sim(emb1, emb3)

    print("\n--- RESULTS ---")
    print(f"Similarity(text1, text2): {sim12:.4f}  (Should be HIGH)")
    print(f"Similarity(text1, text3): {sim13:.4f}  (Should be LOW)")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    test_xlmr()
