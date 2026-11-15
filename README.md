# Projekt 1. Pong - przeciwnik uczący się grać

**Zespół 1, poniedziałek 8:00-10:15.** Przedmiot: Sztuczna inteligencja w grach
i rozszerzonej rzeczywistości. Wersja 1.0.2.

Gra 2D z tablicowym Q-learningiem, treningiem bez grafiki i zapisem wyuczonego
modelu. Agent wybiera ruch w górę, postój albo ruch w dół. Wyniki porównano
z regułą śledzenia piłki, strategią losową i modelem przed uczeniem.

## Uruchomienie od zera

Wymagany Python 3.11 lub nowszy. Sprawdzone środowisko i dokładne wersje są
w `wyniki/manifest.json` oraz `uruchomienie/wymagania.txt`. Instalacja wymaga
połączenia z PyPI. Gotowy model jest dołączony, więc uczenie nie jest potrzebne
do zagrania ani do odtworzenia oceny.

macOS / Linux, w katalogu projektu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r uruchomienie/wymagania.txt
python kod/main.py play
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r uruchomienie/wymagania.txt
.venv\Scripts\python.exe kod\main.py play
```

Po wejściu do gry naciśnij Enter. W/S lub strzałki sterują lewą paletką.
Spacja wstrzymuje grę, Tab zmienia przeciwnika, D przełącza demonstrację,
R rozpoczyna nowy mecz, Esc wraca do menu. Z menu Esc zamyka program.
H wyświetla sterowanie i wstrzymuje rozgrywkę na czas czytania pomocy.
Mecz w interfejsie trwa do 7 punktów. Wymiany w grze nie mają limitu czasu.
Limit 20 sekund dotyczy wyłącznie treningu i oceny eksperymentalnej.

```bash
python kod/main.py play --demo
python kod/main.py evaluate --points 450
```

Druga komenda odtwarza test podstawowego modelu dla ziaren 2000000-2000449.
Gra nie zapisuje zmian w modelu. Pliki NPZ zawierają liczby i JSON, bez pickle.

## Zespół i odpowiedzialność

| Osoba | Zakres odpowiedzialności | Udział organizacyjny |
| --- | --- | --- |
| Artur Zamorowski | Symulacja, fizyka, kolizje i omówienie tych elementów | 1/3 |
| Kacper Wojtowicz | Q-learning, stan agenta, eksperymenty i interpretacja wyników | 1/3 |
| Rafał Wybraniec | Interfejs, dokumentacja i materiały do oddania | 1/3 |

To uzgodniony podział odpowiedzialności. Dane organizacyjne zespołu
są w `dane/zespol.json`.

## Zawartość

| Ścieżka | Zawartość |
| --- | --- |
| `sprawozdanie.pdf` | Sprawozdanie, 8 stron |
| `prezentacja.pdf` | Slajdy do demonstracji |
| `kod/pong/` | Fizyka, agenci, trening, ocena, interfejs i CLI |
| `dane/` | Protokół eksperymentów, scenariusze i dane zespołu |
| `modele/` | Gotowe tablice Q, metadane i przebiegi treningu CSV |
| `wyniki/` | Surowe pomiary CSV, podsumowania, wykresy i zrzuty |
| `uruchomienie/` | Instrukcja PDF i przypięte zależności |
| `dokumentacja/` | Edytowalne teksty sprawozdania i prezentacji |
| `narzedzia/` | Generowanie dokumentacji i sprawdzanie archiwum |

## Uczenie i eksperymenty

Jedna iteracja agenta odpowiada 4 krokom fizyki. Symulacja pracuje z krokiem
1/120 s, a agent podejmuje 30 decyzji na sekundę czasu gry. Trening działa bez
okna i bez ograniczenia do czasu rzeczywistego.

Wariant siatkowy dzieli boisko na kwadraty 50 lub 100 px. Stan zawiera kolumnę
piłki, różnicę wierszy piłki i paletki, znak prędkości poziomej oraz kategorie
prędkości pionowej piłki i paletki. Wariant rozszerzony, używany w demonstracji,
ma 810 stanów. Wykorzystuje błąd względem liniowej prognozy miejsca dolotu,
uwzględniającej odbicia od ścian. To jawnie dodana wiedza o geometrii gry.
Nie przewiduje krzywizny toru od rotacji. Decyzję o ruchu nadal wybiera tablica Q.

Nagroda bazowa wynosi +1 za zdobyty punkt, -1 za stracony i +0,2 za odbicie
własną paletką. Wariant podstawowy uczenia dodaje koszt polecenia ruchu,
karę za błąd pozycjonowania i składnik potencjałowy. Porównania obejmują
wyłączenie wskazówek, kosztu ruchu, zmianę rozdzielczości siatki i współczynnika
aktualizacji. Protokół określa 20 000 epizodów dla każdego z 10 przebiegów.

Przeciwnik treningowy śledzi aktualną wysokość piłki, ma martwą strefę 12 px
i aktualizuje polecenie co 4 decyzje, czyli co 133 ms. Paletki mają identyczne
ograniczenia fizyczne. Osobny test sprawdza reakcję przeciwnika co 33 ms.
Wyniki nie oznaczają skuteczności przeciw dowolnemu graczowi lub algorytmowi.

```bash
python kod/main.py train --episodes 20000 --seed 7 --output modele/wlasny.npz
python kod/main.py play --model modele/wlasny.npz
python kod/main.py experiment --output wyniki_odtworzone --models modele_odtworzone
```

Pełne odtworzenie wykorzystuje trzy procesy. Można ustawić `workers` na 1
w kopii protokołu i przekazać ją przez `--spec`. Surowe wyniki są deterministyczne
dla danego środowiska liczbowego i protokołu. Czasy wykonania i binarne archiwa
modeli nie muszą mieć identycznych sum na innych platformach.

Odsetek wygranych w tabelach dotyczy pojedynczych punktów. Remisy to wymiany
przerwane po 20 s. Dodatkowy mecz laboratoryjny składa się z 9 niezależnie
resetowanych punktów i różni się od meczu do 7 punktów w interfejsie.

## Fizyka i biblioteka gry

Interfejs używa Pygame-ce/SDL. To biblioteka multimedialna, a nie integracja
z gotowym silnikiem typu Godot lub Unity. Pętla gry i model fizyczny są częścią
projektu. Nie deklarujemy realizacji dodatkowego rozszerzenia z gotowym silnikiem.

Fizyka obejmuje przyspieszanie i hamowanie paletek, kąt odbicia zależny od
miejsca trafienia, przekazywanie części prędkości paletki, wzrost szybkości
piłki, rotację, jej zanikanie oraz krzywiznę toru. Kolizje z paletką sprawdzają
przecięcie płaszczyzny jej czoła. To model zręcznościowy. Przy narożnikach używa
uproszczenia zasięgu kontaktu o promień piłki, zamiast dokładnej kolizji koło-prostokąt.

## Generowanie dokumentacji

```bash
python -m pip install -r uruchomienie/wymagania_dev.txt
python narzedzia/wykresy.py
python narzedzia/dokumenty.py
```

Generatory odczytują dołączone pomiary. Nie tworzą przykładowych liczb.
PDF-y powstają w `output/pdf/` i trafiają również do lokalizacji wymaganych
przez instrukcję oddania. Zrzut gry można wykonać bez okna:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python kod/main.py play --demo --frames 240 --screenshot wynik.png
```

Zmienne SDL w tej składni dotyczą macOS/Linux. Zwykłe uruchomienie gry ich
nie wymaga.

## Repozytorium i oddanie

Repozytorium Git jest lokalne. Nie utworzono ani nie opublikowano zewnętrznego
repozytorium. Archiwum zawiera cały kod, więc ocena nie wymaga dostępu do hostingu.
Aktualną wersję można sprawdzić poleceniem `git log -1 --oneline`. Wersję
umieszczoną w archiwum wskazuje `wersja.json`.

Po zapisaniu wszystkich zmian w Git:

```bash
python narzedzia/pakuj.py
```

Wynik: `dist/projekt_1_pon_8.zip`, z jednym katalogiem `projekt_1_pon_8/`.
Paker sprawdza integralność ZIP-a i dołącza sumy SHA-256. Nie dołącza `.git`,
środowiska wirtualnego ani plików tymczasowych. Jedna osoba z zespołu przesyła
ZIP do zadania w Teams. Wszyscy członkowie uczestniczą w demonstracji.

## Źródła

- [Watkins i Dayan, Q-learning, 1992](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf).
- [Ng, Harada i Russell, reward shaping, 1999](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/NgHaradaRussell-shaping-ICML1999.pdf).
- [Oficjalna dokumentacja Pygame-ce](https://pyga.me/docs/).
- Instrukcja realizacji projektu i instrukcja oddania dostarczone przez prowadzącego.

Algorytm Q-learningu i idea kształtowania nagrody pochodzą z literatury.
Implementacja środowiska, reprezentacje stanu, protokół pomiarów i interfejs
powstały w tym repozytorium. Nie użyto gotowego kodu PONG ani zewnętrznych grafik.
