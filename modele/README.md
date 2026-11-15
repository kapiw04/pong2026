# Wyuczone tablice Q

`pong_q.npz` jest kopią `q_seed_7.npz`, wskazaną w protokole przed oceną testową.
Ten model jest gotowy do gry.

Każdy plik NPZ zawiera tablicę `q` typu float32, liczniki `visits` oraz
metadane JSON: wersję enkodera, parametry fizyki, nagrody, ziarno i budżet.
Wczytywanie wyłącza pickle. Sumy SHA-256 zapisano w `wyniki/manifest.json`.

| Nazwa | Wariant |
| --- | --- |
| `q_seed_{7,19,41}.npz` | Reprezentacja względna, wskazówki i koszt ruchu |
| `q_no_shaping_seed_{7,19,41}.npz` | Bez kosztu błędu i składnika potencjałowego, z kosztem ruchu |
| `grid50_seed_7.npz` | Kwadraty 50 px, alfa 0,12 |
| `grid100_seed_7.npz` | Kwadraty 100 px, alfa 0,12 |
| `alpha035_seed_7.npz` | Reprezentacja względna, alfa 0,35 |
| `no_movement_cost_seed_7.npz` | Reprezentacja względna, koszt polecenia ruchu 0 |

Każdy trening obejmuje 20 000 epizodów od zerowej tablicy. Odpowiadający mu
plik `.training.csv` zawiera wszystkie epizody, także te zakończone limitem.
`base_reward` oznacza wyłącznie punkt i odbicia.

Warianty siatkowe używają względnej różnicy wierszy piłki i paletki. Wariant
demonstracyjny korzysta z liniowej prognozy dolotu, która jest dodatkową cechą
opracowaną dla tego środowiska. Porównanie obejmuje rozmiar tablicy i użyte cechy stanu.
