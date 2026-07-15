# RetailSense Flutter App

Application multiplateforme connectee a l'API FastAPI de RetailSense.

## Ecrans disponibles

- Connexion
- Dashboard (etat API + indicateurs)
- Fiche client (segmentation + churn + sentiment)
- Prevision de demande
- Recommandations produits + score d'anomalie

## Architecture

- `lib/app.dart` : shell applicatif et navigation
- `lib/config/api_config.dart` : URL API via `--dart-define`
- `lib/services/api_client.dart` : appels HTTP et gestion des erreurs
- `lib/screens/*.dart` : ecrans metier

## Lancer l'application

Depuis `app_flutter/`:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

Android emulator (si API locale sur machine hote):

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Web:

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

## Build APK (release)

```bash
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=https://retailsense-api.onrender.com
```

Important: remplace `retailsense-api.onrender.com` par ton URL publique reelle.

APK de sortie:

```text
build/app/outputs/flutter-apk/app-release.apk
```
