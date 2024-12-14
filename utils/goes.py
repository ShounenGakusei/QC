import traceback
import numpy as np
import os
import time
from netCDF4 import Dataset
from utils.config import Config
from utils.logs import logger_qc
import GOES
from datetime import datetime, timedelta
import pyproj
from pyresample import utils
from pyresample.geometry import SwathDefinition
from pyresample import bilinear
import re

def schedule_download():
    """
    Función que ejecuta la tarea programada.
    Calcula la fecha actual menos 1 hora y realiza la petición al endpoint correspondiente.
    """
    # Obtener la fecha actual menos 1 hora en el formato esperado
    fecha = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d-%H')
    cGoes = GOESImageProcessor()
    filename = cGoes.download_image_goes(fecha+'-00')
    print({'error': cGoes.errors, 'valido' : cGoes.success, 'filename' : filename})

    
class GOESImageProcessor:
    def __init__(self):
        logger_qc.debug("Iniciando GOES class")
        self.errors = []  # Lista para almacenar errores
        self.success = True  # Indicador de éxito

    def validate_images_goes(self, filename):
        logger_qc.debug(f'Validando archivo de imagen : {filename}')
        if not os.path.exists(filename):
            logger_qc.info("Validacion Imagen (False): No existe el archivo")
            return False
        
        valido = True
        file_size = os.path.getsize(filename)

        creation_time = datetime.fromtimestamp(os.path.getctime(filename))
        logger_qc.debug(f'Fecha de creacion del archivo {creation_time}')
        logger_qc.debug(f'Tamañ del archvo {file_size}')
    
        if (datetime.now() - creation_time) > timedelta(minutes=10):
            if file_size < Config.MIN_IMAGE_SIZE:
                logger_qc.info("Validacion Imagen (False): El archivo es menor a 20mb y ya paso 10min desde su creacion")
                valido = False
            
        """
        Valida si el archivo GOES tiene la estructura esperada.
        Aquí debes implementar la lógica para validar la estructura del archivo.
        Retorna True si la estructura es válida, False en caso contrario.
        """
        try:
            # Lógica de validación de estructura del archivo GOES (reemplazar con validación real)
            # Ejemplo: Verifica si el archivo NetCDF tiene las variables esperadas.
            with Dataset(filename, 'r') as ds:
                logger_qc.debug(f'Leyendo file dataset', filename)
                # Recorrer los canales y tiempos definidos en Config
                for c in Config.CANALES:
                    if not valido:
                        break
                    for t in range(len(Config.TIEMPOS)-1,-1,-1):
                        # Comprobar si existe el grupo y la variable CMI para el canal y tiempo
                        group_name = f'{c}-{t}'
                        if group_name not in ds.groups:
                            logger_qc.info(f"Validacion Imagen (False): Archivo no tiene la esctructura esperada para {c}-{t}")
                            valido = False
                            break
                        
                        group = ds.groups[group_name]
                        if 'CMI' not in group.variables:
                            logger_qc.info(f"Validacion Imagen (False): Archivo no tiene CMI en {c}-{t}")
                            valido =  False
                            break

                        cmi_data = group.variables['CMI'][:].data
                        if np.isnan(cmi_data).all():
                            logger_qc.info(f"Validacion Imagen (False): Archivo solo tiene nulos en {c}-{t}")
                            valido =  False
                            break

        except Exception as e:
            # Si hay un error al abrir o leer el archivo, significa que no es válido
            logger_qc.info(f"Validacion Imagen (False): El archivo no tiene la estrucutra esperada {str(e)}")
            valido = False

        if not valido:
            test_ds = Dataset(filename, 'r', format='NETCDF4')
            test_ds.close()
            os.remove(filename)
        return valido

    def save_nc_file(self, filename, i, c, CMI, LonsCen, LatsCen):
        try:
            logger_qc.info(f"Guardando datos en {filename}, grupo {c}-{i}")
            f = Dataset(filename, 'a', format='NETCDF4')
            tmpGroup = f.createGroup(f'{c}-{i}')

            tmpGroup.createDimension('longitude', LonsCen.shape[1])
            tmpGroup.createDimension('latitude', LatsCen.shape[0])

            parameter01 = tmpGroup.createVariable('CMI', CMI.dtype.type, ('latitude', 'longitude'), zlib=True)
            parameter01[:, :] = CMI

            creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.setncattr('creation_date', creation_date)

            f.close()
        except Exception as e:
            self.errors.append(f"Error en save_nc_file ({c}-{i}): {e}")
            self.success = False
            logger_qc.error(f"Error al guardar archivo NetCDF: {e}")

    def reproject(self, CMI, LonCen, LatCen, LonCenCyl, LatCenCyl):
        try:
            logger_qc.info("Reproyectando datos")
            Prj = pyproj.Proj('+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +a=6378.137 +b=6378.137 +units=km')
            AreaID = 'cyl'
            AreaName = 'cyl'
            ProjID = 'cyl'
            Proj4Args = '+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +a=6378.137 +b=6378.137 +units=km'

            ny, nx = LonCenCyl.shape
            SW = Prj(LonCenCyl.min(), LatCenCyl.min())
            NE = Prj(LonCenCyl.max(), LatCenCyl.max())
            area_extent = [SW[0], SW[1], NE[0], NE[1]]

            AreaDef = utils.get_area_def(AreaID, AreaName, ProjID, Proj4Args, nx, ny, area_extent)
            SwathDef = SwathDefinition(lons=LonCen, lats=LatCen)

            CMICyl = bilinear.resample_bilinear(CMI, SwathDef, AreaDef, radius=6000, fill_value=np.nan, reduce_data=False)
            return CMICyl
        except Exception as e:
            self.errors.append(f"Error en reprojection: {e}")
            self.success = False
            logger_qc.error(f"Error al reproyectar: {e}")
            return None

    def conver_goes_date(self, fecha, hh=5, mm=0, reversa=False):
        if reversa:
            return fecha[0:4] + '-' + fecha[4:6] + '-' + fecha[6:8] + '-' + fecha[8:10] + '-' + fecha[10:12]
        else:
            f = datetime.strptime(fecha, "%Y-%m-%d-%H-%M") + timedelta(hours=hh, minutes=mm)
            return f'{f.year:04}{f.month:02}{f.day:02}-{f.hour:02}{f.minute:02}00'

    def save_coordinates(self, filename, LonCen, LatCen):
        try:
            logger_qc.info(f"Guardando coordenadas en {filename}")
            f = Dataset(filename, 'a', format='NETCDF4')
            tmpGroup = f.createGroup('coordenadas')
            tmpGroup.createDimension('longitude', LonCen.shape[1])
            tmpGroup.createDimension('latitude', LatCen.shape[0])

            lats_file = tmpGroup.createVariable('latitude', LatCen.dtype.type, ('latitude',))
            lons_file = tmpGroup.createVariable('longitude', LonCen.dtype.type, ('longitude',))

            lats_file[:] = LatCen[:, 0]
            lons_file[:] = LonCen[0, :]
            f.close()
        except Exception as e:
            self.errors.append(f"Error en save_coordinates: {e}")
            self.success = False
            logger_qc.error(f"No se pudo agregar las coordenadas: {e}")


    def clean_folder_if_exceeds_limit(self, folder_path,max_size, files_to_remove=12):
        """
        Limpia la carpeta si su tamaño total supera el límite especificado.
        
        Args:
            folder_path (str): Ruta de la carpeta a verificar.
            max_size (int): Tamaño máximo permitido en bytes.
            files_to_remove (int): Número de archivos más antiguos a eliminar si se excede el límite.
        """
        # Calcular el tamaño total de la carpeta
        total_size = 0
        files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path) and filename.endswith('.nc'):  # Solo archivos .nc
                files.append((file_path, os.path.getmtime(file_path)))  # Añadir la fecha de modificación
                total_size += os.path.getsize(file_path)  # Sumar el tamaño del archivo

        # Si el tamaño total excede el límite
        logger_qc.info(f"Espacio actual ocupado {len(files)} :  {total_size} de {max_size} en {folder_path}")

        if total_size > max_size:
            # Ordenar los archivos por fecha de modificación (antiguos primero)
            files.sort(key=lambda x: x[1])  # Ordenar por timestamp (getmtime)
            
            # Eliminar los archivos más antiguos
            for i in range(min(files_to_remove, len(files))):
                try:
                    os.remove(files[i][0])
                    #print(f"Archivo temporal eliminado por exceso de capacidad: {files[i][0]}")
                except Exception as e:
                    print(f"Error al eliminar el archivo temporal {files[i][0]}: {e}")


    def download_image_goes(self, fecha):
        logger_qc.debug(f'Iniciando meotdo download_image_goes')
        pattern = r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$'  # Formato: YYYY-MM-DD-HH-MM
        if not re.match(pattern, fecha):
            logger_qc.debug(f'No se ingreso el foromato adecuado de fecha: {fecha}')
            self.errors.append("Formato de fecha inválido. Use YYYY-MM-DD-HH-MM.")
            self.success = False
            return ''
            
        try:
            start_time = time.time()
            logger_qc.info(f"--------Iniciando descarga de imagen GOES para {fecha}")
            domain = Config.DOMAIN

            # Coordenadas iniciales
            pixresol = 2.0
            xmin, xmax = 80, 1030
            ymin, ymax = 700, 1900

            lat_cor = 14.0 + np.arange(3665) * (-pixresol / 111.0)
            lon_cor = -85.0 + np.arange(2945) * (pixresol / 111.0)
            lat_cen = lat_cor[:-1] - (pixresol / 2.0) / 111.0
            lon_cen = lon_cor[:-1] + (pixresol / 2.0) / 111.0
            lon_cor, lat_cor = np.meshgrid(lon_cor, lat_cor)
            lon_cen, lat_cen = np.meshgrid(lon_cen, lat_cen)
            lon_cor, lat_cor = lon_cor[ymin:ymax + 1, xmin:xmax + 1], lat_cor[ymin:ymax + 1, xmin:xmax]
            lon_cen, lat_cen = lon_cen[ymin:ymax, xmin:xmax], lat_cen[ymin:ymax, xmin:xmax]

            logger_qc.debug(f'Buscando arhcivo de imagen: {Config.IMAGEM_PATH}')
            filename = os.path.join(Config.IMAGEM_PATH,f'{fecha}.nc')
            logger_qc.debug(f'Buscando arhcivo de imagen: {filename}')
            if self.validate_images_goes(filename):               
                return filename
            else:
                self.errors.append(f"No se ha descargado aun la fecha {filename}")
                self.success = False
                return ''
            logger_qc.debug(f'Leyendo archivo dataset en : {filename}')
            f = Dataset(filename, 'w', format='NETCDF4')
            f.close()
            
            logger_qc.debug(f'Convirtiendo fecha del goes')
            fecha_ini = self.conver_goes_date(fecha, mm=-(10 * len(Config.TIEMPOS))) # TODO - len(p['tiempos'])
            fecha_fin = self.conver_goes_date(fecha, mm=10)

            temp_path = os.path.join(Config.IMAGEM_PATH,'dlImages/')
            logger_qc.debug(f'Carpeta temporal de imagenes: {temp_path}')

            logger_qc.debug(f'Limpiando limites de carpetas: {temp_path} - {Config.IMAGEM_PATH}')
            self.clean_folder_if_exceeds_limit(temp_path,Config.MAX_TEMP_FOLDER_SIZE, files_to_remove=len(Config.TIEMPOS)*len(Config.CANALES))
            self.clean_folder_if_exceeds_limit(Config.IMAGEM_PATH,Config.MAX_IMAGE_FOLDER_SIZE, files_to_remove=12)
            LonCen = None
            for c in Config.CANALES:
                logger_qc.debug(f'buscando imagenes de GOES canal: {c}')
                filesT = GOES.download('goes16', 'ABI-L2-CMIPF',
                                       DateTimeIni=fecha_ini, DateTimeFin=fecha_fin,
                                       channel=[c], rename_fmt='%Y%m%d%H%M%S', path_out=temp_path)

                if len(filesT) < len(Config.TIEMPOS):
                    logger_qc.debug(f'No se encontro suficientes imagenes para el canal')
                    self.errors.append(f"No se encontraron suficientes imágenes para el canal {c}")
                    self.success = False
                    os.remove(filename)
                    return ''

                for i in range(len(filesT)):
                    logger_qc.debug(f'Procesando tiempo {i} en canal {c}')
                    ds = GOES.open_dataset(filesT[len(filesT) - i - 1])

                    logger_qc.debug(f'Verificando tiempo y canales correctos')
                    if i == 0 and c == Config.CANALES[0] and Config.SAVE_IMAGES:
                        CMI, LonCen, LatCen = ds.image('CMI', lonlat='center', domain=domain)
                        domain_in_pixels = CMI.pixels_limits
                        mask = np.where(np.isnan(CMI.data) == True, True, False)
                        logger_qc.debug(f'Procesando cordenadas {i}-{c}')
                        self.save_coordinates(filename, lon_cen, lat_cen)
                    else:
                        CMI, _, _ = ds.image('CMI', lonlat='none', domain_in_pixels=domain_in_pixels, nan_mask=mask)

                    logger_qc.debug(f'reproyectando!')
                    CMICyl = self.reproject(CMI.data, LonCen.data, LatCen.data, lon_cen, lat_cen)
                    logger_qc.debug(f'Gaurdando en archov NC')
                    error_save = self.save_nc_file(filename, i, c, (CMICyl * 100).astype(np.int16), lon_cen, lat_cen)
                    if error_save:
                        os.remove(filename)
                        return ''

            logger_qc.info(f"Tiempo de procesamiento: {time.time() - start_time:.2f}s")
            return filename
        except Exception as e:
            traceback.print_exc()
            self.errors.append(f"Error en download_image_goes: {e}")
            self.success = False
            os.remove(filename)
