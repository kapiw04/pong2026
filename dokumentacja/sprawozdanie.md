# PONG
Przeciwnik uczący się grać

Projekt 1 / Zespół 1 / poniedziałek 8:00-10:15
Sztuczna inteligencja w grach i rozszerzonej rzeczywistości
Sprawozdanie, 15 listopada 2026 r.

Celem projektu jest nauczenie paletki sterowania metodą prób i błędów. Po 20 000 punktów uczenia agent w trzech przebiegach wygrywa średnio 62,8% punktów testowych. Model przed uczeniem wygrywa 6,9%. Wyniki dotyczą opisanej reguły przeciwnika, a nie dowolnego gracza.

![Ilustracja](../wyniki/gra.png)

Rys. 1. Rzeczywisty zrzut demonstracji. Po prawej działa model z pliku NPZ.

| Osoba | Odpowiedzialność |
| --- | --- |
| Artur Zamorowski | Symulacja, model fizyki i kolizje. |
| Kacper Wojtowicz | Q-learning, reprezentacja stanu i eksperymenty. |
| Rafał Wybraniec | Interfejs i dokumentacja. |

Podział odpowiedzialności po 1/3. Zespół odpowiada za przygotowanie demonstracji i omówienie wyników.

---

# 1. Zadanie i architektura

Agent steruje prawą paletką. Otrzymuje położenie piłki, jej prędkość i położenie własnej paletki. Dodatkowo symulator udostępnia prędkość paletki i rotację piłki. Agent nie otrzymuje położenia przeciwnika. Wybiera jedną z trzech akcji: -1, 0, +1, odpowiadających ruchowi w górę, postojowi i ruchowi w dół.

Za punkt uznajemy przejście piłki poza boczną granicę boiska. Epizod treningowy kończy się po punkcie albo po 20 s czasu symulowanego. Serwis losuje kierunek, kąt i wysokość piłki oraz początkowe położenia obu paletek.

## Wspólny rdzeń treningu i gry

| Moduł | Rola i przepływ danych |
| --- | --- |
| config.py | Stałe boiska, fizyki i częstotliwości symulacji. |
| physics.py | Pong.reset(), observe(), step(). Akcje obu stron zmieniają stan i zwracają wynik przejścia. |
| agents.py | Dyskretyzacja obserwacji, tablica Q, aktualizacja, strategie odniesienia i zapis modelu. |
| experiments.py | Generowanie epizodów bez grafiki, ocena zamrożonych modeli, CSV i metadane. |
| gui.py | Sceny menu, gry, pauzy i końca meczu. Obsługa klawiatury i rysowanie stanu rdzenia. |
| cli.py | Polecenia play, train, evaluate i experiment. |
| narzedzia/ | Wykresy, generowanie PDF i kontrolowane pakowanie ZIP. |

Pętla uczenia pobiera obserwację, wybiera akcję epsilon-greedy, wykonuje krok środowiska i aktualizuje jedną komórkę tablicy Q. Pętla gry korzysta z tego samego środowiska, ale tylko odczytuje model. Wyświetlanie nie wpływa na czas fizyki.

## Środowisko wykonawcze

Pomiary wykonano w Pythonie 3.13.12 z NumPy 2.3.5. Interfejs korzysta z Pygame-ce 2.5.8 i SDL. NumPy przechowuje tablice, Matplotlib tworzy wykresy, a ReportLab PDF-y. Dokładne wersje przypięto w plikach wymagań.

Pygame-ce jest biblioteką multimedialną. Projekt ma własną pętlę i fizykę. Nie integruje gotowego silnika Godot ani Unity i nie deklaruje takiego rozszerzenia.

---

# 2. Fizyka rozgrywki

Rozszerzenie fizyki zmienia zarówno sterowanie, jak i obserwowany tor piłki. Paletka nie osiąga zadanej prędkości natychmiast. Agent musi odpowiednio wcześnie rozpocząć hamowanie. Trafienie krawędzią i ruch paletki nadają piłce inny kierunek oraz rotację.

| Parametr | Wartość w scenariuszu standard |
| --- | --- |
| Boisko / paletka / promień piłki | 900 x 500 px / 12 x 88 px / 8 px |
| Prędkość / przyspieszenie paletki | 460 px/s / 3600 px/s², identyczne po obu stronach |
| Szybkość piłki | 430 px/s na starcie, wzrost x1,06 po odbiciu, limit 800 px/s |
| Odbicie | Kąt zależny od miejsca trafienia, maks. 0,96 rad przed korektą ruchu |
| Krok fizyki / decyzji | 1/120 s / 1/30 s |
| Rotacja | Zakres [-7, 7], wykładniczy zanik z parametrem 0,55 s⁻¹ |

## Przebieg pojedynczego kroku

Paletka przyspiesza w stronę prędkości zadanej przez akcję. Symulator ogranicza ją do boiska. Następnie koryguje prędkość piłki o efekt rotacji, przesuwa piłkę, odbija ją od ścian i sprawdza przecięcie czoła paletki. Odbicie zachowuje nadmiar drogi po kolizji, co ogranicza przyklejanie do przeszkody.

```
u = clip((y_pilki - y_paletki) / 44, -1, 1)
speed = min(800, 1.06 * hypot(vx, vy))
vy_out = clip(speed*sin(0.96*u) + 0.22*vp,
              -0.88*speed, 0.88*speed)
abs(vx_out) = sqrt(speed**2 - vy_out**2)
```

Rotacja wynosi clip(5·v_p/460 + 2·u, -7, 7). W locie składnik pionowy zmienia się o 0,13·spin·v_x·dt. Potem normalizujemy wektor do poprzedniej szybkości. Tor zakrzywia się, lecz sam efekt rotacji nie dodaje energii. Odbicie od poziomej ściany zmienia znak i zmniejsza rotację współczynnikiem 0,8.

Kolizja z paletką używa przecięcia jej czoła, również gdy piłka przeskoczy tę płaszczyznę w jednym kroku. Zasięg pionowy kontaktu zwiększamy o promień piłki. To przybliżenie narożników, nie dokładna kolizja koła z prostokątem. Model ma charakter zręcznościowy i nie jest symulacją rzeczywistej aerodynamiki.

Test simple_physics wyłącza zależność odbicia od miejsca trafienia, ruchu paletki i rotacji. Pozostawia odbicia od ścian oraz wzrost szybkości. Zmienia dynamikę gotowego modelu i służy do oceny jego przenoszenia.

---

# 3. Stan agenta i uczenie

Zastosowano tablicowy Q-learning [1]. Każdy stan ma trzy wartości odpowiadające akcjom. Tablice rozpoczynają od zera. Uczenie nie korzysta z demonstracji człowieka ani z kopiowania ruchów reguły przeciwnika.

```
Q[s,a] = Q[s,a] + alfa * (r + gamma*max(Q[s_next])
                         - Q[s,a])
Dla zdobytego/straconego punktu: max(Q[s_next]) = 0
```

Współczynnik alfa wynosi 0,12, a gamma 0,98. Epsilon maleje liniowo z 0,9 do 0,05 przez pierwsze 85% epizodów i pozostaje na tym poziomie. Podczas oceny epsilon wynosi zero. Przy równych wartościach preferowany jest postój. Limit czasu odróżniamy od końca punktu: przy limicie aktualizacja zachowuje bootstrap.

| Reprezentacja | Opis | Liczba stanów |
| --- | --- | --- |
| Siatka 50 px | 18 kolumn, 19 różnic wierszy, znak vx, 3 kategorie vy i 3 kategorie prędkości paletki | 6156 |
| Siatka 100 px | 9 kolumn, 9 różnic wierszy, pozostałe cechy jak wyżej | 1458 |
| Względna, demonstracja | 15 przedziałów błędu dolotu, 3 pasy x, znak vx, 3 prędkości paletki i 3 strefy jej położenia | 810 |

Siatki kwadratowe realizują wariant opisany w planie. Dodatkowo sprawdzono redukcję stanu do błędu ustawienia względem przybliżonego miejsca dolotu. Prognoza liniowa używa bieżących x, y, vx, vy i odbić od ścian. Gdy piłka oddala się, punktem odniesienia jest środek boiska. Prognoza pomija rotację. To jawna wiedza dziedzinowa, dlatego porównanie reprezentacji obejmuje również korzyść z prognozowania, nie tylko zmianę liczby komórek.

## System nagród i kar

Nagroda bazowa to +1 za zdobyty punkt, -1 za stratę i +0,2 za własne odbicie. Dodajemy koszt 0,001 za polecenie ruchu. W wariancie ze wskazówkami występuje koszt 0,02·|błąd dolotu|/500 oraz składnik gamma·Phi(s') - Phi(s), gdzie Phi(s) = -|błąd dolotu|/500, a Phi stanu terminalnego jest zerowe [2].

Składnik potencjałowy ma postać opisaną w literaturze, ale cały system zawiera także inne koszty i nagrodę za odbicie. Zmieniają one cel optymalizacji. Nie zakładamy zachowania optymalnej strategii wygrywania ani teoretycznej zbieżności przy agregacji stanów, stałej alfie i pominięciu części dynamiki.

---

# 4. Protokół eksperymentów

Dane wejściowe generuje symulator. Nie pobierano zewnętrznych danych ani modeli. Każdy trening rozpoczyna nową, zerową tablicę Q i używa własnego generatora losowego. Wyniki oceny pochodzą z zamrożonej polityki.

| Ustawienie | Przyjęta wartość |
| --- | --- |
| Budżet | 20 000 epizodów na przebieg, 10 przebiegów = 200 000 punktów uczenia |
| Główne porównanie | Wskazówki włączone / wyłączone, po 3 ziarna: 7, 19, 41 |
| Analiza ustawień | Siatka 50 px, siatka 100 px, alfa 0,35 i brak kosztu ruchu. Każda zmiana: ziarno 7 |
| Walidacja | 180 punktów, ziarna 1000000-1000179. Ocena przed nauką i po 1000, 5000, 10000, 20000 epizodów |
| Test końcowy | 450 punktów na model i scenariusz, ziarna 2000000-2000449 |
| Model demonstracyjny | Z góry wskazane ziarno 7 i reprezentacja względna. Bez wyboru na podstawie testu |

## Przeciwnik i strategie odniesienia

Reguła steruje paletką w stronę bieżącej wysokości piłki z martwą strefą 12 px. Aktualizuje akcję co 4 decyzje, czyli co 133 ms. Paletki obu stron mają tę samą prędkość i przyspieszenie. Uczący się agent reaguje co 33 ms. Asymetria częstości reakcji jest częścią zadania i ogranicza zakres interpretacji wygranych.

W ocenie sprawdzamy także agenta losowego, zerową tablicę Q i regułę po prawej. Reguła porównawcza ma taką samą częstość reakcji jak przeciwnik podstawowy. Test fast_reaction przyspiesza reakcję lewej strony do 33 ms. Fast zwiększa szybkość początkową i maksymalną piłki o 20%. Simple_physics zmienia model odbić.

## Miary i niepewność

Mierzymy udział wygranych punktów, straty, remisy po 20 s, liczbę odbić obu paletek na punkt, czas trwania i udział decyzji z poleceniem ruchu. Dodatkowo liczymy wyniki bloków po 9 niezależnych punktów jako mecze laboratoryjne. Interfejs używa innej reguły: do 7 zdobytych punktów, bez limitu czasu wymiany.

Cały protokół zawiera 13950 punktów testu końcowego i trwał 4.5 min w zarejestrowanym środowisku, z maksymalnie trzema procesami trenującymi równolegle. Walidacja nie aktualizuje modelu. Wspólne ziarna zapewniają takie same serwisy, ale dalsze trajektorie zależą od strategii.

Przedziały Wilsona 95% opisują niepewność udziału wygranych przy ustalonym modelu i rozkładzie serwisów. Rozrzut między trzema treningami raportujemy osobno. Pojedyncze próby ustawień siatki i alfy mają charakter rozpoznawczy.

---

# 5. Wyniki uczenia

![Ilustracja](../wyniki/uczenie.png)

Rys. 2. Walidacja zamrożonych modeli. Linie: średnia z 3 treningów. Cieniowanie: minimum i maksimum, nie przedział ufności.

| Polityka / ziarno | Wygrane | Straty | Remisy | Odbicia / punkt |
| --- | --- | --- | --- | --- |
| Przed nauką | 31 (6,9%) | 419 | 0 | 0.91 |
| Losowy | 43 (9,6%) | 407 | 0 | 0.92 |
| Reguła | 167 (37,1%) | 277 | 6 | 4.02 |
| Q / 7 | 259 (57,6%) | 11 | 180 | 8.42 |
| Q / 19 | 288 (64,0%) | 4 | 158 | 8.27 |
| Q / 41 | 301 (66,9%) | 0 | 149 | 8.20 |

Średni odsetek wygranych po uczeniu ze wskazówkami wynosi 62,8%, a odchylenie standardowe między treningami 4.8 pkt proc. Wariant bez wskazówek osiąga średnio 69,0%. Krzywe nie są monotoniczne. Późniejszy punkt kontrolny może dać gorszą strategię z powodu stałego współczynnika aktualizacji, eksploracji i agregacji stanów.

Dla modelu demonstracyjnego uzyskano 259 wygranych, 11 strat i 180 remisów. Jego udział wygranych to 57,6%, z przedziałem Wilsona [52,9%; 62,0%]. W blokach po 9 punktów wygrał 50 z 50 meczów laboratoryjnych. Surowe wiersze są w evaluation.csv.

Poprawa względem zerowej tablicy potwierdza, że zapisane wartości Q zmieniają zachowanie agenta. Sam wzrost długości wymiany nie oznacza przewagi w wygrywaniu, dlatego raportujemy równocześnie czas, odbicia i wynik punktu.

---

# 6. Porównania i przenoszenie

![Ilustracja](../wyniki/porownanie.png)

Rys. 3. Modele z ziarnem 7 oraz strategie odniesienia. Wąsy: Wilson 95%. Warianty siatkowe różnią się również informacją zawartą w stanie.

| Scenariusz | Q, średnia 3 ziaren | Reguła |
| --- | --- | --- |
| Standard | 62,8% | 37,1% |
| Piłka +20% | 89,0% | 33,8% |
| Prosta fizyka | 55,7% | 40,4% |
| Szybka reakcja przeciwnika | 18,5% | 13,1% |

Przy tym samym budżecie siatka 50 px uzyskała 32,7%, a siatka 100 px 15,3% wygranych punktów. Wariant z alfą 0,35 uzyskał 56,2%. Jedno ziarno nie wystarcza do ogólnego uszeregowania rozdzielczości i alfy. Wynik pokazuje wpływ ustawień w tej konkretnej próbie.

Udział poleceń ruchu wyniósł 65,7% przy koszcie 0,001 oraz 62,3% bez niego. Udział wygranych bez kosztu wyniósł 58,4%. Koszt dotyczy każdej akcji ruchu, a nie bezpośrednio częstotliwości zmiany kierunku. Nie jest więc samodzielną miarą płynności animacji.

Szybsza piłka zwiększa średni udział wygranych Q do 89,0%, bo utrudnia również zadanie regule. Szybka reakcja przeciwnika obniża wynik Q do 18,5%. Rezultat zależy więc silnie od czasu reakcji przeciwnika. Testy używają gotowych tablic i oceniają przenoszenie. Nie mierzą przewagi trenowania z fizyką rozszerzoną nad trenowaniem z prostą.

---

# 7. Odtwarzalność i wnioski

Do gry i oceny wystarcza dostarczony model modele/pong_q.npz. Zawiera tablicę Q, liczniki odwiedzin i metadane JSON. Nie wymaga ponownego uczenia ani pobierania zewnętrznych wag. Plik manifest.json rejestruje konfigurację, środowisko, ziarna i sumy SHA-256 modeli.

```
python -m pip install -r uruchomienie/wymagania.txt
python kod/main.py play --demo
python kod/main.py evaluate --points 450
python kod/main.py experiment \
  --output wyniki_odtworzone --models modele_odtworzone
```

Przebiegi treningowe CSV zawierają epsilon, wynik, liczbę odbić i kroków każdego epizodu. Learning.csv przechowuje osobną ocenę walidacyjną, a evaluation.csv każdy punkt testu. Dokumenty i wykresy można ponownie wygenerować dołączonymi skryptami. Wersję kodu w paczce wskazuje wersja.json i sumy plików w archiwum.

## Sprawdzenie i ograniczenia

Ponowne uruchomienie oceny dołączonego modelu odtwarza wyniki 450 punktów ze scenariusza standard. Gra korzysta z zamrożonej tablicy Q. Zrzuty dokumentują rzeczywiste renderowanie interfejsu Pygame.

Obserwacja i agregacja stanów pomijają część informacji potrzebnych do pełnego modelu Markowa. Prognoza dolotu zakłada lot liniowy. Przeciwnik podstawowy ma wolniejszą reakcję od agenta, a budżet strojenia obejmuje tylko po jednym ziarnie dla kilku ustawień. Pomiary dotyczą środowiska lokalnego; nie potwierdzają ręcznej gry na wszystkich systemach operacyjnych.

## Wnioski i dalsze prace

Q-learning poprawił skuteczność względem modelu przed nauką. Rozdzielenie treningu od grafiki i zapis modeli pozwalają pokazać wynik bez czekania na naukę. Porównanie nagród nie uzasadnia traktowania każdej wskazówki jako poprawy. Następny krok to wieloziarnowe strojenie, porównanie równej częstości reakcji podczas treningu oraz lepsze uwzględnienie rotacji w stanie. Integracja z gotowym silnikiem pozostaje możliwym dalszym rozszerzeniem.

## Źródła i wykorzystane rozwiązania

[1] C. Watkins, P. Dayan, Q-learning, Machine Learning 8, 279-292, 1992.
[2] A. Ng, D. Harada, S. Russell, Policy invariance under reward transformations, ICML, 1999.
[3] Oficjalna dokumentacja Pygame-ce.
[4] Instrukcja realizacji projektu i instrukcja oddania dostarczone przez prowadzącego.
Z literatury przyjęto algorytm i ideę kształtowania nagrody. Środowisko, protokół, reprezentacje stanu i interfejs zaimplementowano w repozytorium.

---
