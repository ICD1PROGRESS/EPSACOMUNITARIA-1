import os
import streamlit as st
from pathlib import Path

# --- Rutas base del proyecto ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RECEIPTS_DIR_PATH = BASE_DIR / "recibos"
LOGOS_DIR = BASE_DIR / "data" / "logos"

# Asegurar que existan las carpetas necesarias
DATA_DIR.mkdir(parents=True, exist_ok=True)
RECEIPTS_DIR_PATH.mkdir(parents=True, exist_ok=True)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)

# --- Base de Datos (DETECTA AUTOMÁTICAMENTE) ---
_env_db = os.getenv("DATABASE_URL", "")
if _env_db and _env_db.strip().startswith("postgresql"):
    # PRODUCCIÓN: PostgreSQL
    DATABASE_URL = _env_db.strip()
    IS_PRODUCTION = True
elif _env_db and _env_db.strip().startswith("sqlite"):
    # DESARROLLO/DEMO: SQLite
    DATABASE_URL = _env_db.strip()
    IS_PRODUCTION = False
else:
    # Fallback a SQLite local
    DATABASE_URL = f"sqlite:///{DATA_DIR.as_posix()}/epsacol.db"
    IS_PRODUCTION = False

# --- Seguridad (JWT / Login) ---
SECRET_KEY = os.getenv("SECRET_KEY", "epsacol-clave-secreta-por-defecto-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 480

# --- Configuración EPSA ---
DEFAULT_LOGO_PATH = os.getenv("DEFAULT_LOGO_PATH", str(LOGOS_DIR / "default.png"))
RECEIPTS_DIR = os.getenv("RECEIPTS_DIR", str(RECEIPTS_DIR_PATH))

# --- Streamlit / Servidor ---
STREAMLIT_SERVER_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
STREAMLIT_SERVER_ADDRESS = os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")

# --- Modo Debug ---
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")

def get_current_epsa_id():
    """Retorna el ID de la EPSA actualmente seleccionada en la sesión."""
    return st.session_state.get("epsa_id")

def get_current_epsa_nombre():
    """Retorna el nombre de la EPSA actual (si se guardó en sesión)."""
    return st.session_state.get("epsa_nombre")

# --- Validación de seguridad (opcional) ---
if IS_PRODUCTION and SECRET_KEY == "epsacol-clave-secreta-por-defecto-2026":
    raise ValueError("❌ ERROR: En producción debes configurar SECRET_KEY real en variables de entorno.")

if not IS_PRODUCTION and SECRET_KEY == "epsacol-clave-secreta-por-defecto-2026":
    import warnings
    warnings.warn("⚠️ Usando SECRET_KEY por defecto. Cambia para producción.", RuntimeWarning)