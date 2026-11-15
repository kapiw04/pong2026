import csv
import html
import json
import os
from pathlib import Path
import re
import shutil
import statistics
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "tmp/matplotlib"))
import matplotlib
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (Image, PageBreak, Paragraph, Preformatted,
                               SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf"
INK = colors.HexColor("#172e3d")
GREEN = colors.HexColor("#148a76")
GREY = colors.HexColor("#546b7b")
PALE = colors.HexColor("#edf4f4")


def fonts():
    base = Path(matplotlib.get_data_path()) / "fonts/ttf"
    for name, filename in [("Body", "DejaVuSans.ttf"), ("Bold", "DejaVuSans-Bold.ttf"),
                           ("Mono", "DejaVuSansMono.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(base / filename)))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold")


STYLES = None


def styles():
    global STYLES
    STYLES = getSampleStyleSheet()
    STYLES.add(ParagraphStyle("TextPL", fontName="Body", fontSize=10, leading=14.7,
                             textColor=INK, spaceAfter=9))
    STYLES.add(ParagraphStyle("SmallPL", parent=STYLES["TextPL"], fontSize=8.3, leading=11.5, spaceAfter=6))
    STYLES.add(ParagraphStyle("HeadingPL", fontName="Bold", fontSize=20, leading=25,
                             textColor=INK, spaceAfter=16))
    STYLES.add(ParagraphStyle("SubPL", fontName="Bold", fontSize=12, leading=17,
                             textColor=GREEN, spaceBefore=7, spaceAfter=8))
    STYLES.add(ParagraphStyle("CoverPL", fontName="Bold", fontSize=29, leading=35,
                             textColor=INK, spaceAfter=14))
    STYLES.add(ParagraphStyle("CodePL", fontName="Mono", fontSize=8, leading=12,
                             textColor=INK, backColor=PALE, borderPadding=10, spaceAfter=12))


def p(text, small=False):
    return Paragraph(text, STYLES["SmallPL" if small else "TextPL"])


def title(text):
    return Paragraph(text, STYLES["HeadingPL"])


def sub(text):
    return Paragraph(text, STYLES["SubPL"])


def code(text):
    return Preformatted(text, STYLES["CodePL"])


def table(rows, widths=None, small=True):
    data = [[p(str(value), small) for value in row] for row in rows]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.spaceAfter = 8
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, 0), .7, GREEN),
        ("LINEBELOW", (0, 1), (-1, -1), .3, colors.HexColor("#d9e3e6")),
    ]))
    return t


def picture(path, width=490, caption=None):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        height = width * im.height / im.width
    items = [Image(str(path), width=width, height=height), Spacer(1, 7)]
    if caption:
        items.append(p(caption, True))
    return items


def footer(c, doc):
    c.setStrokeColor(colors.HexColor("#d9e3e6"))
    c.line(48, 46, A4[0] - 48, 46)
    c.setFont("Body", 8)
    c.setFillColor(GREY)
    c.drawString(48, 31, "PONG / Projekt 1 / Zespół 1")
    c.drawRightString(A4[0] - 48, 31, str(doc.page))
    if doc.page > 1:
        c.setFont("Body", 8)
        c.drawString(48, A4[1] - 36, "Sztuczna inteligencja w grach i rozszerzonej rzeczywistości")


def percent(value):
    return f"{100 * value:.1f}%".replace(".", ",")


def number(value, digits=1):
    return f"{value:.{digits}f}".replace(".", ",")


def manuscript(pages, destination):
    def plain(value):
        return html.unescape(re.sub(r"<[^>]+>", "", value.replace("<br/>", "\n")))

    lines = []
    for page in pages:
        for item in page:
            if isinstance(item, Paragraph):
                value = plain(item.text)
                prefix = "# " if item.style.name in ("CoverPL", "HeadingPL") else "## " if item.style.name == "SubPL" else ""
                lines.extend([prefix + value, ""])
            elif isinstance(item, Preformatted):
                lines.extend(["```", "\n".join(item.lines), "```", ""])
            elif isinstance(item, Table):
                for index, row in enumerate(item._cellvalues):
                    values = []
                    for value in row:
                        values.append(plain(getattr(value, "text", str(value))))
                    lines.append("| " + " | ".join(values) + " |")
                    if index == 0:
                        lines.append("| " + " | ".join(["---"] * len(values)) + " |")
                lines.append("")
            elif isinstance(item, Image):
                lines.extend([f"![Ilustracja](../{Path(item.filename).relative_to(ROOT)})", ""])
        lines.extend(["---", ""])
    destination.write_text("\n".join(lines), encoding="utf-8")


def build_report(summary, manifest):
    s = summary
    seeds = manifest["protocol"]["training_seeds"]
    q = [s[f"q/{seed}/standard"] for seed in seeds]
    no = [s[f"q_no_shaping/{seed}/standard"] for seed in seeds]
    q_mean = statistics.mean(r["win_rate"] for r in q)
    no_mean = statistics.mean(r["win_rate"] for r in no)
    q_sd = statistics.stdev(r["win_rate"] for r in q)
    primary = s["q/7/standard"]
    baseline = s["untrained/0/standard"]
    minutes = manifest["total_seconds"] / 60
    total_points = sum(r["points"] for r in s.values())
    pages = []

    cover = [Paragraph("PONG<br/>Przeciwnik uczący się grać", STYLES["CoverPL"]),
             p("Projekt 1 / Zespół 1 / poniedziałek 8:00-10:15<br/>"
               "Sztuczna inteligencja w grach i rozszerzonej rzeczywistości<br/>"
               "Sprawozdanie, 15 listopada 2026 r."),
             p(f"Agent uczy się sterować paletką w PONG-u metodą prób i błędów. "
               f"Po 20 000 epizodów trzy wytrenowane modele wygrywają średnio "
               f"<b>{percent(q_mean)}</b> punktów w ocenie końcowej. Przed nauką agent wygrywa "
               f"{percent(baseline['win_rate'])}. Przeciwnikiem w tym pomiarze jest "
               "reguła śledząca bieżącą wysokość piłki.")]
    cover += picture(ROOT / "wyniki/gra.png", 470,
                     "Rys. 1. Gra w trybie demonstracji. Wyuczony agent steruje prawą paletką.")
    cover += [table([["Osoba", "Odpowiedzialność"],
                     ["Artur Zamorowski", "Symulacja, model fizyki i kolizje."],
                     ["Kacper Wojtowicz", "Q-learning, reprezentacja stanu i eksperymenty."],
                     ["Rafał Wybraniec", "Interfejs i dokumentacja."]], [143, 347]),
              Spacer(1, 7)]
    pages.append(cover)

    pages.append([title("1. Zadanie i architektura"),
        p("Agent steruje prawą paletką. Wybiera ruch w górę, postój albo ruch w dół, "
          "zapisane jako akcje -1, 0 i +1. Obserwacja zawiera położenie i prędkość piłki, "
          "rotację oraz położenie i prędkość własnej paletki. Pozycja przeciwnika "
          "pozostaje poza obserwacją."),
        p("Za punkt uznajemy przejście piłki poza boczną granicę boiska. Epizod treningowy "
          "kończy się po punkcie albo po 20 s czasu symulowanego. Serwis losuje kierunek, "
          "kąt i wysokość piłki oraz początkowe położenia obu paletek."),
        sub("Podział programu"),
        table([["Moduł", "Rola i przepływ danych"],
               ["config.py", "Stałe boiska, fizyki i częstotliwości symulacji."],
               ["physics.py", "Pong.reset(), observe(), step(). Akcje obu stron zmieniają stan i zwracają wynik przejścia."],
               ["agents.py", "Dyskretyzacja obserwacji, tablica Q, aktualizacja, strategie odniesienia i zapis modelu."],
               ["experiments.py", "Generowanie epizodów bez grafiki, ocena zamrożonych modeli, CSV i metadane."],
               ["gui.py", "Sceny menu, gry, pauzy i końca meczu. Obsługa klawiatury i rysowanie stanu rdzenia."],
               ["app.py, settings.py", "Odczyt konfiguracja.yaml, sprawdzenie parametrów i uruchomienie wybranego trybu."],
               ["narzedzia/", "Wykresy i generowanie dokumentów PDF."]], [103, 387]),
        p("Trening i gra korzystają z tej samej symulacji. Podczas treningu agent "
          "wybiera akcję, wykonuje krok i poprawia jedną wartość w tablicy Q. W grze "
          "odczytuje gotową tablicę. Fizyka ma stały krok czasu, niezależny od rysowania."),
        p("Program uruchamia plik kod/main.py bez argumentów. Tryb, model i parametry "
          "wybiera konfiguracja.yaml. Ścieżki w ustawieniach odnoszą się do katalogu projektu."),
        sub("Środowisko wykonawcze"),
        p(f"Pomiary wykonano w Pythonie {manifest['python'].split()[0]} z NumPy "
          f"{manifest['numpy']}. Interfejs korzysta z Pygame-ce 2.5.8 i SDL. NumPy przechowuje "
          "tablice, PyYAML 6.0.3 odczytuje ustawienia, Matplotlib tworzy wykresy, a ReportLab PDF-y. "
          "Dokładne wersje przypięto w plikach wymagań."),
        p("Pygame-ce obsługuje okno, klawiaturę i rysowanie. Pętlę gry oraz model fizyczny "
          "zawierają moduły projektu.")])

    pages.append([title("2. Fizyka rozgrywki"),
        p("Paletka przyspiesza i hamuje, więc agent musi rozpocząć ruch przed nadejściem "
          "piłki. Miejsce trafienia i prędkość paletki zmieniają odbicie. Ruch paletki "
          "nadaje też rotację, która zakrzywia dalszy tor lotu."),
        table([["Parametr", "Wartość w scenariuszu standard"],
               ["Boisko / paletka / promień piłki", "900 x 500 px / 12 x 88 px / 8 px"],
               ["Prędkość / przyspieszenie paletki", "460 px/s / 3600 px/s², identyczne po obu stronach"],
               ["Szybkość piłki", "430 px/s na starcie, wzrost x1,06 po odbiciu, limit 800 px/s"],
               ["Odbicie", "Kąt zależny od miejsca trafienia, maks. 0,96 rad przed korektą ruchu"],
               ["Krok fizyki / decyzji", "1/120 s / 1/30 s"],
               ["Rotacja", "Zakres [-7, 7], wykładniczy zanik z parametrem 0,55 s⁻¹"]], [190, 300]),
        sub("Przebieg pojedynczego kroku"),
        p("W każdym kroku symulator przesuwa paletki i ogranicza ich pozycje do boiska. "
          "Potem oblicza wpływ rotacji na prędkość piłki, przesuwa ją i rozpatruje kolizje. "
          "Jeśli piłka przekroczy powierzchnię odbicia, zachowuje pozostałą część drogi "
          "po przeciwnej stronie. Piłka kontynuuje ruch po odbiciu."),
        code("u = clip((y_pilki - y_paletki) / 44, -1, 1)\n"
             "speed = min(800, 1.06 * hypot(vx, vy))\n"
             "vy_out = clip(speed*sin(0.96*u) + 0.22*vp,\n"
             "              -0.88*speed, 0.88*speed)\n"
             "abs(vx_out) = sqrt(speed**2 - vy_out**2)"),
        p("Rotacja wynosi clip(5·v_p/460 + 2·u, -7, 7). W locie składnik pionowy "
          "zmienia się o 0,13·spin·v_x·dt. Potem normalizujemy wektor do poprzedniej "
          "szybkości. Rotacja zmienia kierunek ruchu przy zachowaniu szybkości. "
          "Odbicie od poziomej ściany zmienia znak i zmniejsza rotację współczynnikiem 0,8."),
        p("Sprawdzenie przecięcia czoła paletki wykrywa kontakt także wtedy, gdy piłka "
          "przeskoczy tę płaszczyznę w jednym kroku. Pionowy zasięg kontaktu obejmuje "
          "dodatkowo promień piłki, co upraszcza kolizje przy narożnikach. Parametry fizyki "
          "dobrano do gry zręcznościowej."),
        p("Test simple_physics wyłącza zależność odbicia od miejsca trafienia, ruchu "
          "paletki i rotacji. Pozostawia odbicia od ścian oraz wzrost szybkości. "
          "Zmienia dynamikę gotowego modelu i służy do oceny jego przenoszenia.")])

    pages.append([title("3. Stan agenta i uczenie"),
        p("Tablicowy Q-learning [1] przypisuje każdemu stanowi trzy wartości, po jednej "
          "dla każdej akcji. Wszystkie wartości zaczynają od zera. Agent poznaje skutki "
          "własnych ruchów podczas kolejnych epizodów."),
        code("Q[s,a] = Q[s,a] + alfa * (r + gamma*max(Q[s_next])\n"
             "                         - Q[s,a])\n"
             "Dla zdobytego/straconego punktu: max(Q[s_next]) = 0"),
        p("Współczynnik alfa wynosi 0,12, a gamma 0,98. Epsilon maleje liniowo z 0,9 "
          "do 0,05 przez pierwsze 85% epizodów i pozostaje na tym poziomie. Podczas oceny "
          "epsilon wynosi zero. Przy równych wartościach agent wybiera postój. Po zdobyciu "
          "lub stracie punktu aktualizacja pomija wartość następnego stanu. Przy samym "
          "limicie czasu nadal ją uwzględnia."),
        table([["Reprezentacja", "Opis", "Liczba stanów"],
               ["Siatka 50 px", "18 kolumn, 19 różnic wierszy, znak vx, 3 kategorie vy i 3 kategorie prędkości paletki", "6156"],
               ["Siatka 100 px", "9 kolumn, 9 różnic wierszy, pozostałe cechy jak wyżej", "1458"],
               ["Względna, demonstracja", "15 przedziałów błędu dolotu, 3 pasy x, znak vx, 3 prędkości paletki i 3 strefy jej położenia", "810"]], [102, 320, 68]),
        p("Oprócz siatek sprawdzono stan oparty na przewidywanym miejscu dolotu. "
          "Agent oblicza je z bieżących x, y, vx i vy, uwzględniając odbicia od ścian. "
          "Gdy piłka oddala się, odnosi ustawienie paletki do środka boiska. Prognoza "
          "pomija rotację. Porównanie tej reprezentacji z siatką obejmuje zatem dwie "
          "zmiany: mniejszą tablicę i dodatkową informację o spodziewanym torze piłki."),
        sub("System nagród i kar"),
        p("Nagroda bazowa to +1 za zdobyty punkt, -1 za stratę i +0,2 za własne odbicie. "
          "Dodajemy koszt 0,001 za polecenie ruchu. W wariancie ze wskazówkami występuje "
          "koszt 0,02·|błąd dolotu|/500 oraz składnik gamma·Phi(s') - Phi(s), gdzie "
          "Phi(s) = -|błąd dolotu|/500, a Phi stanu terminalnego jest zerowe [2]."),
        p("Koszty ruchu i błędu ustawienia oraz nagroda za odbicie wpływają na to, "
          "czego uczy się agent. Nagroda za odbicia może skłaniać go do przedłużania "
          "wymian. Skuteczność oceniamy osobno na podstawie "
          "wygranych, strat i długości wymian.")])

    pages.append([title("4. Protokół eksperymentów"),
        p("Dane powstają w symulatorze. Każdy trening rozpoczyna zerową tablicę Q "
          "i używa osobnego ziarna losowania. Podczas oceny tablica pozostaje bez zmian, "
          "a agent wybiera akcje bez losowej eksploracji. Protokół zapisano w "
          "dane/eksperyment.yaml."),
        table([["Ustawienie", "Przyjęta wartość"],
               ["Budżet", "20 000 epizodów na przebieg, 10 przebiegów = 200 000 punktów uczenia"],
               ["Główne porównanie", "Wskazówki włączone / wyłączone, po 3 ziarna: 7, 19, 41"],
               ["Analiza ustawień", "Siatka 50 px, siatka 100 px, alfa 0,35 i brak kosztu ruchu. Każda zmiana: ziarno 7"],
               ["Walidacja", "180 punktów, ziarna 1000000-1000179. Ocena przed nauką i po 1000, 5000, 10000, 20000 epizodów"],
               ["Test końcowy", "450 punktów na model i scenariusz, ziarna 2000000-2000449"],
               ["Model demonstracyjny", "Z góry wskazane ziarno 7 i reprezentacja względna. Bez wyboru na podstawie testu"]], [110, 380]),
        sub("Przeciwnik i strategie odniesienia"),
        p("Reguła steruje paletką w stronę bieżącej wysokości piłki z martwą strefą 12 px. "
          "Aktualizuje akcję co 4 decyzje, czyli co 133 ms. Paletki obu stron mają tę samą "
          "prędkość i przyspieszenie. Uczący się agent reaguje co 33 ms. Ma więc przewagę "
          "czasu reakcji. Osobny scenariusz sprawdza wynik po przyspieszeniu przeciwnika."),
        p("W ocenie sprawdzamy także agenta losowego, zerową tablicę Q i regułę po prawej. "
          "Reguła porównawcza ma taką samą częstość reakcji jak przeciwnik podstawowy. "
          "Test fast_reaction przyspiesza reakcję lewej strony do 33 ms. Fast zwiększa "
          "szybkość początkową i maksymalną piłki o 20%. Simple_physics zmienia model odbić."),
        sub("Miary i niepewność"),
        p("Mierzymy udział wygranych punktów, straty, remisy po 20 s, liczbę odbić obu "
          "paletek na punkt, czas trwania i udział decyzji z poleceniem ruchu. Dodatkowo "
          "liczymy wyniki bloków po 9 niezależnych punktów jako mecze laboratoryjne. "
          "Interfejs używa innej reguły: do 7 zdobytych punktów, bez limitu czasu wymiany."),
        p(f"Ocena końcowa obejmuje {total_points} punktów. Trening i pomiary trwały "
          f"{number(minutes)} min na zapisanym środowisku, przy maksymalnie trzech procesach "
          "trenujących równolegle. Te same ziarna dają modelom jednakowe serwisy. "
          "Dalszy przebieg punktu zależy już od wybranych ruchów."),
        p("Przedziały Wilsona 95% opisują zmienność wyniku na nowych serwisach przy "
          "ustalonej tablicy Q. Osobno podajemy rozrzut trzech treningów. Dla siatki "
          "i alfy wykonano po jednej próbie, więc te porównania wymagają dalszego sprawdzenia.")])

    result_rows = [["Polityka / ziarno", "Wygrane", "Straty", "Remisy", "Odbicia / punkt"]]
    for label, key in [("Przed nauką", "untrained/0/standard"), ("Losowy", "random/0/standard"),
                       ("Reguła", "tracking/0/standard")]+[(f"Q / {seed}", f"q/{seed}/standard") for seed in seeds]:
        r = s[key]
        result_rows.append([label, f"{r['wins']} ({percent(r['win_rate'])})", r["losses"], r["draws"], number(r['mean_hits'], 2)])
    pages.append([title("5. Wyniki uczenia"),
        *picture(ROOT / "wyniki/uczenie.png", 490,
                 "Rys. 2. Walidacja zamrożonych modeli. Linie: średnia z 3 treningów. "
                 "Cieniowanie pokazuje zakres od minimum do maksimum z 3 treningów."),
        table(result_rows, [110, 116, 68, 68, 128]),
        Spacer(1, 10),
        p(f"Średni odsetek wygranych po uczeniu ze wskazówkami wynosi {percent(q_mean)}, "
          f"a odchylenie standardowe między treningami {number(100*q_sd)} pkt proc. "
          f"Po wyłączeniu wskazówek w nagrodzie wynik wynosi średnio {percent(no_mean)}. "
          "Wyższy wynik uzyskały modele z wyłączonymi wskazówkami w nagrodzie. "
          "Wykres pokazuje też spadki między punktami kontrolnymi."),
        p(f"Dla modelu demonstracyjnego uzyskano {primary['wins']} wygranych, "
          f"{primary['losses']} strat i {primary['draws']} remisów. Jego udział wygranych "
          f"to {percent(primary['win_rate'])}, z przedziałem Wilsona "
          f"[{percent(primary['win_ci95'][0])}; {percent(primary['win_ci95'][1])}]. "
          f"W blokach po 9 punktów wygrał {primary['match_wins']} z {primary['matches']} "
          "meczów laboratoryjnych. Surowe wiersze są w evaluation.csv."),
        p("Wynik modelu po nauce jest wyższy niż zerowej tablicy i reguły porównawczej. "
          "Duża liczba remisów pokazuje, że agent często utrzymuje piłkę "
          "do końca limitu czasu.")])

    scen_rows = [["Scenariusz", "Q, średnia 3 ziaren", "Reguła"]]
    for scene, label in [("standard", "Standard"), ("fast", "Piłka +20%"),
                         ("simple_physics", "Prosta fizyka"), ("fast_reaction", "Szybka reakcja przeciwnika")]:
        rate = statistics.mean(s[f"q/{seed}/{scene}"]["win_rate"] for seed in seeds)
        scen_rows.append([label, percent(rate), percent(s[f"tracking/0/{scene}"]["win_rate"])])
    g50, g100 = s["grid50/7/standard"], s["grid100/7/standard"]
    high_alpha, no_move = s["alpha035/7/standard"], s["no_movement_cost/7/standard"]
    fast_rate = statistics.mean(s[f"q/{seed}/fast"]["win_rate"] for seed in seeds)
    reaction_rate = statistics.mean(s[f"q/{seed}/fast_reaction"]["win_rate"] for seed in seeds)
    pages.append([title("6. Porównania i przenoszenie"),
        *picture(ROOT / "wyniki/porownanie.png", 490,
                 "Rys. 3. Modele z ziarnem 7 oraz strategie odniesienia. Wąsy: Wilson 95%. "
                 "Warianty siatkowe różnią się również informacją zawartą w stanie."),
        table(scen_rows, [225, 160, 105]),
        Spacer(1, 9),
        p(f"Przy tym samym budżecie siatka 50 px uzyskała {percent(g50['win_rate'])}, "
          f"a siatka 100 px {percent(g100['win_rate'])} wygranych punktów. "
          f"Wariant z alfą 0,35 uzyskał {percent(high_alpha['win_rate'])}. "
          "Dokładniejsza siatka wypadła lepiej w tej próbie. Do wyboru ustawienia "
          "na tej podstawie potrzebne byłyby kolejne ziarna treningu."),
        p(f"Udział poleceń ruchu wyniósł {percent(primary['move_rate'])} przy koszcie 0,001 "
          f"oraz {percent(no_move['move_rate'])} bez niego. Udział wygranych bez kosztu "
          f"wyniósł {percent(no_move['win_rate'])}. W tej próbie model z kosztem "
          "wydawał więcej poleceń ruchu. Częstotliwość zmiany kierunku wymaga osobnego pomiaru."),
        p(f"Szybsza piłka zwiększa średni udział wygranych Q do {percent(fast_rate)}, bo utrudnia "
          f"również zadanie regule. Szybka reakcja przeciwnika obniża wynik Q do {percent(reaction_rate)}. "
          "Rezultat zależy więc silnie od czasu reakcji przeciwnika. Testy używają "
          "gotowych tablic i oceniają przenoszenie między wariantami fizyki.")])

    pages.append([title("7. Odtwarzalność i wnioski"),
        p("Do gry i oceny służy model modele/pong_q.npz. Zawiera tablicę Q, "
          "liczniki odwiedzin i metadane JSON. Plik manifest.json rejestruje konfigurację, środowisko, ziarna "
          "i sumy SHA-256 modeli."),
        p("W konfiguracja.yaml ustaw mode na play, train, evaluate albo experiment, "
          "a następnie uruchom program bez argumentów. W trybie play pole demo włącza "
          "pokaz reguła kontra agent. Sekcja experiment wskazuje protokół YAML oraz "
          "osobne katalogi dla odtworzonych wyników i modeli."),
        code("python -m pip install -r uruchomienie/wymagania.txt\n"
             "python kod/main.py"),
        p("Przebiegi treningowe CSV zawierają epsilon, wynik, liczbę odbić i kroków "
          "każdego epizodu. Learning.csv przechowuje osobną ocenę walidacyjną, a evaluation.csv "
          "każdy punkt testu. Dokumenty i wykresy można ponownie wygenerować dołączonymi "
          "skryptami. Wersję kodu podaje wersja.json. Sumy plików pozwalają sprawdzić "
          "zawartość archiwum."),
        sub("Sprawdzenie i ograniczenia"),
        p("Ponowne uruchomienie oceny dołączonego modelu odtwarza wyniki 450 punktów "
          "ze scenariusza standard. Gra korzysta z zamrożonej tablicy Q. Zrzuty "
          "dokumentują rzeczywiste renderowanie interfejsu Pygame."),
        p("Obserwacja i agregacja stanów pomijają część informacji potrzebnych do pełnego "
          "modelu Markowa. Prognoza dolotu zakłada lot liniowy. Przeciwnik podstawowy "
          "ma wolniejszą reakcję od agenta, a budżet strojenia obejmuje tylko po jednym "
          "ziarnie dla kilku ustawień. Pomiary dotyczą zapisanego środowiska lokalnego."),
        sub("Wnioski i dalsze prace"),
        p("Q-learning nauczył paletkę utrzymywania piłki i poprawił wynik względem "
          "modelu przed nauką. Największym ograniczeniem pozostaje zależność od "
          "przeciwnika: wyrównanie czasu reakcji mocno obniża udział wygranych. "
          "W kolejnym eksperymencie warto trenować przeciw szybszej regule i "
          "powtórzyć porównanie nagród dla większej liczby ziaren. Dopiero potem "
          "można ocenić, które wskazówki i parametry warto zachować."),
        sub("Źródła i wykorzystane rozwiązania"),
        p('[1] C. Watkins, P. Dayan, <link href="https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf" color="#148a76">Q-learning</link>, Machine Learning 8, 279-292, 1992.<br/>'
          '[2] A. Ng, D. Harada, S. Russell, <link href="https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/NgHaradaRussell-shaping-ICML1999.pdf" color="#148a76">Policy invariance under reward transformations</link>, ICML, 1999.<br/>'
          '[3] <link href="https://pyga.me/docs/" color="#148a76">Oficjalna dokumentacja Pygame-ce</link>.<br/>'
          '[4] Instrukcja realizacji projektu i instrukcja oddania dostarczone przez prowadzącego.<br/>'
          'Z literatury przyjęto algorytm i ideę kształtowania nagrody. Środowisko, protokół, '
          'reprezentacje stanu i interfejs zaimplementowano w repozytorium.', True)])

    story = []
    for i, page in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.extend(page)
    path = OUT / "sprawozdanie.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=48, leftMargin=48,
                            topMargin=57, bottomMargin=58, title="PONG - sprawozdanie",
                            author="Artur Zamorowski, Kacper Wojtowicz, Rafał Wybraniec")
    manuscript(pages, ROOT / "dokumentacja/sprawozdanie.md")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    assert len(PdfReader(path).pages) == 8, "Report overflow: expected eight pages"
    shutil.copyfile(path, ROOT / "sprawozdanie.pdf")


def build_instructions():
    pages = [[title("Uruchomienie projektu PONG"),
        p("Projekt 1 / Zespół 1 / poniedziałek 8:00. Wykonuj polecenia w katalogu projektu. "
          "Wymagany Python 3.11 lub nowszy, terminal i ekran dla gry. Instalacja zależności "
          "korzysta z internetu. Trening i ocena działają również bez ekranu."),
        sub("1. Instalacja na macOS / Linux"),
        code("python3 -m venv .venv\nsource .venv/bin/activate\n"
             "python -m pip install -r uruchomienie/wymagania.txt\npython kod/main.py"),
        sub("2. Instalacja na Windows PowerShell"),
        code("py -3 -m venv .venv\n"
             ".venv\\Scripts\\python.exe -m pip install -r uruchomienie/wymagania.txt\n"
             ".venv\\Scripts\\python.exe kod\\main.py"),
        p("W kolejnych poleceniach na Windows używaj .venv\\Scripts\\python.exe."),
        sub("3. Pierwszy przykład bez uczenia"),
        code("python kod/main.py"),
        p("Program czyta konfiguracja.yaml. Domyślny mode: play uruchamia grę z "
          "modelem modele/pong_q.npz. Ustaw play.demo na true, aby zobaczyć pokaz. "
          "Do oceny 450 punktów wybierz mode: evaluate. Każdy tryb uruchamia to samo "
          "polecenie, bez dodatkowych argumentów."),
        table([["Klawisz", "Działanie"], ["Enter", "Gra / nowy mecz po zakończeniu"],
               ["W/S lub strzałki", "Sterowanie lewą paletką"], ["Spacja", "Pauza / wznowienie"],
               ["Tab", "Zmiana przeciwnika i nowy mecz"], ["D / R", "Demonstracja / reset meczu"],
               ["H", "Sterowanie, rozgrywka wstrzymana podczas pomocy"],
               ["Esc", "Menu, następnie zamknięcie programu"]], [140, 350])],
        [title("Eksperymenty i przygotowanie ZIP"),
         sub("4. Własny model i pełne odtworzenie"),
         code("mode: train\ntrain:\n  episodes: 20000\n  seed: 7\n  output: modele/wlasny.npz"),
         p("Zmień te pola w konfiguracja.yaml i uruchom python kod/main.py. "
           "Po treningu wybierz mode: play i ustaw play.model na modele/wlasny.npz. "
           "Tryb experiment odtwarza pełny protokół wskazany w sekcji experiment."),
         p("Pełny eksperyment wykonuje 10 treningów po 20 000 epizodów, używając do "
           "3 procesów. Czas zależy od sprzętu. Pole workers w dane/eksperyment.yaml "
           "ogranicza liczbę procesów. Pliki odtworzone zapisuj "
           "osobno, aby zachować oryginalne pomiary."),
         sub("5. Wykresy i dokumentacja PDF"),
         code("python -m pip install -r uruchomienie/wymagania_dev.txt\n"
              "python narzedzia/wykresy.py\npython narzedzia/dokumenty.py"),
         p("Pakiet deweloperski jest potrzebny tylko do regenerowania dokumentów. "
           "Gra wymaga NumPy, Pygame-ce i PyYAML. Skrypty korzystają z dołączonych CSV "
           "i JSON."),
         sub("6. Oddanie projektu"),
         p("Gotowa paczka to dist/projekt_1_pon_8.zip "
           "z jednym katalogiem projekt_1_pon_8/. Zawiera kod, modele, wyniki, "
           "dokumenty, wersja.json i sumy SHA-256. Jedna osoba przesyła je do zadania "
           "w Teams. Wszyscy członkowie zespołu uczestniczą w prezentacji."),
         sub("Rozwiązywanie problemów"),
         p("Brak modułu pygame lub numpy: sprawdź, czy instalacja i uruchomienie "
           "używają tego samego interpretera. Brak modelu: rozpakuj całe archiwum i zachowaj "
           "katalog modele/. Brak urządzenia wideo: uruchom ocenę bez okna albo korzystaj "
           "z sesji graficznej."),
         p("Wersje sprawdzone lokalnie: Python 3.13.12, NumPy 2.3.5, Pygame-ce 2.5.8, "
           "PyYAML 6.0.3, Matplotlib 3.11.2, ReportLab 5.1.0 i pypdf 7.1.0. "
           "To środowisko użyte do pomiarów.", True)]]
    story = []
    for i, page in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.extend(page)
    path = OUT / "instrukcja_uruchomienia.pdf"
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=48, rightMargin=48,
                      topMargin=57, bottomMargin=58, title="PONG - uruchomienie").build(
                          story, onFirstPage=footer, onLaterPages=footer)
    assert len(PdfReader(path).pages) == 2
    shutil.copyfile(path, ROOT / "uruchomienie/instrukcja_uruchomienia.pdf")


def build_slides(s, manifest):
    width, height = 960, 540
    path = OUT / "prezentacja.pdf"
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setTitle("PONG - przeciwnik uczący się grać")
    c.setAuthor("Artur Zamorowski, Kacper Wojtowicz, Rafał Wybraniec")
    source = []

    def text(value, x, top, w=840, size=22, color=INK, bold=False):
        style = ParagraphStyle("Slide", fontName="Bold" if bold else "Body", fontSize=size,
                               leading=size * 1.36, textColor=color)
        para = Paragraph(value, style)
        _, h = para.wrap(w, 450)
        para.drawOn(c, x, height - top - h)
        return h

    def start(name, number):
        c.setFillColor(colors.white)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        text(name, 48, 35, size=33, bold=True)
        c.setStrokeColor(GREEN)
        c.line(48, height - 99, 912, height - 99)
        text(f"PONG / Zespół 1", 48, 507, size=10, color=GREY)
        text(str(number), 893, 507, w=20, size=10, color=GREY)
        source.extend([f"# {number}. {name}", ""])

    def body(value, top=127, size=22, w=840, x=48):
        text(value, x, top, w, size)
        source.extend([html.unescape(re.sub(r"<[^>]+>", "", value)), ""])

    def img(filename, x, top, w):
        from PIL import Image as PILImage
        file = ROOT / "wyniki" / filename
        with PILImage.open(file) as im:
            h = w * im.height / im.width
        c.drawImage(str(file), x, height - top - h, w, h)
        source.extend([f"![{filename}](wyniki/{filename})", ""])

    start("Pong. Przeciwnik uczący się grać", 1)
    body("Tablicowy Q-learning w grze 2D", size=27)
    img("gra.png", 48, 188, 440)
    body("Artur Zamorowski<br/>Kacper Wojtowicz<br/>Rafał Wybraniec", 213, 21, 340, 579)
    body("Projekt 1<br/>Poniedziałek 8:00", 361, 18, 340, 579)
    c.showPage()

    start("Zadanie i wspólna symulacja", 2)
    body("Agent steruje prawą paletką. Wybiera ruch w górę, postój albo ruch w dół.")
    body("Trening bez grafiki oraz gra korzystają z tego samego modułu fizyki. "
         "Symulacja: 120 Hz. Decyzje agenta: 30 Hz.", 233)
    body("Moduły: fizyka, agenci, eksperymenty, interfejs i ustawienia YAML.<br/>"
         "Model NPZ zawiera tablicę Q i konfigurację. Gra tylko go odczytuje.", 352)
    c.showPage()

    start("Q-learning i dyskretyzacja", 3)
    body("Q(s,a) otrzymuje poprawkę alfa · [r + gamma · max Q(s',a') - Q(s,a)].", size=23)
    body("Siatki kwadratowe 50 i 100 px. Porównanie z reprezentacją względną, "
         "która używa przybliżonego punktu dolotu i ma 810 stanów.", 225)
    body("Każdy trening zaczyna od zerowej tablicy. Epsilon maleje z 0,9 do 0,05. "
         "Podczas testu epsilon = 0. Alfa = 0,12, gamma = 0,98.", 340)
    body("Źródło metody: Watkins i Dayan, Q-learning, 1992. Szczegóły w sprawozdaniu.", 462, 12)
    c.showPage()

    start("Fizyka i nagrody", 4)
    body("Miejsce trafienia i ruch paletki zmieniają kąt odbicia oraz rotację. "
         "Rotacja zakrzywia tor i zanika. Paletki przyspieszają i hamują.")
    body("+1 zdobyty punkt, -1 strata, +0,2 odbicie.<br/>"
         "Koszt polecenia ruchu oraz wariant ze wskazówką pozycjonowania.", 249)
    body("Porównujemy wyłączenie wskazówek i kosztu ruchu. Dodatkowe składniki "
         "nagrody zmieniają cel optymalizacji.", 360)
    c.showPage()

    start("Demonstracja działającej gry", 5)
    body("python kod/main.py", size=26)
    body("W konfiguracja.yaml ustaw mode: play oraz play.demo: true.", 184, 18)
    body("Enter: człowiek kontra agent. W/S: ruch. Spacja: pauza. "
         "Tab: porównanie z regułą, losowym i modelem przed nauką.", 219)
    body("Przedmiot demonstracji: śledzenie piłki, odbicie ruchomą paletką, "
         "rotacja oraz decyzje zapisanej tablicy Q.", 329)
    body("Pygame-ce/SDL i własna fizyka. Gotowy model działa bez ponownego treningu.", 438, 18)
    c.showPage()

    start("Uczenie w trzech niezależnych przebiegach", 6)
    img("uczenie_slajd.png", 48, 112, 820)
    body("Średnia z 3 treningów. Cieniowanie pokazuje zakres od minimum do maksimum.", 478, 15)
    c.showPage()

    start("Wyniki testu i porównanie ustawień", 7)
    img("porownanie_slajd.png", 48, 108, 820)
    rate = statistics.mean(s[f"q/{seed}/standard"]["win_rate"] for seed in (7, 19, 41))
    body(f"Test: 450 punktów. Główny wariant Q: średnio {percent(rate)} wygranych, 3 ziarna treningu.", 485, 15)
    c.showPage()

    start("Ograniczenia, odpowiedzialność i rozwój", 8)
    body("Wynik zależy od przeciwnika i rozdzielczości stanu. Reguła podstawowa reaguje "
         "co 133 ms, agent co 33 ms. Osobny test wyrównuje częstość reakcji.", size=20)
    body("Artur: fizyka i kolizje. Kacper: agent i eksperymenty.<br/>"
         "Rafał: interfejs i dokumentacja.", 249, 20)
    body("Dalsze prace: więcej ziaren strojenia, uwzględnienie rotacji w stanie "
         "i trening przeciw szybszej regule.", 357, 20)
    c.showPage()
    c.save()
    assert len(PdfReader(path).pages) == 8
    shutil.copyfile(path, ROOT / "prezentacja.pdf")
    (ROOT / "dokumentacja/prezentacja.md").write_text("\n".join(source), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fonts()
    styles()
    summary = json.loads((ROOT / "wyniki/summary.json").read_text())
    manifest = json.loads((ROOT / "wyniki/manifest.json").read_text())
    build_report(summary, manifest)
    build_instructions()
    build_slides(summary, manifest)
    print("Utworzono sprawozdanie (8 stron), prezentację (8 slajdów) i instrukcję (2 strony).")


if __name__ == "__main__":
    main()
