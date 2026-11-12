"""Source FBref : page « Big 5 European Leagues — Standard Stats » (une ligne par joueur et par club).

FBref est derrière une vérification anti-robot Cloudflare : la récupération réseau échoue
proprement, l'import d'une page enregistrée depuis le navigateur (--html) fonctionne."""
import html
import re
from html.parser import HTMLParser

from common import http_get, position_fr, season_label

URL = "https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats"
COMPS = {"9": "eng", "12": "esp", "11": "ita", "20": "ger", "13": "fra"}
CLUB_NAMES = {
    "Paris S-G": "Paris SG", "Manchester Utd": "Manchester United", "Newcastle Utd": "Newcastle",
    "Nott'ham Forest": "Nottingham Forest", "Eint Frankfurt": "Eintracht Francfort",
    "Gladbach": "Mönchengladbach", "Leverkusen": "Bayer Leverkusen", "Sheffield Utd": "Sheffield United",
}


class _TableParser(HTMLParser):
    """Lignes du tableau `stats_standard`, cellules repérées par leur attribut data-stat."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.title = [], ""
        self._in_title, self._depth, self._row, self._cell, self._flag_depth = False, 0, None, None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "table":
            if self._depth:
                self._depth += 1
            elif (a.get("id") or "").startswith("stats_standard"):
                self._depth = 1
            return
        if not self._depth:
            return
        if tag == "tr":
            cls = a.get("class") or ""
            self._row = None if ("thead" in cls or "spacer" in cls) else {}
        elif tag in ("td", "th") and self._row is not None and a.get("data-stat"):
            self._cell = {"stat": a["data-stat"], "text": "", "href": None, "flag": None}
        elif self._cell is not None:
            if tag == "a" and not self._cell["href"]:
                self._cell["href"] = a.get("href")
            if tag == "span":
                cls = a.get("class") or ""
                m = re.search(r"\bf-([a-z]{2}(?:-[a-z]{3})?)\b", cls)
                if "f-i" in cls and m:
                    self._cell["flag"], self._flag_depth = m.group(1), 1
                elif self._flag_depth:
                    self._flag_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if not self._depth:
            return
        if tag == "table":
            self._depth -= 1
        elif tag == "span" and self._flag_depth:
            self._flag_depth -= 1
        elif tag in ("td", "th") and self._cell is not None:
            self._row[self._cell["stat"]] = self._cell
            self._cell = None
        elif tag == "tr" and self._row:
            if "player" in self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._cell is not None and not self._flag_depth:
            self._cell["text"] += data


def _id(href, kind):
    m = re.search(r"/en/%s/([^/]+)/" % kind, href or "")
    return m.group(1) if m else None


def _num(row, stat):
    txt = ((row.get(stat) or {}).get("text") or "").strip().replace(",", "")
    try:
        return int(float(txt)) if txt else 0
    except ValueError:
        return 0


def fetch():
    import urllib.error
    try:
        body = http_get(URL, accept="text/html", retries=0).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError("FBref HTTP %d (vérification anti-robot Cloudflare)" % e.code)
    if "Just a moment" in body[:5000]:
        raise RuntimeError("FBref a renvoyé une vérification anti-robot Cloudflare")
    return body


def load(page):
    """Page HTML FBref → jeu de données normalisé (voir update.py)."""
    p = _TableParser()
    p.feed(page.replace("<!--", "").replace("-->", ""))  # tableaux parfois livrés en commentaire
    if not p.rows:
        raise ValueError("tableau stats_standard introuvable ou vide")
    players, clubs = {}, {}
    for r in p.rows:
        pid = _id(r["player"]["href"], "players")
        name = html.unescape(r["player"]["text"].strip())
        league = COMPS.get(_id((r.get("comp_level") or {}).get("href"), "comps"))
        if not pid or not name or not league:
            continue
        team = r.get("team") or r.get("squad") or {}
        fb_club = _id(team.get("href"), "squads")
        club = "fbref-%s" % fb_club if fb_club else None
        raw = team.get("text", "").strip()
        if club:
            clubs.setdefault(club, {"name": CLUB_NAMES.get(raw, raw), "league": league, "fbrefId": fb_club})
        nat = r.get("nationality") or {}
        pl = players.setdefault(pid, {
            "id": "fbref-" + pid, "name": name,
            "nation": nat.get("text", "").strip().upper() or None, "flagCode": nat.get("flag"),
            "position": position_fr((r.get("position") or {}).get("text", "")),
            "age": ((r.get("age") or {}).get("text", "").strip().split("-")[0]) or None,
            "breakdown": [],
        })
        pl["breakdown"].append({"comp": league, "club": club, "matches": _num(r, "games"),
                                "minutes": _num(r, "minutes"), "goals": _num(r, "goals"),
                                "assists": _num(r, "assists")})
    m = re.search(r"(20\d\d)-20\d\d", p.title)
    return {"source": {"name": "FBref", "url": URL}, "season": season_label(int(m.group(1)) if m else None),
            "players": list(players.values()), "clubs": clubs,
            "cutoffs": {"leagues": {"goals": 0, "assists": 0, "ga": 0},  # FBref liste tous les joueurs
                        "all": {"goals": 0, "assists": 0, "ga": 0}}}
