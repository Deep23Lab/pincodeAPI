from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.service_centers import router as service_centers_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="pTron Service Center Finder API")

# Setup CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint 
@app.get("/")
def read_root():
    return {"message": "Welcome to pTron Service Center Finder API"}

# Health check 
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Include routers 
app.include_router(service_centers_router, prefix="/api", tags=["Service Centers"])

if __name__ == "__main__":
    import uvicorn
    # Render and other clouds provide the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
