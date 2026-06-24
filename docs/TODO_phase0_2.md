# TODO : Compléter Phases 0 → 2 (RetailSense AI)

Ce document liste les tâches concrètes, critères d'acceptation et commandes rapides pour achever
les phases 0, 1 et 2 du projet.

## Phase 0 — Cadrage & mise en place
- [ ] Vérifier / compléter `README.md` (installation, activation venv, exécution scripts)
  - Critère : une personne suivant le README peut activer le venv et exécuter `python db/init_db.py`.
- [ ] Figeler les dépendances dans `requirements.txt` (versions précises).
  - Critère : `pip install -r requirements.txt` n'échoue pas sur un venv propre.
- [ ] Ajouter/valider `.gitignore` (ex : venv/, .venv/, __pycache__/, data/raw/ si volumineux, *.db)
- [ ] Confirmer la présence des jeux de données dans `data/raw/` et documenter leurs sources dans `data/Tables.txt`.
- [ ] Créer un `docs/backlog.md` simple (milestones/issues) ou utiliser la section TODO du README.

## Phase 1 — Conception et création de la DB (SQLite) & ETL
- [ ] Vérifier `db/init_db.py` : idempotence, création des tables, contraintes et index.
  - Critère : exécution répétée ne provoque pas d'erreurs et toutes les tables existent.
- [ ] Mettre en place un script ETL (`src/etl.py` ou dans `src/data_prep.py`) qui :
  - charge CSV depuis `data/raw/`,
  - nettoie types (dates, montants),
  - insère les données dans SQLite par transactions.
  - Critère : les counts de lignes attendus sont présents et le script ne lève pas d'exception.
- [ ] Ajouter `db/queries.sql` avec requêtes d'agrégation utiles (CA par mois, CA par client, top produits, last_purchase).
- [ ] Ajouter tests rapides `tests/test_db.py` qui valident existence tables et résultats basiques.

## Phase 2 — Préparation & feature engineering (Notebook `notebooks/data_processing.ipynb`)
Notebook principal : `notebooks/data_processing.ipynb` (doit être exécutable du début à la fin)

- [ ] Cellule 1 — Titre & objectifs (markdown)
- [ ] Cellule 2 — Imports et configuration (pandas, numpy, sqlalchemy, logging)
- [ ] Cellule 3 — Connexion SQLite et inspection des tables
- [ ] Cellule 4 — Chargement DataFrames bruts depuis SQLite
- [ ] Cellule 5 — Nettoyage : types, valeurs manquantes critiques, duplicates, petites diagnostics
- [ ] Cellule 6 — Jointures : orders × order_items × customers × products × reviews
- [ ] Cellule 7 — Calcul RFM par client (Récence, Fréquence, Montant) + résumé
- [ ] Cellule 8 — Définition du label churn (ex : inactivité > N jours) et création d'un jeu étiqueté
- [ ] Cellule 9 — Feature engineering : date parts, panier moyen, taux de retour, encodages
- [ ] Cellule 10 — Split train/val/test et sauvegarde dans `data/processed/` (CSV ou parquet)
- [ ] Cellule 11 — Vérifications finales et petit rapport (counts, exemples)

Livrables Phase 2 :
- `notebooks/data_processing.ipynb` exécutable et commenté
- `src/data_prep.py` (fonctions réutilisables : load_sqlite, build_rfm, build_features, save_splits)
- jeux nettoyés dans `data/processed/` : `train.csv`, `val.csv`, `test.csv` (ou .parquet)
- test `tests/test_data_prep.py` qui vérifie colonnes attendues et shapes > 0

## Commandes PowerShell utiles
```powershell
& .\venv\Scripts\Activate.ps1
python .\db\init_db.py
sqlite3 .\db\retailsense.db ".tables"
Get-ChildItem -Path .\data\processed\ -File
papermill .\notebooks\data_processing.ipynb .\notebooks\runs\data_processing_run.ipynb
```

## Notes / Priorités
- Priorité immédiate : Phase 1 (exécuter et valider `db/init_db.py`) puis Phase 2 (exécuter notebook et produire jeux processed).
- Documenter chaque décision dans le notebook et dans `docs/` (seuil churn, choix d'encodage, etc.).
