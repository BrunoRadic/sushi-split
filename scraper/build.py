"""Povuče Wolt podatke i zapiše statične JSON-e za GitHub Pages.

python scraper/build.py            # povuče s Wolta
python scraper/build.py --offline  # koristi scraper/raw/ (za lokalno dotjerivanje parsera)

Izlaz u docs/data/:
  items.json    trenutne stavke s €/kom i popustom
  venues.json   restorani sa sažetkom
  history.json  {item_id: [[datum, cijena_centi, originalna_centi|null], ...]}; nova točka samo kad se cijena promijeni
  meta.json     vrijeme zadnjeg ažuriranja i brojke
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "docs" / "data"
os.environ.setdefault("RAW_DIR", str(ROOT / "raw"))
os.environ.setdefault("OVERRIDES", str(ROOT / "overrides.csv"))

import wolt  # noqa: E402  (mora nakon env varijabli)


def load(name: str, default):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def dump(name: str, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    offline = "--offline" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    venues = wolt.discover(wolt.cached("_venues", wolt.LIST_URL, offline))
    rows, ok, failed = [], [], []
    for v in venues:
        try:
            rows += wolt.parse(v["slug"], wolt.cached(v["slug"], wolt.URL.format(v["slug"]), offline))
            ok.append(v)
            print(f"OK  {v['slug']}", file=sys.stderr)
        except Exception as e:
            failed.append(v["slug"])
            print(f"ERR {v['slug']}: {e}", file=sys.stderr)

    if not ok:
        sys.exit("Nijedan restoran nije povučen, stari podaci ostaju netaknuti.")

    wolt.apply_overrides(rows, wolt.load_overrides())

    # Restoran koji ovaj put nije uspio zadržava stare stavke, da stranica ne ostane prazna.
    old_items = load("items.json", [])
    rows_out = []
    for r in rows:
        rows_out.append({
            "id": r["id"], "venue_slug": r["venue"], "name": r["name"], "description": r["description"],
            "category": r["category"], "type": r["type"], "fish": r["fish"],
            "pieces": r["pieces"], "pieces_src": r["pieces_src"] or None,
            "price_eur": round(r["price_cents"] / 100, 2),
            "original_eur": round(r["original_cents"] / 100, 2) if r["original_cents"] else None,
            "eur_per_piece": round(r["price_cents"] / 100 / r["pieces"], 2) if r["pieces"] else None,
            "discount_pct": r["discount_pct"], "popular": r["popular"],
        })
    rows_out += [i for i in old_items if i["venue_slug"] in failed]

    # Povijest: nova točka samo kad se (cijena, originalna) promijeni.
    history = load("history.json", {})
    changes = 0
    for r in rows:
        point = [r["price_cents"], r["original_cents"]]
        h = history.setdefault(r["id"], [])
        if not h or h[-1][1:] != point:
            h.append([now, *point])
            changes += 1

    # Sažetak po restoranu.
    old_venues = {v["slug"]: v for v in load("venues.json", [])}
    venues_out = []
    for v in ok + [old_venues[s] for s in failed if s in old_venues]:
        vi = [i for i in rows_out if i["venue_slug"] == v["slug"]]
        sushi = [i for i in vi if i["type"] != "ostalo"]
        if not sushi:
            continue
        per_piece = [i["eur_per_piece"] for i in sushi if i["fish"] and i["eur_per_piece"]]
        discounts = [i["discount_pct"] for i in vi if i["discount_pct"]]
        venues_out.append({
            **{k: v[k] for k in ("slug", "name", "address", "lat", "lon", "rating", "price_range")},
            "sushi_items": len(sushi),
            "with_pieces": sum(1 for i in sushi if i["pieces"]),
            "min_eur_per_piece": min(per_piece) if per_piece else None,
            "deals": len(discounts),
            "max_discount": max(discounts) if discounts else None,
        })
    names = {v["slug"]: v["name"] for v in venues_out}
    for i in rows_out:
        i["venue_name"] = names.get(i["venue_slug"], i["venue_slug"])

    dump("items.json", rows_out)
    dump("venues.json", sorted(venues_out, key=lambda v: v["name"]))
    dump("history.json", history)
    dump("meta.json", {"updated_at": now, "venues_ok": len(ok), "venues_failed": failed,
                       "items": len(rows_out), "changes": changes})
    print(f"Gotovo: {len(ok)} restorana, {len(rows_out)} stavki, {changes} promjena cijena", file=sys.stderr)


if __name__ == "__main__":
    main()
