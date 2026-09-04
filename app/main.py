import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .core.database import engine, Base
from .api.v1 import (
    auth, administrateur, patients, docteurs, pharmacie, hopitaux, chauffeurs,
    rendez_vous, disponibilite, localisation, ia, transport
)

logger = logging.getLogger(__name__)

# Créer les tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables créées avec succès")
except Exception as exc:
    logger.warning("Base de données non disponible au démarrage : %s", exc)

app = FastAPI(
    title="Santé-Fianarantsoa API",
    description="""
    ## 🏥 Plateforme intelligente de services de santé géolocalisés
    
    ### Fonctionnalités principales
    - 👤 **Authentification multi-rôles** (Patient, Docteur, Pharmacie, Chauffeur, Admin)
    - 📍 **Géolocalisation** des services de santé
    - 🤖 **Analyse IA** des symptômes
    - 📅 **Gestion des rendez-vous**
    - 🚑 **Transport médical** en temps réel
    - 💊 **Pharmacies de garde**
    - 🏥 **Gestion des hôpitaux**
    
    ### Workflow d'inscription
    1. **Patient** → Inscription automatiquement approuvée
    2. **Professionnel** (Docteur, Pharmacie, Hôpital, Chauffeur) → En attente de validation admin
    3. **Admin** → Valide ou rejette les inscriptions
    """,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configuration OAuth2 pour Swagger
app.swagger_ui_init_oauth = {
    "clientId": "swagger-ui",
    "appName": "Santé-Fianarantsoa API",
    "usePkceWithAuthorizationCodeGrant": False,
}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers - TOUS ACTIVÉS
app.include_router(auth.router, prefix="/api/v1")
app.include_router(administrateur.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(docteurs.router, prefix="/api/v1")
app.include_router(pharmacie.router, prefix="/api/v1")
app.include_router(hopitaux.router, prefix="/api/v1")
app.include_router(chauffeurs.router, prefix="/api/v1")
app.include_router(rendez_vous.router, prefix="/api/v1")
app.include_router(disponibilite.router, prefix="/api/v1")
app.include_router(localisation.router, prefix="/api/v1")
app.include_router(ia.router, prefix="/api/v1")
app.include_router(transport.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API Santé-Fianarantsoa",
        "docs": "/api/docs",
        "version": "2.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Custom OpenAPI avec sécurité
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Santé-Fianarantsoa API",
        version="2.0.0",
        description="""
        ## 🏥 Plateforme intelligente de services de santé géolocalisés
        
        ### Authentification
        1. **Inscription** : Chaque rôle a son propre endpoint d'inscription
        2. **Validation** : Les professionnels doivent être validés par un admin
        3. **Connexion** : Utilisez `/api/v1/auth/login-form` pour Swagger
        
        ### Rôles disponibles
        - `admin` : Gestion complète
        - `patient` : Utilisateur standard
        - `docteur` : Professionnel de santé
        - `pharmacie` : Établissement pharmaceutique
        - `hopital` : Établissement hospitalier
        - `chauffeur` : Transport médical
        """,
        routes=app.routes,
    )
    
    # Ajouter le schéma de sécurité
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/login-form",
                    "scopes": {}
                }
            }
        }
    }
    
    # Appliquer la sécurité à toutes les routes (sauf auth)
    for path in openapi_schema["paths"]:
        if not path.startswith("/api/v1/auth"):
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [
                    {"OAuth2PasswordBearer": []}
                ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)