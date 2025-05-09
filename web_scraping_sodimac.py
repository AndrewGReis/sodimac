import requests
import json
import time
import logging
import csv
from bs4 import BeautifulSoup

# Configuração de logging para salvar os logs em um arquivo e no console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Para exibir no console
        logging.FileHandler('sodimac_scraping.log', mode='a', encoding='utf-8')  # Para salvar em arquivo
    ]
)

# Headers para as requisições
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9'
}

# Constantes de configuração
MAX_PAGES = 20  # Limite seguro de páginas
REQUEST_DELAY = 1  # Delay entre requisições em segundos

def get_html(url):
    """Obtém o HTML da página"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Erro ao obter HTML da URL {url}: {str(e)}")
        return None

def get_json_data_from_script(url):
    """Obtém os dados JSON do script __NEXT_DATA__"""
    html = get_html(url)
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Encontra o script com id '__NEXT_DATA__' e extrai os dados JSON
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if not script_tag:
            logging.error(f"Script __NEXT_DATA__ não encontrado na URL: {url}")
            return None
        
        json_data = json.loads(script_tag.string)  # Converte o conteúdo para JSON
        return json_data
    except Exception as e:
        logging.error(f"Erro ao processar o script __NEXT_DATA__ na URL {url}: {str(e)}")
        return None

def scrape_products_from_json(json_data):
    """Raspa os produtos a partir dos dados JSON extraídos"""
    products = []
    try:
        props = json_data['props']['pageProps']
        
        if 'initialState' not in props or 'product' not in props['initialState']:
            logging.warning("Dados de produtos não encontrados no JSON.")
            return products
        
        product_list = props['initialState']['product']['productList']['products']
        if not product_list:
            logging.warning("Nenhum produto encontrado no JSON.")
            return products
        
        for product in product_list:
            name = product.get('name', 'N/A')
            price = product.get('price', {}).get('formattedValue', 'N/A')
            discount = product.get('discount', 'N/A')
            url = f"https://www.sodimac.com.br{product.get('url', '')}"
            
            # Adiciona os dados coletados
            products.append({
                'Nome': name,
                'Preco': price,
                'Desconto': discount,
                'URL': url
            })
    except KeyError as e:
        logging.error(f"Erro ao processar os dados do JSON: {str(e)}")
    
    return products

def save_to_csv(products, filename='produtos_sodimac.csv'):
    """Salva os produtos em arquivo CSV"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['Nome', 'Preco', 'Desconto', 'URL'])
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
        base_url = "https://www.sodimac.com.br/sodimac-br/category/cat170549/prateleiras-e-modulos"
        all_products = []
        
        for page in range(1, MAX_PAGES + 1):
            current_url = f"{base_url}?currentpage={page}"
            logging.info(f"Processando página {page}: {current_url}")
            
            json_data = get_json_data_from_script(current_url)
            if not json_data:
                logging.info(f"Sem dados JSON na página {page}, encerrando a coleta.")
                break
            
            # Raspa os produtos a partir dos dados JSON
            products = scrape_products_from_json(json_data)
            if not products:
                logging.info(f"Sem produtos na página {page}, encerrando a coleta.")
                break
            
            all_products.extend(products)
            time.sleep(REQUEST_DELAY)
        
        if all_products:
            save_to_csv(all_products)
            logging.info(f"Processo concluído. Total de produtos coletados: {len(all_products)}")
        else:
            logging.warning("Nenhum produto coletado.")
        
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
    finally:
        logging.info("Execução do programa finalizada.")  # Log de finalização

if __name__ == "__main__":
    main()
