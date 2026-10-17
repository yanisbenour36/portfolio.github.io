import json, re, sys, urllib.request, datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

SORTIE = "portfolio/portfolio/veille/actus.json"  # a changer si le site est un jour a la racine
PAR_THEME = 3
JOURS = 45
RANSOM = ["ransomware", "rançongiciel", "rancongiciel", "ransom"]
FLUX = [
    ("Ransomware", "BleepingComputer", "https://www.bleepingcomputer.com/feed/", RANSOM),
    ("Ransomware", "The Hacker News", "https://feeds.feedburner.com/TheHackersNews", RANSOM),
    ("Ransomware", "ZATAZ", "https://www.zataz.com/feed/", RANSOM),
    ("Ransomware", "Dark Reading", "https://www.darkreading.com/rss.xml", RANSOM),
    ("Ransomware", "SecurityWeek", "https://feeds.feedburner.com/securityweek", RANSOM),
    ("Ransomware", "CERT-FR", "https://www.cert.ssi.gouv.fr/feed/", RANSOM),
    ("OSINT", "Bellingcat", "https://www.bellingcat.com/feed/", None),
    ("OSINT", "IntelTechniques", "https://inteltechniques.com/blog/feed/", None),
]


def lire(url):
    req = urllib.request.Request(url, headers={"User-Agent": "veille-portfolio/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return ET.fromstring(r.read())


def date_de(txt):
    if not txt:
        return None
    try:
        d = parsedate_to_datetime(txt)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(txt.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def articles(racine):
    for it in racine.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        ch = {}
        for c in it:
            n = c.tag.split("}")[-1]
            if n == "link" and c.get("href"):
                ch.setdefault("link", c.get("href"))
            elif n in ("title", "link", "pubDate", "updated", "published") and c.text:
                ch.setdefault(n, c.text.strip())
        yield ch


def main():
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=JOURS)
    par_theme, vus = {}, set()
    for theme, source, url, mots in FLUX:
        try:
            racine = lire(url)
        except Exception as e:
            print("ECHEC", source, e)
            continue
        for ch in articles(racine):
            titre = re.sub(r"\s+", " ", ch.get("title", "")).strip()[:160]
            lien = ch.get("link", "")
            d = date_de(ch.get("pubDate") or ch.get("published") or ch.get("updated"))
            if not titre or not lien.startswith("https://") or not d or d < limite or lien in vus:
                continue
            if mots and not any(m in titre.lower() for m in mots):
                continue
            vus.add(lien)
            par_theme.setdefault(theme, []).append((d, {"titre": titre, "date": d.strftime("%Y-%m-%d"), "theme": theme, "source": source, "resume": "Article à lire sur le site de la source.", "lien": lien}))
    choix = []
    for liste in par_theme.values():
        liste.sort(key=lambda x: x[0], reverse=True)
        choix += liste[:PAR_THEME]
    if not choix:
        print("Rien de nouveau : fichier conserve.")
        return
    choix.sort(key=lambda x: x[0], reverse=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump([x[1] for x in choix], f, ensure_ascii=False, indent=1)
    print(len(choix), "articles ecrits")


if __name__ == "__main__":
    main()
