# LLM Language Coverage — Deep Search Findings
Date: February 11, 2026

## Language Performance Hierarchy (MMLU-ProX, 2025)

Identical questions tested across languages. Ranking by best achievable accuracy:

| Tier | Languages | Accuracy Range |
|------|-----------|---------------|
| Tier 1: Excellent | English | 70-75% |
| Tier 2: Strong | French, Spanish, Portuguese, German | 65-68% |
| Tier 3: Good | Chinese, Japanese | 63-66% |
| Tier 4: Adequate | Korean, Arabic, Thai, Hindi | 60-63% |
| Tier 5: Weak | Bengali | ~57% |
| Tier 6: Poor | Swahili | ~40-52% |

Gap between English and Swahili: 30+ percentage points.

## Artificial Analysis Multilingual Index (live, Feb 2026)

Top model scores by language (Global-MMLU-Lite, 16 languages):
- English: 95 (Claude Opus 4.6)
- Chinese: 94 (Claude Opus 4.6, Gemini 3 Pro)
- Spanish: 94 (Gemini 3 Pro, Claude Opus 4.6)
- French: 94 (GPT-5.1)
- Hindi: 92 (Claude Opus 4.6)

## Language Ranker (AAAI 2025) — Embedding Similarity to English

LlaMa2 7B ranking (18 languages):
Spanish (0.616) → French (0.592) → Russian (0.589) → Czech (0.587) → German (0.581) → Catalan (0.582) → Dutch (0.569) → Italian (0.567) → Serbian (0.555) → Ukrainian (0.551) → Polish (0.534) → Swedish (0.531) → Vietnamese (0.529) → Portuguese (0.598) → Indonesian (0.577) → Chinese (0.446) → Korean (0.199) → Japanese (0.194)

## African Languages (June 2025 survey)

- 2,000+ African languages exist
- Only 42 have ANY LLM support
- Only 4 consistently supported: Amharic, Swahili, Afrikaans, Malagasy
- 98% of African languages have zero coverage
- 20 active African scripts completely neglected

## Key Stats

- ~7,000 languages spoken worldwide
- Most LLMs trained on ~100 of them
- English = <20% of world's population but ~50% of web content
- 24.3% performance gap between high-resource and low-resource languages (MMLU-ProX)

## Live Dashboards

- Artificial Analysis: https://artificialanalysis.ai/models/multilingual
- AI Language Proficiency Monitor (200 languages): https://huggingface.co/spaces/fair-forward/evals-for-every-language

## Sources

- MMLU-ProX (2025): https://arxiv.org/html/2503.10497v1
- Language Ranker (AAAI 2025): https://arxiv.org/html/2404.11553v1/
- Fortune (July 2025): https://fortune.com/asia/2025/07/15/ai-llm-language-english-cantonese-vietnamese-translation/
- State of LLMs for African Languages (June 2025): https://arxiv.org/abs/2506.02280
- AI Language Proficiency Monitor (July 2025): https://arxiv.org/html/2507.08538v1
