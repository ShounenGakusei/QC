import tensorflow as tf
import logging

from utils.config import Config

class QCModel:
    model = None
    errors = {}
    valido = True

    def __init__(self):
        try:
            self.model = tf.keras.models.load_model(Config.MODEL_PATH)
            logging.info("Modelo cargado exitosamente.")
        except Exception as e:
            logging.error(f"Error al cargar el modelo: {e}")
            raise

    def predecir_unitario(self, fecha, estacion, precipitacion):
        return {'hola' : 'prueba' , 'fecha' : fecha, 'estacion' : estacion, 'precipitacion' : precipitacion}

    def predecir_masivo(self, ):
        pass
