#!/usr/bin/env python3
"""Génère scraper/fixtures/demo_big5.html : une page au format FBref (même balisage
data-stat que le vrai tableau) avec des joueurs réels mais des CHIFFRES INVENTÉS.
Sert uniquement à développer le site tant que l'accès FBref n'est pas réglé."""
import os
import random

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "demo_big5.html")

COMPS = {"9": ("eng", "Premier-League", "Premier League"), "12": ("es", "La-Liga", "La Liga"),
         "11": ("it", "Serie-A", "Serie A"), "20": ("de", "Bundesliga", "Bundesliga"),
         "13": ("fr", "Ligue-1", "Ligue 1")}
CLUBS = {  # id FBref: (nom FBref, compétition)
    "b8fd03ef": ("Manchester City", "9"), "18bb7c10": ("Arsenal", "9"), "822bd0ba": ("Liverpool", "9"),
    "cff3d9bb": ("Chelsea", "9"), "b2b47a98": ("Newcastle Utd", "9"), "8602292d": ("Aston Villa", "9"),
    "53a2f082": ("Real Madrid", "12"), "206d90db": ("Barcelona", "12"), "db3b9613": ("Atlético Madrid", "12"),
    "2b390eca": ("Athletic Club", "12"), "2a8183b3": ("Villarreal", "12"),
    "d609edc0": ("Inter", "11"), "dc56fe14": ("Milan", "11"), "e0652b02": ("Juventus", "11"),
    "d48ad4ff": ("Napoli", "11"), "922493f3": ("Atalanta", "11"),
    "054efa67": ("Bayern Munich", "20"), "add600ae": ("Dortmund", "20"), "c7a9f859": ("Leverkusen", "20"),
    "acbb6a5b": ("RB Leipzig", "20"), "598bc722": ("Stuttgart", "20"),
    "e2d8892c": ("Paris S-G", "13"), "5725cc7b": ("Marseille", "13"), "fd6114db": ("Monaco", "13"),
    "d53c0b06": ("Lyon", "13"), "cb188c0c": ("Lille", "13"),
}
# (id joueur, nom, nation FBref, classe flag-icons, poste, [clubs])
PLAYERS = [
    ("1f44ac21", "Erling Haaland", "NOR", "no", "FW", ["b8fd03ef"]),
    ("42fd9c7f", "Kylian Mbappé", "FRA", "fr", "FW", ["53a2f082"]),
    ("82ec26c1", "Harry Kane", "ENG", "gb-eng", "FW", ["054efa67"]),
    ("e342ad68", "Mohamed Salah", "EGY", "eg", "FW", ["822bd0ba"]),
    ("82ec26c2", "Lamine Yamal", "ESP", "es", "FW", ["206d90db"]),
    ("d70ce98e", "Lautaro Martínez", "ARG", "ar", "FW", ["d609edc0"]),
    ("8e92be30", "Ousmane Dembélé", "FRA", "fr", "FW", ["e2d8892c"]),
    ("dea698d9", "Bukayo Saka", "ENG", "gb-eng", "FW", ["18bb7c10"]),
    ("4d224fe8", "Vinicius Júnior", "BRA", "br", "FW", ["53a2f082"]),
    ("b5dd8e9b", "Raphinha", "BRA", "br", "FW", ["206d90db"]),
    ("a4d6a4f4", "Cole Palmer", "ENG", "gb-eng", "MF", ["cff3d9bb"]),
    ("5e8b2a0d", "Alexander Isak", "SWE", "se", "FW", ["822bd0ba"]),
    ("c0c5ee74", "Florian Wirtz", "GER", "de", "MF", ["822bd0ba"]),
    ("2c2d1e3f", "Michael Olise", "FRA", "fr", "FW", ["054efa67"]),
    ("9b1a2c3d", "Serhou Guirassy", "GUI", "gn", "FW", ["add600ae"]),
    ("8a7b6c5d", "Mason Greenwood", "ENG", "gb-eng", "FW", ["5725cc7b"]),
    ("7f6e5d4c", "Ollie Watkins", "ENG", "gb-eng", "FW", ["8602292d"]),
    ("6e5d4c3b", "Julián Álvarez", "ARG", "ar", "FW", ["db3b9613"]),
    ("5d4c3b2a", "Mateo Retegui", "ITA", "it", "FW", ["922493f3"]),
    ("4c3b2a19", "Christian Pulisic", "USA", "us", "FW", ["dc56fe14"]),
    ("3b2a1908", "Dušan Vlahović", "SRB", "rs", "FW", ["e0652b02"]),
    ("2a190807", "Romelu Lukaku", "BEL", "be", "FW", ["d48ad4ff"]),
    ("19080706", "Nico Williams", "ESP", "es", "FW", ["2b390eca"]),
    ("08070605", "Ayoze Pérez", "ESP", "es", "FW", ["2a8183b3"]),
    ("07060504", "Patrik Schick", "CZE", "cz", "FW", ["c7a9f859"]),
    ("06050403", "Loïs Openda", "BEL", "be", "FW", ["acbb6a5b", "e0652b02"]),
    ("05040302", "Deniz Undav", "GER", "de", "FW", ["598bc722"]),
    ("04030201", "Jonathan David", "CAN", "ca", "FW", ["e0652b02"]),
    ("03020100", "Bradley Barcola", "FRA", "fr", "FW", ["e2d8892c"]),
    ("0201ffee", "Folarin Balogun", "USA", "us", "FW", ["fd6114db"]),
    ("01ffeedd", "Hamza Igamane", "MAR", "ma", "FW", ["cb188c0c"]),
    ("ffeeddcc", "Georges Mikautadze", "GEO", "ge", "FW", ["d53c0b06"]),
    ("eeddccbb", "Bruno Guimarães", "BRA", "br", "MF", ["b2b47a98"]),
    ("ddccbbaa", "Martin Ødegaard", "NOR", "no", "MF", ["18bb7c10"]),
    ("ccbbaa99", "Kevin De Bruyne", "BEL", "be", "MF", ["d48ad4ff"]),
    ("bbaa9988", "Alejandro Grimaldo", "ESP", "es", "DF", ["c7a9f859"]),
    ("aa998877", "Jude Bellingham", "ENG", "gb-eng", "MF", ["53a2f082"]),
    ("99887766", "Pedri", "ESP", "es", "MF", ["206d90db"]),
    ("88776655", "Achraf Hakimi", "MAR", "ma", "DF", ["e2d8892c"]),
    ("77665544", "John McGinn", "SCO", "gb-sct", "MF", ["8602292d"]),
]


def link(kind, pid, name, text=None):
    return '<a href="/en/%s/%s/%s">%s</a>' % (kind, pid, name.replace(" ", "-"), text or name)


def main():
    rnd = random.Random(2026)
    rows = []
    for i, (pid, name, nat, flag, pos, clubs) in enumerate(PLAYERS):
        base_g = max(0, 14 - i // 3 + rnd.randint(-2, 2)) if pos == "FW" else rnd.randint(0, 5)
        base_a = rnd.randint(0, 9) if pos != "FW" or i % 3 else rnd.randint(0, 5)
        if pos in ("MF", "DF"):
            base_a += rnd.randint(2, 6)
        parts = [0.6, 0.4] if len(clubs) == 2 else [1.0]
        total_mp = rnd.randint(11, 13)
        for cid, share in zip(clubs, parts):
            cname, comp = CLUBS[cid]
            ccode, cslug, cname_comp = COMPS[comp]
            mp = max(1, round(total_mp * share))
            starts = max(0, mp - rnd.randint(0, 3))
            minutes = starts * 85 + (mp - starts) * 25
            g, a = round(base_g * share), round(base_a * share)
            rows.append(
                '<tr><th data-stat="ranker">%d</th>' % (len(rows) + 1)
                + '<td data-stat="player" csk="%s">%s</td>' % (name, link("players", pid, name))
                + '<td data-stat="nationality"><a href="/en/country/%s/x"><span style="white-space: nowrap">'
                  '<span class="f-i f-%s" style="">%s</span> %s</span></a></td>' % (nat, flag, flag, nat)
                + '<td data-stat="position">%s</td>' % pos
                + '<td data-stat="team">%s</td>' % link("squads", cid, cname + "-Stats", cname)
                + '<td data-stat="comp_level"><a href="/en/comps/%s/%s-Stats"><span class="f-i f-%s" '
                  'style="">%s</span> %s</a></td>' % (comp, cslug, ccode, ccode, cname_comp)
                + '<td data-stat="age">%d-%03d</td>' % (rnd.randint(20, 33), rnd.randint(0, 364))
                + '<td data-stat="games">%d</td><td data-stat="games_starts">%d</td>' % (mp, starts)
                + '<td data-stat="minutes">%s</td>' % format(minutes, ",")
                + '<td data-stat="goals">%d</td><td data-stat="assists">%d</td></tr>' % (g, a))
        if i == 20:
            rows.append('<tr class="thead"><th data-stat="ranker">Rk</th><td data-stat="player">Player</td></tr>')
    html = ("<!DOCTYPE html><html><head><title>2026-2027 Big 5 European Leagues Player Stats | FBref.com"
            "</title></head><body><div id=\"all_stats_standard\"><!--\n<table id=\"stats_standard\"><thead>"
            "<tr><th>Rk</th></tr></thead><tbody>%s</tbody></table>\n--></div></body></html>" % "".join(rows))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("écrit :", OUT, "(%d lignes)" % len(rows))


if __name__ == "__main__":
    main()
