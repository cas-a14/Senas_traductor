"""Utilidades de dibujo sobre la imagen de la cámara."""
import cv2


def dibujar_caja_delimitadora(imagen, puntos_mano, letra=None):
    """Dibuja una caja y una sola letra sobre la mano"""
    alto_imagen, ancho_imagen, _ = imagen.shape
    x_min, y_min = ancho_imagen, alto_imagen
    x_max, y_max = 0, 0

    for punto in puntos_mano.landmark:
        x = int(punto.x * ancho_imagen)
        y = int(punto.y * alto_imagen)

        x_min = min(x, x_min)
        y_min = min(y, y_min)
        x_max = max(x, x_max)
        y_max = max(y, y_max)

    margen = 20
    x_min = max(0, x_min - margen)
    y_min = max(0, y_min - margen)
    x_max = min(ancho_imagen - 1, x_max + margen)
    y_max = min(alto_imagen - 1, y_max + margen)

    # Dibujar el rectángulo alrededor de la mano
    cv2.rectangle(imagen, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

    # Dibujar una sola letra sobre la mano
    if letra and letra != "?":
        posicion_y = max(35, y_min - 10)
        cv2.putText(imagen, letra, (x_min, posicion_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 3)