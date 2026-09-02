# Devis Traiteur

Application pour créer, versionner et exporter en PDF des devis de traiteur.
Les **fichiers Excel restent la source de vérité** ; SQLite n'est qu'un index reconstruisible.

## Idées clés

- **Un devis = un dossier** `data/devis/<référence>/`.
- **Une version = un fichier figé** `v<N>_<AAAA-MM-JJ>.xlsx`, jamais écrasé.
- **Édition par champs structurés** (dates + tableau de produits) injectés dans une copie du
  template → la mise en page du template est toujours préservée.
- **Génération fidèle par « chirurgie XML »** : on n'écrit PAS le fichier avec openpyxl (qui
  supprime le logo et le tableau stylisé). On clone la ligne du tableau `Tableau1` directement
  dans le XML et on décale les lignes de total, en laissant intacts le logo, les styles et le
  pied de page. Voir [backend/app/excel_service.py](backend/app/excel_service.py).
- **Export PDF fidèle** via LibreOffice headless (`xlsx → pdf`).
- **Mode dégradé** : si l'appli est indisponible, on peut créer une version à la main
  (copier le dernier `.xlsx`, incrémenter `N`, changer la date). Le bouton
  **« Scanner le dossier Excel »** la réintègre ensuite dans la base.

## Architecture

```
backend/   FastAPI + SQLModel (SQLite) + openpyxl + LibreOffice
frontend/  React (Vite + TypeScript)
data/
  templates/template.xlsx          <- votre modèle de devis
  templates/template_mapping.json  <- correspondance champs <-> cellules
  devis/<référence>/v<N>_<date>.xlsx
deploy/    Dockerfile, docker-compose.yml, devis.service (systemd)
```

## Structure du template

`data/templates/template.xlsx` est **votre vrai modèle** (logo « MAISON ADITYA », en-tête,
pied de page). La feuille contient :

- `E2` : date de devis · `B16` : date de la prestation
- Un tableau Excel `Tableau1` (en-tête ligne 17) avec les colonnes **Produit, Quantité,
  Prix Unit HT, TVA, Total HT**. Le corps commence ligne 18.
- Sous le tableau : Montant Total HT / TVA / TTC (formules à références structurées).

Il n'y a **pas de bloc client** sur la feuille : le nom, le téléphone et « comment il m'a
connu » sont gérés dans la base, rattachés au devis. Les repères de structure (ligne d'en-tête,
formule de ligne) sont des constantes en haut de `excel_service.py` — c'est là qu'on ajuste
si vous modifiez la disposition du template.

## Développement (Mac)

```bash
./dev.sh          # backend :8000 + front :5173
```
Prérequis : Python 3, Node 20+, et LibreOffice (`brew install --cask libreoffice`).

## Déploiement Raspberry Pi

### Option A — Docker (recommandé)

1. Dans `deploy/docker-compose.yml`, pointez le volume vers votre dossier OneDrive
   synchronisé sur le Pi :
   ```yaml
   volumes:
     - "/home/pi/OneDrive/sarl ASD/Compta/Devis Traiteur:/data"
   ```
   Ce dossier doit contenir `templates/template.xlsx`, `templates/template_mapping.json`
   et un sous-dossier `devis/`.
2. ```bash
   cd deploy && docker compose up -d --build
   ```
3. Ouvrez `http://<ip-du-pi>:8000`.

### Option B — systemd (sans Docker)

Voir les instructions en tête de `deploy/devis.service`.
Installez LibreOffice : `sudo apt-get install libreoffice-calc`.

## Sécurité (mot de passe)

- Mot de passe en clair dans `backend/.env` : `APP_PASSWORD=...` (vide = aucune protection).
- À la connexion, le navigateur mémorise un jeton (localStorage) → **pas besoin de retaper**
  le mot de passe à chaque fois. Bouton « Se déconnecter » pour l'oublier.
- **Blocage anti-force brute** : après plus de `MAX_LOGIN_ATTEMPTS` (défaut 10) essais ratés,
  l'appli se bloque et écrit `APP_ENABLED=false` dans `.env`. Ce blocage **survit au
  redémarrage**. Pour réactiver, remettez **manuellement** `APP_ENABLED=true` dans `.env`
  puis redémarrez le serveur.

> Le mot de passe protège l'API. Servez l'appli derrière HTTPS (ou sur votre réseau local
> uniquement) pour que le mot de passe ne circule pas en clair sur le réseau.

## Configuration

Copiez `backend/.env.example` en `backend/.env` et adaptez `DATA_DIR` (chemin du dossier
OneDrive), `TEMPLATE_PATH`, etc.
```

## API principale

| Méthode | Route | Rôle |
|---|---|---|
| GET/POST | `/api/clients` | Lister / créer un client |
| GET/POST | `/api/devis` | Lister / créer un devis |
| POST | `/api/devis/{id}/versions` | Enregistrer une nouvelle version datée |
| GET | `/api/devis/version/{id}/pdf` | Télécharger le PDF |
| GET | `/api/devis/version/{id}/xlsx` | Télécharger l'Excel |
| POST | `/api/devis/scan` | Réconcilier le dossier Excel avec la base |
| POST | `/api/devis/import-anciens` | Importer les anciens `.xlsx` du dossier `IMPORT_SOURCE_DIR` |

## Importer d'anciens devis

Renseignez `IMPORT_SOURCE_DIR` dans `backend/.env` (dossier contenant vos anciens `.xlsx`),
puis cliquez **« Importer d'anciens devis »** sur la page Devis. Chaque ancien devis devient
un devis + une version v1 (régénérée avec le template courant), rattaché à un client provisoire
« À préciser — … » que vous renommez ensuite via **Éditer** sur la page Clients. L'import est
idempotent (relancer n'ajoute pas de doublons).

Le devis affiche un **bloc client à droite** (cellules E10-E12 : nom / téléphone / email),
rempli automatiquement depuis le client rattaché.
