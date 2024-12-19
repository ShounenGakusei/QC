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

@app.route('/predict-ui', methods=['GET','POST'])
def predict_ui():
    if request.method == 'GET':
        return render_template('index.html')
 
    fecha = request.form.get('fecha', default='default', type=str)
    codigo = request.form.get('codigo', default='default', type=str)
    dato = request.form.get('dato', default='-1', type=str)

    #data = model.predecir_unitario(fecha, codigo, dato)
    output_data, input_data  = Predict_Model(model).get_prediction( fecha, codigo, dato)
    
    """
    if output_data['Status'] and (type(input_data['imagen']) == np.ndarray):
        input_data['imagen'] = np.transpose(input_data['imagen'], (0, 3, 1, 2))
        fig = px.imshow(input_data['imagen'], animation_frame=0, facet_col=1, binary_string=True, labels={'facet_col': 'CANAL'})
        plot_div = fig.to_html(full_html=False)
        return render_template('prediccion-resumen.html', plot_div=plot_div, output=output_data)
    else:
        return render_template('prediccion-resumen.html', output=output_data)
    """
    return render_template('prediccion-resumen.html', output=output_data)

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



if __name__ == '__main__':
    #scheduler.init_app(app)
    #scheduler.start()
    #setup_logging()
    app.run(debug=True,port=Config.PORT, threaded=False, host='0.0.0.0')
