import traceback
import pandas as pd
import tensorflow as tf
from utils.logs import logger_qc
from utils.config import Config
import logging
from netCDF4 import Dataset
from utils.goes import GOESImageProcessor
import numpy as np

def getPosMap(x, array):
    pos = -1
    for i in range(len(array)):
        if abs(array[i] - x) <= 0.01:
            pos = i
    return pos

def findStationCoords(lons, lats, cordX, cordY):
    x = getPosMap(cordX, lons)
    y = getPosMap(cordY, lats)
    return x, y


class Predict_Model():  
    def __init__(self, model):
        self.errors = []  # Lista para almacenar errores
        self.success = True  # Indicador de éxito
        self.model = model
        self._get_station_data()
        self._get_model_params()

    def _get_imagen_data(self, filename, lon, lat):
        if not self.success:
            return {}
        
        data = []
        try:
            ds = Dataset(filename)
            coord = ds.groups['coordenadas']
            lats = coord['latitude'][:].data
            lons = coord['longitude'][:].data

            x, y = findStationCoords(lons, lats, lon, lat)

            margen = int(self.input_shapes[0][2] / 2)
            for i in range(self.input_shapes[0][1]-1,-1,-1):
                canalImages = []
                for c in Config.CANALES:
                    cmis = ds.groups[f'{c}-{i}']
                    cmi = cmis.variables['CMI'][:].data.astype(np.uint16)
                    cropedImg = cmi[y - margen:y + margen, x - margen:x + margen]
                    canalImages.append(cropedImg)

                data.append(np.dstack(canalImages))

            data = np.stack(data, axis=0)

            ds.close()
        except Exception as e:
            ds.close()
            traceback.print_exc()
            logger_qc.error(f"Error al obtener imgaen data: {e}")
            self.errors.append(f"Error al obtener imgaen data: {e}")
            self.success = False
            return [0]
        return data

    def _get_model_params(self):
        if not self.model:
            self.valido = False
            return 
        
        self.inputLayers = []
        self.input_shapes = []
        config = self.model.get_config()
        for layer in config['layers']:
            if layer['class_name'] == 'InputLayer':
                self.inputLayers.append(layer['name'])
                self.input_shapes.append(layer['config']['batch_input_shape'])

    def _get_station_data(self):
        if not self.success:
            return {}
        
        try:
            self.stations = pd.read_csv(Config.STATION_PATH).set_index('CODE').to_dict(orient='index')
        except Exception as e:
            self.errors.append(f"Error en abrir el archivo de estaciones: {Config.STATION_PATH}-{str(e)}")
            self.success = False
            logger_qc.error(f"Error en abrir el archivo de estaciones: {Config.STATION_PATH}-{str(e)}")
            return {}
        

    def _get_model_data(self):        
        if not self.success:
            return {}
        
        try:
            data_station = self.stations[self.station]
        except KeyError:
            self.errors.append(f"No se encontró la estacion en la base {self.station}")
            self.success = False
            logger_qc.error(f"No se encontró la estacion en la base {self.station}")
            return {}
        
        result =  {
            'alt' : data_station['ALT'],
            'umb1' : data_station['Umbral1'], 
            'coordLon':float(data_station['LON']), 
            'coordLat':float(data_station['LAT']),
            'value' : self.value
        }
    
        cGoes = GOESImageProcessor()
        self.filename = cGoes.download_image_goes(self.fecha)
        if not cGoes.success:
            self.errors.append(f"Error en obtener imagen GOES para fecha {self.fecha}: {str(cGoes.errors)}")
            self.success = False
            logger_qc.error(f"Error en obtener imagen GOES para fecha {self.fecha}: {str(cGoes.errors)}")
        result['imagen_file'] = self.filename
        return result

    def _get_model_result(self, data):
        if not self.success:
            return -1, 'NC'
    
        try:
            prediction = self.model.predict({self.inputLayers[0]: np.full((1, data['imagen'].shape[0], data['imagen'].shape[1],
                                                    data['imagen'].shape[2], data['imagen'].shape[3]),
                                                    data['imagen']),
                        self.inputLayers[1]: np.full((1,), float(data['value'])), # 2
                        self.inputLayers[3]: np.full((1,), float(data['alt'])), #3
                        self.inputLayers[2]: np.full((1,), float(data['umb1'])) # 1
                        }, verbose=0)
        except Exception as e:
            traceback.print_exc()
            self.errors.append(f"Error en prediccion del modelo: {str(e)}")
            self.success = False
            logger_qc.error(f"Error en prediccion del modelo: {str(e)}")
            return -1 , 'NC'       
        pred_value = round(float(prediction[0]),4)
        return pred_value, 'C' if pred_value >= Config.UMBRAL else 'M'
    
    def get_prediction(self, fecha, station, value):
        logger_qc.info(f"Iniciando prediccion :  {fecha} - {station} - {value}")
        response = {}
        self.fecha = fecha
        self.station = station
        self.value = value

        self.filename = ''
        
        try:
            self.value = float(value)
            if self.value < 0:
                self.errors.append(f'El valor de precipitacin debe ser positivo: {self.value}')    
                self.success = False
        except ValueError:
            self.errors.append(f'El dato de precipitacion no se peude convertir a float: {self.value}')
            self.success = False


        # Validamos la data
        input_model = self._get_model_data()
        if self.success:
            input_model['imagen'] = self._get_imagen_data(self.filename, input_model['coordLon'], input_model['coordLat'])
        
        prediction, pred_text = self._get_model_result(input_model)

        if self.success:
            response = {'Flag': pred_text, 'Message': self.errors, 
                                'parametros': {'Dato': self.value,
                                                'Fecha': self.fecha,
                                                'station' : self.station,
                                                'Longitud': input_model['coordLon'],
                                                'Latitud': input_model['coordLat'],
                                                'altitud': input_model['alt'],
                                                'per90': input_model['umb1'],},
                'Status': self.success, 'Probability': prediction*100
                }
            
            colores = {'NC': 'grey', 'C': 'green', 'M': 'yellow'}
            response['color'] = colores[response['Flag']]
        else:
            response = {'Flag' : 'NC', 'Message' : self.errors, 'parametros' : {'Dato': self.value,
                                                'Fecha': self.fecha,'station' : self.station}
                                                , 'Status' : False, 'Probability' : 0}

        return response ,input_model

