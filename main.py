from flask import Flask, render_template, request, jsonify
import numpy as np
import tensorflow as tf
from utils.config import Config
from utils.goes import GOESImageProcessor, schedule_download
from flask_apscheduler import APScheduler
from utils.predict import Predict_Model


app = Flask(__name__,static_folder='static')
scheduler = APScheduler()
scheduler.api_enabled = True
try:
    model = tf.keras.models.load_model(Config.MODEL_PATH)
except Exception as e:
    model = None
    print('ERROR AL INICAR EL MODELO !')
is_running = False


@app.route('/')
def home():
    #schedule_download()
    return render_template('index.html')
    
@app.route('/predict/<fecha>/<codigo>/<dato>', methods=['GET'])
def predict(fecha, codigo, dato):
    print('INICIO DE PREDICCION...')
    output_data, input_data  = Predict_Model(model).get_prediction( fecha, codigo, dato)

    return jsonify(output_data)

@app.route('/download-goes/<fecha>', methods=['GET','POST'])
def download_goes_data(fecha):
    cGoes = GOESImageProcessor()
    filename = cGoes.download_image_goes(fecha)
    return jsonify({'error': cGoes.errors, 'valido' : cGoes.success, 'filename' : filename})
 

@scheduler.task("interval", id="do_job_1", seconds=15*60)
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



if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    #setup_logging()
    app.run(debug=True,port=Config.PORT, threaded=False, host='0.0.0.0')
