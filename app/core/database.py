from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import logging

logger = logging.getLogger(__name__)

try:
    # Nettoyer la chaîne de connexion
    db_url = settings.DATABASE_URL.strip()
    
    # Si la chaîne contient des caractères bizarres, on les nettoie
    # Garder uniquement les caractères ASCII valides pour une URL
    import re
    if not re.match(r'^[a-zA-Z0-9\+\.\:\/\%\@\-\_\=\?&]+$', db_url):
        logger.warning("La chaîne de connexion contient des caractères non-ASCII. Nettoyage...")
        db_url = re.sub(r'[^\x00-\x7F]+', '', db_url)
        logger.info(f"URL nettoyée: {db_url}")
    
    engine = create_engine(
        db_url,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "client_encoding": "UTF8",
            "connect_timeout": 10
        }
    )
    
    @event.listens_for(engine, "connect")
    def set_client_encoding(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET client_encoding TO 'UTF8'")
        cursor.close()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    logger.info("Base de données configurée avec succès")
    
except Exception as e:
    logger.error(f"Erreur de configuration de la base de données: {e}")
    # Fallback sur SQLite pour le développement
    logger.warning("Utilisation de SQLite en fallback...")
    engine = create_engine("sqlite:///./sante_fianarantsoa.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()