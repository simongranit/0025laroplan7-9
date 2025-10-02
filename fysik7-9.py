from fpdf import FPDF


# Helper function to generate a PDF with math problems for a specific year
def create_math_pdf(year, questions, font_file):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Registrera din egen font
    pdf.add_font("CustomFont", "", font_file, uni=True)  # Regular stil
    pdf.add_font("CustomFont", "B", font_file, uni=True)  # Bold stil (samma fil om Bold inte finns separat)

    # Använd den registrerade fonten
    pdf.set_font("CustomFont", "B", size=16)  # Bold för titel
    pdf.cell(200, 10, txt=f"Fysikfrågor för Årskurs {year}", ln=True, align="C")
    pdf.ln(10)

    # Lägg till frågor
    pdf.set_font("CustomFont", size=12)  # Regular för frågor
    for i, question in enumerate(questions, start=1):
        pdf.multi_cell(0, 10, f"{i}. {question}")
        pdf.ln(5)

    # Spara PDF
    filename = f"Fysik_Åk{year}.pdf"
    pdf.output(filename, "F")
    return filename


# Yearly questions: A-level
questions_7 = [

"Vad är materia och vilka egenskaper har den?",
"Förklara vad som menas med massa och volym. Hur mäter man dessa storheter?",
"Vad är skillnaden mellan tyngd och massa?",
"Beskriv de tre aggregationsformerna: fast, flytande och gas.",
"Hur påverkar värme ämnens tillstånd och volym?",
"Vad är densitet, och hur kan man räkna ut den för olika material?",
"Vad menas med kraft och vilka enheter används för att mäta den?",
"Ge exempel på olika typer av krafter, såsom gravitationskraft och friktionskraft.",
"Vad innebär begreppet tryck, och hur påverkas trycket av olika faktorer?",
"Hur fungerar hävstänger och andra enkla maskiner?",
"Vad är energi, och vilka olika former av energi finns det?",
"Förklara energiprincipen: energi kan varken skapas eller förstöras.",
"Hur omvandlas energi i vardagliga exempel, såsom i en glödlampa?",
"Vad är ljud, och hur sprider det sig i olika material?",
"Vilka faktorer påverkar ljudets hastighet?",
"Vad är ljus och hur reflekteras det av olika ytor?",
"Hur fungerar enkla optiska instrument som speglar och linser?",
"Vad är skillnaden mellan konvexa och konkava linser?",
"Vad är en skugga, och hur bildas den?",
"Hur kan vi mäta temperatur och vad innebär värmeledning?"
]
questions_8 = [

"Vad är skillnaden mellan hastighet och acceleration?",
"Hur beräknas medelhastighet och momentanhastighet?",
"Förklara Newtons tre rörelselagar med exempel.",
"Vad är arbete och effekt, och hur beräknas de?",
"Hur fungerar mekaniskt arbete i en lutande plan?",
"Vad är värmeenergi och hur sprids den genom ledning, strömning och strålning?",
"Hur påverkas ett föremåls rörelse av krafter som verkar på det?",
"Vilka är de viktigaste formerna av energiomvandlingar i ett vattenkraftverk?",
"Vad är elektrisk ström och spänning? Ge exempel på deras användning.",
"Hur fungerar en elektrisk krets, och vilka komponenter kan ingå?",
"Vad är skillnaden mellan serie- och parallellkoppling?",
"Vad innebär magnetism, och hur används magneter i tekniska tillämpningar?",
"Hur påverkas en kompass av jordens magnetfält?",
"Vad är växelström och likström?",
"Hur fungerar elektromagneter, och var används de?",
"Vad är ljusets brytning och totalreflektion?",
"Hur bildas regnbågar, och vad förklarar deras färger?",
"Vad är ljudstyrka och frekvens, och hur påverkar de ljudupplevelsen?",
"Vad är en ljudvåg, och hur mäter vi ljudets egenskaper?",
"Vilka faktorer påverkar en planets gravitationskraft?"
]
questions_9 = [

"Vad är skillnaden mellan tyngdpunkt och stödyta?",
"Hur påverkas föremål av fritt fall och luftmotstånd?",
"Vad innebär begreppet tröghet?",
"Hur fungerar en hävstång enligt momentlagen?",
"Vad är arbete, energi och effekt, och hur hänger de samman?",
"Vad är skillnaden mellan potentiell och kinetisk energi?",
"Hur fungerar kraftmoment, och vilka praktiska exempel finns?",
"Beskriv principerna för energiproduktion i kärnkraftverk.",
"Vad är elektromagnetisk strålning och vilka typer finns?",
"Hur fungerar induktion och generatorer?",
"Förklara principen bakom transformatorer och deras användning.",
"Vad är halvledare, och hur används de i elektronik?",
"Vad är resistans, och vilka faktorer påverkar den i en elektrisk krets?",
"Hur fungerar en el-motor och en generator?",
"Vad är växelspänning och likspänning, och hur används de?",
"Hur uppstår ljud, och hur kan vi styra ljudvågor?",
"Beskriv universums uppkomst enligt Big Bang-teorin.",
"Vad är skillnaden mellan planet, stjärna och galax?",
"Hur påverkar jordens rotation dygn och årstider?",
"Vad är relativitetsteorin, och hur påverkar den vår förståelse av tid och rum?"
]


# Generate PDFs
font_path = "02587_ARIALMT.ttf"
file_7 = create_math_pdf(7, questions_7, font_path)
file_8 = create_math_pdf(8, questions_8, font_path)
file_9 = create_math_pdf(9, questions_9, font_path)

file_7, file_8, file_9


