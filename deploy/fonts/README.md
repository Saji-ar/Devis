# Polices personnalisées (optionnel)

Déposez ici les fichiers de police (.ttf / .otf) que vous voulez utiliser pour un
rendu identique à l'original — par exemple **Aptos** (police du template).

Où trouver Aptos sur votre Mac (si Office installé) :
- `~/Library/Fonts/` ou `/Library/Fonts/` → fichiers commençant par `Aptos`.

Copiez-les dans ce dossier, puis reconstruisez l'image : `docker compose up -d --build`.

Sans police déposée ici, l'appli utilise **Carlito** (équivalent libre d'Aptos,
installé automatiquement) — rendu très proche et texte sélectionnable.
