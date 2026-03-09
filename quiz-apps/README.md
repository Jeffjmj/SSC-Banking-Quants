# quiz-apps

Simple webapp for Siddhi quiz data (`question_text`, `options`, `correct_option`, `explanation`).

## Run locally

### Recommended (from repo root)
```bash
python -m http.server 8010
```
Then open:
- `http://localhost:8010/quiz-apps/index.html`

### Alternative (serve only quiz-apps folder)
If you run a server inside `quiz-apps/`, copy the dataset file into this folder:
- `ssc_math_numeric_qna_clean.json`

The app tries these paths in order:
1. `../Siddhi/ssc_math_numeric_qna_clean.json`
2. `/Siddhi/ssc_math_numeric_qna_clean.json`
3. `./ssc_math_numeric_qna_clean.json`
