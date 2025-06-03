import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pos_user:pos_password@postgres:5432/pos_system"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Créer toutes les tables de la base de données"""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Obtenir une session de base de données"""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise
