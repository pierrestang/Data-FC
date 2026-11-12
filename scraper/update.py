#!/usr/bin/env python3
"""Data FC — mise à jour nocturne des classements.

Sources (bibliothèque standard Python 3.9+ uniquement) :
  - FBref : tentée en premier ; aujourd'hui bloquée par Cloudflare en accès automatique,
    mais une page enregistrée depuis le navigateur s'importe avec --html.
  - ESPN : API publique, utilisée automatiquement quand FBref est inaccessible.
Puis : drapeaux (flag-icons), logos de clubs (Wikidata → Wikipedia, en SVG), et écriture
atomique de site/data/leaderboard.json. En cas d'échec, le fichier précédent est conservé.

Usage :
    python3 scraper/update.py                     # auto : FBref, sinon ESPN
    python3 scraper/update.py --source espn
    python3 scraper/update.py --html page.html    # page FBref enregistrée
    python3 scraper/update.py --html scraper/fixtures/demo_big5.html --demo
"""
import argparse
import datetime as dt
import json
import logging
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NATIONS, http_get, log  # noqa: E402
from sources import espn, fbref  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA_FILE = os.path.join(SITE, "data", "leaderboard.json")
CACHE_DIR = os.path.join(ROOT, "scraper", "cache")
LOG_FILE = os.path.join(ROOT, "logs", "update.log")
FLAG_CDN = "https://cdn.jsdelivr.net/npm/flag-icons@7.5.0/flags/4x3/{}.svg"

COMPETITIONS = {
    "eng": {"name": "Premier League", "type": "league", "flag": "gb-eng", "wikidata": "Q9448"},
    "esp": {"name": "La Liga", "type": "league", "flag": "es", "wikidata": "Q324867"},
    "ita": {"name": "Serie A", "type": "league", "flag": "it", "wikidata": "Q15804"},
    "ger": {"name": "Bundesliga", "type": "league", "flag": "de", "wikidata": "Q82595"},
    "fra": {"name": "Ligue 1", "type": "league", "flag": "fr", "wikidata": "Q13394"},
    "ucl": {"name": "Champions League", "type": "cup", "wiki": "UEFA Champions League"},
    "uel": {"name": "Europa League", "type": "cup", "wiki": "UEFA Europa League"},
    "uecl": {"name": "Conference League", "type": "cup", "wiki": "UEFA Conference League"},
    "usc": {"name": "Supercoupe de l’UEFA", "type": "club", "wiki": "UEFA Super Cup"},
    "fic": {"name": "Coupe intercontinentale de la FIFA", "type": "club", "wiki": "FIFA Intercontinental Cup"},
    "efa": {"name": "FA Cup", "type": "domcup", "wiki": "FA Cup"},
    "elc": {"name": "Carabao Cup", "type": "domcup", "wiki": "EFL Cup"},
    "cdr": {"name": "Copa del Rey", "type": "domcup", "wiki": "Copa del Rey"},
    "coi": {"name": "Coppa Italia", "type": "domcup", "wiki": "Coppa Italia"},
    "dfb": {"name": "DFB-Pokal", "type": "domcup", "wiki": "DFB-Pokal"},
    "cdf": {"name": "Coupe de France", "type": "domcup", "wiki": "Coupe de France"},
    "ecs": {"name": "Community Shield", "type": "domsuper", "wiki": "FA Community Shield"},
    "esc": {"name": "Supercopa de España", "type": "domsuper", "wiki": "Supercopa de España"},
    "isc": {"name": "Supercoppa Italiana", "type": "domsuper", "wiki": "Supercoppa Italiana"},
    "gsc": {"name": "Supercoupe d’Allemagne", "type": "domsuper", "wiki": "DFL-Supercup"},
    "tdc": {"name": "Trophée des champions", "type": "domsuper", "wiki": "Trophée des Champions"},
    "unl": {"name": "Ligue des nations UEFA", "type": "national", "wiki": "UEFA Nations League"},
    "euq": {"name": "Qualifications à l’Euro 2028", "type": "national", "wiki": "UEFA Euro 2028 qualifying"},
    "wcq": {"name": "Éliminatoires CdM 2030 – Amérique du Sud", "type": "national",
            "wiki": "2030 FIFA World Cup qualification (CONMEBOL)"},
    "can": {"name": "Coupe d’Afrique des nations 2027", "type": "national", "wiki": "2027 Africa Cup of Nations"},
    "asc": {"name": "Coupe d’Asie 2027", "type": "national", "wiki": "2027 AFC Asian Cup"},
    "cnl": {"name": "Ligue des nations de la CONCACAF", "type": "national", "wiki": "CONCACAF Nations League"},
    "gold": {"name": "Gold Cup 2027", "type": "national", "wiki": "CONCACAF Gold Cup"},
}
LEAGUES = {k: v for k, v in COMPETITIONS.items() if v["type"] == "league"}
# Article Wikipedia (en) forcé quand le rapprochement par nom échoue ou est ambigu.
WIKI_OVERRIDES = {"Paris FC": "Paris FC", "Toulouse": "Toulouse FC", "FC Augsburg": "FC Augsburg",
                  "Paris Saint-Germain": "Paris Saint-Germain FC", "Bodo/Glimt": "FK Bodø/Glimt",
                  "Braga": "S.C. Braga"}


# --------------------------------------------------------------------------- #
def write_atomic(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def is_svg(data):
    head = data[:4000].lstrip().lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head)


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|ac|as|ssc|sc|afc|bc|ss|us|rc|rcd|ca|cd|sd|ud|vfb|vfl|tsg|sv|fsv|bv|ogc|losc|"
               r"stade|club|de|calcio|football|1)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# --------------------------------------------------------------------------- #
# Drapeaux
# --------------------------------------------------------------------------- #
def ensure_flags(codes):
    ok = set()
    for code in sorted(c for c in codes if c):
        path = os.path.join(SITE, "assets", "flags", code + ".svg")
        if not os.path.exists(path):
            try:
                data = http_get(FLAG_CDN.format(code))
                if is_svg(data):
                    write_atomic(path, data)
            except Exception as e:  # noqa: BLE001
                log.warning("drapeau %s indisponible : %s", code, e)
        if os.path.exists(path):
            ok.add(code)
    return ok


# --------------------------------------------------------------------------- #
# Logos de clubs : club → article Wikipedia → image de l'infobox (SVG)
# --------------------------------------------------------------------------- #
def _sparql(query):
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query})
    return json.loads(http_get(url, accept="application/sparql-results+json"))["results"]["bindings"]


def _title(article_url):
    return urllib.parse.unquote(article_url.rsplit("/", 1)[1]).replace("_", " ")


def resolve_wiki_titles(clubs):
    """Renvoie {clé club: titre d'article Wikipedia anglais}."""
    titles = {}
    fb = {k: c["fbrefId"] for k, c in clubs.items() if c.get("fbrefId")}
    if fb:  # identifiant FBref → Wikidata (P8642)
        rows = _sparql("SELECT ?id ?a WHERE { VALUES ?id {%s} ?c wdt:P8642 ?id . ?a schema:about ?c ; "
                       "schema:isPartOf <https://en.wikipedia.org/> . }" % " ".join('"%s"' % v for v in fb.values()))
        by_fb = {r["id"]["value"]: _title(r["a"]["value"]) for r in rows}
        titles.update({k: by_fb[v] for k, v in fb.items() if v in by_fb})
    rest = {k: c for k, c in clubs.items() if k not in titles}
    if rest:  # rapprochement par nom parmi les clubs de chaque championnat (Wikidata P118)
        rows = _sparql(
            'SELECT ?lg ?a (GROUP_CONCAT(DISTINCT ?n; separator="|") AS ?names) WHERE { VALUES ?lg {%s} '
            "?c wdt:P118 ?lg ; wdt:P31/wdt:P279* wd:Q476028 . ?a schema:about ?c ; "
            "schema:isPartOf <https://en.wikipedia.org/> . { ?c rdfs:label ?n } UNION { ?c skos:altLabel ?n } "
            'FILTER(LANG(?n) IN ("en","fr","es","it","de")) } GROUP BY ?lg ?a'
            % " ".join("wd:" + l["wikidata"] for l in LEAGUES.values()))
        index = {}
        for r in rows:
            lg = r["lg"]["value"].rsplit("/", 1)[1]
            for n in r["names"]["value"].split("|"):
                index.setdefault((lg, norm(n)), set()).add(_title(r["a"]["value"]))
        for k, c in rest.items():
            if c["name"] in WIKI_OVERRIDES:
                titles[k] = WIKI_OVERRIDES[c["name"]]
                continue
            if not c.get("league"):
                continue  # club hors Big 5 : recherche plein texte ci-dessous
            hits = index.get((LEAGUES[c["league"]]["wikidata"], norm(c["name"])), set())
            if len(hits) == 1:
                titles[k] = next(iter(hits))
            else:
                log.warning("club non rapproché de Wikipedia : %s (%d candidat(s))", c["name"], len(hits))
    others = {k: c for k, c in clubs.items() if k not in titles and not c.get("league")}
    if others:
        titles.update(_search_clubs(others))
    return titles


def _search_clubs(clubs):
    """Clubs hors Big 5 (coupes d'Europe) : recherche Wikidata par nom, premier résultat qui est un club."""
    candidates = {}
    for k, c in clubs.items():
        try:
            res = json.loads(http_get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
                "action": "wbsearchentities", "search": c["name"].replace("/", " "), "language": "en",
                "type": "item", "limit": 7, "format": "json"})))
            candidates[k] = [x["id"] for x in res.get("search", [])]
        except Exception as e:  # noqa: BLE001
            log.warning("recherche Wikidata %s : %s", c["name"], e)
        time.sleep(0.3)
    qids = sorted({q for v in candidates.values() for q in v})
    if not qids:
        return {}
    rows = _sparql("SELECT ?c ?a WHERE { VALUES ?c {%s} ?c wdt:P31/wdt:P279* wd:Q476028 . ?a schema:about ?c ; "
                   "schema:isPartOf <https://en.wikipedia.org/> . }" % " ".join("wd:" + q for q in qids))
    article = {r["c"]["value"].rsplit("/", 1)[1]: _title(r["a"]["value"]) for r in rows}
    out = {}
    for k, qs in candidates.items():
        hit = next((article[q] for q in qs if q in article), None)
        if hit:
            out[k] = hit
        else:
            log.info("pas d'article Wikipedia trouvé pour %s (logo ESPN utilisé)", clubs[k]["name"])
    return out


def _download_crest(key, title, folder="clubs"):
    api = "https://en.wikipedia.org/w/api.php?"
    wikitext = json.loads(http_get(api + urllib.parse.urlencode({
        "action": "parse", "page": title, "prop": "wikitext", "section": 0, "redirects": 1,
        "format": "json"})))["parse"]["wikitext"]["*"]
    m = re.search(r"\|\s*(?:image|logo|crest)\s*=\s*(?:\[\[(?:File|Image):)?([^|\]\n<{}]+?\.(?:svg|png))",
                  wikitext, re.I)
    if not m:
        return None
    info = json.loads(http_get(api + urllib.parse.urlencode({
        "action": "query", "titles": "File:" + m.group(1).strip(), "prop": "imageinfo", "iiprop": "url",
        "format": "json"})))
    url = (next(iter(info["query"]["pages"].values())).get("imageinfo") or [{}])[0].get("url")
    if not url:
        return None
    time.sleep(1.0)
    data = http_get(url)
    rel = "assets/%s/%s.%s" % (folder, key, "svg" if is_svg(data) else "png")
    write_atomic(os.path.join(SITE, rel), data)
    return rel


def ensure_club_logos(clubs):
    path = os.path.join(CACHE_DIR, "clubs.json")
    cache, now = read_json(path, {}), time.time()
    exists = lambda rel: bool(rel) and os.path.exists(os.path.join(SITE, rel))  # noqa: E731
    todo = {k: c for k, c in clubs.items()
            if not exists(cache.get(k, {}).get("logo"))
            and (not exists(cache.get(k, {}).get("fallback")) or now - cache[k].get("checkedAt", 0) > 7 * 86400)}
    if todo:
        log.info("recherche de %d logo(s) de club", len(todo))
        try:
            titles = resolve_wiki_titles(todo)
        except Exception as e:  # noqa: BLE001
            log.warning("Wikidata indisponible : %s", e)
            titles = {}
        for k, c in todo.items():
            entry = dict(cache.get(k, {}), checkedAt=now, wiki=titles.get(k))
            try:
                if entry["wiki"]:
                    entry["logo"] = _download_crest(k, entry["wiki"])
                    time.sleep(1.5)  # politesse envers Wikimedia, qui limite fortement le débit
                if not exists(entry.get("logo")) and c.get("fallbackLogo") and not exists(entry.get("fallback")):
                    rel = "assets/clubs/%s-fallback.png" % k
                    write_atomic(os.path.join(SITE, rel), http_get(c["fallbackLogo"]))
                    entry["fallback"] = rel
            except Exception as e:  # noqa: BLE001
                log.warning("logo %s (%s) : %s", c["name"], entry.get("wiki"), e)
                continue  # rien de mémorisé : nouvel essai la nuit suivante
            cache[k] = entry
        write_atomic(path, json.dumps(cache, indent=1, ensure_ascii=False).encode())
    for k, c in clubs.items():
        e = cache.get(k, {})
        c["logo"] = e.get("logo") if exists(e.get("logo")) else (e.get("fallback") if exists(e.get("fallback")) else None)


def competition_icons(with_assets):
    """Drapeau du pays pour un championnat, logo officiel (Wikipedia) pour une coupe d'Europe."""
    icons = {}
    for k, c in COMPETITIONS.items():
        if c["type"] == "league":
            icons[k] = "assets/flags/%s.svg" % c["flag"]
            continue
        found = [f for f in ("%s.svg" % k, "%s.png" % k) if os.path.exists(os.path.join(SITE, "assets", "comps", f))]
        if not found and with_assets:
            try:
                rel = _download_crest(k, c["wiki"], folder="comps")
                found = [os.path.basename(rel)] if rel else []
            except Exception as e:  # noqa: BLE001
                log.warning("logo %s : %s", c["name"], e)
        icons[k] = "assets/comps/" + found[0] if found else None
    return icons


# --------------------------------------------------------------------------- #
def finalize(ds, with_assets):
    out = []
    for pl in ds["players"]:
        b = [x for x in pl["breakdown"] if x["matches"] > 0 and x["comp"] in COMPETITIONS]
        if not b:
            continue
        order = list(COMPETITIONS)
        b.sort(key=lambda x: order.index(x["comp"]))
        pl["breakdown"] = b
        # Joueur « Big 5 » : il a joué un des cinq championnats, ou son club en fait partie.
        pl["big5"] = any(COMPETITIONS[x["comp"]]["type"] == "league" or
                         (ds["clubs"].get(x["club"]) or {}).get("league") for x in b)
        out.append(pl)
    used = {x["club"] for p in out for x in p["breakdown"]}
    clubs = {k: v for k, v in ds["clubs"].items() if k in used}
    ds["clubs"] = clubs
    nat_teams = {k: v for k, v in clubs.items() if v.get("national")}
    if with_assets:
        flags = ensure_flags({p.get("flagCode") for p in out} | {l["flag"] for l in LEAGUES.values()}
                             | {NATIONS.get((v.get("nation") or "").upper()) for v in nat_teams.values()})
        ensure_club_logos({k: v for k, v in clubs.items() if k not in nat_teams})
    else:
        flags = set()
    for v in nat_teams.values():  # sélection nationale : son drapeau sert de logo
        code = NATIONS.get((v.get("nation") or "").upper())
        v["logo"] = "assets/flags/%s.svg" % code if code in flags else None
    for pl in out:
        code = pl.pop("flagCode", None)
        pl["flag"] = "assets/flags/%s.svg" % code if code in flags else None
    for c in clubs.values():
        c.pop("fallbackLogo", None)
        c.pop("fbrefId", None)
        c.pop("nation", None)
        c.setdefault("logo", None)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["auto", "fbref", "espn"], default="auto")
    ap.add_argument("--html", help="page FBref enregistrée localement (implique --source fbref)")
    ap.add_argument("--demo", action="store_true", help="marque le jeu de données comme démonstration")
    ap.add_argument("--no-assets", action="store_true", help="ne télécharge ni drapeaux ni logos")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)])
    try:
        if args.html:
            with open(args.html, encoding="utf-8", errors="replace") as f:
                ds = fbref.load(f.read())
            log.info("import FBref local : %s", args.html)
        else:
            ds = None
            if args.source in ("auto", "fbref"):
                try:
                    ds = fbref.load(fbref.fetch())
                except Exception as e:  # noqa: BLE001
                    if args.source == "fbref":
                        raise
                    log.info("FBref indisponible (%s) → ESPN", e)
            if ds is None:
                ds = espn.load(os.path.join(CACHE_DIR, "espn_athletes.json"))
        players = finalize(ds, not args.no_assets)
        icons = competition_icons(not args.no_assets)
        if len(players) < 50 and not args.demo:
            raise ValueError("seulement %d joueurs extraits : données incomplètes ?" % len(players))
        payload = {
            "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "season": ds["season"], "demo": bool(args.demo), "source": ds["source"],
            "cutoffs": ds["cutoffs"],
            "competitions": {k: {"name": v["name"], "type": v["type"], "icon": icons[k]}
                             for k, v in COMPETITIONS.items()},
            "clubs": ds["clubs"], "players": players,
        }
        write_atomic(DATA_FILE, json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
        log.info("OK (%s) : %d joueurs, %d clubs, saison %s", ds["source"]["name"], len(players),
                 len(ds["clubs"]), ds["season"])
        return 0
    except Exception as e:  # noqa: BLE001
        log.error("échec de la mise à jour (données précédentes conservées) : %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
