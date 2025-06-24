import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pos_user:pos_password@postgres:5432/pos_system"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def wait_for_db(max_retries=30, delay=1):
    """Attendre que la base de données soit disponible"""
    for attempt in range(max_retries):
        try:
            # Essayer de se connecter à la base de données
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Base de données disponible!")
            return True
        except OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Tentative {attempt + 1}/{max_retries}: Base de données non disponible, attente {delay}s...")
                time.sleep(delay)
            else:
                print(f"Impossible de se connecter à la base de données après {max_retries} tentatives")
                raise e
    return False


def create_tables():
    """Créer toutes les tables de la base de données"""
    wait_for_db()
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Obtenir une session de base de données"""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise
