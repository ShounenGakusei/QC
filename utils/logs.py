import logging
from utils.config import Config
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger('SistemaQC')
    if not logger.hasHandlers():
        # Configuración de logs
        log_level = Config.LOG_LEVEL
        log_file = Config.LOG_FILE

        # Manejo de archivos con rotación
        file_handler = RotatingFileHandler(
            log_file, maxBytes=1*1024*1024, backupCount=2  # 5MB por archivo, 3 backups
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))

        logger.setLevel(log_level)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

# Configura el logger al importar este módulo
logger_qc = setup_logging()
