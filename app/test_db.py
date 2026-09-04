import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"URL: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Version PostgreSQL
        result = conn.execute(text("SELECT version()"))
        print(f"✅ PostgreSQL: {result.fetchone()[0]}")
        
        # Version PostGIS
        result = conn.execute(text("SELECT PostGIS_Version()"))
        print(f"✅ PostGIS: {result.fetchone()[0]}")
        
        # Fonctions PostGIS disponibles
        result = conn.execute(text("SELECT COUNT(*) FROM pg_proc WHERE proname LIKE '%postgis%'"))
        print(f"✅ Fonctions PostGIS: {result.fetchone()[0]}")
        
        # Créer une table de test
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS test_geometries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                geom GEOMETRY(Point, 4326)
            )
        """))
        print("✅ Table de test créée")
        
        # Insérer un point
        conn.execute(text("""
            INSERT INTO test_geometries (name, geom) 
            VALUES ('Test Point', ST_SetSRID(ST_MakePoint(47.5, -21.4), 4326))
        """))
        print("✅ Point inséré")
        
        # Lire le point
        result = conn.execute(text("""
            SELECT name, ST_AsText(geom) FROM test_geometries
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]}")
            
except Exception as e:
    print(f"❌ Erreur: {e}")