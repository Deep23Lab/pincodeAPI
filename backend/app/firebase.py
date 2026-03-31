import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
def init_firebase():
    if not firebase_admin._apps:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # Fallback to current directory for development
            cred_file = "firebase-key.json"
            if os.path.exists(cred_file):
                cred = credentials.Certificate(cred_file)
                firebase_admin.initialize_app(cred)
            else:
                # Still try if env variable is set but file not found in that exact check
                try:
                    firebase_admin.initialize_app()
                except Exception as e:
                    print(f"Warning: Firebase Admin failed to initialize: {e}")

    return firestore.client()

db = init_firebase()
