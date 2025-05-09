import requests
import json
import time
import logging
import csv
from bs4 import BeautifulSoup

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    handlers=[
        # Handler para arquivo (mantém todos os logs)
        logging.FileHandler('sodimac_scraping.log', mode='a', encoding='utf-8'),
        # Handler para terminal customizado
        logging.StreamHandler()
    ]
)

# Desativa logs do requests e urllib3
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Classe customizada para filtrar logs no terminal
class TerminalFilter(logging.Filter):
    def filter(self, record):
        # Mostra apenas mensagens específicas no terminal
        messages_to_show = [
            "Salvo ",
            "Coleta concluída",
            "Execução finalizada"
        ]
        return any(msg in record.getMessage() for msg in messages_to_show)

# Aplica o filtro ao handler do terminal
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.addFilter(TerminalFilter())

# Headers atualizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

MAX_PAGES = 20
REQUEST_DELAY = 1

def get_html(url):
    """Obtém o HTML da página"""
    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Erro ao obter HTML: {str(e)}")
        return None

def get_json_data_from_script(url):
    """Obtém os dados JSON"""
    html = get_html(url)
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        script_tag = soup.select_one('script#__NEXT_DATA__')
        if not script_tag:
            return None
        return json.loads(script_tag.string)
    except Exception:
        return None

def scrape_products_from_json(json_data):
    """Raspa os produtos da estrutura JSON"""
    products = []
    try:
        search_data = json_data['props']['pageProps']['searchProps']['searchData']
        product_list = search_data.get('results', [])
        
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
            except Exception:
                continue
    except Exception:
        pass
    
    return products

def save_to_csv(products, filename='produtos_sodimac.csv'):
    """Salva os produtos em CSV"""
    try:
        fieldnames = ['Nome', 'Preco', 'Preco_Original', 'Desconto', 'URL', 'SKU', 'Disponibilidade']
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        
        # Mensagem formatada para o terminal
        print(f"\n==== Relatório de execução ====")
        print(f"Salvo {len(products)} produtos em '{filename}'")
        return True
    except Exception:
        return False

def main():
    """Função principal"""
    try:
        base_url = "https://www.sodimac.com.br/sodimac-br/category/cat170549/prateleiras-e-modulos"
        all_products = []
        
        for page in range(1, MAX_PAGES + 1):
            current_url = f"{base_url}?currentpage={page}"
            json_data = get_json_data_from_script(current_url)
            if not json_data:
                break
            
            products = scrape_products_from_json(json_data)
            if not products:
                break
                
            all_products.extend(products)
            time.sleep(REQUEST_DELAY)
        
        if all_products:
            if save_to_csv(all_products):
                print(f"Coleta concluída com sucesso! Total: {len(all_products)} produtos")
        else:
            print("Nenhum produto foi coletado")
            
    except KeyboardInterrupt:
        print("Execução interrompida pelo usuário")
    except Exception:
        print("Ocorreu um erro durante a execução")
    finally:
        print("Execução finalizada!\n")

if __name__ == "__main__":
    main()