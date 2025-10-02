from __future__ import annotations

from collections.abc import Iterable

from fpdf import FPDF

from .models import Question


class QuestionPDF(FPDF):
    def header(self) -> None:  # noqa: D401
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, self.title, ln=1, align="C")
        self.ln(2)

    def footer(self) -> None:  # noqa: D401
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.cell(0, 10, f"Sida {self.page_no()}", align="C")


def render_questions_to_pdf(questions: Iterable[Question], title: str, include_solutions: bool) -> bytes:
    pdf = QuestionPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(title)
    pdf.add_page()

    pdf.set_font("Helvetica", size=11)
    for idx, question in enumerate(questions, start=1):
        pdf.multi_cell(0, 8, f"{idx}. {question.stem}")
        if question.choices:
            for choice in question.choices:
                pdf.multi_cell(0, 6, f"   - {choice}")
        if include_solutions:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 6, f"Svar: {question.answer}")
            pdf.multi_cell(0, 6, f"Förklaring: {question.solution_explainer}")
            pdf.set_font("Helvetica", size=11)
        pdf.ln(4)

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return pdf_bytes
