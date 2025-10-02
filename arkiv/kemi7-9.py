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
    pdf.cell(200, 10, txt=f"Kemifrågor för Årskurs {year}", ln=True, align="C")
    pdf.ln(10)

    # Lägg till frågor
    pdf.set_font("CustomFont", size=12)  # Regular för frågor
    for i, question in enumerate(questions, start=1):
        pdf.multi_cell(0, 10, f"{i}. {question}")
        pdf.ln(5)

    # Spara PDF
    filename = f"Kemi_Åk{year}.pdf"
    pdf.output(filename, "F")
    return filename


# Yearly questions: A-level
questions_7 = [

"Vad är en atom? Beskriv dess delar och deras egenskaper.",
"Vad är skillnaden mellan ett grundämne och en kemisk förening? Ge exempel.",
"Vilka metoder kan användas för att separera ämnen i en blandning? Ge exempel.",
"Beskriv vattnets kretslopp och de processer som ingår.",
"Vad menas med densitet, och hur kan den beräknas för fasta och flytande ämnen?",
"Förklara begreppen smältpunkt och kokpunkt och deras betydelse.",
"Hur förändras partiklarna i ett ämne när det övergår från fast till flytande form?",
"Vad är en lösning och vilka faktorer påverkar lösligheten av ett ämne?",
"Ge exempel på kemiska reaktioner i din omgivning och förklara hur de sker.",
"Hur kan vi använda indikatorer för att identifiera syror och baser?",
"Vad är skillnaden mellan en fysikalisk förändring och en kemisk reaktion?",
"Beskriv partikelmodellen och hur den förklarar ämnens egenskaper.",
"Vilka säkerhetsregler gäller i ett kemilaboratorium?",
"Vad händer med energin vid en fasövergång, t.ex. smältning eller avdunstning?",
"Hur påverkar temperaturen reaktionshastigheten?",
"Förklara varför vissa ämnen leder elektricitet medan andra inte gör det.",
"Vad är pH-skalan och hur används den för att mäta surhetsgrad?",
"Vilka är de vanligaste gaserna i luften, och hur påverkar de vår miljö?",
"Hur fungerar filtrering, och när används det i vardagen?",
"Vad innebär hållbar utveckling inom kemi?"
]
questions_8 = [

"Vad är skillnaden mellan starka och svaga syror? Ge exempel.",
"Vad händer vid en neutralisationsreaktion? Ge exempel.",
"Hur kan man balansera en kemisk reaktionsformel?",
"Vad är en jon och hur bildas den?",
"Vilka faktorer påverkar hastigheten på en kemisk reaktion?",
"Hur påverkar temperatur och koncentration reaktioners hastighet?",
"Vad är en exoterm och en endoterm reaktion? Ge exempel.",
"Vad är fotosyntesen och varför är den viktig för livet på jorden?",
"Vad är skillnaden mellan en jonförening och en molekylförening?",
"Förklara hur metaller reagerar med syror och vilka gaser som bildas.",
"Hur påverkar syror och baser miljön, till exempel vid försurning?",
"Beskriv hur olika metaller korroderar och hur korrosion kan förebyggas.",
"Vad är en katalysator och hur påverkar den kemiska reaktioner?",
"Vilka är de vanligaste ämnena i jordens atmosfär?",
"Beskriv kolets kretslopp och dess betydelse för ekosystemet.",
"Hur används kemiska analyser för att identifiera okända ämnen?",
"Vilken roll spelar enzymer i kemiska processer i kroppen?",
"Hur påverkar fossila bränslen miljön, och vilka alternativ finns?",
"Vad är en polymer, och hur används polymerer i vår vardag?",
"Förklara begreppen oxidation och reduktion."
]
questions_9 = [
"Vad innebär begreppet kemisk jämvikt? Ge exempel.",
"Vad är elektrolys och hur används det inom industrin?",
"Förklara hur galvaniska celler fungerar och används i batterier.",
"Vilka faktorer påverkar en reaktions jämvikt?",
"Vad innebär oxidation och reduktion, och hur sker dessa reaktioner?",
"Hur framställs järn ur järnmalm, och vilka miljöeffekter har detta?",
"Vad menas med molförhållande i en kemisk reaktion?",
"Vilka gaser bidrar till växthuseffekten, och hur kan den minskas?",
"Beskriv skillnaden mellan kovalent och jonbindning.",
"Vilka metoder används för att rena vatten i en vattenreningsprocess?",
"Hur fungerar en syra-bas-titrering?",
"Beskriv hur organiska föreningar är uppbyggda och varför de är viktiga.",
"Vad är skillnaden mellan fossila och förnybara energikällor?",
"Vilken roll spelar kolväten i vardagskemin och industrin?",
"Hur påverkar kemiska ämnen miljön, t.ex. plaster och bekämpningsmedel?",
"Vad är en katalysator och hur används de i bilar och fabriker?",
"Hur kan vi minska vår kemiska påverkan på miljön?",
"Vad innebär radioaktivitet, och hur används det inom medicin?",
"Hur kan vi balansera redoxreaktioner?",
"Beskriv hur syror och baser påverkar vardagen, exempelvis i matlagning."
]


# Generate PDFs
font_path = "02587_ARIALMT.ttf"
file_7 = create_math_pdf(7, questions_7, font_path)
file_8 = create_math_pdf(8, questions_8, font_path)
file_9 = create_math_pdf(9, questions_9, font_path)

file_7, file_8, file_9


