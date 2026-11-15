# 1. Pong. Przeciwnik uczący się grać

Tablicowy Q-learning w grze 2D

![gra.png](wyniki/gra.png)

Artur ZamorowskiKacper WojtowiczRafał Wybraniec

Projekt 1Poniedziałek 8:00

# 2. Zadanie i wspólna symulacja

Agent steruje prawą paletką. Wybiera ruch w górę, postój albo ruch w dół.

Trening bez grafiki oraz gra korzystają z tego samego modułu fizyki. Symulacja: 120 Hz. Decyzje agenta: 30 Hz.

Moduły: fizyka, agenci, eksperymenty, interfejs i ustawienia YAML.Model NPZ zawiera tablicę Q i konfigurację. Gra tylko go odczytuje.

# 3. Q-learning i dyskretyzacja

Q(s,a) otrzymuje poprawkę alfa · [r + gamma · max Q(s',a') - Q(s,a)].

Siatki kwadratowe 50 i 100 px. Porównanie z reprezentacją względną, która używa przybliżonego punktu dolotu i ma 810 stanów.

Każdy trening zaczyna od zerowej tablicy. Epsilon maleje z 0,9 do 0,05. Podczas testu epsilon = 0. Alfa = 0,12, gamma = 0,98.

Źródło metody: Watkins i Dayan, Q-learning, 1992. Szczegóły w sprawozdaniu.

# 4. Fizyka i nagrody

Miejsce trafienia i ruch paletki zmieniają kąt odbicia oraz rotację. Rotacja zakrzywia tor i zanika. Paletki przyspieszają i hamują.

+1 zdobyty punkt, -1 strata, +0,2 odbicie.Koszt polecenia ruchu oraz wariant ze wskazówką pozycjonowania.

Porównujemy wyłączenie wskazówek i kosztu ruchu. Dodatkowe składniki nagrody zmieniają cel optymalizacji.

# 5. Demonstracja działającej gry

python kod/main.py

W konfiguracja.yaml ustaw mode: play oraz play.demo: true.

Enter: człowiek kontra agent. W/S: ruch. Spacja: pauza. Tab: porównanie z regułą, losowym i modelem przed nauką.

Przedmiot demonstracji: śledzenie piłki, odbicie ruchomą paletką, rotacja oraz decyzje zapisanej tablicy Q.

Pygame-ce/SDL i własna fizyka. Gotowy model działa bez ponownego treningu.

# 6. Uczenie w trzech niezależnych przebiegach

![uczenie_slajd.png](wyniki/uczenie_slajd.png)

Średnia z 3 treningów. Cieniowanie pokazuje zakres od minimum do maksimum.

# 7. Wyniki testu i porównanie ustawień

![porownanie_slajd.png](wyniki/porownanie_slajd.png)

Test: 450 punktów. Główny wariant Q: średnio 62,8% wygranych, 3 ziarna treningu.

# 8. Ograniczenia, odpowiedzialność i rozwój

Wynik zależy od przeciwnika i rozdzielczości stanu. Reguła podstawowa reaguje co 133 ms, agent co 33 ms. Osobny test wyrównuje częstość reakcji.

Artur: ruch paletek, dyskretyzacja stanu, instrukcja.Kacper: odbicia piłki, Q-learning, analiza wyników.Rafał: interfejs, trening agenta, sprawozdanie.

Dalsze prace: więcej ziaren strojenia, uwzględnienie rotacji w stanie i trening przeciw szybszej regule.
