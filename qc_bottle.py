from bottle import Bottle, run, request, response
import os
import time
from datetime import datetime, timedelta
from utils.goes import GOESImageProcessor
import threading

# Crear una instancia de la aplicación Bottle
app = Bottle()

# Ruta para la raíz de la API (opcional, solo para verificar si el servidor está funcionando)
@app.route('/')
def home():
    return "¡Hola, mundo! API de Bottle está funcionando."

# Ruta para descargar una imagen GOES (según tu código, esta es una acción importante)
@app.route('/download_image', method='GET')
def download_image():
    fecha = request.query.fecha  # Obtiene la fecha del parámetro 'fecha' en la consulta URL
    if not fecha:
        response.status = 400  # Bad Request
        return {'error': 'Falta el parámetro de fecha en la solicitud.'}

    # Instanciamos tu clase GOESImageProcessor
    cGoes = GOESImageProcessor()
    filename = cGoes.download_image_goes(fecha)
    
    if filename:
        return {'status': 'success', 'filename': filename}
    else:
        response.status = 500  # Internal Server Error
        return {'error': 'Hubo un problema al descargar la imagen.'}

# Variable para controlar la ejecución
task_running = False
last_run_time = None
task_thread = None

# Función para ejecutar la tarea
def execute_task():
    global task_running, last_run_time, task_thread

    # Actualizar el tiempo de inicio
    last_run_time = datetime.now()
    task_running = True

    # Obtener la fecha de la imagen (1 hora antes)
    fecha = (last_run_time - timedelta(hours=1)).strftime("%Y%m%d%H%M")
    
    # Ejecutar la tarea
    cGoes = GOESImageProcessor()
    try:
        cGoes.download_images_goes(fecha)
    except Exception as e:
        print(f"Error al descargar la imagen: {e}")
    finally:
        task_running = False
        task_thread = None


# Planificar la tarea periódica
def schedule_task():
    global task_running, task_thread, last_run_time

    while True:
        # Si no se está ejecutando, iniciar una nueva tarea
        if not task_running:
            task_thread = threading.Thread(target=execute_task)
            task_thread.start()
        
        # Si la tarea dura más de 30 minutos, forzar reinicio
        if task_running and last_run_time:
            elapsed_time = (datetime.now() - last_run_time).total_seconds()
            if elapsed_time > 1800:  # 30 minutos
                print("Tarea durando demasiado, forzando reinicio...")
                task_thread.join(timeout=1)
                task_running = False
                task_thread = None
        
        # Esperar 10 minutos antes de verificar nuevamente
        time.sleep(600)


# Iniciar la tarea programada en un hilo separado
task_scheduler = threading.Thread(target=schedule_task, daemon=True)
task_scheduler.start()


@app.route('/')
def home():
    return "¡Hola, mundo! API de Bottle está funcionando."


@app.route('/status', method='GET')
def status():
    global task_running, last_run_time
    status = {
        'task_running': task_running,
        'last_run_time': last_run_time.strftime("%Y-%m-%d %H:%M:%S") if last_run_time else "Nunca"
    }
    return status


# Ejecutar el servidor
if __name__ == "__main__":
    run(app, host='0.0.0.0', port=8080)
