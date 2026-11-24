# Sushi Split

Cijene sushija u Splitu s Wolta, preračunate po komadu. Radi samo na GitHubu:
GitHub Actions 4x dnevno povuče podatke u `docs/data/`, a GitHub Pages servira stranicu.

## Postavljanje (jednom)

1. Napravi **public** repo i pushaj ovaj folder.
2. Settings → Pages → Source: *Deploy from a branch*, Branch: `main`, folder `/docs` → Save.
3. Actions → **Scrape** → *Run workflow* (prvo punjenje podataka).
4. Za minutu-dvije stranica je na `https://<tvoj-username>.github.io/<ime-repoa>/`.

## Broj komada

Upiši u `scraper/overrides.csv` i pushaj, workflow se pokrene sam:
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

## Ako Wolt blokira GitHub Actions

Ako u logu workflowa vidiš `ERR` za sve restorane (403/429), pokreći scrape s Maca i pushaj:
```
python3 scraper/build.py && git add docs/data && git commit -m "Podaci" && git push
```
