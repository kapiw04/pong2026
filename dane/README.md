# Dane i scenariusze

Projekt generuje dane przez symulację. Nie korzysta z zewnętrznego zbioru danych.

`eksperyment.json` określa liczbę epizodów, ziarna uczenia, osobne ziarna oceny,
warianty nagrody oraz model wybrany do demonstracji. Jeden epizod to jeden punkt.
Ziarna walidacji zaczynają się od 1000000, a testu od 2000000. Oba zbiory są
odrębne od strumieni losowych używanych podczas uczenia.

Scenariusze testowe:

- `standard`: piłka początkowo 430 px/s, limit 800 px/s, fizyka rozszerzona.
- `fast`: piłka początkowo 516 px/s, limit 960 px/s. Bez dodatkowego uczenia.
- `simple_physics`: ten sam agent w fizyce bez wpływu miejsca trafienia,
  prędkości paletki i rotacji. To test zmiany dynamiki, a nie osobny trening.
- `fast_reaction`: przeciwnik reaguje co decyzję zamiast co cztery decyzje.

W każdym scenariuszu paletki obu stron mają te same parametry. Lewa paletka
śledzi bieżącą wysokość piłki z martwą strefą 12 px. Zwykle aktualizuje polecenie
co 4 decyzje, czyli co 133 ms. Wiersze `evaluation.csv` zawierają ziarno
każdego punktu, wynik, liczbę odbić, czas symulacji i informację o limicie czasu.
`zespol.json` jest wspólnym źródłem danych organizacyjnych dokumentacji.
