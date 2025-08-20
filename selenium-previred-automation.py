# ----------------------------------------------
# Script: PRIVADO 
# SE OMITIERON ALGUNAS COSAS PRIVADAS DE FLUJOS INTERNOS (ES UN EJEMPLO)
# Autor: AlexST360
# Función: Automatiza la carga de movimientos de personal
#          en Previred y descarga comprobantes por trabajador.
# Herramientas: Python, Selenium, pandas
# ----------------------------------------------

import os                  # Para manejo de rutas y archivos
import time                # Para pausas temporales
import shutil              # Para mover/copiar archivos
import logging             # Para logs de ejecución
import configparser        # Para leer archivo de configuración
import pandas as pd        # Para manejar datos de Excel
from datetime import datetime, timedelta  # Para fechas dinámicas
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# -------------------------------------------------------
# CONFIGURACIÓN DEL PROYECTO
# -------------------------------------------------------

# Crear objeto para leer archivo config.ini
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")  # Archivo externo con rutas y credenciales

# Rutas de trabajo
RUTA_IMP = config["rutas"]["IMP"]          # Carpeta de entrada de archivos
RUTA_DESCARGAS = config["rutas"]["descargas"]  # Carpeta donde se guardan los PDFs

# Credenciales y URL Previred
PREVIRED_URL = config["previred"]["url"]
USUARIO = config["previred"]["usuario"]
CLAVE = config["previred"]["clave"]

# Configuración de logs para seguimiento de ejecución
logging.basicConfig(
    filename="ingreso_movimiento_personal.log",  # Archivo de log
    level=logging.INFO,                          # Nivel de logs INFO
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# -------------------------------------------------------
# FUNCIONES AUXILIARES
# -------------------------------------------------------

def iniciar_driver():
    """
    Inicializa el navegador Chrome con Selenium
    y configura la carpeta de descargas.
    """
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Abrir maximizado

    # Configurar carpeta de descargas automática
    prefs = {"download.default_directory": RUTA_DESCARGAS}
    chrome_options.add_experimental_option("prefs", prefs)

    # Ruta del ChromeDriver
    service = Service("chromedriver.exe")

    # Crear instancia del navegador
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_previred(driver):
    """
    Realiza el login en Previred usando usuario y clave
    desde el archivo config.ini
    """
    driver.get(PREVIRED_URL)  # Abrir URL de Previred

    # Esperar que el input de usuario esté disponible y enviar usuario
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "usuario"))
    ).send_keys(USUARIO)

    # Ingresar contraseña
    driver.find_element(By.ID, "clave").send_keys(CLAVE)

    # Click en botón ingresar
    driver.find_element(By.ID, "btnIngresar").click()

    logging.info("Login exitoso en Previred")  # Log para seguimiento

def cargar_archivo_movimientos(driver, archivo_txt):
    """
    Carga un archivo de movimientos de personal en Previred
    y confirma la carga
    """
    # Ir a módulo "Movimientos de Personal"
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Movimientos de Personal"))
    ).click()

    # Subir archivo .txt
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "fileInput"))
    ).send_keys(archivo_txt)

    # Click en botón "Cargar"
    driver.find_element(By.ID, "btnCargar").click()
    logging.info(f"Archivo cargado: {archivo_txt}")

    # Confirmar la carga
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "btnConfirmar"))
    ).click()
    logging.info("Carga confirmada")

def generar_comprobantes(driver, excel_path):
    """
    Genera comprobantes por trabajador a partir de un Excel
    con RUT y Código de Movimiento
    """
    # Leer archivo Excel con pandas
    df = pd.read_excel(excel_path)

    # Obtener lista de RUTs únicos para no duplicar procesos
    rut_unicos = df["RUT"].drop_duplicates()

    # Iterar por cada fila del Excel
    for _, row in df.iterrows():
        rut = str(row["RUT"]).strip()          # RUT trabajador
        cod_mov = str(row["CodMov"]).strip()   # Código de movimiento
        afp = str(row.get("AFP", "")).strip()  # AFP si existe
        afc = str(row.get("AFC", "")).strip()  # AFC si existe

        try:
            # Entrar al módulo "Comprobante por Trabajador"
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Comprobante por Trabajador"))
            ).click()

            # Ingresar RUT en el formulario
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "rutTrabajador"))
            ).clear()
            driver.find_element(By.ID, "rutTrabajador").send_keys(rut)

            # Seleccionar todas las AFP
            driver.find_element(By.ID, "afpSelect").send_keys("Todas")

            # Configurar fechas dinámicas (hoy y mañana)
            hoy = datetime.today().strftime("%d/%m/%Y")
            manana = (datetime.today() + timedelta(days=1)).strftime("%d/%m/%Y")
            driver.find_element(By.ID, "fechaDesde").send_keys(hoy)
            driver.find_element(By.ID, "fechaHasta").send_keys(manana)

            # Click en botón "Generar" para crear comprobante PDF
            driver.find_element(By.ID, "btnGenerar").click()
            time.sleep(5)  # Pausa para que PDF se descargue

            # Renombrar PDF y mover a carpeta correspondiente
            nombre_pdf = f"{rut}_{cod_mov}.pdf"
            origen = os.path.join(RUTA_DESCARGAS, "comprobante.pdf")  # PDF descargado
            destino_carpeta = os.path.join(RUTA_DESCARGAS, "AFP" if afp else "AFC")
            os.makedirs(destino_carpeta, exist_ok=True)
            destino = os.path.join(destino_carpeta, nombre_pdf)

            if os.path.exists(origen):
                shutil.move(origen, destino)  # Mover PDF
                logging.info(f"Comprobante guardado: {destino}")

                # Si tiene AFP y AFC, copiar también a otra carpeta
                if afp and afc:
                    destino2 = os.path.join(RUTA_DESCARGAS, "AFC", nombre_pdf)
                    shutil.copy(destino, destino2)
                    logging.info(f"Comprobante también copiado a: {destino2}")

        except Exception as e:
            logging.error(f"Error generando comprobante para {rut}: {e}")

# -------------------------------------------------------
# FLUJO PRINCIPAL
# -------------------------------------------------------
if __name__ == "__main__":
    driver = iniciar_driver()  # Abrir navegador
    try:
        login_previred(driver)  # Hacer login en Previred

        # Ejemplo de procesamiento de un archivo de prueba
        archivo_txt = os.path.join(RUTA_IMP, "empresa1", "movimientos.txt")
        cargar_archivo_movimientos(driver, archivo_txt)

        # Generar comprobantes según Excel de trabajadores
        excel_path = os.path.join(RUTA_IMP, "empresa1", "trabajadores.xlsx")
        generar_comprobantes(driver, excel_path)

    finally:
        driver.quit()  # Cerrar navegador siempre al final
