from selenium import webdriver #controla el navegador
from selenium.webdriver.common.by import By #Permite localizar elementos (por ID, CSS, XPath, etc.).
from selenium.webdriver.chrome.service import Service #definir la ruta de chromedriver
from selenium.webdriver.chrome.options import Options #Configura opciones de Chrome (ej: headless, tamaño de ventana).
from selenium.webdriver.support.ui import WebDriverWait #esperar dinámicamente a que un elemento evitando errores de timing
from selenium.webdriver.support import expected_conditions as EC #esperar dinámicamente a que un elemento evitando errores de timing
from webdriver_manager.chrome import ChromeDriverManager 
##CONFIGURAR CHROME
options = Options()
options.add_argument("--headless=new")  # Ejecuta en segundo plano
options.add_argument("--window-size=1280,800")  # Tamaño de ventana virtual

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)


driver.get("https://the-internet.herokuapp.com/login")  #abrir la pagina del login

#Localizar y completar campos del formulario
username_input = driver.find_element(By.ID, "username")
password_input = driver.find_element(By.ID, "password") 

username_input.send_keys("tomsmith")
password_input.send_keys("SuperSecretPassword!")

#clic en login
login_button = driver.find_element(By.CSS_SELECTOR, "button.radius")
login_button.click()

#Esperar mensaje de éxito
success_message = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "flash"))
)

print("Mensaje de login:", success_message.text)

#Cerrar el navegador
driver.quit()
