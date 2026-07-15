# RetailSenseAI API

## Demarrage local

```bash
cd e:/Data/CDI_College/Cours_Profession_de_Inteligence_Artificiel/16-Projet_intergration/RetailSenseAI
.venv\Scripts\activate
uvicorn api.main:app --reload --reload-dir api --host 127.0.0.1 --port 8000
```

Swagger / OpenAPI:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/openapi.json

## Variables d'environnement (preparation phase 8)

- `RETAILSENSE_MODELS_DIR` (defaut: `./models`)
- `RETAILSENSE_ANOMALY_THRESHOLD` (defaut: `2.5`)
- `RETAILSENSE_API_VERSION` (defaut: `1.1.0`)
- `RETAILSENSE_CORS_ORIGINS` (defaut: `*`, liste separee par virgule)
- `RETAILSENSE_MODEL_REGISTRY_PATH` (defaut: `./models/model_registry.json`)
- `RETAILSENSE_REQUEST_LOG_ENABLED` (defaut: `true`)
- `RETAILSENSE_LOG_LEVEL` (defaut: `INFO`)

Exemple PowerShell:

```powershell
$env:RETAILSENSE_MODELS_DIR = "e:/Data/.../RetailSenseAI/models"
$env:RETAILSENSE_CORS_ORIGINS = "http://localhost:3000,http://localhost:8080"
```

## Endpoints

Systeme:

- `GET /health` : etat de l'API + artefacts modeles charges/manquants
- `GET /metadata/models` : details internes des modeles detectes

Inference IA:

- `POST /predict/churn`
- `POST /predict/segmentation`
- `POST /predict/demand`
- `POST /predict/recommendations`
- `POST /predict/anomaly`
- `POST /predict/sentiment`

## Exemples JSON

Churn:

```json
{
	"total_price": 150.0,
	"total_freight": 12.5,
	"total_weight": 2.1,
	"n_items": 3,
	"max_installments": 3,
	"payment_value": 162.5,
	"delivery_days": 4,
	"delay_days": 0,
	"purchase_month": 7,
	"purchase_dow": 4,
	"main_category": "electronics",
	"payment_type": "credit_card",
	"customer_state": "SP"
}
```

Demand forecast:

```json
{
	"recent_daily_orders": [18, 20, 17, 23, 22, 26, 29, 24],
	"horizon_days": 7
}
```

Recommendations:

```json
{
	"customer_id": "CUST-001",
	"segment": 2,
	"churn_risk": 0.74,
	"recent_categories": ["electronics", "accessories"],
	"top_k": 5
}
```

## Docker (phase 8)

Depuis la racine du projet:

```bash
cp .env.example .env
docker compose up --build -d
```

Test rapide:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metadata/models
```
