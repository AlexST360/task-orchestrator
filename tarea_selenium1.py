from selenium import webdriver

driver = webdriver.Chrome()
driver.get("https://www.google.com")
print("Título de la página:", driver.title)
driver.quit()
