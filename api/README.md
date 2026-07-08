# RetailSenseAI API

Pour démarrer l'API localement :

```bash
cd e:/Data/CDI_College/Cours_Profession_de_Inteligence_Artificiel/16-Projet_intergration/RetailSenseAI
.venv\Scripts\activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints disponibles :
- GET /health
- POST /predict/churn
- POST /predict/segmentation
- POST /predict/sentiment
- GET /predict/delivery

Documentation Swagger :
- http://127.0.0.1:8000/docs
