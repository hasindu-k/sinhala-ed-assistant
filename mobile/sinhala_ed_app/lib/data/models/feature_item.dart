// mobile/sinhala_ed_app/lib/data/models/feature_item.dart
import 'package:flutter/material.dart';

class FeatureItem {
  final IconData icon;
  final String title;
  final List<String> bullets;
  final VoidCallback? onTap;

  FeatureItem({
    required this.icon,
    required this.title,
    required this.bullets,
    this.onTap,
  });
}

/// Predefined feature list
final List<FeatureItem> featureItems = [
  FeatureItem(
    icon: Icons.document_scanner,
    title: 'Sinhala Document Processing & Embedding',
    bullets: [
      'Enhanced Tesseract OCR + pre-processing for handwritten Sinhala.',
      'Embeddings via fine-tuned Llama 2.',
      'SQLite storage for offline access.',
    ],
  ),
  FeatureItem(
    icon: Icons.headset_mic,
    title: 'Voice-Based Q&A',
    bullets: [
      'Whisper-based ASR tuned for Sri Lankan accents.',
      'Seamless offline/online handling.',
    ],
  ),
  FeatureItem(
    icon: Icons.summarize,
    title: 'Text Q&A & Summaries',
    bullets: [
      'Sinhala-specific RAG with strict source grounding.',
      'Contextual summarization with citation control.',
    ],
  ),
  FeatureItem(
    icon: Icons.fact_check,
    title: 'Answer Evaluation',
    bullets: [
      'Semantic grading with embeddings + rules.',
      'Explainable feedback and adaptive thresholds.',
    ],
  ),
];
