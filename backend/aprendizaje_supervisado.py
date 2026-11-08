"""
Aprendizaje supervisado (lado ADMINISTRADOR): dataset etiquetado,
entrenamiento, evaluación y firma del modelo.

Solo lo usa admin.py. main.py nunca importa este archivo, así que esta
lógica (incluida la firma) no viaja dentro del ejecutable del usuario.
"""
import os
import csv
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

import seguridad
from deteccion import extraer_caracteristicas, ClasificadorSenas as ClasificadorBase
from config import RUTA_DATASET, RUTA_MODELO, MIN_MUESTRAS_POR_LETRA, NUM_CARACTERISTICAS


class ClasificadorSenas(ClasificadorBase):
    """Añade al clasificador básico la gestión del dataset y el entrenamiento."""

    def __init__(self):
        super().__init__()
        self.clave_privada = None  # la asigna admin.py tras autenticarse

    # ---------------- Dataset ----------------
    def guardar_muestras(self, muestras):
        """Agrega las muestras [(letra, vector), ...] al CSV (letra + 63 características)"""
        nuevo_archivo = not os.path.exists(RUTA_DATASET)
        with open(RUTA_DATASET, "a", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            if nuevo_archivo:
                escritor.writerow(["letra"] + [f"f{i}" for i in range(NUM_CARACTERISTICAS)])
            for letra, vector in muestras:
                escritor.writerow([letra] + [f"{v:.6f}" for v in vector])

    def cargar_dataset(self):
        """Lee el CSV y devuelve X (características) e y (etiquetas)"""
        if not os.path.exists(RUTA_DATASET):
            return None, None
        etiquetas, vectores = [], []
        with open(RUTA_DATASET, newline="", encoding="utf-8") as f:
            lector = csv.reader(f)
            next(lector, None)  # saltar encabezado
            for fila in lector:
                if len(fila) != NUM_CARACTERISTICAS + 1:
                    continue
                etiquetas.append(fila[0])
                vectores.append([float(v) for v in fila[1:]])
        if not etiquetas:
            return None, None
        return np.array(vectores, dtype=np.float32), np.array(etiquetas)

    # ---------------- Entrenamiento ----------------
    def entrenar(self):
        """
        Entrena RandomForest, evalúa con datos de prueba (20 %) y guarda y
        firma el modelo final entrenado con todos los datos.
        """
        try:
            X, y = self.cargar_dataset()
            if X is None:
                return (f"No existe el archivo '{RUTA_DATASET}' o está vacío.\n\n"
                        "Use 'Iniciar' y luego 'Grabar muestras' para capturar datos "
                        "etiquetados de cada letra.")

            letras, cuentas = np.unique(y, return_counts=True)
            if len(letras) < 2:
                return "Se necesitan muestras de al menos 2 letras distintas."
            if cuentas.min() < MIN_MUESTRAS_POR_LETRA:
                escasas = ", ".join(f"{l}({c})" for l, c in zip(letras, cuentas)
                                    if c < MIN_MUESTRAS_POR_LETRA)
                return (f"Hay letras con menos de {MIN_MUESTRAS_POR_LETRA} muestras: "
                        f"{escasas}.\nGrabe más muestras (se recomiendan 100 o más por letra).")

            X_ent, X_prueba, y_ent, y_prueba = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y)

            modelo = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            modelo.fit(X_ent, y_ent)

            pred = modelo.predict(X_prueba)
            exactitud = accuracy_score(y_prueba, pred)
            reporte = classification_report(y_prueba, pred, zero_division=0)
            print("\n===== Evaluación con datos de prueba =====")
            print(f"Exactitud: {exactitud:.3f}\n{reporte}")

            modelo_final = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            modelo_final.fit(X, y)
            joblib.dump(modelo_final, RUTA_MODELO)
            self.modelo = modelo_final

            nota_firma = "AVISO: el modelo NO se firmó (sin sesión de administrador)."
            if self.clave_privada is not None:
                seguridad.firmar_archivo_modelo(self.clave_privada)
                nota_firma = "Modelo firmado digitalmente."

            return (f"Letras: {len(letras)} | Muestras totales: {len(y)}\n"
                    f"Entrenamiento: {len(y_ent)} | Prueba: {len(y_prueba)}\n\n"
                    f"Exactitud en datos de prueba: {exactitud * 100:.1f} %\n\n"
                    f"Modelo guardado en '{RUTA_MODELO}'. {nota_firma}\n"
                    "El reporte completo por letra está en la consola.")
        except Exception as error:
            return f"Error durante el entrenamiento:\n{error}"