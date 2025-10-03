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
  question_bank.py
  recommendations.py
  pdf.py
  models.py
llm/
  base.py
  deepseek.py
content/
  questions/
  generated/
  quizzes/
```

### Skapa frågebanker från läroplanen

Använd `services.question_bank` för att generera större frågebanker med hjälp av DeepSeek.
Modulen läser avsnitt ur PDF:erna `Matematik_Åk7-9.pdf` och sparar resultatet i
`content/generated/` som sedan laddas in automatiskt av innehållslagret.

Exempel på användning i ett Python-skal:

```python
from services.question_bank import CurriculumQuestionBankBuilder, QuestionBankRequest

builder = CurriculumQuestionBankBuilder()
builder.build(QuestionBankRequest(grade=7, topics=["Algebra"], total_questions=80))
```

Sätt `refresh=True` i `QuestionBankRequest` för att skriva över en befintlig fil.

## Tester

Projektet använder `pytest`. Kör `pytest` eller `make test` för att verifiera funktionalitet.

> 💡 **Felsökning:** Om `pytest` klagar på saknade paket som `pypdf` eller `respx`, saknas
> sannolikt grundberoendena i din miljö. Kör `pip install -e .[dev]` (eller `make dev`)
> en gång innan du kör testerna så installeras allt som behövs.
