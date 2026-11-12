"""Source ESPN : API publiques du site (sans clé, sans vérification anti-robot).

1. `/statistics` de chaque compétition : 50 meilleurs buteurs + 50 meilleurs passeurs
   → ensemble des joueurs candidats et seuils de complétude.
2. `/teams` de chaque compétition : quels clubs jouent quel championnat / quelle coupe.
3. API « core », pour chaque candidat et chaque compétition jouée par son club :
   matchs, minutes, buts et passes exacts (une ligne absente d'un top 50 est ainsi récupérée).
4. Fiche joueur (nationalité, poste, âge), en cache 30 jours.

Seuils : un joueur absent de toutes les listes a, dans chaque compétition, au plus autant de buts
que le 50e buteur et de passes que le 50e passeur. Le site n'affiche que ce qui dépasse ces seuils."""
import json
import os
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from common import NATIONS, http_get, log, position_fr, season_label

COMPS = {
    "eng": "eng.1", "esp": "esp.1", "ita": "ita.1", "ger": "ger.1", "fra": "fra.1",
    "ucl": "uefa.champions", "uel": "uefa.europa", "uecl": "uefa.europa.conf",
    "usc": "uefa.super_cup", "fic": "fifa.intercontinental_cup",
    "efa": "eng.fa", "elc": "eng.league_cup", "cdr": "esp.copa_del_rey", "coi": "ita.coppa_italia",
    "dfb": "ger.dfb_pokal", "cdf": "fra.coupe_de_france",
    "ecs": "eng.charity", "esc": "esp.super_cup", "isc": "ita.super_cup", "gsc": "ger.super_cup", "tdc": "fra.super_cup",
    "unl": "uefa.nations", "euq": "uefa.euroq", "wcq": "fifa.worldq.conmebol",
    "can": "caf.nations", "asc": "afc.asian.cup", "cnl": "concacaf.nations.league", "gold": "concacaf.gold",
}
LEAGUE_KEYS = ("eng", "esp", "ita", "ger", "fra")
CUP_KEYS = ("ucl", "uel", "uecl")
CLUB_OTHER_KEYS = ("usc", "fic")          # compétitions de clubs ponctuelles
NATIONAL_KEYS = ("unl", "euq", "wcq", "can", "asc", "cnl", "gold")  # sélections nationales
# Coupes et supercoupes nationales, par pays (un club anglais joue FA Cup + Carabao Cup + Community Shield).
DOMESTIC = {"eng": ("efa", "elc", "ecs"), "esp": ("cdr", "esc"), "ita": ("coi", "isc"),
            "ger": ("dfb", "gsc"), "fra": ("cdf", "tdc")}
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{}/"
CORE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/{}/seasons/{}/types/1/athletes/{}/statistics"
ATHLETE_URL = "https://site.web.api.espn.com/apis/common/v3/sports/soccer/{}/athletes/{}"
LIST_SIZE = 50
CACHE_TTL = 30 * 86400


def _stat(athlete, name):
    for s in athlete.get("statistics") or []:
        if s.get("name") == name:
            return int(s.get("value") or 0)
    return 0


def _core_stats(slug, year, aid):
    """Stats exactes d'un joueur dans une compétition, ou None s'il n'y a pas joué."""
    try:
        d = json.loads(http_get(CORE.format(slug, year, aid)))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    s = {x["name"]: x.get("value") or 0 for c in d["splits"]["categories"] for x in c["stats"]}
    return {"matches": int(s.get("appearances", 0)), "minutes": int(s.get("minutes", 0)),
            "goals": int(s.get("totalGoals", 0)), "assists": int(s.get("goalAssists", 0))}


def _logo(team):
    logos = [l["href"] for l in team.get("logos") or [] if "dark" not in (l.get("rel") or [])]
    return logos[0] if logos else None


def load(cache_path):
    players, clubs, team_comps, cuts, year = {}, {}, {}, {}, None

    active = []
    for key, slug in COMPS.items():
        national = key in NATIONAL_KEYS
        # Listes des meilleurs buteurs / passeurs
        try:
            data = json.loads(http_get(SITE.format(slug) + "statistics"))
        except Exception as e:  # noqa: BLE001
            if key in LEAGUE_KEYS:
                raise
            log.warning("ESPN %s indisponible : %s", slug, e)
            continue
        season_year = (data.get("season") or {}).get("year")
        year = year or season_year
        # ESPN renvoie l'édition précédente tant que la nouvelle n'a pas commencé : on l'ignore.
        if key not in LEAGUE_KEYS and not any(st.get("leaders") for st in data.get("stats") or []):
            log.info("ESPN %s : aucune statistique pour l'instant, ignorée", slug)
            continue
        if key not in LEAGUE_KEYS and season_year and year and season_year < year:
            log.info("ESPN %s : édition en cours pas encore commencée (ESPN renvoie %s), ignorée",
                     slug, (data.get("season") or {}).get("displayName"))
            continue
        active.append(key)
        # Clubs / sélections engagés
        teams = json.loads(http_get(SITE.format(slug) + "teams"))["sports"][0]["leagues"][0]["teams"]
        for t in (x["team"] for x in teams):
            team_comps.setdefault(t["id"], set()).add(key)
            cid = "espn-" + t["id"]
            c = clubs.setdefault(cid, {"name": t.get("displayName"), "league": None, "fallbackLogo": _logo(t)})
            if national:
                c.update(national=True, nation=t.get("abbreviation"))
            if key in LEAGUE_KEYS:
                c["league"] = key
        lists = {s["name"]: s.get("leaders") or [] for s in data.get("stats") or []}
        goals, assists = lists.get("goalsLeaders"), lists.get("assistsLeaders")
        if key in LEAGUE_KEYS and (not goals or not assists):
            raise ValueError("ESPN %s : classements absents" % slug)
        goals, assists = goals or [], assists or []
        cuts[key] = (int(goals[-1]["value"]) if len(goals) >= LIST_SIZE else 0,
                     int(assists[-1]["value"]) if len(assists) >= LIST_SIZE else 0)
        for entry in goals + assists:
            a = entry["athlete"]
            pl = players.setdefault(a["id"], {"name": a.get("displayName"), "team": None, "nat_team": None,
                                              "rows": {}, "slug": slug})
            tid = (a.get("team") or {}).get("id")
            if tid and national:
                pl["nat_team"] = tid
            elif tid and (key in LEAGUE_KEYS or not pl["team"]):
                pl["team"] = tid
            pl["rows"].setdefault(key, {"club": "espn-%s" % tid if tid else None, "matches": _stat(a, "appearances"),
                                        "minutes": None, "goals": _stat(a, "totalGoals"),
                                        "assists": _stat(a, "goalAssists")})
            if tid and "espn-" + tid not in clubs:
                clubs["espn-" + tid] = {"name": a["team"].get("displayName"), "league": None,
                                        "fallbackLogo": _logo(a["team"])}
                if national:
                    clubs["espn-" + tid].update(national=True, nation=a["team"].get("abbreviation"))
        log.info("ESPN %s : %d clubs, seuils %d buts / %d passes", slug, len(teams), *cuts[key])
        time.sleep(0.3)

    # Stats exactes par compétition (API core) pour chaque candidat.
    # Compétitions à vérifier : celles où il figure, celles de son club, et — s'il a joué en sélection —
    # toutes les compétitions de sélections en cours (un joueur peut manquer d'un top 50).
    def comps_for(pl):
        c = set(pl["rows"]) | team_comps.get(pl["team"], set())
        if pl["nat_team"]:
            c |= {k for k in NATIONAL_KEYS if k in active}
        return c
    jobs = [(aid, key) for aid, pl in players.items() for key in comps_for(pl)]

    def work(job):
        try:
            return job, _core_stats(COMPS[job[1]], year, job[0]), None
        except Exception as e:  # noqa: BLE001  — on garde la ligne du top 50 si elle existe
            return job, None, e

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:  # 4 requêtes simultanées au plus
        for (aid, key), s, err in pool.map(work, jobs):
            pl = players[aid]
            if err:
                log.warning("stats %s %s (%s) : %s", key, aid, pl["name"], err)
            elif s and s["matches"] > 0:
                team = pl["nat_team"] if key in NATIONAL_KEYS else pl["team"]
                club = (pl["rows"].get(key) or {}).get("club") or ("espn-" + team if team else None)
                pl["rows"][key] = dict(s, club=club)
    log.info("%d requêtes de stats détaillées en %d s", len(jobs), time.time() - t0)

    # Fiches joueurs (nationalité, poste, âge), en cache ; les manquantes sont récupérées en parallèle.
    cache, now = _read(cache_path), time.time()
    stale = [aid for aid in players if now - cache.get(aid, {}).get("fetchedAt", 0) > CACHE_TTL]

    def fiche(aid):
        try:
            d = json.loads(http_get(ATHLETE_URL.format(players[aid]["slug"], aid), timeout=20)).get("athlete", {})
        except Exception as e:  # noqa: BLE001
            log.warning("fiche ESPN %s (%s) : %s", aid, players[aid]["name"], e)
            return aid, None
        cc = d.get("citizenshipCountry") or {}
        return aid, {"fetchedAt": now, "nation": cc.get("abbreviation"), "nationName": d.get("citizenship"),
                     "position": (d.get("position") or {}).get("name"), "age": d.get("age")}

    fetched = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for aid, c in pool.map(fiche, stale):
            if c:
                cache[aid] = c
                fetched += 1
    out = []
    for aid, pl in players.items():
        c = cache.get(aid) or {}
        nat = (c.get("nation") or "").upper() or None
        if nat and nat not in NATIONS:
            log.warning("code pays inconnu %s (%s)", nat, pl["name"])
        rows = [dict(r, comp=k) for k, r in pl["rows"].items() if r["matches"] > 0]
        out.append({"id": "espn-" + aid, "name": pl["name"], "nation": nat, "nationName": c.get("nationName"),
                    "flagCode": NATIONS.get(nat), "position": position_fr(c.get("position")), "age": c.get("age"),
                    "breakdown": rows})
    if fetched:
        log.info("%d fiche(s) joueur ESPN récupérée(s)", fetched)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)

    return {"source": {"name": "ESPN", "url": "https://www.espn.com/soccer/"}, "season": season_label(year),
            "players": out, "clubs": clubs, "cutoffs": _cutoffs(cuts)}


def _cutoffs(cuts):
    """Seuils par périmètre affiché : championnats, chaque coupe, toutes compétitions."""
    def trio(g, a, ga):
        return {"goals": g, "assists": a, "ga": ga}
    lg = [cuts[k] for k in LEAGUE_KEYS]
    cp = [cuts[k] for k in CUP_KEYS if k in cuts]
    L = trio(max(g for g, _ in lg), max(a for _, a in lg), max(g + a for g, a in lg))
    C = trio(max(g for g, _ in cp), max(a for _, a in cp), max(g + a for g, a in cp)) if cp else trio(0, 0, 0)
    # « Toutes compétitions » = compétitions de clubs (championnat + coupe d'Europe + supercoupes).
    O = [cuts[k] for k in CLUB_OTHER_KEYS if k in cuts]
    osum = trio(sum(g for g, _ in O), sum(a for _, a in O), sum(g + a for g, a in O))
    N = [cuts[k] for k in NATIONAL_KEYS if k in cuts]  # un joueur peut jouer plusieurs compétitions de sélection
    nsum = trio(sum(g for g, _ in N), sum(a for _, a in N), sum(g + a for g, a in N))
    # Coupes nationales : un joueur peut manquer de chaque liste de son pays → somme par pays, pire pays.
    def dom(keys):
        per = [[cuts[k] for k in ks if k in cuts and k in keys] for ks in DOMESTIC.values()]
        return trio(max((sum(g for g, _ in c) for c in per), default=0), max((sum(a for _, a in c) for c in per), default=0),
                    max((sum(g + a for g, a in c) for c in per), default=0))
    dom_all = {k for ks in DOMESTIC.values() for k in ks}
    D = dom(dom_all)
    out = {"leagues": L, "cups": C, "national": nsum, "all": {k: L[k] + C[k] + osum[k] + D[k] for k in L},
           "domcups": dom({ks[0] for ks in DOMESTIC.values()} | {"elc"}),
           "domsuper": dom({ks[-1] for ks in DOMESTIC.values()})}
    for k in LEAGUE_KEYS + CUP_KEYS + CLUB_OTHER_KEYS + NATIONAL_KEYS + tuple(sorted(dom_all)):
        if k in cuts:
            out[k] = trio(cuts[k][0], cuts[k][1], sum(cuts[k]))
    return out


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}
