import requests
from bs4 import BeautifulSoup
import logging
import time
import random
from urllib.parse import urljoin
import sys
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import os

# Configuração de caminhos
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROJECT_DIR, 'sodimac_scraping.log')
DEBUG_HTML = os.path.join(PROJECT_DIR, 'debug_sodimac.html')
CSV_FILE = os.path.join(PROJECT_DIR, 'sodimac_produtos.csv')

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Silencia mensagens do TensorFlow

# Configuração de encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuração de logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# Configurações do navegador headless
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Headers personalizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.sodimac.com.br/',
    'DNT': '1',
}

# Configurações de tempo
BASE_DELAY = 3
RANDOM_DELAY = (1, 5)  # Intervalo aleatório entre requisições
TIMEOUT = 30
BASE_URL = "https://www.sodimac.com.br"

def get_random_delay():
    """Retorna um delay aleatório entre requisições."""
    return BASE_DELAY + random.uniform(*RANDOM_DELAY)

def get_page(url):
    """Faz a requisição HTTP com tratamento de erros."""
    try:
        time.sleep(get_random_delay())
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        if "block" in response.text.lower() or "captcha" in response.text.lower():
            logging.warning("Possível bloqueio detectado na página")
            return None
            
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao acessar {url}: {str(e)}")
        return None

def get_page_with_selenium(url):
    """Obtém o conteúdo da página usando Selenium para renderização JS."""
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Esconde automação
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        driver.get(url)
        
        # Espera inteligente por produtos
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='product'], .product"))
        )
        
        # Rola a página gradualmente
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, window.innerHeight / 2)")
            time.sleep(1)
            
        page_source = driver.page_source
        driver.quit()
        return page_source
    except Exception as e:
        logging.error(f"Erro no Selenium: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None

def parse_products(html):
    """Extrai produtos da página HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    
    # Salva o HTML para debug
    with open(DEBUG_HTML, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Seletores atualizados
    product_cards = soup.select("[data-testid='product-card'], .product-card")
    
    for card in product_cards:
        try:
            # Nome do produto
            name_elem = card.select_one("[data-testid='product-title'], .product-title")
            name = name_elem.get_text(strip=True) if name_elem else "Nome não encontrado"
            
            # Preço
            price_elem = card.select_one("[data-testid='price-value'], .price")
            price = price_elem.get_text(strip=True) if price_elem else "Preço não disponível"
            
            # Link do produto
            link_elem = card.select_one("a[href]")
            product_url = urljoin(BASE_URL, link_elem['href']) if link_elem else BASE_URL
            
            # Avaliação
            rating_elem = card.select_one("[data-testid='rating-stars'], .rating")
            rating = rating_elem.get_text(strip=True) if rating_elem else "Sem avaliação"
            
            # Código SKU
            sku_elem = card.select_one("[data-testid='product-sku'], .sku")
            sku = sku_elem.get_text(strip=True) if sku_elem else "SKU não disponível"
            
            products.append({
                'name': name,
                'price': price,
                'url': product_url,
                'rating': rating,
                'sku': sku
            })
        except Exception as e:
            logging.warning(f"Erro ao processar produto: {str(e)}")
            continue
    
    return products

def scrape_category(category_url, max_pages=3):
    """Raspa produtos de uma categoria com paginação controlada."""
    logging.info(f"Iniciando scraping para: {category_url}")
    products = []
    page = 1
    has_next_page = True
    
    while has_next_page and page <= max_pages:
        logging.info(f"Processando página {page}")
        
        if page > 1:
            paginated_url = f"{category_url}?page={page}"
        else:
            paginated_url = category_url
            
        if page == 1:
            html_content = get_page_with_selenium(paginated_url)
        else:
            response = get_page(paginated_url)
            html_content = response.text if response else None
        
        if not html_content:
            logging.warning(f"Falha ao acessar página {page}")
            break
            
        page_products = parse_products(html_content)
        if not page_products:
            logging.info(f"Nenhum produto encontrado na página {page}. Finalizando.")
            break
            
        products.extend(page_products)
        logging.info(f"Página {page}: {len(page_products)} produtos adicionados")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        next_button = soup.find('button', {'aria-label': 'Próxima página'})
        has_next_page = bool(next_button) and not next_button.get('disabled', False)
        
        page += 1
        time.sleep(get_random_delay())
    
    return products

def save_to_csv(products, filename=CSV_FILE):
    """Salva os produtos em um arquivo CSV."""
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['name', 'price', 'url', 'rating', 'sku']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        logging.info(f"Dados salvos em {filename}")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar CSV: {str(e)}")
        return False

def main():
    # URL de exemplo - Ferramentas
    category_url = "https://www.sodimac.com.br/sodimac-br/category/cat20001/Ferramentas/"
    
    print("Iniciando scraping do site Sodimac...")
    products = scrape_category(category_url, max_pages=2)  # Limita a 2 páginas para teste
    
    if products:
        if save_to_csv(products):
            print(f"\n✅ Scraping concluído com sucesso!")
            print(f"📊 Total de produtos coletados: {len(products)}")
            print(f"📄 Arquivo gerado: '{CSV_FILE}'")
            
            print("\nExemplos de produtos coletados:")
            for prod in products[:3]:
                print(f"- {prod['name']} | {prod['price']} | Avaliação: {prod['rating']}")
        else:
            print("❌ Erro ao salvar os dados.")
    else:
        print("❌ Nenhum produto foi extraído. Verifique o arquivo de log.")
    
    print(f"\nDica: Verifique o arquivo '{DEBUG_HTML}' para ajustar os seletores se necessário.")

if __name__ == "__main__":
    main()
    # testandooooo