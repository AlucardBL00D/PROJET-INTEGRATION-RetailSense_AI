# RetailSense AI

Plateforme d'analyse et de prediction pour le retail, combinee avec API FastAPI, application Flutter et pipelines ML/DL.

## 1. Contexte

RetailSense AI est un projet d'integration de fin de formation en intelligence artificielle.

Le projet repond a une question simple: comment convertir des donnees transactionnelles e-commerce en decisions actionnables pour les equipes marketing, operations et relation client.

Cas d'usage principaux:

- Prediction du churn client
- Segmentation RFM
- Prevision de la demande
- Recommandation de categories produits
- Detection d'anomalies
- Analyse de sentiment d'avis clients

## 2. Apercu Architecture

```text
Data sources (CSV + SQL)
        |
Preprocessing (Pandas / Numpy)
        |
ML / DL training (scikit-learn, TensorFlow)
        |
Model registry + artifacts (models/)
        |
FastAPI inference layer (api/main.py)
        |
Flutter app + Swagger + tests
```

Architecture technique:

- API: FastAPI + Pydantic
- IA: scikit-learn + TensorFlow/Keras
- App client: Flutter
- Conteneurisation: Docker / docker-compose
- CI: GitHub Actions (API)

## 3. Structure du depot

```text
RetailSenseAI/
|- api/                  # API FastAPI et endpoints inference
|- app_flutter/          # Application mobile/web Flutter
|- data/                 # Jeux de donnees bruts et preprocesses
|- docs/                 # Documentation projet et livrables phase 8/9
|- models/               # Artefacts entraines (joblib, keras, csv)
|- tests/                # Tests API
|- scripts/              # Scripts d'execution locale (LAN, mobile)
|- requirements.txt
`- README.md
```

## 4. Installation

### 4.1 Prerequis

- Python 3.10+
- pip
- (Optionnel) Flutter SDK
- (Optionnel) Docker Desktop

### 4.2 Setup local

```bash
git clone <URL_DU_DEPOT>
cd RetailSenseAI
python -m venv .venv
```

Remplacer <URL_DU_DEPOT> par l'URL GitHub du projet.

Windows PowerShell:

```powershell
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Execution

### 5.1 API locale

```bash
uvicorn api.main:app --reload --reload-dir api --host 127.0.0.1 --port 8000
```

Acces:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Healthcheck: http://127.0.0.1:8000/health

Variables d'environnement utiles:

- RETAILSENSE_MODELS_DIR (defaut: ./models)
- RETAILSENSE_MODEL_REGISTRY_PATH (defaut: ./models/model_registry.json)
- RETAILSENSE_ANOMALY_THRESHOLD (defaut: 2.5)
- RETAILSENSE_CORS_ORIGINS (defaut: *)
- RETAILSENSE_REQUEST_LOG_ENABLED (defaut: true)
- RETAILSENSE_LOG_LEVEL (defaut: INFO)

### 5.2 Execution Flutter

```bash
cd app_flutter
flutter pub get
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Test sur telephone Android (meme Wi-Fi):

```powershell
.\scripts\run_api_lan.ps1
.\scripts\run_flutter_phone.ps1
```

## 6. Tests

Tests API:

```bash
pytest tests/test_api.py -q
```

CI automatique:

- Workflow: .github/workflows/api-ci.yml

## 7. Endpoints API

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

## 8. Resultats et indicateurs

Indicateurs consolides dans models/:

- Churn: models/churn_metrics_summary.csv
- Livraison/retard: models/delivery_metrics_summary.csv
- Historique MLP: models/mlp_history.csv

Les performances detaillees, limites et comparatifs sont decrits dans:

- docs/RAPPORT_TECHNIQUE_PHASE9.md

## 9. Captures d'ecran et demonstration

Elements a inclure dans le portfolio:

- Swagger avec appels endpoint reussis
- Ecran Flutter dashboard
- Exemple prediction churn + sentiment
- Pipeline data/ML (schema)
- Vue du dashboard Power BI

Guide de production des captures:

- docs/SCREENSHOTS_GUIDE.md

## 10. Livrables Phase 9

- Rapport technique (15-25 pages): docs/RAPPORT_TECHNIQUE_PHASE9.md
- Support soutenance (10-15 slides): docs/SOUTENANCE_PHASE9_SLIDES.md
- Checklist publication portfolio: docs/PHASE_9_PORTFOLIO_PLAN.md

## 11. Limites actuelles

- Les modeles sont charges depuis des artefacts locaux; pas de model serving distribue.
- Les jeux de donnees peuvent evoluer et impacter la reproductibilite si non versionnes strictement.
- Les tests couvrent le contrat API principal mais restent majoritairement orientes integration.

## 13. Roadmap

- Ajouter versionning strict des datasets et model cards.
- Ajouter tests de performance (latence P95) et robustesse donnees.
- Mettre en ligne une demo cloud stable (API + front).

## 14. Licence

Ce projet est distribue sous licence MIT.

## 15. Auteur

Xavier Archambault
Projet d'integration - Technicien en Intelligence Artificielle
