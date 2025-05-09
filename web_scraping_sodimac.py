import requests
import json
import time
import logging
import csv
from bs4 import BeautifulSoup

def configure_logging():
    """Configura o sistema de logging para arquivo e terminal"""
    logging.getLogger().handlers = []
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    
    file_handler = logging.FileHandler('sodimac_scraping.log', mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    class TerminalFilter(logging.Filter):
        def filter(self, record):
            return any(msg in record.getMessage() for msg in [
                "Iniciando coleta", "Salvo ", "Coleta concluída", 
                "Execução finalizada", "Erro durante", "interrompida"
            ])
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(TerminalFilter())
    logger.addHandler(stream_handler)
    
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

MAX_PAGES = 20
REQUEST_DELAY = 1

def fetch_page_content(url):
    """Obtém o conteúdo HTML de uma URL"""
    try:
        logging.debug(f"Requisitando URL: {url}")
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()
        logging.debug(f"Resposta recebida - Status: {response.status_code}, Tamanho: {len(response.text)} bytes")
        return response.text
    except Exception as e:
        logging.error(f"Erro ao obter página: {str(e)}")
        return None

def extract_json_from_page(html_content):
    """Extrai dados JSON do conteúdo HTML da página"""
    if not html_content:
        logging.debug("Conteúdo HTML vazio recebido para extração JSON")
        return None
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tag = soup.select_one('script#__NEXT_DATA__')
        
        if not script_tag:
            logging.warning("Script __NEXT_DATA__ não encontrado na página")
            return None
            
        logging.debug("Script __NEXT_DATA__ encontrado, extraindo dados JSON")
        return json.loads(script_tag.string)
    except Exception as e:
        logging.error(f"Erro ao extrair JSON: {str(e)}")
        return None

def parse_product_data(json_data):
    """Analisa os dados JSON e extrai informações dos produtos"""
    products = []
    if not json_data:
        return products
        
    try:
        logging.debug("Iniciando análise dos dados dos produtos")
        search_data = json_data['props']['pageProps']['searchProps']['searchData']
        product_list = search_data.get('results', [])
        logging.debug(f"Encontrados {len(product_list)} produtos para processar")
        
        for product in product_list:
            try:
                price_info = product.get('price', {})
                products.append({
                    'Nome': product.get('displayName', 'N/A'),
                    'Preco': price_info.get('formattedValue', 'N/A'),
                    'Preco_Original': price_info.get('originalFormattedValue', price_info.get('formattedValue', 'N/A')),
                    'Desconto': product.get('discountText', 'N/A'),
                    'URL': f"https://www.sodimac.com.br{product.get('url', '')}",
                    'SKU': product.get('productId', 'N/A'),
                    'Disponibilidade': product.get('stock', {}).get('status', 'N/A')
                })
            except Exception as e:
                logging.warning(f"Erro ao processar produto: {str(e)}")
                continue
    except KeyError as e:
        logging.error(f"Estrutura de dados inesperada - chave não encontrada: {str(e)}")
    except Exception as e:
        logging.error(f"Erro inesperado ao analisar produtos: {str(e)}")
    
    logging.debug(f"Produtos processados com sucesso: {len(products)}")
    return products

def save_products_to_csv(products, filename='produtos_sodimac.csv'):
    """Salva a lista de produtos em um arquivo CSV"""
    try:
        if not products:
            logging.warning("Nenhum produto para salvar no CSV")
            return False
            
        fieldnames = ['Nome', 'Preco', 'Preco_Original', 'Desconto', 'URL', 'SKU', 'Disponibilidade']
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        
        logging.info(f"Salvo {len(products)} produtos em '{filename}'")
        print(f"\n==== Relatório de execução ====")
        print(f"Salvo {len(products)} produtos em '{filename}'")
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar CSV: {str(e)}")
        return False

def scrape_category_products(base_url, max_pages=MAX_PAGES):
    """Raspa produtos de uma categoria por várias páginas"""
    all_products = []
    logging.info(f"Iniciando coleta para URL: {base_url}")
    
    for page in range(1, max_pages + 1):
        page_url = f"{base_url}?currentpage={page}"
        logging.debug(f"Processando página {page} - URL: {page_url}")
        
        html_content = fetch_page_content(page_url)
        
        if not html_content:
            logging.warning(f"Falha ao obter página {page}")
            break
            
        json_data = extract_json_from_page(html_content)
        
        if not json_data:
            logging.warning(f"Dados inválidos na página {page}")
            break
            
        products = parse_product_data(json_data)
        
        if not products:
            logging.info(f"Nenhum produto encontrado na página {page}")
            break
            
        all_products.extend(products)
        logging.debug(f"Página {page} processada - Total acumulado: {len(all_products)} produtos")
        time.sleep(REQUEST_DELAY)
    
    logging.info(f"Coleta finalizada - Total de produtos: {len(all_products)}")
    return all_products

def main():
    """Função principal de execução"""
    configure_logging()
    logging.info("==== Iniciando programa de coleta ====")
    
    try:
        category_url = "https://www.sodimac.com.br/sodimac-br/category/cat170549/prateleiras-e-modulos"
        products = scrape_category_products(category_url)
        
        if products:
            if save_products_to_csv(products):
                logging.info(f"Coleta concluída com sucesso! Total: {len(products)} produtos")
                print(f"Coleta concluída com sucesso! Total: {len(products)} produtos")
        else:
            logging.warning("Nenhum produto foi coletado")
            print("Nenhum produto foi coletado")
            
    except KeyboardInterrupt:
        logging.warning("Execução interrompida pelo usuário")
        print("\nExecução interrompida pelo usuário")
    except Exception as e:
        logging.error(f"Erro durante a execução: {str(e)}", exc_info=True)
        print(f"\nErro durante a execução: {str(e)}")
    finally:
        logging.info("==== Programa finalizado ====")
        print("Execução finalizada!\n")

if __name__ == "__main__":
    main()