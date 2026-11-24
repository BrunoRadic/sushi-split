# Sushi Split

Cijene sushija u Splitu s Wolta, preračunate po komadu. Mac 4x dnevno povuče podatke
u `docs/data/` i pusha ih, a GitHub Pages servira stranicu.
(Wolt blokira GitHub Actions s 429, pa scrape ide s kućne IP adrese.)

## Postavljanje (jednom)

1. Napravi **public** repo i pushaj ovaj folder.
2. Settings → Pages → Source: *Deploy from a branch*, Branch: `main`, folder `/docs` → Save.
3. Na Macu: `./scripts/install-mac.sh` (repo ne smije biti u Desktop/Documents/Downloads).
4. Za minutu-dvije nakon prvog pusha stranica je na `https://<tvoj-username>.github.io/<ime-repoa>/`.

## Broj komada

Upiši u `scraper/overrides.csv`, pa pokreni `./scripts/update.sh`:
```
venue,name,pieces,type
sora-sushi-bar,type:roll,8,
biberon-sushi-bar,Nika roll,8,
antique-sushi-bar,Gyoze ✨,,ostalo
```
- `type:roll`: default za sve rollove tog restorana bez broja komada (na stranici označeno s ≈)
- točan naziv ima prednost pred pravilom
- samo `type` popunjen: ispravlja tip

## Lokalno

```
python3 scraper/build.py              # povuče s Wolta, zapiše docs/data/
python3 scraper/build.py --offline    # ponovi obradu iz scraper/raw/ bez novih zahtjeva
cd docs && python3 -m http.server     # stranica na http://localhost:8000
```

## Ručno ažuriranje

```
./scripts/update.sh
```
