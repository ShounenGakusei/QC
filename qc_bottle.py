from bottle import Bottle, run, request, response
import os
import time

from utils.goes import GOESImageProcessor

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

# Ruta para mostrar el estado de la API
@app.route('/status', method='GET')
def status():
    return {'status': 'API funcionando correctamente'}

# Ejecutar el servidor
if __name__ == "__main__":
    run(app, host='0.0.0.0', port=8080)
