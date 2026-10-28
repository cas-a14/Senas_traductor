# Detector de Lenguaje de Señas

Aplicación de escritorio que reconoce **letras estáticas del lenguaje de señas (A–Z)** a partir de la posición de la mano frente a una cámara. Usa **MediaPipe** para detectar los 21 puntos de la mano y un modelo de **aprendizaje supervisado (Random Forest)** para clasificar la letra.

Proyecto de la materia *Reconocimiento de patrones sintáctico estructural* (L40648), Ingeniería en Sistemas Inteligentes, Centro Universitario UAEM Nezahualcóyotl.

**Integrantes:** Arias Pérez Casandra Guadalupe · Delis Monterrubio Esli Michelle
**Profesor:** Víctor Antonio Flores Lezama

---

## ¿Cómo funciona?

1. **OpenCV** captura el video de la cámara.
2. **MediaPipe Hands** detecta la mano y devuelve 21 puntos (landmarks).
3. Los puntos se centran en la muñeca y se normalizan por tamaño, lo que da un vector de **63 características** (x, y, z de cada punto).
4. El modelo **Random Forest** (scikit-learn), entrenado con muestras etiquetadas, predice la letra.
5. Si la confianza es menor a 0.60, la app muestra `?` en lugar de arriesgar una letra.

> **Alcance:** solo señas **estáticas**. Letras que implican movimiento (por ejemplo J y Z en algunos alfabetos) solo se reconocen por su postura inicial. No reconoce palabras ni frases.

---

## Estructura del proyecto

| Archivo | Descripción |
|---|---|
| `main.py` | Punto de entrada del **usuario**: solo detección. |
| `admin.py` | Punto de entrada del **administrador**: detección + grabación de muestras + entrenamiento (pide contraseña). |
| `interfaz.py` | Interfaz gráfica (Tkinter) y procesamiento de video. |
| `aprendizaje_supervisado.py` | Extracción de características, dataset, entrenamiento, evaluación y predicción. |
| `seguridad.py` | Contraseña de administrador y firma digital del modelo. |
| `dibujo.py` | Dibujo de la caja y la letra sobre la mano. |
| `config.py` | Rutas y parámetros (umbral de confianza, mínimo de muestras). |
| `requirements.txt` | Dependencias. |
| `modelo_senas.joblib` | Modelo entrenado. |
| `modelo_senas.joblib.sig` | Firma digital del modelo. |
| `clave_publica.pem` | Clave pública para verificar la firma. |
| `dataset_senas.csv` | Muestras etiquetadas (opcional; solo lo necesita quien reentrena). |

---

## Requisitos

- Python 3.9 – 3.12 (recomendado 3.10 o 3.11)
- Una cámara web
- En Linux, Tkinter: `sudo apt install python3-tk`

## Instalación

```bash
git clone https://github.com/cas-a14/Senas_traductor.git
cd Senas_traductor

# Opcional pero recomendado: entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r backend/requirements.txt
```

Las versiones de `mediapipe` y `scikit-learn` están fijadas en `requirements.txt`. La de scikit-learn debe coincidir con la que se usó para entrenar el modelo, porque un `.joblib` solo es seguro de cargar con esa misma versión.

---

## Uso (usuario)

```bash
python backend/main.py
```

1. Pulsa **Iniciar** para activar la cámara.
2. Muestra tu mano frente a la cámara y forma una letra.
3. La letra detectada aparece en el panel derecho y sobre la mano.
4. Pulsa **Detener** para terminar.

**Consejos:** buena iluminación, mano completa dentro del encuadre y fondo sin muchos objetos. Mientras no haya una seña reconocida, se muestra `?`.

---

## Modo administrador (entrenar el modelo)

```bash
python backend/admin.py
```

**Primera vez:** se te pide crear una contraseña (mínimo 8 caracteres). Se generan `clave_privada_admin.pem` (cifrada con tu contraseña) y `clave_publica.pem`.

**Entrenar:**

1. Pulsa **Iniciar**, elige una letra en el selector y pulsa **Grabar muestras**.
2. Forma la seña y muévela ligeramente (ángulo, distancia, inclinación) durante 10–20 segundos. Pulsa **Detener grabación y guardar**. Las muestras se agregan a `dataset_senas.csv` sin borrar las anteriores.
3. Repite para cada letra. El mínimo exigido es de 10 muestras por letra; se recomiendan **100 o más**, y una cantidad parecida en todas las letras.
4. Pulsa **Entrenar y evaluar modelo**. El programa reserva el 20 % de las muestras para evaluar, muestra la exactitud y el reporte por letra (en la consola), reentrena con todos los datos y guarda y **firma** el modelo.

Cada reentrenamiento parte de cero con todo el dataset, por lo que agregar muestras nuevas (otra mano, otras personas, otra iluminación) mejora el modelo. Si grabas con la mano izquierda, usa las mismas etiquetas que con la derecha.

> La exactitud mostrada se calcula con muestras de las mismas sesiones de grabación, por lo que puede ser optimista. Para una medición más honesta, graba una sesión aparte (otro día u otra persona) sin usarla para entrenar y pruébala.

---

## Seguridad

- **Contraseña de administrador:** la clave privada de firma está cifrada con ella. Sin la contraseña no se puede entrenar ni firmar modelos.
- **Modelo firmado:** cada modelo se firma con Ed25519. La app del usuario **verifica la firma antes de cargar** el modelo y lo rechaza si fue modificado. Esto importa porque los archivos `.joblib` pueden ejecutar código al abrirse.
- **Privacidad:** el video se procesa de forma local y no se guarda. El dataset solo contiene coordenadas de la mano, no imágenes.
- **Nunca subas `clave_privada_admin.pem`:** ya está en el `.gitignore`. Guarda una copia de respaldo fuera del repositorio.
- Quien clone el repositorio puede modificar su propia copia del código, pero no puede firmar un modelo como si fuera del administrador.

Si se filtra la clave privada: genera claves nuevas, vuelve a firmar el modelo y sube la nueva `clave_publica.pem`.

---

## Solución de problemas

| Problema | Posible solución |
|---|---|
| "El modelo no tiene una firma válida" | El `.joblib` y el `.sig` no corresponden. Descarga ambos de nuevo, o entrena con `python backend/admin.py`. |
| "No se encontró el modelo entrenado" | Falta `modelo_senas.joblib` en la carpeta del proyecto. |
| No abre la cámara | Cierra otras aplicaciones que la usen. Si tienes varias cámaras, cambia el índice en `cv2.VideoCapture(0)` (en `interfaz.py`). |
| `AttributeError: module 'mediapipe' has no attribute 'solutions'` | Instala la versión fijada: `pip install mediapipe==0.10.14`. |
| Error o aviso al cargar el modelo | La versión de scikit-learn no coincide con la del entrenamiento. Instala la de `requirements.txt`. |
| Muchas letras salen como `?` | Faltan muestras o hay poca variedad. Graba más y reentrena. |

---

## Tecnologías y licencias

| Librería | Uso | Licencia |
|---|---|---|
| Python (Tkinter, Threading, Queue, Time) | Lenguaje e interfaz | PSF License |
| OpenCV | Captura y procesamiento de video | Apache 2.0 |
| MediaPipe | Detección de la mano (21 landmarks) | Apache 2.0 |
| scikit-learn | Modelo Random Forest y evaluación | BSD 3-Clause |
| joblib | Guardado y carga del modelo | BSD 3-Clause |
| NumPy | Operaciones numéricas | BSD 3-Clause |
| Pillow | Imágenes en la interfaz | HPND (MIT-CMU) |
| cryptography | Firma digital y cifrado de la clave | Apache 2.0 o BSD |

## Trabajo futuro

- Reconocimiento de señas con movimiento (secuencias de fotogramas).
- Reconocimiento de palabras y frases.
- Pruebas automáticas y medición formal de exactitud con personas distintas a las del entrenamiento.
