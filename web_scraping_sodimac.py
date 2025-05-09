import requests
from bs4 import BeautifulSoup
import json
import time
import logging
import csv

# Configuração de logging para salvar os logs em um arquivo e no console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Para exibir no console
        logging.FileHandler('sodimac_scraping.log', mode='w', encoding='utf-8')  # Para salvar em arquivo
    ]
)

# Headers para as requisições
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9'
}

# Constantes de configuração
MAX_PAGES_PER_CATEGORY = 20  # Limite seguro de páginas por categoria
REQUEST_DELAY = 1  # Delay entre requisições em segundos

def get_json_data(url):
    """Obtém os dados JSON da página"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.select_one('script#__NEXT_DATA__')
        
        if not script_tag:
            logging.error("Script __NEXT_DATA__ não encontrado")
            return None
            
        return json.loads(script_tag.text)
    except Exception as e:
        logging.error(f"Erro ao obter dados JSON: {str(e)}")
        return None

def extract_categories(homepage_url):
    """Extrai categorias do JSON da página inicial"""
    json_data = get_json_data(homepage_url)
    if not json_data:
        return []
    
    try:
        categories = []
        props = json_data['props']['pageProps']
        
        # Navega na estrutura JSON para encontrar as categorias
        for category in props['initialState']['menu']['departments']:
            cat_name = category['name']
            cat_url = f"https://www.sodimac.com.br{category['url']}"
            categories.append((cat_name, cat_url))
        
        logging.info(f"Encontradas {len(categories)} categorias")
        return categories
    except KeyError as e:
        logging.error(f"Estrutura JSON inesperada: {str(e)}")
        return []

def scrape_category_products(category_name, category_url):
    """Raspa produtos de uma categoria com limite de páginas"""
    products = []
    has_more_pages = True
    page = 1
    
    while has_more_pages and page <= MAX_PAGES_PER_CATEGORY:
        try:
            current_url = f"{category_url.rstrip('/')}?currentpage={page}"
            logging.info(f"Processando página {page}: {current_url}")
            
            json_data = get_json_data(current_url)
            if not json_data:
                has_more_pages = False
                break
                
            # Extrai produtos da estrutura JSON
            props = json_data['props']['pageProps']
            if 'initialState' not in props or 'product' not in props['initialState']:
                has_more_pages = False
                break
                
            product_list = props['initialState']['product']['productList']['products']
            if not product_list:
                has_more_pages = False
                break
                
            for product in product_list:
                products.append({
                    'Categoria': category_name,
                    'Nome': product.get('name', 'N/A'),
                    'Preco': product.get('price', {}).get('formattedValue', 'N/A'),
                    'Desconto': product.get('discount', 'N/A'),
                    'URL': f"https://www.sodimac.com.br{product.get('url', '')}"
                })
            
            # Verifica se há mais páginas disponíveis
            page += 1
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            logging.error(f"Erro ao processar página {page}: {str(e)}")
            has_more_pages = False
    
    logging.info(f"Total de produtos coletados em '{category_name}': {len(products)}")
    return products

def save_to_csv(products, filename='produtos_sodimac.csv'):
    """Salva os produtos em arquivo CSV"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['Categoria', 'Nome', 'Preco', 'Desconto', 'URL'])
            writer.writeheader()
            writer.writerows(products)
        logging.info(f"Dados salvos em '{filename}'")
        return True
    except Exception as e:
        logging.error(f"Falha ao salvar CSV: {str(e)}")
        return False

def main():
    """Função principal de execução"""
    logging.info("Iniciando execução do programa...")  # Log de início
    
    try:
        homepage_url = "https://www.sodimac.com.br"
        
        # 1. Coletar categorias
        categories = extract_categories(homepage_url)
        if not categories:
            logging.error("Nenhuma categoria encontrada. Encerrando.")
            return
            
        # 2. Raspar produtos de cada categoria
        all_products = []
        for category_name, category_url in categories[:3]:  # Limitando a 3 categorias para teste
            products = scrape_category_products(category_name, category_url)
            all_products.extend(products)
            
        # 3. Salvar resultados
        save_to_csv(all_products)
        
        logging.info(f"Processo concluído. Total de produtos coletados: {len(all_products)}")
        
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
    finally:
        logging.info("Execução do programa finalizada.")  # Log de finalização

if __name__ == "__main__":
    main()
