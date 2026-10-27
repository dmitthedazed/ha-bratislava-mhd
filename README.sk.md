<p align="center">
  <img src="custom_components/bratislava_mhd/brand/logo.png" alt="Dopravný podnik Bratislava" height="64">
</p>

<h1 align="center">Bratislava MHD pre Home Assistant</h1>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=dmitthedazed&repository=ha-bratislava-mhd&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Pridať do HACS"></a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=bratislava_mhd"><img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Pridať integráciu"></a>
</p>

<p align="center">
  <a href="https://github.com/dmitthedazed/ha-bratislava-mhd/actions/workflows/tests.yml"><img src="https://github.com/dmitthedazed/ha-bratislava-mhd/actions/workflows/tests.yml/badge.svg?branch=main" alt="Tests"></a>
  <a href="https://github.com/dmitthedazed/ha-bratislava-mhd/actions/workflows/validate.yml"><img src="https://github.com/dmitthedazed/ha-bratislava-mhd/actions/workflows/validate.yml/badge.svg?branch=main" alt="Validate"></a>
</p>

<p align="center"><a href="README.md">English</a> · <b>Slovenčina</b></p>

Kedy mi ide električka? Odpoveď máš priamo na dashboarde: odchody bratislavských
električiek, trolejbusov a autobusov naživo, zo zastávok, ktoré si vyberieš. Dáta posiela
online tabuľa imhd.sk, takže netreba účet ani API kľúč.

- Zastávky nájdeš na mape, podľa adresy alebo podľa názvu a spôsoby môžeš kombinovať.
  Potom odklikneš nástupištia, z ktorých naozaj chodíš.
- Každé nástupište je senzor. Stav ukazuje minúty do najbližšieho odchodu, zvyšok tabule je
  v atribútoch.
- Meškania sú v reálnom čase. Pri spojoch naživo vidíš aj to, kde vozidlo práve je a čo je
  zač: typ, nízkopodlažnosť, klimatizácia.
- Karta je súčasťou integrácie. Ťukni na nástupište a uvidíš len jeho odchody. Zmestí sa aj
  do úzkeho stĺpca.

<p align="center">
  <img src="docs/cards.png" alt="Karty s odchodmi" width="720">
</p>

## Inštalácia

Treba Home Assistant **2025.1** alebo novší. Najjednoduchšie je tlačidlo „Pridať do HACS“
hore (ide cez [My Home Assistant](https://my.home-assistant.io/)). Ak to nejde:

1. HACS → ⋮ → **Custom repositories**.
2. Vlož `https://github.com/dmitthedazed/ha-bratislava-mhd`, kategória **Integration**.
3. Nájdi **Bratislava MHD** a klikni na **Download**.
4. Reštartuj Home Assistant.

<details>
<summary>Ručná inštalácia</summary>

1. Skopíruj `custom_components/bratislava_mhd` do `<config>/custom_components/bratislava_mhd`.
2. Reštartuj Home Assistant.

</details>

## Nastavenie

Klikni na „Pridať integráciu“ hore alebo otvor **Nastavenia → Zariadenia a služby → Pridať
integráciu → Bratislava MHD**. Potom vyber, ako hľadať zastávky:

- **Na mape.** Špendlík začína pri tvojom dome, posuň ho a nastav polomer.
- **Podľa adresy**, napr. `Obchodná 10` alebo `Ružinov, Bajkalská`. Adresu dohľadá
  OpenStreetMap v rámci Slovenska.
- **Podľa názvu.** Stačí kus názvu a diakritika je dobrovoľná: `hodzovo` nájde Hodžovo nám.
  Viac naraz oddeľ čiarkou: `hodzovo, trnavske myto`.

Prvé hľadanie nenašlo všetko? Zaškrtni **Nájsť ďalšie zastávky** a hľadaj znova, vybrané
zastávky ti zostanú. V poslednom kroku vyberieš nástupištia. Z každej zastávky bude
zariadenie, z každého nástupišťa senzor.

Cez **Konfigurovať** pri integrácii zmeníš, koľko odchodov si nástupište drží, a pridáš
alebo odoberieš zastávky.

## Karta

`bratislava-mhd-card` prichádza s integráciou, nič ďalšie neinštaluješ. Po reštarte HA raz
obnov stránku (Ctrl+F5). V zozname kariet ju nájdeš ako **Bratislava MHD** a vizuálny editor
sa spýta na zastávku. V YAML:

```yaml
type: custom:bratislava-mhd-card
stop: 394             # id zastávky
platforms: [A, B]     # nepovinné, predvolene všetky
max: 6                # nepovinné
```

Písmená nástupíšť v hlavičke karty sú tlačidlá. Ťuknutím filtruješ, druhým ťuknutím sa
vrátiš ku všetkým.

| Filter podľa nástupišťa | Úzke stĺpce |
|:---:|:---:|
| <img src="docs/platform-filter.png" alt="Filter nástupišťa" width="300"> | <img src="docs/narrow.png" alt="Úzke karty" width="300"> |

<details>
<summary>Všetky možnosti karty</summary>

| Možnosť | Predvolene | Popis |
|---|---|---|
| `stop` | | Id zastávky. Výber karty doplní tvoju prvú zastávku |
| `stops` | | Viac zastávok, každá vo vlastnej karte. Bez `stop` aj `stops` uvidíš všetky |
| `platforms` | všetky | Len tieto nástupištia, napr. `[A, B]` |
| `max` | `6` | Koľko odchodov ukázať |
| `show_vehicle` | `true` | Typ vozidla, nízkopodlažnosť, klimatizácia |
| `title` | názov zastávky | Vlastný nadpis |
| `entities` | všetky senzory Bratislava MHD | Senzory nástupíšť vybrané ručne |

</details>

## Senzory

Jeden na nástupište, napríklad `sensor.hodzovo_nam_nastupiste_a`. Stav sú minúty do
najbližšieho odchodu, alebo `unknown`, keď nič nejde.

<details>
<summary>Atribúty</summary>

`stop_id`, `stop_name`, `platform`, `connected`, `info` (oznamy dopravcu) a `departures`,
zoznam takýchto položiek:

```yaml
- line: "4"
  headsign: Dúbravka
  expected: 1793070180     # epoch sekundy, s meškaním
  scheduled: 1793070180
  minutes: 3
  delay: 0                 # minúty
  realtime: true           # false: len podľa cestovného poriadku
  stuck: false             # imhd.sk hlási vozidlo ako uviaznuté
  last_stop: MiÚ Nové Mesto
  vehicle:
    type: Škoda 29T ForCity Plus
    low_floor: true
    ac: true
```

Keď spojenie s imhd.sk vypadne, senzory si nechajú poslednú tabuľu a pripoja sa samy.

</details>

## Príklady

<details>
<summary>Upozornenie 5 minút pred odchodom</summary>

```yaml
alias: "MHD: čas vyraziť"
triggers:
  - trigger: numeric_state
    entity_id: sensor.hodzovo_nam_nastupiste_a
    below: 6
actions:
  - action: notify.mobile_app_my_phone
    data:
      message: >-
        {% set d = state_attr('sensor.hodzovo_nam_nastupiste_a', 'departures')[0] %}
        Linka {{ d.line }} smer {{ d.headsign }} ide o {{ d.minutes }} min.
mode: single
```

</details>

<details>
<summary>Najbližšie odchody v karte Markdown</summary>

```yaml
type: markdown
title: Hodžovo nám.
content: >-
  {% for d in state_attr('sensor.hodzovo_nam_nastupiste_a', 'departures') or [] %}
  **{{ d.line }}** {{ d.headsign }}: {{ d.minutes }} min{{ ' (+%d)' % d.delay if d.delay > 0 }}
  {% else %}
  _zatiaľ nič nejde_
  {% endfor %}
```

</details>

## Odkiaľ sú dáta

Odchody idú z online tabule imhd.sk. Názvy zastávok, ich polohy a nástupištia z verejného
katalógu zastávok na `api.magicsk.eu`. Adresy sa posielajú do
[OpenStreetMap Nominatim](https://nominatim.org/), a to len pri nastavovaní.

Regionálne autobusy IDS BK sa ukážu, len ak ich imhd.sk zobrazuje.

## Licencia

GPL-3.0. Integrácia je neoficiálna a s Dopravným podnikom Bratislava, imhd.sk ani IDS BK
nemá nič spoločné. Názov a logo DPB patria Dopravnému podniku Bratislava, sú tu len na to,
aby bolo jasné, o akú sieť ide.
