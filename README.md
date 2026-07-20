# RetailSense AI

Plateforme d'analyse predictive pour le retail qui combine une API FastAPI, une application Flutter et plusieurs pipelines ML/DL pour transformer des donnees e-commerce en decisions actionnables.

## 1. Vue d'ensemble

RetailSense AI est un projet d'integration de fin de formation en intelligence artificielle. L'objectif est de centraliser plusieurs cas d'usage IA dans une meme solution exploitable par des equipes marketing, operations et relation client.

Cas d'usage couverts:

- Prevision de la demande
- Prediction du churn client
- Segmentation RFM
- Recommandation de categories produits
- Detection d'anomalies
- Analyse de sentiment d'avis clients

## 2. Architecture

```text
Sources de donnees (CSV + SQL)
        |
Preprocessing (Pandas / NumPy)
        |
Entrainement ML / DL (scikit-learn, TensorFlow / Keras)
        |
Registre de modeles + artefacts (models/)
        |
Couche d'inference FastAPI (api/main.py)
        |
Application Flutter + Swagger + tests API
```

Stack technique:

- Backend API: FastAPI + Pydantic
- Machine Learning: scikit-learn
- Deep Learning: TensorFlow / Keras
- Application cliente: Flutter
- Deploiement: Docker, docker-compose, Render
- Validation: pytest + GitHub Actions

## 3. Fonctionnalites principales

- Exposition des modeles via une API REST documentee avec Swagger
- Consultation de l'etat des artefacts et du registre des modeles
- Interface Flutter pour tester les cas d'usage metier
- Scripts de lancement local pour usage desktop, web et telephone Android
- Artefacts pre-entraines deja inclus dans le depot pour les demonstrations

## 4. Structure du depot

```text
RetailSenseAI/
|- api/                  # API FastAPI et endpoints d'inference
|- app_flutter/          # Application Flutter mobile/web
|- data/                 # Donnees brutes et preprocesses
|- docs/                 # Documentation projet et livrables
|- models/               # Modeles entraines et metriques consolidees
|- notebooks/            # Notebooks de construction, traitement et entrainement
|- scripts/              # Scripts d'execution locale et LAN
|- src/                  # Scripts techniques et verifications ponctuelles
|- tests/                # Tests API
|- docker-compose.yml
|- Dockerfile
|- requirements.txt
`- README.md
```

## 5. Installation locale

### 5.1 Prerequis

- Python 3.10 ou plus recent
- pip
- Flutter SDK pour lancer l'application cliente
- Docker Desktop pour le deploiement conteneurise

### 5.2 Setup

```bash
git clone https://github.com/AlucardBL00D/PROJET-INTEGRATION-RetailSense_AI
cd RetailSenseAI
python -m venv .venv
```

Windows PowerShell:

```powershell
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 6. Demarrage rapide

### 6.1 API FastAPI en local

```bash
uvicorn api.main:app --reload --reload-dir api --host 127.0.0.1 --port 8000
```

Acces utiles:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Healthcheck: http://127.0.0.1:8000/health
- Metadonnees modeles: http://127.0.0.1:8000/metadata/models

Variables d'environnement prises en charge:

- RETAILSENSE_MODELS_DIR, defaut `./models`
- RETAILSENSE_MODEL_REGISTRY_PATH, defaut `./models/model_registry.json`
- RETAILSENSE_ANOMALY_THRESHOLD, defaut `2.5`
- RETAILSENSE_API_VERSION, defaut `1.1.0`
- RETAILSENSE_CORS_ORIGINS, defaut `*`
- RETAILSENSE_REQUEST_LOG_ENABLED, defaut `true`
- RETAILSENSE_LOG_LEVEL, defaut `INFO`

### 6.2 Application Flutter

```bash
cd app_flutter
flutter pub get
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Telephone Android physique sur le meme reseau Wi-Fi:

```powershell
.\scripts\run_api_lan.ps1
.\scripts\run_flutter_phone.ps1
```

Autres cibles utiles:

- Android emulator: `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000`
- Web Chrome: `flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000`

## 7. API disponible

Systeme:

- GET /
- GET /health
- GET /metadata/models

Inference:

- POST /predict/churn
- POST /predict/segmentation
- POST /predict/demand
- POST /predict/recommendations
- POST /predict/anomaly
- POST /predict/sentiment

## 8. Tests et CI

Lancement local des tests API:

```bash
pytest tests/test_api.py -q
```

Validation automatique:

- Workflow GitHub Actions: `.github/workflows/api-ci.yml`
- Python CI: 3.11
- Variables de tests configurees pour charger les artefacts locaux du dossier `models/`

## 9. Deploiement

### 9.1 Docker local

```bash
docker compose up --build
```

### 9.2 Render

Le fichier `render.yaml` decrit un service web Docker `retailsense-api` avec:

- Healthcheck sur `/health`
- Chargement des modeles depuis `/app/models`
- Configuration predefinie des variables d'environnement principales
- Auto deploy active

## 10. Resultats et artefacts

Artefacts et indicateurs disponibles dans `models/`:

- `churn_metrics_summary.csv`
- `delivery_metrics_summary.csv`
- `mlp_history.csv`
- `model_registry.json`
- Modeles `joblib`, `keras` et poids `h5`

## 11. Documentation associee

Documents utiles dans `docs/`:

- `PHASE_8_DEPLOIEMENT.md`
- `PHASE_9_PORTFOLIO_PLAN.md`
- `Guide_Modules_ML_DL_RetailSense.txt`
- Livrables PDF et notebook de deploiement

Documentation complementaire:

- `api/README.md` pour les exemples de payloads API
- `app_flutter/README.md` pour le lancement multi-plateforme Flutter

## 12. Limites actuelles

- Les modeles sont servis depuis des artefacts locaux et non depuis une infrastructure de model serving dediee.
- La reproductibilite depend du versionnage des jeux de donnees et des artefacts.
- Les tests se concentrent surtout sur le contrat API et moins sur des suites fonctionnelles de bout en bout.
- Le projet cible en priorite la demonstration technique et pedagogique plutot qu'une exploitation de production a grande echelle.

## 13. Auteur

Xavier Archambault  
Projet d'integration - Technicien en Intelligence Artificielle

## 14. Licence

Ce projet est distribue sous licence MIT.
