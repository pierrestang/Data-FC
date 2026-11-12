# Data FC — prototype

Classements des meilleurs buteurs et passeurs des cinq grands championnats européens
(Premier League, La Liga, Serie A, Bundesliga, Ligue 1) et des trois coupes d'Europe
(Champions League, Europa League, Conference League), saison en cours.
Prototype pour ordinateur uniquement.

## Lancer

```sh
python3 -m http.server 8090 -d site        # puis http://127.0.0.1:8090
python3 scraper/update.py                  # mise à jour : FBref si accessible, sinon ESPN
python3 scraper/update.py --html page.html # import d'une page FBref enregistrée depuis le navigateur
python3 scraper/make_demo_fixture.py && python3 scraper/update.py --html scraper/fixtures/demo_big5.html --demo
scraper/launchd/install.sh                 # tâche nocturne à 00:00 (--remove pour la retirer)
```

## Arborescence

```
scraper/update.py            orchestration, drapeaux, logos, écriture du JSON (stdlib Python uniquement)
scraper/sources/fbref.py     lecture de la page FBref Big 5 (réseau ou fichier enregistré)
scraper/sources/espn.py      API publiques ESPN (source automatique actuelle, 8 compétitions)
scraper/common.py            HTTP avec relances, codes pays → drapeaux
scraper/make_demo_fixture.py page factice au balisage FBref, chiffres inventés
scraper/launchd/             tâche launchd (minuit, heure locale) + script d'installation
scraper/cache/               clubs → logos, fiches joueurs ESPN (nationalité, poste, âge ; 30 jours)
site/                        site statique : index.html, styles.css, app.js
site/data/leaderboard.json   données publiées (écriture atomique)
site/assets/flags|clubs/     SVG téléchargés une fois puis mis en cache
logs/update.log              journal des mises à jour
```

## Compétitions couvertes

| Groupe | Compétitions (clé ESPN) |
|---|---|
| Championnats | Premier League, La Liga, Serie A, Bundesliga, Ligue 1 |
| Coupes d'Europe | Champions League, Europa League, Conference League |
| Autres clubs | Supercoupe de l'UEFA, Coupe intercontinentale de la FIFA |
| Coupes nationales | FA Cup, Carabao Cup, Copa del Rey, Coppa Italia, DFB-Pokal, Coupe de France |
| Supercoupes nationales | Community Shield, Supercopa de España, Supercoppa Italiana, Supercoupe d'Allemagne, Trophée des champions |
| Sélections | Ligue des nations UEFA, Qualifs Euro 2028, Élim. CdM 2030 (CONMEBOL), CAN 2027, Coupe d'Asie 2027, Ligue des nations CONCACAF 2026-27, Gold Cup 2027 |

- **« Toutes compétitions » = toutes les compétitions de clubs** (championnat, coupes d'Europe,
  coupes et supercoupes nationales, supercoupes internationales), pour les joueurs des clubs du
  Big 5. Les sélections sont à part (filtre « Sélections »).
- Tant qu'une édition n'a pas commencé, ESPN renvoie la précédente (ex. Euro 2024 pour les qualifs
  2028) ou rien : le script l'ignore, et le filtre l'affiche grisée « (à venir) ». Elle apparaît
  d'elle-même dès les premiers matchs.
- Sélection nationale dans le détail : drapeau du pays en guise de logo, nom en français.
- Une nuit complète ≈ 2 600 requêtes ESPN (4 en parallèle), environ 7 minutes.

## Source des données

**FBref reste la source prioritaire, mais elle est inaccessible en automatique** : Cloudflare
répond par une vérification anti-robot (HTTP 403). Je ne l'ai pas contournée : ce serait
contraire aux conditions du site et fragile. Chaque nuit, le script tente FBref (une requête)
puis bascule sur **ESPN**, dont l'API publique du site répond sans clé ni protection.

ESPN, pour chacune des 8 compétitions : les 50 meilleurs buteurs et les 50 meilleurs passeurs
(→ liste des joueurs candidats) et la liste des clubs engagés. Puis, pour chaque candidat et
chaque compétition jouée par son club, l'API « core » d'ESPN donne matchs, **minutes**, buts et
passes exacts ; une ligne absente d'un top 50 (ex. 1 but en Europa League) est donc bien comptée.
Environ 1 400 requêtes par nuit, 4 en parallèle au plus : quelques minutes.

- **Listes limitées à 50** : un joueur absent de toutes les listes a au plus, dans chaque
  compétition, autant de buts que le 50e buteur et de passes que le 50e passeur. Le site n'affiche
  donc que la partie du classement **garantie complète** (ex. « à partir de 5 buts » en toutes
  compétitions) et le dit sous le tableau.
- FBref (import manuel) ne couvre que les championnats : les vues coupes disparaissent alors.

Pour repasser sur FBref ponctuellement : enregistrer la page Big 5 dans le navigateur (⌘S)
et lancer `python3 scraper/update.py --html <fichier>`.

## Choix (à rediscuter)

**Données**
- Un joueur transféré en cours de saison apparaît sur plusieurs lignes FBref : on **additionne**
  ses stats pour le classement, et le **détail dépliable** reprend chaque ligne (championnat + club).
- Club affiché : celui où le joueur a le plus joué (minutes), avec un badge « +1 » s'il en a eu deux.
- **Filtre de compétition** : Toutes compétitions (par défaut) · Championnats, puis chacun des
  5 championnats · Coupes d'Europe, puis chacune des 3 coupes. L'URL garde le choix (`#ger`, `#ucl`…).
  « Toutes » = championnat + coupe d'Europe, pour les joueurs des clubs du Big 5 (un joueur de
  Benfica n'y figurerait qu'avec ses buts européens, ce serait trompeur). « Coupes d'Europe » et
  chaque coupe montrent leur vrai classement, clubs hors Big 5 compris.
- Coupes nationales et sélections exclues.
- Le détail dépliable liste toutes les compétitions du joueur ; celles hors du périmètre choisi
  sont grisées. Icône : drapeau pour un championnat, logo officiel pour une coupe.
- **Buts + passes** (troisième onglet et colonne « B+P ») : simple addition, sans pondération,
  classé et départagé comme les deux autres.
- **Classement** : stat brute décroissante, puis ratio par match (stat ÷ matchs joués).
  Même stat et même ratio = même rang (1, 2, 2, 4…). Les joueurs à 0 sont exclus.
- En cas d'échec (réseau, page incomplète, < 50 joueurs), **le dernier fichier valide est conservé** :
  le site affiche alors l'ancien horodatage.
- Horodatage discret dans la barre du tableau (« Mis à jour il y a 3 heures ») ; date exacte et
  source au survol ; passe en orange si la dernière mise à jour réussie date de plus de 26 h.

**Visuels**
- Drapeaux : [flag-icons](https://github.com/lipis/flag-icons) (MIT, SVG 4:3), y compris
  Angleterre/Écosse/Pays de Galles/Irlande du Nord, récupérés via le code de drapeau fourni par FBref.
- Logos de clubs : club → Wikidata (identifiant FBref P8642, ou rapprochement par nom parmi les
  clubs du championnat) → article Wikipedia anglais → image de l'infobox (presque toujours un SVG).
  Quelques exceptions forcées dans `WIKI_OVERRIDES` (update.py). Repli : logo PNG 500 px d'ESPN,
  puis monogramme. Les logos sont des marques des clubs : acceptable pour un prototype,
  à revoir avant toute mise en ligne publique.
- Wikimedia limite fortement le débit : le script attend et réessaie (HTTP 429), et la première
  récupération des ~96 clubs peut prendre une dizaine de minutes. Ensuite, tout est en cache.

**Interface**
- HTML/CSS/JS sans framework ni build : un fichier JSON statique suffit, rien à installer.
- Geist + Geist Mono (Google Fonts), chiffres tabulaires alignés à droite, bordures horizontales
  seulement, mode clair par défaut avec bascule sombre mémorisée.
- **Un seul tableau** (top 10 + « Afficher plus ») : rang, joueur (nom, poste, âge), club et
  nationalité (drapeau + pays en français), matchs, puis Buts, Passes, Total (buts + passes).
  Totaux toujours affichés ; le menu à cases à cocher de la barre de filtre choisit les colonnes (Buts, Passes, Total ; au moins une) et ajoute en option une sous-colonne « / match » à droite
  de chaque total. La ligne dépliée montre totaux et ratios par compétition. Clic sur « Buts »,
  « Passes » ou « Total » = tri par le total ; sur « / match » = tri par le ratio. La colonne triée
  est surlignée. Tri par ratio : joueurs ayant joué au moins 40 % des matchs du plus assidu.
- `launchd` sur le Mac (gratuit, natif) plutôt qu'un cron cloud : les IP de serveurs (GitHub Actions…)
  sont encore plus bloquées par FBref. Si le Mac dort à minuit, la tâche part au réveil.
