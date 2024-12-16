from datetime import datetime, timedelta
import os

import GOES
from utils.config import Config
"""
class WebsiteUser(HttpUser):
    #wait_time = between(1, 6000)

    #@task(10)
    def test_2(self):
        self.client.get("/predecir?dato=0.4")
        
    #@task(1)
    def test1(self):
        self.client.get("/predecir?dato=0.4&fecha=2022-01-31-12-00")

    #@task(1)
    def test2(self):
        self.client.get("/predecir?dato=0.4&fecha=2022-01-31-14-00")

    #@task(1)
    def test3(self):
        self.client.get("/predecir?dato=0.4&fecha=2022-01-31-16-00")
"""
def download_goes():
    f = datetime.strptime('2022-01-31-16-00', "%Y-%m-%d-%H-%M") + timedelta(hours=5, minutes=0)
    f2 = datetime.strptime('2022-01-31-16-00', "%Y-%m-%d-%H-%M") + timedelta(hours=6, minutes=0)
    temp_path = os.path.join(Config.IMAGEM_PATH,'dlImages/')
    fecha_ini =  f'{f.year:04}{f.month:02}{f.day:02}-{f.hour:02}{f.minute:02}00'
    fecha_fin =  f'{f2.year:04}{f2.month:02}{f2.day:02}-{f2.hour:02}{f2.minute:02}00'
    filesT = GOES.download('goes16', 'ABI-L2-CMIPF',
            DateTimeIni=fecha_ini, DateTimeFin=fecha_fin,
            channel=['13'], rename_fmt='%Y%m%d%H%M%S', path_out=temp_path)
    
    print(filesT)
    try:
        os.remove(filesT)
    except:
        pass
    return

download_goes()