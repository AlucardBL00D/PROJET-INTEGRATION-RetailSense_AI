# Phase 8 - Deploiement et industrialisation legere

## Objectif

Rendre la solution executable hors du poste de developpement avec une procedure reproductible.

## 1) Conteneurisation API

Fichiers:
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.example`

### Demarrage local avec Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

Verifier:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata/models
```

Arret:

```bash
docker compose down
```

## 2) Configuration externalisee

Variables gerees:
- `RETAILSENSE_MODELS_DIR`
- `RETAILSENSE_MODEL_REGISTRY_PATH`
- `RETAILSENSE_ANOMALY_THRESHOLD`
- `RETAILSENSE_API_VERSION`
- `RETAILSENSE_CORS_ORIGINS`
- `RETAILSENSE_REQUEST_LOG_ENABLED`
- `RETAILSENSE_LOG_LEVEL`

## 3) Deploiement accessible (Render, rapide)

Le projet contient deja un blueprint `render.yaml`.

Etapes:
1. Pousser le repo sur GitHub.
2. Sur Render: **New +** > **Blueprint**.
3. Selectionner le repo RetailSenseAI.
4. Valider la creation du service Docker `retailsense-api`.
5. Attendre l'etat **Live** puis copier l'URL publique.

Verification:

```bash
curl https://retailsense-api.onrender.com/health
curl https://retailsense-api.onrender.com/metadata/models
```

Important: remplace `retailsense-api.onrender.com` par ton URL reelle.

Connexion Flutter:

```bash
flutter run --dart-define=API_BASE_URL=https://retailsense-api.onrender.com
```

## 4) Suivi minimal et versioning des modeles

### Journalisation des requetes

Chaque requete recoit:
- `X-Request-ID`
- `X-Process-Time-ms`

Les logs incluent debut/fin, methode, endpoint, statut et latence.

### Versioning modeles

Le fichier `models/model_registry.json` fait office de registre minimal.
Le endpoint `GET /metadata/models` expose les versions de modeles actives.

## 5) Procedure de reentrainement (MLOps leger)

1. Mettre a jour les donnees `data/raw` et `data/processed`.
2. Reexecuter notebooks et scripts de training pour generer nouveaux artefacts dans `models/`.
3. Mettre a jour `models/model_registry.json` (version, date, stage).
4. Executer la validation API locale:

```bash
pytest tests/test_api.py -q
```

5. Redemarrer l'API (ou redeployer le conteneur).
6. Verifier regressions:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata/models
```

## 6) APK Android

### Build release

Depuis `app_flutter/`:

```bash
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=https://retailsense-api.onrender.com
```

APK genere:
- `app_flutter/build/app/outputs/flutter-apk/app-release.apk`

Note: l'autorisation reseau Android (`INTERNET`) est activee dans le manifest.
