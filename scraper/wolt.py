"""Wolt sushi scraper: povlači meni za listu restorana i računa €/kom."""
from __future__ import annotations
import csv, json, os, re, sys, time, urllib.request

LAT, LON = 43.5116, 16.4396  # Split
LIST_URL = f"https://consumer-api.wolt.com/v1/pages/venue-list/category-sushi?lat={LAT}&lon={LON}"
URL ="https://consumer-api.wolt.com/consumer-api/consumer-assortment/v1/venues/slug/{}/assortment"
RAW_DIR = os.environ.get("RAW_DIR", "raw")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "hr"}

KOM_RE = re.compile(r"(\d+)\s*(?:kom|komada|pcs|pieces)", re.I)
LEAD_RE = re.compile(r"^\s*(\d+)\s*x?\b", re.I)


def pieces(desc: str) -> int | None:
    """'4x maki, 4x roll' -> 8 | '8 miješani roll' -> 8 | '(8 komada)' -> 8 | 'Losos' -> None"""
    if not desc:
        return None
    total = 0
    for part in re.split(r"[,\n]", desc):
        m = LEAD_RE.match(part)
        if m:
            total += int(m.group(1))
    if total:
        return total
    m = KOM_RE.search(desc)
    return int(m.group(1)) if m else None


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def discover(data: dict) -> list[dict]:
    """Iz venue-list odgovora izvuče restorane."""
    venues = []
    for sec in data.get("sections", []):
        for it in sec.get("items", []):
            v = it.get("venue")
            if not v:
                continue
            venues.append({
                "slug": v["slug"],
                "name": v["name"],
                "address": v.get("address", "").strip(),
                "lon": v["location"][0],
                "lat": v["location"][1],
                "rating": (v.get("rating") or {}).get("score"),
                "price_range": v.get("price_range"),
                "tags": ",".join(v.get("tags", [])),
            })
    return venues


TYPES = [  # redoslijed je bitan: prvi pogodak pobjeđuje
    ("set", r"\bmeni|menu|\bbox\b|\bset\b|^M\d+"),
    ("sashimi", r"sa[s]?h?imi"),
    ("temaki", r"temaki"),
    ("maki", r"\bmaki\b|hosomaki"),
    ("roll", r"roll|uramaki|futomaki|philadelphia|california"),
    ("nigiri", r"nig[i]?ri|sushi"),
]
FISH = re.compile(r"losos|salmon|sake|tuna|tun[aeiu]|maguro|škamp|kozic|prawn|shrimp|ebi|surimi|rak|unagi|jegulj|skuš|hamachi|ikura|kavijar|riba|fish", re.I)
NON_SUSHI = re.compile(r"gyoz|noodle|wok|bowl|juha|soup|edamame|spring roll|teriyaki steak|bun\b|desert|dessert|piće|drink", re.I)


FILLING = re.compile(r"avokad|krastav|sezam|majonez|krem sir|philadelphia|mascarpon|sir\b", re.I)


def item_type(name: str, desc: str, category: str) -> str:
    if NON_SUSHI.search(name):
        return "ostalo"
    for t, pat in TYPES:  # 1) naziv
        if re.search(pat, name, re.I):
            return t
    if re.search(r"riž", desc, re.I) and FILLING.search(desc):  # 2) "4x riža, avokado, losos" = roll
        return "roll"
    for t, pat in TYPES:  # 3) kategorija kao zadnji fallback
        if re.search(pat, category, re.I):
            return t
    return "ostalo"


def load_overrides(path: str = os.environ.get("OVERRIDES", "overrides.csv")) -> dict:
    """venue,name,pieces,type — name je točan naziv ili 'type:roll' za default tog tipa u restoranu."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["venue"].strip(), r["name"].strip())] = r
    return out


def apply_overrides(rows: list[dict], ov: dict):
    for r in rows:
        exact = ov.get((r["venue"], r["name"]))
        if exact and exact.get("type"):
            r["type"] = exact["type"].strip()
        if r["pieces"]:
            continue
        rule = exact if exact and exact.get("pieces") else ov.get((r["venue"], f"type:{r['type']}"))
        if rule and rule.get("pieces"):
            r["pieces"] = int(rule["pieces"])
            r["pieces_src"] = "ručno" if rule is exact else "pravilo"
            r["eur_per_piece"] = round(r["price_eur"] / r["pieces"], 2)


def parse(slug: str, data: dict) -> list[dict]:
    cat_of = {iid: c["name"] for c in data.get("categories", []) for iid in c.get("item_ids", [])}
    rows = []
    for it in data.get("items", []):
        price = it["price"] / 100
        orig = (it.get("original_price") or 0) / 100
        desc = it.get("description") or ""
        cat = cat_of.get(it["id"], "")
        m = KOM_RE.search(it["name"])  # "Pop box (22 komada)"; ne LEAD_RE jer "021 Maki" nije 21 kom
        n_desc = pieces(desc)
        n = n_desc or (int(m.group(1)) if m else None)
        src = "opis" if n_desc else ("naziv" if n else "")
        rows.append({
            "id": it["id"],
            "venue": slug,
            "category": cat,
            "type": item_type(it["name"], desc, cat),
            "fish": bool(FISH.search(f"{it['name']} {desc}")),
            "name": it["name"],
            "description": desc.replace("\n", " "),
            "pieces": n,
            "pieces_src": src,
            "price_cents": it["price"],
            "original_cents": it.get("original_price") or None,
            "price_eur": price,
            "eur_per_piece": round(price / n, 2) if n else None,
            "original_eur": orig or None,
            "discount_pct": round((1 - price / orig) * 100) if orig > price else None,
            "popular": any(t.get("id") == "popular" for t in it.get("tags") or []),
        })
    return rows


def save(path: str, rows: list[dict]):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def coverage(rows: list[dict]) -> list[dict]:
    sushi = [r for r in rows if r["type"] != "ostalo"]
    print("\nPokrivenost (sushi stavke s poznatim brojem komada):")
    for v in sorted({r["venue"] for r in sushi}):
        vr = [r for r in sushi if r["venue"] == v]
        ok = sum(1 for r in vr if r["pieces"])
        print(f"  {ok:>3}/{len(vr):<3} {ok / len(vr):>4.0%}  {v}")
    missing = [{"venue": r["venue"], "name": r["name"], "pieces": "", "type": r["type"],
                "description": r["description"], "price_eur": r["price_eur"]}
               for r in sushi if not r["pieces"]]
    save("missing.csv", missing)
    print(f"  → {len(missing)} stavki bez broja komada u missing.csv")
    return missing


def report(rows: list[dict]):
    print("\nNajjeftinije po komadu (samo riba), po tipu:")
    for t in ["maki", "roll", "nigiri", "sashimi", "set"]:
        best = sorted((r for r in rows if r["type"] == t and r["fish"] and r["eur_per_piece"]),
                      key=lambda r: r["eur_per_piece"])[:3]
        if best:
            print(f"  [{t}]")
            for r in best:
                print(f"    {r['eur_per_piece']:>5.2f} €/kom  {r['price_eur']:>6.2f} €  {r['pieces']:>3} kom  {r['name']}  ({r['venue']})")
    deals = sorted((r for r in rows if r["discount_pct"]), key=lambda r: -r["discount_pct"])
    print(f"\nAkcije: {len(deals)}")
    for r in deals:
        print(f"  -{r['discount_pct']}%  {r['name']}  {r['original_eur']} → {r['price_eur']} €  ({r['venue']})")


def cached(name: str, url: str, offline: bool) -> dict:
    """Sirovi JSON sprema u raw/ — s --offline radiš na parseru bez novih zahtjeva prema Woltu."""
    path = os.path.join(RAW_DIR, f"{name}.json")
    if offline:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    data = get(url)
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    time.sleep(2)  # pristojno prema API-ju
    return data


def main():
    offline = "--offline" in sys.argv
    venues = discover(cached("_venues", LIST_URL, offline))
    print(f"Pronađeno {len(venues)} restorana", file=sys.stderr)
    save("venues.csv", venues)

    rows = []
    for v in venues:
        try:
            rows += parse(v["slug"], cached(v["slug"], URL.format(v["slug"]), offline))
            print(f"OK  {v['slug']}", file=sys.stderr)
        except Exception as e:
            print(f"ERR {v['slug']}: {e}", file=sys.stderr)

    apply_overrides(rows, load_overrides())
    save("sushi.csv", rows)
    coverage(rows)
    report(rows)


if __name__ == "__main__":
    main()
