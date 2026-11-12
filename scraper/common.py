"""Outils partagés : HTTP poli, libellés, correspondance codes pays → flag-icons."""
import datetime as dt
import logging
import time
import urllib.error
import urllib.request

USER_AGENT = "DataFC/0.1 (prototype personnel; quelques requetes par nuit)"
log = logging.getLogger("dfc")


def http_get(url, accept=None, timeout=30, retries=3):
    """GET simple ; sur HTTP 429/503 on attend (Retry-After ou 5 s, 20 s, 60 s) puis on réessaie."""
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == retries:
                raise
            wait = e.headers.get("Retry-After")
            wait = int(wait) if wait and wait.isdigit() else (5, 20, 60)[attempt]
            log.info("HTTP %d, nouvelle tentative dans %d s", e.code, min(wait, 120))
            time.sleep(min(wait, 120))


def season_label(start_year=None):
    if not start_year:
        today = dt.date.today()
        start_year = today.year if today.month >= 7 else today.year - 1
    return "%d-%d" % (start_year, start_year + 1)


_POS = {"GK": "Gardien", "DF": "Défenseur", "MF": "Milieu", "FW": "Attaquant",
        "G": "Gardien", "D": "Défenseur", "M": "Milieu", "F": "Attaquant",
        "GOALKEEPER": "Gardien", "DEFENDER": "Défenseur", "MIDFIELDER": "Milieu", "FORWARD": "Attaquant"}


def position_fr(raw):
    key = (raw or "").split(",")[0].strip().upper()
    return _POS.get(key, raw or "")


# Codes FIFA/CIO à 3 lettres → nom de fichier flag-icons (ISO 3166-1 alpha-2, ou gb-eng…).
NATIONS = {
    "AFG": "af", "ALB": "al", "ALG": "dz", "AND": "ad", "ANG": "ao", "ARG": "ar", "ARM": "am",
    "AUS": "au", "AUT": "at", "AZE": "az", "BAH": "bs", "BEL": "be", "BEN": "bj", "BER": "bm",
    "BFA": "bf", "BIH": "ba", "BLR": "by", "BOL": "bo", "BRA": "br", "BUL": "bg", "BDI": "bi",
    "CAN": "ca", "CHA": "td", "CHI": "cl", "CHN": "cn", "CIV": "ci", "CMR": "cm", "COD": "cd",
    "CGO": "cg", "COL": "co", "COM": "km", "CPV": "cv", "CRC": "cr", "CRO": "hr", "CTA": "cf",
    "CUB": "cu", "CUW": "cw", "CYP": "cy", "CZE": "cz", "DEN": "dk", "DOM": "do", "ECU": "ec",
    "EGY": "eg", "ENG": "gb-eng", "EQG": "gq", "ERI": "er", "ESP": "es", "EST": "ee", "ETH": "et",
    "FIN": "fi", "FRA": "fr", "FRO": "fo", "GAB": "ga", "GAM": "gm", "GEO": "ge", "GER": "de",
    "GHA": "gh", "GLP": "gp", "GNB": "gw", "GRE": "gr", "GRN": "gd", "GUF": "gf", "GUI": "gn",
    "GUA": "gt", "GUY": "gy", "HAI": "ht", "HON": "hn", "HUN": "hu", "IDN": "id", "IND": "in",
    "IRL": "ie", "IRN": "ir", "IRQ": "iq", "ISL": "is", "ISR": "il", "ITA": "it", "JAM": "jm",
    "JOR": "jo", "JPN": "jp", "KAZ": "kz", "KEN": "ke", "KOR": "kr", "KOS": "xk", "KSA": "sa",
    "LBR": "lr", "LBY": "ly", "LIE": "li", "LTU": "lt", "LUX": "lu", "LVA": "lv", "MAD": "mg",
    "MAR": "ma", "MDA": "md", "MEX": "mx", "MKD": "mk", "MLI": "ml", "MLT": "mt", "MNE": "me",
    "MOZ": "mz", "MRT": "mr", "MSR": "ms", "MTN": "mr", "MTQ": "mq", "NAM": "na", "NED": "nl",
    "NGA": "ng", "NIG": "ne", "NIR": "gb-nir", "NOR": "no", "NZL": "nz", "PAN": "pa", "PAR": "py",
    "PER": "pe", "PHI": "ph", "PLE": "ps", "POL": "pl", "POR": "pt", "PUR": "pr", "QAT": "qa",
    "ROU": "ro", "RSA": "za", "RUS": "ru", "RWA": "rw", "SCO": "gb-sct", "SEN": "sn", "SLE": "sl",
    "SLV": "sv", "SMR": "sm", "SRB": "rs", "SUI": "ch", "SUR": "sr", "SVK": "sk", "SVN": "si",
    "SWE": "se", "SYR": "sy", "TAN": "tz", "TOG": "tg", "TRI": "tt", "TUN": "tn", "TUR": "tr",
    "UAE": "ae", "UGA": "ug", "UKR": "ua", "URU": "uy", "USA": "us", "UZB": "uz", "VEN": "ve",
    "VIE": "vn", "WAL": "gb-wls", "ZAM": "zm", "ZIM": "zw", "SDN": "sd", "SOM": "so", "LCA": "lc",
    "MYA": "mm", "THA": "th", "IRE": "ie", "MON": "mc", "GIB": "gi", "NCL": "nc", "REU": "re",
    # Variantes propres à ESPN
    "MOR": "ma", "CRM": "cm", "ROM": "ro", "PAL": "ps", "PAK": "pk", "MTG": "me", "SBA": "rs", "XKX": "xk", "KORS": "kr", "KORN": "kp",
}
