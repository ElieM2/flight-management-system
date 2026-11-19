# Scripts i18n ponctuels

Ces scripts ont servi à compléter ou corriger les fichiers de traduction (`.po`). Ils ne font pas partie de l’application au runtime.

Les lancer depuis la racine du dépôt, uniquement en maintenance, par exemple :

```bash
python scripts/i18n/fix_po_duplicates.py
```

Certains d’entre eux attendent une clé optionnelle (`DEEPL_API_KEY`) si une traduction automatique est demandée. Ils ne doivent pas être exposés comme commandes de production.
