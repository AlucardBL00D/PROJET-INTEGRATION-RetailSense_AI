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

## Application Flutter

* Tableau de bord
* Gestion des clients
* Consultation des prédictions
* Recommandations personnalisées

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
venv\Scripts\activate
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
uvicorn api.main:app --reload
```

Documentation Swagger :

```text
http://localhost:8000/docs
```

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
