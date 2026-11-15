# Projekt 1. Pong - przeciwnik uczący się grać

Zespół 1, poniedziałek 8:00-10:15. Przedmiot: Sztuczna inteligencja w grach
i rozszerzonej rzeczywistości.

Gra Pong z przeciwnikiem uczącym się metodą tablicowego Q-learningu.
Porównujemy wpływ rozmiaru siatki i współczynnika uczenia na wynik gry.

| Osoba | Zakres |
| --- | --- |
| Artur Zamorowski | Budowa i trenowanie modelu |
| Kacper Wojtowicz | Gra, interfejs i prezentacja |
| Rafał Wybraniec | Sprawozdanie, dokumentacja i dobór parametrów |

## Uruchomienie

Python 3.11 lub nowszy. Biblioteki: NumPy 2.3.5, Pygame-ce 2.5.8, PyYAML 6.0.3.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r uruchomienie/wymagania.txt
python kod/main.py play
```

Na Windows użyj `py -3 -m venv .venv`, a następnie interpretera
`.venv\Scripts\python.exe` w poleceniach instalacji i uruchomienia.

Enter rozpoczyna mecz do 7 punktów. W/S lub strzałki sterują lewą paletką,
Spacja włącza pauzę, D przełącza pokaz, R rozpoczyna nowy mecz,
H pokazuje sterowanie, Esc wraca do menu. Wymiana trwa do zdobycia punktu.

## Trzy tryby

```bash
python kod/main.py play
python kod/main.py train
python kod/main.py evaluate
```

Parametry są w `konfiguracja.yaml`. Pole `model` wybiera model do gry,
`demo: true` włącza pokaz reguła kontra agent. `train` uczy wszystkie modele
z listy `models` i zapisuje ich ocenę. `evaluate` ocenia zapisane modele.
Ścieżki odnoszą się do katalogu projektu.

Modele porównują siatki 50 i 100 px oraz współczynniki uczenia 0,12 i 0,35.
Stan zawiera pozycję piłki i paletki, kierunek poziomy oraz kategorie prędkości
pionowej piłki i paletki. Nagroda wynosi +1 za punkt, -1 za stratę i +0,2 za odbicie.
Trening i ocena mają limit 20 s na punkt. Paletki obu stron podejmują decyzję co 1/30 s.

## Pliki

- `kod/`: uruchamianie, fizyka, agent i interfejs.
- `modele/`: cztery gotowe tablice Q.
- `wyniki/uczenie.csv`: ocena modeli w trakcie treningu.
- `wyniki/ocena.csv`: wyniki końcowych punktów przeciw regule śledzącej piłkę.
- `wyniki/*.png`: wykresy i zrzut użyte w sprawozdaniu.
- `dokumentacja/`: źródła LaTeX sprawozdania i prezentacji.
- `sprawozdanie.pdf`, `prezentacja.pdf`, `uruchomienie/`: materiały do oddania.

Pygame-ce obsługuje okno i klawiaturę. Własna fizyka obejmuje przyspieszanie
paletek, zmianę kąta odbicia, przekazywanie ruchu paletki i rotację piłki.

Oba dokumenty można skompilować z katalogu `dokumentacja/`:

```bash
latexmk -pdf -outdir=../tmp/latex sprawozdanie.tex
latexmk -pdf -outdir=../tmp/latex prezentacja.tex
```

Kompilacja wymaga TeX Live lub MiKTeX z `latexmk` i `pdflatex`.
Pliki PDF powstają w `tmp/latex/`.
Archiwum do oddania: `dist/projekt_1_pon_8.zip`.
Repozytorium: https://github.com/kapiw04/pong2026.
