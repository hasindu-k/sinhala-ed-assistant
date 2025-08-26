// lib/presentation/pages/home/widgets/welcome_section.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/theme.dart';
import 'feature_card.dart';
import 'tip_banner.dart';
import 'action_buttons.dart';

class WelcomeSection extends StatelessWidget {
  const WelcomeSection({super.key});

  @override
  Widget build(BuildContext context) {
    final textColor = ThemeUtils.getTextColor(context);
    final secondary = ThemeUtils.getSecondaryTextColor(context);

    return Center(
      child: Padding(
        padding: ThemeUtils.getLargePadding(),
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Title
              Text(
                'Welcome to Sinhala Ed Assistant',
                textAlign: TextAlign.center,
                style: AppTextStyles.displaySmall.copyWith(color: textColor),
              ),
              const SizedBox(height: 12),

              // Subtitle
              Text(
                'Your bilingual educational copilot for Sinhala resources.',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyLarge.copyWith(color: secondary),
              ),

              const SizedBox(height: 24),

              const TipBanner(
                icon: Icons.lightbulb,
                text:
                    'Tip: You can switch Light/Dark/System from Profile → Theme.',
              ),

              const SizedBox(height: 16),

              // Feature cards grid
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 680;
                  final crossAxisCount = isWide ? 2 : 1;

                  return GridView.count(
                    crossAxisCount: crossAxisCount,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    childAspectRatio: isWide ? 3.2 : 2.7,
                    children: const [
                      FeatureCard(
                        icon: Icons.document_scanner,
                        title: 'Sinhala Document Processing & Embedding',
                        bullets: [
                          'Enhanced Tesseract OCR + pre-processing for handwritten Sinhala.',
                          'Embeddings via fine-tuned Llama 2.',
                          'SQLite storage for offline access.',
                        ],
                      ),
                      FeatureCard(
                        icon: Icons.headset_mic,
                        title: 'Voice-Based Q&A',
                        bullets: [
                          'Whisper-based ASR tuned for Sri Lankan accents.',
                          'Seamless offline/online handling.',
                        ],
                      ),
                      FeatureCard(
                        icon: Icons.summarize,
                        title: 'Text Q&A & Summaries',
                        bullets: [
                          'Sinhala-specific RAG with strict source grounding.',
                          'Contextual summarization with citation control.',
                        ],
                      ),
                      FeatureCard(
                        icon: Icons.fact_check,
                        title: 'Answer Evaluation',
                        bullets: [
                          'Semantic grading with embeddings + rules.',
                          'Explainable feedback and adaptive thresholds.',
                        ],
                      ),
                    ],
                  );
                },
              ),

              const SizedBox(height: 20),

              const ActionButtonsRow(),
            ],
          ),
        ),
      ),
    );
  }
}
