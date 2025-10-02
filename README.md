# Matte Diagnostik (Åk 7–9)

En webbaserad matte-övningsapp för årskurs 7–9. Projektet är uppdelat i flera faser
som täcker innehållshantering, diagnostiklogik, AI-feedback och PDF-export.

## Kom igång

1. Skapa och aktivera ett Python 3.11-venv.
2. Installera beroenden:
   ```bash
   pip install -e .[dev]
   ```
3. Kopiera `.env.example` till `.env` och fyll i `DEEPSEEK_API_KEY`.
4. Starta Streamlit:
   ```bash
   streamlit run app/streamlit_app.py
   ```

## Make-kommandon

```bash
make dev   # Installerar projektet i utvecklingsläge (pip install -e .[dev])
make lint  # Kör ruff
make type  # Kör mypy
make test  # Kör pytest
```

## Struktur

```
app/
  streamlit_app.py
  pages/
services/
  content.py
  diagnostics.py
  recommendations.py
  pdf.py
  models.py
llm/
  base.py
  deepseek.py
content/
  questions/
  quizzes/
```

## Tester

Projektet använder `pytest`. Kör `pytest` eller `make test` för att verifiera funktionalitet.
