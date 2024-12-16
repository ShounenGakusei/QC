import os

class Config:
    # Umbrales para la clasificación
    LOG_LEVEL = 'DEBUG'  # Nivel de logs: DEBUG, INFO, WARNING, ERROR
    LOG_FILE = 'app_logs.log'  # Archivo donde se guardan los logs
    MODEL_PATH = os.path.join(os.getcwd(), 'models', 'model.hdf5')
    IMAGEM_PATH = os.path.join(os.getcwd(), 'imagenes')
    STATION_PATH = os.path.join(os.getcwd(), 'static', 'stations_data.csv')
    SAVE_IMAGES = True
    CANALES = ["07", "08", "13"]
    TIEMPOS = ["00", "50", "40", "30", "20", "10"]
    
    PORT = 5000
    MIN_IMAGE_SIZE = (28 * 1024 * 1024) # 20 MB
    MAX_TEMP_FOLDER_SIZE = 3 * (480 * 1024 * 1024) # 480mb pro hora
    MAX_IMAGE_FOLDER_SIZE = 12 * (28 * 1024 * 1024) # 28MB por hora
    DOMAIN = [-88.0, -63.0, -25.0, 5.0]
    UMBRAL = 0.5

    SCHEDULER_API_ENABLED = True



