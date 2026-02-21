import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    # Local: usa SQLite (arquivo local.db na pasta do projeto)
    # Railway: você vai usar DATABASE_URL do Postgres depois.
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pasta onde os PDFs ficam localmente
    STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.abspath("./data"))

    # Expiração em dias
    RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "10"))