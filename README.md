# Pong

Projekt 1, Sztuczna inteligencja w grach i rozszerzonej rzeczywistości.
Zespół 1, poniedziałek 8:00–10:15.

| Osoba | Zakres |
| --- | --- |
| Artur Zamorowski | Model bazowy i trening |
| Kacper Wojtowicz | Usprawnienia modelu względem wariantu bazowego, interfejs i prezentacja |
| Rafał Wybraniec | Silnik gry, sprawozdanie i dobór parametrów |

## Uruchomienie

Wymagany jest Python 3.11 lub nowszy. Gotowe modele są dołączone.
Proszę rozpakować archiwum i otworzyć terminal w katalogu projektu.
Jeśli projekt został pobrany z GitHuba, proszę otworzyć katalog repozytorium.

Na macOS i Linux proszę wykonać:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/main.py play
```

Na Windows proszę wykonać:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src\main.py play
```

Domyślne ustawienie `demo: true` w `config.yaml` uruchamia pokaz
Trackera przeciw agentowi. Aby zagrać samodzielnie, proszę nacisnąć
Esc, a następnie Enter. Mecz trwa do 7 punktów.

- Proszę używać W/S lub strzałek do poruszania lewą paletką.
- Proszę nacisnąć Spację, aby zatrzymać lub wznowić grę.
- Proszę nacisnąć D, aby rozpocząć nowy mecz i przełączyć tryb pokazu.
- Proszę nacisnąć R, aby rozpocząć nowy mecz w bieżącym trybie.
- Proszę nacisnąć H, aby wyświetlić lub ukryć pomoc.
- Proszę nacisnąć Esc, aby wrócić do menu. Aby zamknąć grę z menu,
  proszę nacisnąć Esc ponownie.

Aby uruchomić pozostałe tryby, proszę wykonać odpowiednie polecenie
w aktywnym środowisku wirtualnym:

```bash
python src/main.py train
python src/main.py evaluate
python src/main.py matches
```

`evaluate` ocenia wybrany model i poprzedni model na wspólnych serwisach.
`matches` sprawdza pełne mecze do 7 punktów, bez okna i limitu 20 s na wymianę.
`train` rozpoczyna nowy trening pojedynczego ustawienia z sekcji `training`.
Najlepsza tablica zastępuje model gry, jeśli w ocenie końcowej wygrywa
częściej, niż przegrywa.
Na Windows proszę zastąpić `python` przez `.venv\Scripts\python.exe`.
Aby zmienić parametry, proszę edytować `config.yaml`.
Ścieżki w konfiguracji odnoszą się do katalogu projektu.

## Agent i trening

Tablicowy Q-learning wybiera ruch w górę, postój lub ruch w dół.
Stan zawiera pozycję i prędkość piłki, pozycję i prędkość paletki oraz spin.
Koduje też bieżącą różnicę wysokości piłki i paletki. Nie przewiduje miejsca
odbicia. Sytuacje odbite względem poziomej osi boiska współdzielą wiersz Q.

Trening zaczyna od zerowej tablicy. Nagrody: +1 za punkt, -1 za stratę,
+0,2 za odbicie. Co 100 000 epizodów model jest oceniany na 400 serwisach
walidacyjnych. Najlepszy checkpoint przechodzi końcową ocenę; zastępuje
model gry, jeśli wygrywa częściej od Trackera. Trening i gra używają
jednej implementacji fizyki w Pythonie.

Wybrany model ma komórkę 25 px, alfę 0,15 i gammę 0,995. Pochodzi
z checkpointu 1 800 000 epizodów treningu.
Na wspólnych 5000 serwisach o ziarnach 11 000 000–11 004 999:

| Model | Wygrane | Porażki | Limit 20 s |
| --- | ---: | ---: | ---: |
| Usprawniony | 50,24% | 24,56% | 25,20% |
| Bazowy W32 | 27,86% | 48,74% | 23,40% |

W 100 pełnych meczach na ziarnach 12 000 000–12 000 099 agent wygrał
89 razy, a Tracker 11. Łączny wynik punktów: 673:352.

## Pliki

- `src/main.py`: uruchamianie, trening i ocena.
- `src/pong/`: agent, fizyka i interfejs.
- `models/`: tablice Q porównywanych modeli.
- `results/`: krzywa uczenia, końcowe wyniki i pełne mecze.
- `docs/report.tex`, `report.pdf`: sprawozdanie z eksperymentu bazowego W32 i usprawnień modelu.
- `docs/data/experiments.zip`: dane obu eksperymentów i metadane modelu użyte w sprawozdaniu.
- `docs/instructions.pdf`, `docs/instructions.tex`: instrukcja uruchomienia i jej źródło.

Repozytorium: [pong2026](https://github.com/kapiw04/pong2026).
