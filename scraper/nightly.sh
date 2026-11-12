#!/bin/sh
# Tâche de minuit : met à jour les classements puis publie les nouvelles données sur GitHub
# (le push déclenche le déploiement GitHub Pages, cf. .github/workflows/pages.yml).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/.local/bin"
stamp() { date "+%Y-%m-%d %H:%M:%S"; }

/usr/bin/python3 scraper/update.py || { echo "$(stamp) mise à jour échouée, rien n'est publié"; exit 1; }

git add site/data scraper/cache
if git diff --cached --quiet; then
  echo "$(stamp) aucune donnée nouvelle, rien à publier"
  exit 0
fi
git commit -q -m "Données du $(date +%Y-%m-%d)" || exit 1
# Rattrape d'éventuels commits faits ailleurs avant d'envoyer
git pull -q --rebase origin main && git push -q origin main \
  && echo "$(stamp) données publiées sur GitHub" \
  || { echo "$(stamp) échec de l'envoi sur GitHub"; exit 1; }
