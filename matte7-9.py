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
    pdf.cell(200, 10, txt=f"Matematikfrågor för Årskurs {year}", ln=True, align="C")
    pdf.ln(10)

    # Lägg till frågor
    pdf.set_font("CustomFont", size=12)  # Regular för frågor
    for i, question in enumerate(questions, start=1):
        pdf.multi_cell(0, 10, f"{i}. {question}")
        pdf.ln(5)

    # Spara PDF
    filename = f"Matematik_Åk{year}.pdf"
    pdf.output(filename, "F")
    return filename


# Yearly questions: A-level
questions_7 = [
    "En rektangel har en omkrets på 24 cm. Sidorna är i förhållandet 1:2. Vad är längden och bredden på rektangeln?",
    "Tre vänner delade på en summa pengar i förhållandet 2:3:5. Om den totala summan var 1000 kr, hur mycket fick var och en?",
    "En kub har en sidlängd på 5 cm. Om kubens volym tredubblas, vad är den nya sidlängden?",
    "En cykel har hjul med en diameter på 70 cm. Hur långt rullar hjulet på ett varv? Ge svaret i meter.",
    "En sjundedel av en klass består av tjejer och resten är killar. Om det totalt finns 28 elever, hur många tjejer och killar finns det?",
    "En person köper en vara för 200 kr exklusive moms. Momssatsen är 25 %. Hur mycket betalar personen totalt?",
    "Summan av två tal är 75 och skillnaden är 15. Vilka är talen?",
    "Rita och beskriv en triangel som har två lika långa sidor och en omkrets på 18 cm.",
    "Skriv talen 2/5, 0,4 och 45 % i storleksordning.",
    "Ett företag ökar sin omsättning med 10 % varje år. Om företagets nuvarande omsättning är 1 miljon, hur stor är omsättningen om två år?",
    "Om du kastar två tärningar, vad är sannolikheten att summan blir 7?",
    "Beräkna produkten av 4/7 och 3/5. Förklara hur du löste det.",
    "En linje har lutningen 3 och går genom punkten (1, 2). Skriv linjens ekvation.",
    "Omkretsen av en cirkel är 31,4 cm. Vad är cirkelns radie? Använd π = 3,14.",
    "Solve for x: 4x - 5 = 15.",
    "Två tal är i förhållandet 3:4. Summan av de två talen är 56. Bestäm talen.",
    "Ett prisma har en bas som är en triangel med en area på 12 cm² och en höjd på 10 cm. Vad är prismans volym?",
    "Räkna ut arean för en halv cirkel med radien 14 cm.",
    "Fyra vänner delar på en pizza i förhållandet 1:2:3:4. Om pizzan väger 1000 g, hur mycket får varje person?",
    "Skriv en steg-för-steg-lösning för att förenkla uttrycket (3x - 2) + 2(2x + 4)."
]

questions_8 = [
    "Lös ekvationen: 2(x + 3) = 14.",
    "Beräkna sannolikheten att dra ett rött kort från en vanlig kortlek utan jokrar.",
    "En rektangulär pool är 10 meter lång och 5 meter bred. Hur mycket vatten behövs för att fylla den om den är 2 meter djup?",
    "Förläng och förenkla uttrycket: (x/3 + 4) + (2x/3 - 1).",
    "En vara som kostar 300 kr är prissänkt med 15 %. Vad är det nya priset?",
    "En funktion ges av f(x) = 2x + 3. Bestäm värdet av f(4).",
    "Rita en graf för y = -2x + 4. Vad är lutningen?",
    "Tre olika tröjor kostar 200 kr, 250 kr och 300 kr. Hur stor är den genomsnittliga kostnaden?",
    "Beräkna medianen av talen 12, 18, 7, 10, 15 och 19.",
    "En kon har en höjd på 10 cm och en basradie på 5 cm. Beräkna volymen.",
    "Ett bolån har en ränta på 2 % årligen. Hur mycket ränta betalar du det första året på ett lån på 1 000 000 kr?",
    "Summan av fem på varandra följande heltal är 100. Vilka är talen?",
    "En triangel har basen 12 cm och höjden 9 cm. Beräkna arean.",
    "Lös ojämlikheten: 3x - 4 > 8.",
    "En cylinder har en höjd på 12 cm och en radie på 5 cm. Vad är cylinderns volym?",
    "Lös systemet av ekvationer: x + y = 10 och 2x - y = 4.",
    "Beräkna andelen elever som gillar matte om 18 av 45 elever valt matte som sitt favoritämne.",
    "Förenkla uttrycket: 5a + 2 - 3a + 7.",
    "Två linjer ges av y = 2x + 3 och y = -x + 4. Bestäm skärningspunkten.",
    "En graf visar att priset på en produkt ökade linjärt med tiden. Efter 3 månader är priset 600 kr och efter 6 månader är priset 1200 kr. Hur mycket ökar priset per månad?"
]

questions_9 = [
    "En rektangel har en bredd som är hälften av dess längd. Om rektangeln har en omkrets på 36 cm, bestäm dess längd och bredd.",
    "Lös ekvationen: x^2 - 5x + 6 = 0.",
    "Beräkna volymen av en pyramid med basarea 50 cm² och höjd 12 cm.",
    "En cykel ökar sin hastighet linjärt från 10 km/h till 30 km/h under en tid på 10 minuter. Bestäm accelerationen.",
    "Räkna ut värdet av cos(60°) och sin(45°).",
    "Förenkla uttrycket: (2x^2 - x) + (3x - 4x^2).",
    "Bestäm lösningen till systemet: 3x - y = 5 och 2x + y = 10.",
    "En kon har volymen 100 cm³ och höjden 6 cm. Bestäm basens radie.",
    "Ett lån minskar med 2 % i månaden. Hur mycket återstår av ett lån på 500 000 kr efter ett år?",
    "Lös ekvationen: |x - 3| = 7.",
    "Ett laboratorium upptäcker att en population av bakterier fördubblas varannan timme. Om det finns 100 bakterier vid start, hur många finns efter 8 timmar?",
    "Räkna ut arean av en triangel med sidorna 7 cm, 8 cm och 9 cm. Använd Herons formel.",
    "Skriv ekvationen för en cirkel med centrum (2, -3) och radien 5.",
    "Om A = {1, 2, 3} och B = {2, 3, 4}, bestäm unionen och snittet av A och B.",
    "Lös ojämlikheten: 2(x - 1) ≥ 3x + 2.",
    "Två linjer är parallella och har lutningen 4. Vad är avståndet mellan dem om deras y-axel skärningar är -3 och 5?",
    "En fabrik producerar en vara med en kostnad C(x) = 5x^2 + 10x + 50. Hur förändras kostnaden när produktionen ökar från 10 till 20 enheter?",
    "Ett prisma har en bas som är en trapezoid med baslängder 6 cm och 10 cm, höjd 4 cm. Prismans höjd är 8 cm. Beräkna dess volym.",
    "Beräkna den andra derivatan för funktionen f(x) = x^3 - 3x^2 + 2x.",
    "Lös differentialekvationen: dy/dx = 3x + 2, där y(0) = 1."
]

# Generate PDFs
font_path = "02587_ARIALMT.ttf"
file_7 = create_math_pdf(7, questions_7, font_path)
file_8 = create_math_pdf(8, questions_8, font_path)
file_9 = create_math_pdf(9, questions_9, font_path)

file_7, file_8, file_9
