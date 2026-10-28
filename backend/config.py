"""Configuración y parámetros globales del detector de señas."""
import os

# Carpeta del proyecto: las rutas funcionan en cualquier equipo/clon del repositorio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_DATASET = os.path.join(BASE_DIR, "dataset_senas.csv")
RUTA_MODELO = os.path.join(BASE_DIR, "modelo_senas.joblib")  # modelo entrenado   # modelo entrenado (lo usa todo el mundo)
UMBRAL_CONFIANZA = 0.60                 # por debajo de esto se muestra "?"
MIN_MUESTRAS_POR_LETRA = 10             # mínimo para poder entrenar/evaluar
NUM_CARACTERISTICAS = 63                # 21 landmarks x (x, y, z)

# --- Seguridad ---
RUTA_FIRMA = RUTA_MODELO + ".sig"                                   # firma del modelo (SÍ se sube a git)
RUTA_CLAVE_PUBLICA = os.path.join(BASE_DIR, "clave_publica.pem")    # verifica la firma (SÍ se sube a git)
RUTA_CLAVE_PRIVADA = os.path.join(BASE_DIR, "clave_privada_admin.pem")  # NUNCA se sube a git
MIN_LONGITUD_CONTRASENA = 8