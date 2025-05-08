import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sodimac_scraping.log'),
        logging.StreamHandler()
    ]
)

def setup_driver():
    """Configura o WebDriver com opções otimizadas"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Configurações para evitar detecção
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

def scrape_products():
    driver = setup_driver()
    try:
        url = "https://www.sodimac.com.br/sodimac-br/category/cat20001/Ferramentas/"
        logging.info(f"Acessando: {url}")
        driver.get(url)
        
        # Espera explícita para os produtos carregarem
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='product-card']"))
        )
        
        # Scroll para carregar todos os produtos
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # Coleta os produtos
        products = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='product-card']")
        logging.info(f"Encontrados {len(products)} produtos")
        
        # Extrai informações básicas
        for product in products[:5]:  # Mostra apenas os 5 primeiros para teste
            try:
                name = product.find_element(By.CSS_SELECTOR, "[data-testid='product-title']").text
                price = product.find_element(By.CSS_SELECTOR, "[data-testid='price-value']").text
                logging.info(f"Produto: {name} | Preço: {price}")
            except Exception as e:
                logging.warning(f"Erro ao extrair produto: {str(e)}")
        
        return len(products)
        
    except Exception as e:
        logging.error(f"Erro durante o scraping: {str(e)}")
        return 0
    finally:
        driver.quit()
        logging.info("Navegador finalizado")

if __name__ == "__main__":
    logging.info("=== INÍCIO DO SCRAPING ===")
    total_products = scrape_products()
    logging.info(f"=== FIM DO SCRAPING | Total de produtos: {total_products} ===")