# Projekt 1. Pong - przeciwnik uczący się grać

Zespół 1, poniedziałek 8:00-10:15. Wersja 1.1.0.
Przedmiot: Sztuczna inteligencja w grach i rozszerzonej rzeczywistości.

Gra Pong z przeciwnikiem uczonym przez Q-learning. Agent steruje prawą
paletką. Trening działa bez grafiki, a gotowy model jest dołączony do projektu.

## Zespół

| Osoba | Zakres |
| --- | --- |
| Artur Zamorowski | Symulacja, fizyka i kolizje |
| Kacper Wojtowicz | Agent, trening i eksperymenty |
| Rafał Wybraniec | Interfejs i dokumentacja |

## Uruchomienie

Wymagany Python 3.11 lub nowszy. Wersje bibliotek są przypięte
w `uruchomienie/wymagania.txt`: NumPy 2.3.5, Pygame-ce 2.5.8 i PyYAML 6.0.3.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r uruchomienie/wymagania.txt
python kod/main.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r uruchomienie/wymagania.txt
.venv\Scripts\python.exe kod\main.py
```

Enter rozpoczyna grę. W/S lub strzałki sterują paletką, Spacja włącza pauzę,
H pokazuje sterowanie, Esc wraca do menu. Mecz trwa do 7 punktów.
Wymiany w grze nie mają limitu czasu.

## Konfiguracja

Wszystkie ustawienia są w `konfiguracja.yaml`. Program uruchamia się bez
argumentów. Ścieżki w YAML są liczone względem katalogu projektu.

| `mode` | Działanie |
| --- | --- |
| `play` | Gra z modelem wskazanym w `play.model`; `play.demo: true` włącza pokaz |
| `train` | Trening według sekcji `train`, domyślnie 20 000 epizodów |
| `evaluate` | Ocena modelu, domyślnie 450 punktów |
| `experiment` | Pełne porównanie z protokołu `dane/eksperyment.yaml` |

Po treningu własnego modelu ustaw `mode: play` i `play.model: modele/wlasny.npz`.
Wyniki ponownej oceny i eksperymentów trafiają domyślnie do osobnych katalogów.
Limit 20 s na punkt dotyczy tylko treningu i oceny.

## Zawartość

| Katalog lub plik | Zawartość |
| --- | --- |
| `kod/pong/` | Gra, fizyka, Q-learning i odczyt ustawień |
| `dane/` | Protokół eksperymentów i opis scenariuszy |
| `modele/` | Gotowe tablice Q i przebiegi treningu CSV |
| `wyniki/` | Pomiary, podsumowania, wykresy i zrzuty gry |
| `uruchomienie/` | Instrukcja PDF i wymagania |
| `dokumentacja/` | Teksty dokumentów |
| `narzedzia/` | Generowanie wykresów i PDF-ów |
| `sprawozdanie.pdf` | Opis rozwiązania i wyniki, 8 stron |
| `prezentacja.pdf` | Slajdy do prezentacji |

Pygame-ce/SDL obsługuje okno, klawiaturę i rysowanie. Fizyka projektu obejmuje
przyspieszanie paletek, odbicie zależne od miejsca trafienia i ruchu paletki,
rotację piłki oraz wzrost jej szybkości po odbiciu.

## Wyniki i dokumentacja

Pełny eksperyment obejmuje 10 treningów po 20 000 punktów. Porównuje nagrody,
rozmiary siatki i współczynnik uczenia. Parametry oraz ziarna są zapisane
w `dane/eksperyment.yaml`, a pomiary w `wyniki/`. Gra działa z dołączonym
modelem `modele/pong_q.npz`, bez ponownego uczenia.

```bash
python -m pip install -r uruchomienie/wymagania_dev.txt
python narzedzia/wykresy.py
python narzedzia/dokumenty.py
```

Paczka do oddania to `dist/projekt_1_pon_8.zip`. Zawiera cały kod, modele,
wyniki i PDF-y. Wersję wskazuje `wersja.json`, a zawartość można sprawdzić
przez `SUMY_SHA256.txt`. Repozytorium Git jest lokalne.

## Źródła

- [Watkins i Dayan, Q-learning, 1992](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf).
- [Ng, Harada i Russell, reward shaping, 1999](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/NgHaradaRussell-shaping-ICML1999.pdf).
- [Dokumentacja Pygame-ce](https://pyga.me/docs/).
