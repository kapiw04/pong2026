# Pomiary

Wyniki pochodzą z protokołu zapisanego w `dane/eksperyment.yaml`.
Parametry pozostały takie same po przeniesieniu konfiguracji do YAML.

- `evaluation.csv`: 13 950 punktów testu końcowego. Kolumny identyfikują politykę,
  ziarno treningu, scenariusz i ziarno serwisu. `winner` to 1 dla prawej strony,
  -1 dla lewej i 0 przy limicie czasu. `hits` liczy odbicia obu paletek.
- `learning.csv`: 50 ocen walidacyjnych, po 180 punktów każda. `win_rate`
  pochodzi z oceny bez eksploracji.
- `summary.json`: agregaty każdego modelu i scenariusza, przedziały Wilsona 95%,
  czas, odbicia, udział poleceń ruchu i wyniki bloków po 9 punktów.
- `manifest.json`: protokół, parametry środowiska, wersje, czas i sumy modeli.
- `uczenie.png`, `porownanie.png`, `odpornosc.png`: wykresy z pomiarów.
- Pliki z końcówką `_slajd.png`: te same dane z większymi napisami do prezentacji.
- `gra.png`, `menu.png`: rzeczywiste renderowanie interfejsu Pygame.

Średnia głównego wariantu na teście standardowym wynosi 62,8% wygranych
punktów. Wariant bez wskazówek osiąga 69,0%. Dla porównania reguła uzyskuje
37,1%, losowy 9,6%, a zerowa tablica 6,9%. Warianty Q obejmują 3 ziarna
uczenia, strategie odniesienia jeden zestaw 450 serwisów.

Reguła podstawowa wydaje nowe polecenie co 133 ms, a agent Q co 33 ms.
Przy przyspieszeniu reakcji przeciwnika udział wygranych głównego wariantu
spada średnio do 18,5%. Wynik zależy od czasu reakcji przeciwnika.
Zwiększenie szybkości piłki pomaga w tym teście agentowi,
ponieważ utrudnia śledzenie także jego przeciwnikowi.

Wykres uczenia pokazuje średnią oraz zakres minimum-maksimum z 3 ziaren.
Wykres porównawczy pokazuje ziarno 7 i przedziały Wilsona, które opisują
zmienność serwisów przy ustalonym modelu. Rozrzut treningów jest osobną miarą.
