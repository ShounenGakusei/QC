from flask import Flask, render_template, request, jsonify
import numpy as np
import tensorflow as tf
from utils.goes import GOESImageProcessor, schedule_download
from flask_apscheduler import APScheduler
from utils.predict import Predict_Model
from utils.config import Config
import os

app = Flask(__name__,static_folder='static')
#scheduler = APScheduler()
#scheduler.api_enabled = True
try:
    model = tf.keras.models.load_model(os.path.join(Config.MODEL_PATH, 'model_v3.hdf5'))

except Exception as e:
    model = None
    print('ERROR AL INICAR EL MODELO !', str(e))
is_running = False


def check_config():
    print(f'PARAMETROS INCIALES DEL SISTEMA! ')
    for attribute, value in vars(Config).items():
        print(f'{attribute}: {value}')

check_config()

@app.route('/')
def home():
    #schedule_download()
    return render_template('index.html')

# Ruta para verificar las imágenes
@app.route('/check_images', methods=['GET'])
def check_files():
    # Directorio donde se encuentran las imágenes
    folder_path = Config.IMAGEM_PATH

    # Verificar si la ruta es válida
    if not os.path.exists(folder_path):
        return jsonify({"error": "El directorio no existe"}), 404

    # Obtener todos los archivos del directorio
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    result = []
    cGoes = GOESImageProcessor()

    # Validar las imágenes
    for file in files:
        file_path = os.path.join(folder_path, file)
        if cGoes.validate_images_goes(file_path):  # Verifica si la imagen es válida
            result.append(file[:-3])  # Añadir al resultado si es válida

    # Regresar los archivos existentes y válidos
    if result:
        return jsonify({"Imagenes descargadas": result}), 200
    else:
        return jsonify({"message": "No se encontraron imágenes válidas."}), 404


    
@app.route('/predict/<fecha>/<dato>/<longitud>/<latitud>/<altitud>/<umbral>', methods=['GET'])
def predict(fecha, dato, longitud, latitud, altitud, umbral):
    print('INICIO DE PREDICCION...')
    output_data, input_data  = Predict_Model(model).get_prediction( fecha, dato, longitud, latitud, altitud, umbral)

    return jsonify(output_data)

@app.route('/download-goes/<fecha>', methods=['GET','POST'])
def download_goes_data(fecha):
    cGoes = GOESImageProcessor()
    filename = cGoes.download_image_goes(fecha)
    return jsonify({'error': cGoes.errors, 'valido' : cGoes.success, 'filename' : filename})

@app.route('/predict-ui', methods=['GET', 'POST'])
def predict_ui():
    if request.method == 'GET':
        return render_template('index.html')

    # Obtener datos del formulario
    fecha = request.form.get('fecha', default='default', type=str)
    dato = request.form.get('dato', default='-1', type=str)
    latitud = request.form.get('latitud', default='0.0', type=str)
    longitud = request.form.get('longitud', default='0.0', type=str)
    altitud = request.form.get('altitud', default='0', type=str)
    umbral = request.form.get('umbral', default='0', type=str)

    # Realizar la predicción con el modelo
    try:
        output_data, input_data = Predict_Model(model).get_prediction(
            fecha, dato, longitud, latitud, altitud, umbral
        )
    except Exception as e:
        return render_template('error.html', error=str(e))  # Manejo de errores

    # Renderizar el resumen de predicción
    return render_template('prediccion-resumen.html', output=output_data, input=input_data)


#@scheduler.task("interval", id="do_job_1", seconds=15*60)
def goes_download_schedule():
    global is_running
    if is_running:  # Si la tarea ya está en ejecución, no hacer nada
        print("La tarea ya está en ejecución. Ignorando nueva ejecución.")
        return
    try:
        is_running = True  # Marcar la tarea como en ejecución
        print("Ejecutando la tarea de descarga GOES")
        schedule_download()  # Aquí va tu lógica de descarga
    finally:
        is_running = False  # Marcar la tarea como terminada, para que pueda ejecutarse nuevamente en el siguiente ciclo

@app.route('/view-logs', methods=['GET'])
def view_logs():
    log_file_path = 'app_logs.log'  # Ruta al archivo de logs
    try:
        # Leer las últimas 200 líneas del archivo
        with open(log_file_path, 'r') as log_file:
            lines = log_file.readlines()
            last_200_lines = lines[-200:]  # Obtener las últimas 200 líneas

        # Formatear las líneas para mostrarlas en HTML
        formatted_logs = ''.join(last_200_lines).replace('\n', '<br>')
        return render_template('view_logs.html', logs=formatted_logs)

    except FileNotFoundError:
        return render_template('view_logs.html', logs="El archivo de logs no se encontró.")
    except Exception as e:
        return render_template('view_logs.html', logs=f"Error al leer los logs: {str(e)}")



if __name__ == '__main__':
    #scheduler.init_app(app)
    #scheduler.start()
    #setup_logging()
    app.run(debug=True,port=Config.PORT, threaded=False, host='0.0.0.0')
