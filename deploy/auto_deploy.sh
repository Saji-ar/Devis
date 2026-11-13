#!/usr/bin/env bash
# Deploiement automatique (CD) pour le Raspberry Pi.
#
# Recupere la derniere version de la branche suivie et reconstruit le conteneur
# UNIQUEMENT si quelque chose a change. Idempotent : sans nouveaute, ne fait rien.
#
# Prevu pour tourner via cron (toutes les ~2 min), protege par flock pour eviter
# les executions concurrentes. Installation : voir deploy/README ou la doc.
#
#   */2 * * * * /usr/bin/flock -n /tmp/devis-deploy.lock \
#       /home/saji__ar/Devis/deploy/auto_deploy.sh >> /home/saji__ar/devis-deploy.log 2>&1
#
set -euo pipefail

REPO="${DEVIS_REPO:-/home/saji__ar/Devis}"
BRANCH="${DEVIS_BRANCH:-main}"

cd "$REPO"

git fetch --quiet origin "$BRANCH"
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0   # rien de nouveau, on sort sans bruit
fi

echo "[$(date '+%F %T')] Nouvelle version detectee ($REMOTE), deploiement..."
# --ff-only : avance proprement; echoue (sans casser) si le Pi a des modifs locales.
git merge --ff-only "origin/$BRANCH"
cd deploy
docker compose up -d --build
echo "[$(date '+%F %T')] Deploiement termine."
