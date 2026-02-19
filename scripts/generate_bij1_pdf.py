"""
Generate a PDF of the BIJ1 Amsterdam 2026 election program
by combining all topic pages scraped from amsterdam.bij1.org/programma-2026.
"""

from fpdf import FPDF


FONT_DIR = "/System/Library/Fonts/Supplemental"


class BIJ1PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_font("Arial", "", f"{FONT_DIR}/Arial.ttf")
        self.add_font("Arial", "B", f"{FONT_DIR}/Arial Bold.ttf")
        self.add_font("Arial", "I", f"{FONT_DIR}/Arial Italic.ttf")
        self.add_font("Arial", "BI", f"{FONT_DIR}/Arial Bold Italic.ttf")

    def header(self):
        self.set_font("Arial", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "BIJ1 Amsterdam \u2014 Verkiezingsprogramma 2026", align="R")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Pagina {self.page_no()}", align="C")

    def chapter_title(self, title: str, subtitle: str = ""):
        self.add_page()
        w = self.epw
        self.set_fill_color(30, 30, 30)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 18)
        self.multi_cell(w, 10, title, fill=True, padding=(6, 4, 4, 4))
        if subtitle:
            self.set_fill_color(60, 60, 60)
            self.set_font("Arial", "I", 12)
            self.multi_cell(w, 8, subtitle, fill=True, padding=(3, 4, 4, 4))
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section_heading(self, text: str):
        self.ln(3)
        self.set_font("Arial", "B", 12)
        self.set_text_color(20, 20, 20)
        self.multi_cell(self.epw, 7, text)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def sub_heading(self, text: str):
        self.ln(2)
        self.set_font("Arial", "B", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(self.epw, 6, text)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        self.set_font("Arial", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(self.epw, 5.5, text)
        self.ln(1)

    def bullet_item(self, text: str):
        self.set_font("Arial", "", 10)
        self.set_text_color(30, 30, 30)
        indent = 4
        self.set_x(self.l_margin + indent)
        self.multi_cell(self.epw - indent, 5.5, f"\u2022  {text}")
        self.set_x(self.l_margin)


def build_pdf():
    pdf = BIJ1PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(18, 15, 18)

    # ──────────────────────────────────────────────
    # COVER PAGE
    # ──────────────────────────────────────────────
    pdf.add_page()
    w = pdf.epw
    pdf.set_font("Arial", "B", 32)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(30)
    pdf.cell(w, 14, "BIJ1 Amsterdam", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "B", 22)
    pdf.cell(w, 10, "Verkiezingsprogramma 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Arial", "I", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(w, 8, "Gemeenteraadsverkiezingen Amsterdam", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(w, 8, "18 maart 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_font("Arial", "", 11)
    pdf.cell(w, 6, "Bron: amsterdam.bij1.org/programma-2026", align="C", new_x="LMARGIN", new_y="NEXT")

    # ──────────────────────────────────────────────
    # 1. INLEIDING
    # ──────────────────────────────────────────────
    pdf.chapter_title("Inleiding", "Amsterdam voor alle mensen")
    pdf.section_heading("Voorwoord van Tofik Dibi")
    pdf.body_text(
        "Amsterdam is een stad van dromen, creativiteit en culturele diversiteit, waar mensen met "
        "verschillende achtergronden samenleven. Maar de scheidslijn tussen Amsterdammers wordt "
        "scherper — tussen rijk en arm, tussen wit en niet-wit. Investeringen in openbaar vervoer "
        "bevoordelen de binnenstad, terwijl Zuid en Oost diensten verliezen."
    )
    pdf.body_text(
        "BIJ1 strijdt voor een Amsterdam voor alle mensen. Dat betekent concrete actie op "
        "dekolonisatie, eerlijke economie en echte gelijkheid. Wonen, zorg en cultuur zijn "
        "rechten — geen verdienmodellen. Ons programma is opgebouwd rond drie pijlers: "
        "radicale gelijkwaardigheid, ecosocialistische lokale economie, en democratie van onderop."
    )

    # ──────────────────────────────────────────────
    # 2. ANTIRACISME EN DEKOLONISATIE
    # ──────────────────────────────────────────────
    pdf.chapter_title("Antiracisme en Dekolonisatie", "Van excuses naar daden")
    pdf.body_text(
        "BIJ1 gelooft in een stad waar gelijke waardigheid geen abstract ideaal is, maar "
        "dagelijkse realiteit. De aanpak combineert progressieve actie met inclusieve dialoog."
    )

    pdf.section_heading("1. Racisme en discriminatie als topprioriteit bestrijden")
    for item in [
        "Elke wethouder ontwikkelt uitsluitingspreventiebeleid binnen zijn portefeuille.",
        "Adviesraad Gelijkwaardigheid verzamelt continu ervaringen vanuit gemeenschappen.",
        "In 2030 weerspiegelen gemeentelijke organisaties de demografische diversiteit van Amsterdam.",
        "Elk departement krijgt een antiracismecoördinator.",
        "Jaarlijkse racismemonitoring met klachten, uitsluitingspraktijken en doorstroom.",
        "Discriminatoir gedrag heeft directe consequenties — opleiding eerst, daarna ontslag.",
        "Zwarte Piet verboden via gemeentelijke verordening met financiële boetes.",
        "Discriminerende bedrijven op zwarte lijst; recidivisten verliezen opdrachten.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("2. Racistisch geweld bestrijden")
    for item in [
        "Etnisch profileren is onacceptabel; alle politiestops worden gedocumenteerd en geanalyseerd.",
        "Racistisch politiegeweld leidt tot disciplinaire maatregelen of ontslag.",
        "Onafhankelijk klachtenmechanisme met diverse gemeenschapsleden.",
        "Aanslagen op moskeeën, synagogen en LGBTQ+-plekken zijn topprioriteit voor politie.",
        "Alle religieuze gebouwen onder dreiging krijgen gemeentegefinancierde beveiliging.",
        "Slavernij- en kolonisatieonderwijs is verplicht, niet optioneel.",
        "Keti Koti (1 juli) wordt officiële gemeentelijke herdenkings- en feestdag.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("3. Activisme waarderen")
    for item in [
        "Uitgebreide subsidies voor duurzame grassroots organisaties.",
        "Meerjarige kernfinanciering vervangt tijdelijke projectsubsidies.",
        "Gemeentelijke panden beschikbaar voor organisaties uit gemarginaliseerde gemeenschappen.",
        "Bureaucratische drempels voor demonstraties verlaagd.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("4. Herdenking en herstelrecht")
    for item in [
        "Amsterdam vertaalt excuses voor slavernij naar materieel herstel voor nakomeling.",
        "Herstelfonds voor onderwijs, economische ontwikkeling, traumaprojecten en symbolische betalingen.",
        "Indonesische onafhankelijkheidsdag (17 augustus 1945) officieel erkend.",
        "Dekolonisatiecommissie herziet straatnamen, bruggen en standbeelden.",
        "4 mei-herdenking uitgebreid met slachtoffers van Indonesisch koloniaal geweld.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("5. Internationale solidariteit")
    for item in [
        "Geen zusterstadrelaties met regimes die koloniale bezetting of apartheid praktiseren.",
        "Samenwerking met Tel Aviv en Beijing als zusterstad beëindigd.",
        "Zusterstadrelatie met Paramaribo hersteld.",
        "Wapenproducenten en militaire technologiehandelaars mogen zich niet in Amsterdam vestigen.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 3. WONEN EN LEVEN
    # ──────────────────────────────────────────────
    pdf.chapter_title("Wonen en Leven", "Wonen als recht, niet als markt")
    pdf.body_text(
        "Amsterdam telt 11.065 dakloze bewoners terwijl 21.170 woningen leegstaan. BIJ1 wil "
        "de verschuiving maken van woningmarkt naar publieke volkshuisvesting."
    )

    pdf.section_heading("Betaalbaar en beschikbaar wonen")
    for item in [
        "Gemeentelijk woningbedrijf bouwt sociale en middenhuurwoningen zonder winstdruk.",
        "Norm: '100% sociaal waar mogelijk', vervangt de 40-40-20 norm.",
        "Strikte middenhuurgrens van €800–€1.100 per maand.",
        "Nul-verplaatsingsbeleid bij renovaties; recht op terugkeer gegarandeerd.",
        "Verhuurvergunning verplicht voor eigenaren van meerdere woningen.",
        "Urgente onderhoudsproblemen binnen 48 uur opgelost via noodteam.",
        "Housing First-aanpak om uitzettingen te voorkomen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Inclusief wonen")
    for item in [
        "200 nieuwe rolstoeltoegankelijke woningen voor 2030.",
        "15% van nieuwbouw voldoet aan universele ontwerpstandaarden.",
        "Geïntegreerde zorgvoorzieningen binnen woongebouwen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Klimaatrechtvaardig wonen")
    for item in [
        "Energielabel C voor alle sociale huurwoningen binnen vier jaar.",
        "Gemeentelijk energiebedrijf opgericht in 2026.",
        "Prioriteit voor vergroening in kwetsbare wijken.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 4. KLIMAAT EN GROEN
    # ──────────────────────────────────────────────
    pdf.chapter_title("Klimaat en Groen", "Klimaatrechtvaardigheid nu")
    pdf.body_text(
        "BIJ1 pleit voor klimaatrechtvaardigheid, niet louter klimaatneutraliteit. Jaarlijks "
        "sterven 12.000 mensen in Nederland vroegtijdig aan luchtvervuiling. Fossiele "
        "afhankelijkheid vindt zijn wortels in het kolonialisme van de 19e eeuw."
    )

    pdf.section_heading("Gezondheidsschade vervuiling")
    for item in [
        "Schiphol reduceert naar 300.000 vliegbewegingen per jaar.",
        "Onmiddellijk PFAS-emissieverbod; PFAS gevonden in Amsterdams drinkwater.",
        "ICL-sluiting vanwege aanhoudende overtredingen en ligging op Palestijns grondgebied.",
        "Eén op de vijf astmatische kinderen in Nederland lijdt aan luchtvervuiling.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Een rechtvaardig energiesysteem")
    for item in [
        "Klimaatneutraliteit in 2030 (niet 2050); degrowth als leidend principe.",
        "Alle gebouwen fossielvrij voor 2030.",
        "Verplichte zonnepanelen en groene daken op nieuwbouw.",
        "Actieve ondersteuning voor energiecoöperaties.",
        "Geen nieuwe datacenters tenzij essentieel voor vermindering big-tech-afhankelijkheid.",
        "Haven duurzaam en fossielvrij voor 2030.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Groen voor alle Amsterdammers")
    for item in [
        "Gegarandeerde toegankelijke groene ruimte voor elke bewoner.",
        "Bescherming van grote, oude bomen met monumentenstatus.",
        "Lutkemeerpolder wordt biologisch landbouwland.",
        "Restaurantbezoeken gestimuleerd naar lokale, duurzame inkoop.",
        "Geen nieuwe slachthuizen; gemeentelijke catering volledig veganistisch.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 5. VEILIGHEID
    # ──────────────────────────────────────────────
    pdf.chapter_title("Veiligheid", "Een veilige stad voor iedereen")
    pdf.body_text(
        "BIJ1 is een abolitionistische partij: echte veiligheid komt voort uit het wegwerken van "
        "ongelijkheden — niet uit meer politie of controle. Solidariteit, zorg en preventie "
        "staan centraal."
    )

    pdf.section_heading("Politie en veiligheid")
    for item in [
        "Meldpunt voor politiegeweld en discriminatie.",
        "Gespecialiseerde politie-eenheid voor discriminatiezaken.",
        "Bodycams voor alle agenten; etnisch profileren gestopt.",
        "Onafhankelijk klachtenmechanisme met diverse gemeenschapsleden.",
        "Boa's zonder wapens.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Gendergerelateerd geweld en LHBTIQ+-veiligheid")
    for item in [
        "Uitgebreide anti-geweldsprogramma's in samenwerking met gemeenschapsorganisaties.",
        "Uitgebreide opvangcapaciteit voor overlevenden van huiselijk geweld.",
        "Gespecialiseerde politietraining; toegewijde opvang voor dakloze LGBTQ+-personen.",
        "Cruisinggebieden erkend als gemeenschapsruimten.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Investeren in plaats van handhaven")
    for item in [
        "Investering in maatschappelijk werk, talentontwikkeling en buurtpreventieprogramma's.",
        "Herstelrecht als alternatief voor strafrechtelijke vervolging.",
        "Beëindigen van de 'Top400'-aanpak en gerelateerde targetingprogramma's.",
        "Amsterdam stopt met het bijhouden van lijsten van 'geradicaliseerde' activisten.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 6. WERK EN INKOMEN
    # ──────────────────────────────────────────────
    pdf.chapter_title("Werk en Inkomen", "Eerlijk werk, eerlijke stad")
    pdf.body_text(
        "6,6% van de Amsterdammers leefde in 2024 onder de armoedegrens — het dubbele van het "
        "landelijk gemiddelde. Meer dan de helft van deze arme bewoners werkt; ze verdienen "
        "simpelweg te weinig."
    )

    pdf.section_heading("Lonen en koopkracht")
    for item in [
        "Minimumloon van minimaal €19 per uur, zonder jeugdtarief.",
        "Inkomensdrempel voor gezinstoelagen verhoogd van 130% naar 150% sociaal minimum.",
        "Gelijke stagevergoeding ongeacht leeftijd.",
        "Prioriteit voor vaste contracten boven tijdelijke.",
        "Platformbedrijven aangesproken op schijnzelfstandigheid.",
        "Fair Hospitality-keurmerk voor bedrijven met vaste contracten.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Bijstand en re-integratie")
    for item in [
        "Verplichte tegenprestaties afgeschaft; vrijwilligerswerk wordt vrijwillig.",
        "Inkomenstoeslag van €250 per maand zonder bijstandskorting.",
        "Sancties vervangen door begeleiding.",
        "Handhavingsonderzoeken gericht op kwetsbare mensen gestopt.",
        "Onafhankelijke ombudspersoon met eigen klachtenloket.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Sekswerk: decriminalisatie en veiligheid")
    for item in [
        "Nieuwe regelgeving ontwikkeld mét sekswerkcollectieven.",
        "Meer vergunde en onvergunde werklocaties (75% verloren sinds 2000).",
        "Weerstand tegen discriminerende nationale wetgeving (Wgts, Wrs).",
        "Sekswerkersloket: digitaal platform voor rechtenschendingen.",
        "Bankpartnerschappen om financiële uitsluiting te voorkomen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Arbeidsmigratie en ongedocumenteerden")
    for item in [
        "Strenge kwaliteitseisen voor migrantenhuisvesting met gemeentelijke vergunningen.",
        "Regionaal meldpunt voor arbeidsuitbuiting in meerdere talen.",
        "Alleen gecertificeerde uitzendbureaus (SNF, SNA) voor gemeente.",
        "Fysiek loket voor recent gearriveerde migranten voor BRP-inschrijving en rechten.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 7. ZORG EN WELZIJN
    # ──────────────────────────────────────────────
    pdf.chapter_title("Zorg en Welzijn", "Zorg is geen verdienmodel")
    pdf.body_text(
        "Gezondheidsverschillen in Zuidoost, Noord en Nieuw-West zijn gedocumenteerd. BIJ1 "
        "verwerpt winstgedreven zorgmodellen en dure consultants. Kwalitatieve zorgverleners "
        "behouden vereist economische zekerheid, eerlijk loon en stabiele contracten."
    )

    pdf.section_heading("Toegankelijke zorg voor iedereen")
    for item in [
        "Gestroomlijnde regelgeving voor betere toegankelijkheid van programma's.",
        "Verbeterde diensten voor transgenderpersonen, migranten, sekswerkers en daklozen.",
        "Gelijke vertegenwoordiging van ervaringsdeskundigheid en professionele expertise.",
        "Meertalige informatie en leesvaardigheidsondersteuning.",
        "Bescherming tegen digitale barrières voor kwetsbare groepen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Diversiteit en inclusie in de zorg")
    for item in [
        "Verplichte diversiteitstraining voor gemeentelijk en zorgpersoneel.",
        "Respectvolle behandeling van non-binaire personen met zelfgekozen voornaamwoorden.",
        "Transgenderzorg geïntegreerd in gemeentelijke gezondheidsplanning.",
        "HIV-zichtbaarheidscampagnes gericht op risicogroepen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("WMO en GGZ")
    for item in [
        "Afschaffing eigen bijdragen voor bewoners met stadskaart.",
        "Verschuiving van aanbesteding naar subsidies en lokale partnerschappen.",
        "Seksuele zorg erkend als fundamenteel recht voor gehandicapten.",
        "Informed consent als standaard; onderzoek naar niet-medicamenteuze interventies.",
        "Geen 'harde overgangen' bij leeftijd 18; woonbegeleiding voor 18-23 jarigen.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 8. ZELFBESCHIKKING EN TOEGANKELIJKHEID
    # ──────────────────────────────────────────────
    pdf.chapter_title("Zelfbeschikking en Toegankelijkheid",
                       "Een radicaal gelijkwaardige stad is toegankelijk")
    pdf.body_text(
        "Amsterdam kent toegangsbarrières: smalle drukke stoepen, gebouwen zonder lift, "
        "complexe gemeentecommunicatie. BIJ1 stelt: de stad past zich aan aan de bewoner — "
        "niet andersom."
    )

    pdf.section_heading("Toegankelijkheid openbare ruimte en gebouwen")
    for item in [
        "Mensen met een beperking betrekken bij toegankelijkheidsplanning met vetorecht.",
        "CROW-toegankelijkheidsnormen gehaald in 2030.",
        "Gemeentelijke gebouwen toegankelijk met liften, oprijplaten en informatiesystemen.",
        "Gratis, genderneutrale, rolstoeltoegankelijke toiletten in de hele stad.",
        "Gemeentecommunicatie op B1-taalniveau in grotere, leesbare lettertypen.",
        "Documenten in gesproken en braillevoringen beschikbaar.",
        "Prikkelarme winkeluren voor autistische en sensorisch gevoelige personen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Lichamelijke autonomie")
    for item in [
        "Veilige toegang tot abortuszorg; politie beschermt kliniekentoegang.",
        "Noodfonds voor ongedocumenteerde migranten die abortuszorg zoeken.",
        "ABA- en DTT-behandelingen voor autistische kinderen afgebouwd (beleid sinds 2025).",
        "Gelaatsbedekkende kledingverboden niet gehandhaafd door gemeente.",
        "Gemeenteambtenaren vrije keuze religieuze feestdagen.",
        "Verzet tegen herinstelling dienstplicht; rechtsbijstand voor gewetensbezwaarden.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 9. VERKEER EN VERVOER
    # ──────────────────────────────────────────────
    pdf.chapter_title("Verkeer en Vervoer",
                       "Bereikbaar, toegankelijk en verkeersveilig Amsterdam")
    pdf.body_text(
        "Openbaar vervoer kost te veel voor veel bewoners; sommige haltes zijn niet "
        "rolstoeltoegankelijk. BIJ1 streeft naar gratis OV voor kwetsbare groepen en een "
        "Amsterdam voor fietsers en voetgangers."
    )

    pdf.section_heading("Gratis, kwaliteits- en toegankelijk OV")
    for item in [
        "Gratis OV voor jongeren, senioren en bewoners tot 150% van het sociaal minimum.",
        "Gelijke OV-kwaliteit in alle stadsdelen.",
        "Metro-lijn 53 niet gesloten; lijn 51 verlengd naar Isolatorweg-Gaasperplas.",
        "Nachtvervoer uitgebreid voor nachtploeg- en vroegwerkers.",
        "Maximaal 350 meter loopafstand tot dichtstbijzijnde OV-halte.",
        "Volledige toegankelijkheid alle bestaande haltes voor 2027.",
        "€19 minimumloon voor alle OV-medewerkers in gemeente.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Ruimte voor voetgangers en fietsers")
    for item in [
        "Eenrichtingsverkeer voor auto's binnen de A10.",
        "Rood asfalt fietspaden minimaal 2,5 meter breed.",
        "Uitbreiding fietsparkeergelegenheid.",
        "Inkomensgebonden fietsaankoopsubsidies voor lage inkomens.",
        "Gratis fietslessen voor niet-fietsers; alle basisschoolleerlingen doen praktisch fietsexamen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Schiphol")
    for item in [
        "Onmiddellijk verbod op binnenlandse vluchten en nachtvluchten.",
        "Geleidelijke afbouw totaal vliegverkeer.",
        "Geen gemeentelijke medewerking aan luchthavenuitbreiding.",
        "Vliegroutes aangepast om oervliegen boven de stad te vermijden.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 10. ARMOEDE
    # ──────────────────────────────────────────────
    pdf.chapter_title("Armoede", "Van overleven naar leven")
    pdf.body_text(
        "16% van de huishoudens leeft onder de armoedegrens; in Zuidoost 22%. Eén op zes "
        "kinderen groeit op in huishoudens zonder voldoende middelen. Armoede is een gevolg "
        "van politieke keuzes — niet van persoonlijk falen."
    )

    pdf.section_heading("Bestaanszekerheid en menswaardige minimumstandaard")
    for item in [
        "Gemeentelijke minimumstandaarden voor bestaanszekerheid.",
        "Crisisfonds voor urgente behoeften zonder aanvraagprocedures.",
        "Gratis hygiëneproducten op aangewezen locaties.",
        "Jaarlijkse Armoede-atlas voor documentatie van ongelijkheid per wijk.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Eerlijke, toegankelijke regelingen")
    for item in [
        "Stadskaart uitgebreid tot 150% sociaal minimum.",
        "Gratis menstruatieproducten en anticonceptie via stadskaart.",
        "Extra steun voor eenoudergezinnen.",
        "Neveninkomstentoeslag van €500 per maand zonder bijstandskorting.",
        "Onmiddellijk voorschot bij bijstandsaanvraag.",
        "Gemeente dekt volledige zorgkosten.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Schulden en voedselzekerheid")
    for item in [
        "Alomvattende aanpak voor formele en informele schulden.",
        "Kwijtschelding van gemeentelijke schulden.",
        "Voedselveiligheid als recht via partnerschappen.",
        "10% regionaal voedsel inkopen voor 2030.",
        "Gratis schoolmaaltijden het hele jaar, ook in vakanties.",
        "50% van gemeentelijk groen wordt eetbaar.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 11. ECONOMIE
    # ──────────────────────────────────────────────
    pdf.chapter_title("Economie", "Een economie die werkt voor iedereen")
    pdf.body_text(
        "BIJ1 streeft naar een ecosocialistische lokale economie: circulair, duurzaam en "
        "solidair georganiseerd. Publieke samenwerking vervangt marktkrachten. Grote "
        "bedrijfsmacht moet verminderen; coöperaties en lokale, sociale, duurzame ondernemingen "
        "krijgen meer ruimte."
    )

    pdf.section_heading("Collectieve en coöperatieve ondernemingen")
    for item in [
        "Geen nieuwe multinationals, grote distributiecentra of datacenters.",
        "Wapenproducenten en brievenbusmaatschappijen worden verdreven.",
        "Gemeentelijke subsidies die multinationals aantrekken worden beëindigd.",
        "10% belasting op dividenden van bedrijven met hoofdkantoor in Amsterdam.",
        "Gemeentelijke coöperatieve bank opgericht — bewoners zijn mede-eigenaar.",
        "Coöperatieve incubator: half-gemeentelijk, half-burgermaatschappij.",
        "Non-profit buurtsupers: gezonde maaltijden en basislevensmiddelen tegen sociale tarieven.",
        "Kleine leningen voor starters in Nieuw-West, Noord en Zuidoost.",
        "Gemeente verkoopt geen gemeentegrond of -vastgoed; koopt waar mogelijk bij.",
        "Massatoerisme beperkt: maximaal 7 dagen Airbnb; geen nieuwe hotelvergunningen.",
        "Belasting op dividenden, lege panden harder belast.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 12. ASIEL EN MIGRATIE
    # ──────────────────────────────────────────────
    pdf.chapter_title("Asiel en Migratie", "Geen mens is illegaal")
    pdf.body_text(
        "BIJ1 pleit voor een stad waar iedereen — ongeacht verblijfsstatus of documenten — "
        "waardigheid en gelijke rechten heeft. Amsterdam positioneert zich als Vrijhaven Stad "
        "met onvoorwaardelijke steun."
    )

    pdf.section_heading("Amsterdam zegt NEE tegen uitzettingen")
    for item in [
        "Nieuwkomers krijgen gelijke rechten als bewoners.",
        "Verzet tegen detentie, deportatie en georganiseerde controles op ongedocumenteerden.",
        "Beperkingen op politie-identiteitscontroles gericht op uitzetting.",
        "Gemeentelijke diensten garanderen veilige toegang zonder deportatierisico.",
        "Verzet tegen detentiecentrum Schiphol en uitzettingsvluchten.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Veilig dak, voedsel en zorg voor iedereen")
    for item in [
        "Onvoorwaardelijke 24-uurs opvang het hele jaar.",
        "Kindvriendelijke, stabiele asielaccommodatie.",
        "Gespecialiseerde ondersteuning voor LGBTQI+-ongedocumenteerden.",
        "Politietraining over vluchtelingentrauma.",
        "Universele toegang tot voedselbanken.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Werk, onderwijs en cultuur voor iedereen")
    for item in [
        "Gegarandeerde werkgelegenheid vanaf dag één.",
        "Gratis taalles tot C1-niveau.",
        "MBO-toegang voor ongedocumenteerde jongeren met gemeentelijke beurzen.",
        "Introductie van 'Amsterdampas' als officieel stadsidentiteitsbewijs.",
        "Permanente verblijfsvergunning voor Surinaamse voormalige Nederlandse staatsburgers.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 13. ONDERWIJS EN KANSENGELIJKHEID
    # ──────────────────────────────────────────────
    pdf.chapter_title("Onderwijs en Kansengelijkheid",
                       "Dekoloniseer het Nederlandse onderwijs")
    pdf.body_text(
        "Het huidige onderwijssysteem werkt ongelijkheid in de hand. Afkomst en inkomen van "
        "opvoeders bepalen schoolsucces. Leerlingen met een 'niet-westerse migratieachtergrond' "
        "en leerlingen uit kwetsbare milieus hebben structureel te maken met slecht onderwijs, "
        "achterstelling en discriminatie."
    )
    pdf.body_text(
        "BIJ1 staat achter onze leraren. In Amsterdam is er een groot tekort aan leraren; "
        "scholen met de meeste kwetsbare leerlingen lijden hier het meest onder."
    )

    pdf.section_heading("Antidiscriminatie- en diversiteitsbeleid in het onderwijs")
    for item in [
        "Gemeentelijk onderzoek naar institutioneel racisme bij onderwijsinstellingen.",
        "Elke instelling krijgt een antidiscriminatie- en diversiteitscommissie.",
        "Inclusief lesmateriaal zonder koloniale taal of stereotyperingen.",
        "Slavernijverleden en koloniale geschiedenis structureel in curriculum.",
        "Scholen actief betrokken bij Keti Koti, 4 en 5 mei, IDAHOT.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Pak onjuiste schooladviezen, discriminatie en segregatie aan")
    for item in [
        "Onafhankelijk instituut biedt bindende second opinion voor schooladviezen.",
        "Thuissituatie mag geen rol spelen bij schooladvies.",
        "Ouders actief betrokken en geïnformeerd over ontwikkeling kind vanaf groep 4.",
        "Testen op hoogbegaafdheid, ASS en neurodivergentie toegankelijk voor iedereen.",
        "Ouderbijdrage afgeschaft om sociale uitsluiting te voorkomen.",
        "Gratis OV voor scholieren VO en MBO.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Sta achter onze leraren")
    for item in [
        "Extra subsidie en bonussen voor leraren op scholen met lerarentekorten.",
        "Gemeente helpt scholen met administratie en ICT-taken.",
        "Deel van sociale huurwoningen gereserveerd voor onderwijspersoneel.",
        "BIJ1 steunt PO in actie en overige stakingen in het onderwijs.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 14. KUNST EN CULTUUR
    # ──────────────────────────────────────────────
    pdf.chapter_title("Kunst en Cultuur", "De stad die samen maakt")
    pdf.body_text(
        "Cultuur is geen luxe of marketingtool, maar essentiële publieke infrastructuur. "
        "Toch bedraagt het cultureel aanbod in het centrum 3,7 m² per bewoner, "
        "versus 0,61 m² in Nieuw-West en 0,94 m² in Zuidoost. "
        "Slechts 4,2% van het kunstbudget bereikt Zuidoost, waar 10% van Amsterdam woont."
    )

    pdf.section_heading("Gelijke toegang, ongelijke investering")
    for item in [
        "Groter aandeel kunstfinanciering naar achtergestelde stadsdelen.",
        "15.000+ m² extra culturele ruimte in Zuidoost voor 2030.",
        "Gemeentelijke investering van €140 per bewoner in alle stadsdelen.",
        "Alle gesubsidieerde instellingen betalen leefbaar loon (€16,50/uur) vanaf 2027.",
        "30% leidinggevende functies bezet door mensen met migratieachtergrond voor 2030.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Culturele infrastructuur")
    for item in [
        "Elk stadsdeel minimaal 0,25 m² broedplaatsruimte per bewoner.",
        "Gesubsidieerde huur maximaal 50% van marktprijs; minimaal 10 jaar contracten.",
        "Nieuwe Bijlmer Park Theater (6.600-7.000 m²) klaar in 2030.",
        "Poppodium (500-1.000 capaciteit) in 2028.",
        "OBA Next (8.500 m²) in 2027-2028.",
        "Nationaal Slavernijmuseum opening ~2029/30 met governance door nakomeling.",
        "€1 miljoen per jaar voor Sociale Veiligheidsgroepen in de nachteconomie.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Toegankelijkheid en koloniaal erfgoed")
    for item in [
        "Gratis museum- en voorstellingstoegang met Stadskaart.",
        "Maximaal €5 voor jongeren (tot 18) en studenten.",
        "Alle koloniale objecten in kaart gebracht en gepubliceerd voor 2026.",
        "Geroofd kunst teruggegeven voor 2030.",
        "5+ buurtbibliotheken heropend.",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 15. DIGITALE RECHTEN EN TECHNOLOGIE
    # ──────────────────────────────────────────────
    pdf.chapter_title("Digitale Rechten en Technologie",
                       "Het internet was altijd al van ons")
    pdf.body_text(
        "Economische ongelijkheid, privacyschendingen en institutioneel racisme worden verdiept "
        "door toenemend digitaal gebruik. Amsterdam heeft decennialang een internationale rol "
        "gespeeld in de ontwikkeling van digitale infrastructuur. Technologie is nooit neutraal."
    )

    pdf.section_heading("Amsterdam breekt met big tech")
    for item in [
        "Afhankelijkheid van big tech beëindigd; Microsoft en Google-diensten gefaseerd afgebouwd.",
        "Online diensten lokaal ontwikkeld en beheerd met onderwijsinstellingen en EU-samenwerking.",
        "Onafhankelijke ethische toetsing vereist vóór verwerking van persoonsgegevens via AI.",
        "Inkoop van lokale, open-source diensten op basis van Europese privacynormen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Privacybescherming en digitale infrastructuur")
    for item in [
        "Bewonersgegevens lokaal opgeslagen, geen Amerikaanse bedrijfsafhankelijkheid.",
        "Gemeentelijke dataverzameling beperkt tot absolute noodzaak.",
        "Tracking, profilering en risico-assessmentsystemen die marginaliseren afgeschaft.",
        "Activisten en dissidenten beschermd tegen registratie of politielijsten.",
        "Alle bewoners toegang tot betaalbaar, stabiel internet.",
        "Geschikte apparaten via bibliotheken en buurtcentra.",
        "Openbare internettoegang voor daklozen.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Menselijke maat en duurzaamheid")
    for item in [
        "Fysieke serviceloketten behouden naast digitale diensten.",
        "Menselijke correctie mogelijk wanneer systemen falen.",
        "Gemeentewerkers getraind om algoritmische discriminatie te herkennen en voorkomen.",
        "'Digitale degrowth': mineraalverspilling en energieverbruik verminderen; reparatie en hergebruik.",
        "Bewustzijnscampagnes over mineraalherkomst (kobalt, coltan).",
    ]:
        pdf.bullet_item(item)

    # ──────────────────────────────────────────────
    # 16. DEMOCRATISERING EN MEDIA
    # ──────────────────────────────────────────────
    pdf.chapter_title("Democratisering en Media", "De stad die niet buigt")
    pdf.body_text(
        "BIJ1 wil een Amsterdam zonder fascisme en angst, waar bewoners niet worden verdeeld "
        "door macht of polariserende retoriek. Echte democratie begint met luisteren en "
        "wederzijds respect. In plaats van bewoners die aansluiten bij vooraf geplande "
        "initiatieven, neemt de lokale overheid deel aan wat bewoners zelf organiseren."
    )

    pdf.section_heading("Zelforganisatie")
    for item in [
        "Zuidoost als model voor onderlinge zorg en zelforganisatie via buurtplatforms.",
        "Stadsdelen informeren bewoners over erkende platforms; bewoners kiezen eigen structuren.",
        "Buurtplatforms proactief geconsulteerd bij beslissingen.",
        "Vereenvoudigde buurtbudgetprocedures op B1-taalniveau.",
        "Gemeentelijke ondersteuning voor 'commons': gedeelde middelen toegankelijk voor alle gemeenschapsleden.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Participatie en democratisering")
    for item in [
        "Verbeterde gemeentecommunicatie buiten formele besluitvorming.",
        "Bewonerspanels bij alle nieuwbouw- en renovatieprojecten.",
        "Grotere betrokkenheid van kinderen en jongeren bij lokale besluitvorming.",
        "Jaarlijkse publieke vergaderingen ('De Verenigde Straten').",
        "Jeugdparticipatie vanaf 16 jaar in lokale democratie.",
        "Gedecentraliseerde beslissingsbevoegdheid naar stadsdelen.",
        "Consultancycontracten beëindigd; vervangen door gemeentepersoneel.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Dekolonisatie van de gemeentelijke organisatie")
    for item in [
        "Meer representatie van gehandicapten, mensen in armoede, transpersonen en mensen van kleur.",
        "Onafhankelijke externe ombudspersonen voor discriminatieklachten.",
        "Loongelijkheid over organisatieniveaus.",
    ]:
        pdf.bullet_item(item)

    pdf.section_heading("Media en democratische informatievoorziening")
    for item in [
        "Gemeentelijke communicatiefinanciering omgeleid naar onafhankelijke buurtmedia.",
        "Subsidiefonds voor onafhankelijke journalisten, nadruk op gemarginaliseerde makers.",
        "Structurele (niet eenmalige) financiering voor bewoners-eigenmedia.",
        "Betaalbare ruimten voor redacties, podcasters en mediacollectieven.",
        "'Mediavouchers' waarmee bewoners gekozen nieuwsbronnen kunnen steunen.",
        "Mediageletterdheid op scholen en buurtcentra als recht, niet luxe.",
        "Investering in open-source platforms en veilige dataruimten voor lokale journalistiek.",
    ]:
        pdf.bullet_item(item)

    return pdf


if __name__ == "__main__":
    import os

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "programs", "bij1.pdf"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = build_pdf()
    pdf.output(output_path)
    print(f"PDF geschreven naar: {output_path}")
