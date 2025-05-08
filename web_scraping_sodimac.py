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

def scrape_product_details(url):
    driver = setup_driver()
    try:
        logging.info(f"Acessando página do produto: {url}")
        driver.get(url)
        
        # Espera explícita para a página carregar
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-testid='product-name']"))
        )
        
        # Extrai informações do produto
        product_info = {
            'name': driver.find_element(By.CSS_SELECTOR, "h1[data-testid='product-name']").text,
            'current_price': driver.find_element(By.CSS_SELECTOR, "span[data-testid='price-value']").text,
            'original_price': driver.find_element(By.CSS_SELECTOR, "span[data-testid='price-original']").text,
            'discount': driver.find_element(By.CSS_SELECTOR, "span[data-testid='price-discount']").text,
            'installments': driver.find_element(By.CSS_SELECTOR, "span[data-testid='price-installment']").text,
            'description': driver.find_element(By.CSS_SELECTOR, "div[data-testid='product-description']").text if driver.find_elements(By.CSS_SELECTOR, "div[data-testid='product-description']") else "N/A"
        }
        
        logging.info(f"Informações do produto coletadas: {product_info}")
        return product_info
        
    except Exception as e:
        logging.error(f"Erro ao coletar detalhes do produto: {str(e)}")
        return None
    finally:
        driver.quit()
        logging.info("Navegador finalizado")

if __name__ == "__main__":
    logging.info("=== INÍCIO DO SCRAPING ===")
    
    # URL de exemplo da churrasqueira (da segunda imagem)
    product_url = "https://www.sodimac.com.br/sodimac-br/product/768155/churrasqueira-a-gas-com-3-queimadores-e-1-queimador-lateral-cinza/768155/?cid=prd_hom_36009"
    
    product_data = scrape_product_details(product_url)
    
    if product_data:
        logging.info("\n=== DADOS DO PRODUTO ===")
        logging.info(f"Nome: {product_data['name']}")
        logging.info(f"Preço atual: {product_data['current_price']}")
        logging.info(f"Preço original: {product_data['original_price']}")
        logging.info(f"Desconto: {product_data['discount']}")
        logging.info(f"Parcelamento: {product_data['installments']}")
        logging.info(f"Descrição: {product_data['description'][:100]}...")  # Mostra apenas os 100 primeiros caracteres
    else:
        logging.error("Não foi possível coletar os dados do produto")
    
    logging.info("=== FIM DO SCRAPING ===")