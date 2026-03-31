# pTron Service Center Finder

A backend API to find the nearest pTron service centers using FastAPI and Firebase Firestore.

## Features
- **Exact Pincode Search**: Instantly find service centers in your specific area.
- **Nearest Fallback**: If no exact match is found, the system calculates the TOP 3 nearest centers using the Haversine formula.
- **Google Sheets Sync**: Easily update the database by syncing directly from a Google Sheet.
- **Dockerized**: Easy deployment with Docker and Docker Compose.

## Project Structure
- `backend/`: FastAPI application (Pandas, Firebase Admin SDK).
- `docker-compose.yml`: Orchestrates the backend service.

## Setup Instructions

### 1. Prerequisites
- Docker and Docker Compose installed.
- A Firebase project with Firestore enabled.
- A Firebase Service Account JSON key.

### 2. Configuration
1. Place your Firebase service account JSON file in the `backend/` directory and rename it to `firebase-key.json`.
2. Create a `.env` file in the root directory (use `.env.example` as a template):
   ```env
   GOOGLE_SHEET_ID=your_google_sheet_id
   FIREBASE_PROJECT_ID=your_firebase_project_id
   GOOGLE_API_KEY=your_google_maps_api_key (optional fallback)
   ```

### 3. Running the Application
You can run the application directly using the included PowerShell script (no Docker required):
```bash
.\run_local.ps1
```

If you prefer using Docker and have it running:
```bash
docker-compose up --build
```
- Backend API: [http://localhost:8000](http://localhost:8000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Syncing Data
Once the application is running, visit `http://localhost:8000/api/sync-data` to populate Firestore with data from your Google Sheet.

## Data Source Requirements
The Google Sheet should have the following columns (Headers must match):
- `Pincode`
- `Service Centre Name`
- `Address`
- `Phone Number`
- `State`
- `Partner`
- `Latitude (lat)`
- `Longitude (lng)`
