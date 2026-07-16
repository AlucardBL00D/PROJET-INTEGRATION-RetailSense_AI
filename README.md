# 🛒 RetailSense AI

### Plateforme intelligente d'analyse et de prédiction pour le commerce de détail

👨‍💻 Développé par **Xavier Archambault**
🎓 Projet de fin de formation – Technicien en Intelligence Artificielle

---

# Description du projet

RetailSense AI est une plateforme intelligente d'analyse et de prédiction destinée au commerce de détail. Le projet a été réalisé dans le cadre du projet d'intégration final du programme de Technicien en Intelligence Artificielle.

L'objectif principal est de transformer les données d'une entreprise de vente au détail en informations exploitables grâce à l'analyse de données, au Machine Learning, au Deep Learning et à la visualisation décisionnelle.

La plateforme permet notamment :

* L'analyse du comportement des clients
* La segmentation de la clientèle
* La prédiction du churn (attrition client)
* La prévision de la demande
* La détection d'anomalies et de fraudes
* La recommandation de produits
* L'analyse des avis clients
* La consultation des résultats via une API REST et une application multiplateforme

---

# Objectifs

Ce projet met en pratique l'ensemble des compétences acquises durant les 18 mois de formation :

* Python
* SQLite
* Pandas
* NumPy
* Scikit-learn
* TensorFlow / Keras
* Power BI
* FastAPI
* Flutter / Dart
* Docker
* Git et GitHub

---

# Architecture du projet

```text
RetailSense_AI/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── db/
│   ├── schema.sql
│   └── retailsense.db
│
├── notebooks/
│
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── machine_learning/
│   ├── deep_learning/
│   └── utils/
│
├── models/
│
├── api/
│
├── app_flutter/
│
├── powerbi/
│
├── docs/
│
├── requirements.txt
│
└── README.md
```

Flux de données :

```text
Sources de données
        ↓
    SQLite
        ↓
Pandas / NumPy
        ↓
 Modèles ML & DL
        ↓
     FastAPI
        ↓
 Application Flutter
```

---

# Fonctionnalités

## Analyse de données

* Nettoyage et préparation des données
* Fusion de plusieurs sources de données
* Création d'indicateurs métier
* Construction de matrices RFM

## Machine Learning

* Segmentation de clientèle (K-Means, DBSCAN)
* Prédiction du churn
* Prévision des ventes
* Comparaison de plusieurs modèles

## Deep Learning

* MLP pour les données tabulaires
* LSTM pour la prévision des ventes
* Transformers pour l'analyse des avis clients
* Autoencodeurs pour la détection d'anomalies
* GAN pour la génération de données synthétiques
* GNN pour les recommandations de produits

## Visualisation

* Tableaux de bord Power BI
* KPI interactifs
* Rapports décisionnels

## API REST

* Consultation des prédictions
* Analyse des clients
* Prévisions de ventes
* Recommandations produits
* Détection d'anomalies
* Analyse du sentiment d'avis

## Application Flutter

* Tableau de bord
* Écran de connexion
* Fiche client (segment + churn + sentiment)
* Prévision de demande
* Recommandations personnalisées et score d'anomalie

---

# Technologies utilisées

| Domaine            | Technologie        |
| ------------------ | ------------------ |
| Programmation      | Python             |
| Base de données    | SQLite             |
| Analyse de données | Pandas, NumPy      |
| Machine Learning   | Scikit-learn       |
| Deep Learning      | TensorFlow / Keras |
| API                | FastAPI            |
| Visualisation      | Power BI           |
| Application        | Flutter            |
| Déploiement        | Docker             |
| Versionnement      | Git / GitHub       |

---

# Installation

## Cloner le projet

```bash
git clone https://github.com/votre-compte/RetailSense_AI.git
cd RetailSense_AI
```

## Créer un environnement virtuel

```bash
python -m venv venv
```

## Activer l'environnement

Windows :

```bash
& .\.venv\Scripts\Activate.ps1                        
```

Linux / Mac :

```bash
source venv/bin/activate
```

## Installer les dépendances

```bash
pip install -r requirements.txt
```

---

# Exécution

## Lancer l'API

```bash
uvicorn api.main:app --reload --reload-dir api --host 127.0.0.1 --port 8000
```

Pour tester depuis un telephone (meme Wi-Fi que le PC), lance l'API en LAN:

```powershell
.\scripts\run_api_lan.ps1
```

Sinon commande manuelle:

```bash
uvicorn api.main:app --reload --reload-dir api --host 0.0.0.0 --port 8000
```

Variables d'environnement (préparation phase 8) :

```bash
RETAILSENSE_MODELS_DIR=./models
RETAILSENSE_ANOMALY_THRESHOLD=2.5
RETAILSENSE_API_VERSION=1.1.0
RETAILSENSE_CORS_ORIGINS=*
```

Documentation Swagger :

```text
http://localhost:8000/docs
```

## Lancer l'application Flutter

```bash
cd app_flutter
flutter pub get
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Telephone Android physique (API sur le PC):

```powershell
.\scripts\run_flutter_phone.ps1
```

Commande manuelle avec IP LAN du PC (exemple):

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.25:8000
```

Android Emulator (API locale) :

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Phase 8 - Deploiement et industrialisation legere

### Dockeriser l'API

```bash
cp .env.example .env
docker compose up --build -d
```

Verifier l'API:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata/models
```

Arret:

```bash
docker compose down
```

### Variables d'environnement de production

- `RETAILSENSE_MODELS_DIR`
- `RETAILSENSE_MODEL_REGISTRY_PATH`
- `RETAILSENSE_ANOMALY_THRESHOLD`
- `RETAILSENSE_API_VERSION`
- `RETAILSENSE_CORS_ORIGINS`
- `RETAILSENSE_REQUEST_LOG_ENABLED`
- `RETAILSENSE_LOG_LEVEL`

### Deployer l'API sur Render (gratuit)

1. Pousser le projet sur GitHub.
2. Aller sur Render, choisir **New +** puis **Blueprint**.
3. Selectionner le repo RetailSenseAI (Render detecte automatiquement `render.yaml`).
4. Lancer le deploiement et attendre le statut **Live**.
5. Ouvrir l'URL publique Render et verifier:

```bash
curl https://retailsense-api.onrender.com/health
curl https://retailsense-api.onrender.com/metadata/models
```

Important: remplace `retailsense-api.onrender.com` par ton URL reelle Render.

### Versioning minimal des modeles

Le fichier `models/model_registry.json` sert de registre simple des artefacts en production.
Le endpoint `GET /metadata/models` expose les versions chargees.

### Build APK Android (release)

Depuis `app_flutter/`:

```bash
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=https://retailsense-api.onrender.com
```

Important: remplace `retailsense-api.onrender.com` par ton URL publique reelle.

APK de sortie:

```text
app_flutter/build/app/outputs/flutter-apk/app-release.apk
```

### Documentation detaillee

Guide complet de phase 8: `docs/PHASE_8_DEPLOIEMENT.md`

---

# Jeux de données

Les données utilisées proviennent de jeux de données publics de commerce électronique.

Exemples :

* Olist Brazilian E-Commerce Dataset
* Online Retail Dataset
* Amazon Reviews
* Données transactionnelles publiques ou synthétiques

---

# Résultats attendus

* Segmentation automatique des clients
* Prédiction du risque de départ des clients
* Prévision des ventes futures
* Détection des transactions anormales
* Recommandations personnalisées
* Analyse automatique des avis clients

---

# Améliorations futures

* Authentification des utilisateurs
* Déploiement Cloud
* Tableau de bord en temps réel
* Pipeline MLOps
* CI/CD automatisée
* Surveillance des performances des modèles

---

# Compétences démontrées

* Analyse de données
* Machine Learning
* Deep Learning
* Développement Backend
* Développement Mobile
* Visualisation de données
* Déploiement Docker
* Gestion de projet IA

---

# Licence

Projet réalisé dans un cadre pédagogique dans le cadre du programme de Technicien en Intelligence Artificielle.

---

# Remerciements

Projet réalisé au Collège CDI dans le cadre du programme de Technicien en Intelligence Artificielle.

Professeur encadrant : Reda Mohammed Chatou

---

**Développé par Xavier Archambault**
