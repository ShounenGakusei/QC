import requests
import pytest
import csv

# Dirección de tu servicio Flask
BASE_URL = "http://localhost:5000/predict"

# Caso base válido
base_test_case = {
    'id' : 0,
    "fecha": "2024-11-27-15-00",
    "dato": "3",
    "longitud": "-80.0",
    "latitud": "-20.0",
    "altitud": "1000",
    "umbral": "8",
    "status": True
}

# Casos de prueba: usa el caso base y modifica solo lo necesario
test_cases = [
    {**base_test_case},
    {**base_test_case,'id':1 , "fecha": "asda", "status": False},  # Caso con fecha incorrecta
    {**base_test_case,'id':2 , "fecha": "2040-11-27-15-00", "status": False},  # Caso con fecha futura
    {**base_test_case,'id':3 , "dato": "-10", "status": False},  # Caso con dato numérico
    {**base_test_case,'id':4 , "longitud": "-90.0", "status": False},  # Caso con longitud incorrecta
    {**base_test_case,'id':5 , "latitud": "-30.0", "status": False},  # Caso con latitud incorrecta
    {**base_test_case,'id':6 , "umbral": "-10", "status": False},  # Caso con umbral negativo
    {**base_test_case,'id':7 , "dato": "70", "status": True}  # Caso válido (el último, sin cambios)
]



# Función para hacer la solicitud y verificar la respuesta
def test_predict_case(test_case):
    url = f"{BASE_URL}/{test_case['fecha']}/{test_case['dato']}/{test_case['longitud']}/{test_case['latitud']}/{test_case['altitud']}/{test_case['umbral']}"
    
    # Realiza la solicitud GET al endpoint
    response = requests.get(url)
    
    data = response.json()
    assert data['Status'] == test_case['status'], f'No se devolvio el estado estado'
    if not data['Status']:
        assert data['Flag'] == 'NC', f'El flag debe ser NC si el estado es False'
        assert len(data['Message'])  > 0 , 'No boto mensaje de error correcto!'
    
    # Preparamos los valores a guardar
    status = data['Status']
    mensaje = data['Message']
    
    return {
        "ID": test_case['id'],
        "Fecha": test_case['fecha'],
        "Dato": test_case['dato'],
        "Longitud": test_case['longitud'],
        "Latitud": test_case['latitud'],
        "Altitud": test_case['altitud'],
        "Umbral": test_case['umbral'],
        "Valor Esperado (Status)": test_case['status'],
        "Valor Devuelto (Status)": status,
        'Flag' : data['Flag'],
        "Mensaje Devuelto": mensaje
    }

# Función para guardar los resultados en un archivo CSV
def save_results_to_csv(results):
    headers = ['ID', 'Fecha', 'Dato', 'Longitud', 'Latitud', 'Altitud', 'Umbral', 
               'Valor Esperado (Status)', 'Valor Devuelto (Status)','Flag', 'Mensaje Devuelto']

    with open("resultados_pruebas.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        
        # Escribir los resultados
        for result in results:
            row = [
                result['ID'], result['Fecha'], result['Dato'], result['Longitud'], 
                result['Latitud'], result['Altitud'], result['Umbral'], 
                result['Valor Esperado (Status)'], result['Valor Devuelto (Status)'], 
                result['Flag'],result['Mensaje Devuelto']  # Ya es una cadena
            ]
            writer.writerow(row)

# Ejecutar las pruebas
def run_tests():
    results = []
    for test_case in test_cases:  # Ejecutar solo los primeros 2 casos para ejemplo
        result = test_predict_case(test_case)
        results.append(result)
        print(f"Test passed for {test_case['fecha']} / {test_case['dato']}")

    # Verificar los resultados antes de guardarlos
    print(results)
    
    # Guardar los resultados en archivo
    save_results_to_csv(results)
    print("Resultados guardados en 'resultados_pruebas.csv'")

if __name__ == "__main__":
    run_tests()
