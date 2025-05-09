import requests
from bs4 import BeautifulSoup
import logging
import csv
import time
from collections import defaultdict
import socket

# ========== CONFIGURAÇÕES GLOBAIS ==========
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Referer': 'https://www.sodimac.com.br/'
}
REQUEST_TIMEOUT = 30
DELAY_BETWEEN_REQUESTS = 2
MAX_RETRIES = 3
SKIP_FAILED_CATEGORIES = True
MAX_PAGES_PER_CATEGORY = 5

# Configuração de logging
logging.basicConfig(
    filename='sodimac_scraping.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(lineno)d - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

socket.setdefaulttimeout(REQUEST_TIMEOUT)

# ========== FUNÇÕES AUXILIARES ==========
def log_execution_time(stages):
    """Gera relatório de tempo de execução"""
    total_time = sum(stages.values())
    report = (
        f"\nRELATORIO DE TEMPO:\n"
        f"TOTAL: {total_time:.2f} segundos\n"
        f"DOWNLOAD: {stages.get('DOWNLOAD', 0):.2f}s\n"
        f"PARSING: {stages.get('PARSING', 0):.2f}s\n"
        f"EXTRACAO: {stages.get('EXTRACAO', 0):.2f}s\n"
        f"SALVAMENTO: {stages.get('SALVAMENTO', 0):.2f}s\n"
        f"Concluido!\n"
    )
    return report

def generate_category_report(all_products):
    """Gera relatório por categoria"""
    category_counts = defaultdict(int)
    for product in all_products:
        category_counts[product['Categoria']] += 1
    
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    report = "\n=== RELATORIO POR CATEGORIA ===\n"
    for category, count in sorted_categories:
        report += f"- {category.ljust(25)}: {count} produtos\n"
    report += "==============================="
    
    return report

def save_to_csv(products, filename='produtos_sodimac.csv'):
    """Salva os dados em CSV"""
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

# ========== FUNÇÕES PRINCIPAIS ==========
def get_categories(url_home):
    """Coleta categorias do menu principal"""
    try:
        response = requests.get(url_home, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # DEBUG: Salvar HTML para análise
        with open('debug_homepage.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logging.info("HTML salvo em 'debug_homepage.html'")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tentativa com vários seletores alternativos
        menu_categorias = (
            soup.find('div', {'data-testid': 'nav-categories'}) or
            soup.find('nav', class_='nav-categories') or
            soup.find('ul', class_='nav-list') or
            soup.find('div', class_='js-navigation')
        )
        
        if not menu_categorias:
            logging.error("HTML da página:\n" + soup.prettify()[:2000])  # Log parcial do HTML
            raise ValueError("Menu de categorias não encontrado!")
            
        # Extração dos links
        links_categorias = menu_categorias.find_all('a', href=True)
        categories = []
        
        for link in links_categorias:
            nome = link.text.strip()
            if not nome or len(nome) < 2:  # Filtra links vazios ou muito curtos
                continue
                
            url_relativa = link['href']
            if not url_relativa.startswith('http'):
                url_absoluta = f"https://www.sodimac.com.br{url_relativa}"
            else:
                url_absoluta = url_relativa
                
            # Filtra links inválidos
            if 'category' in url_absoluta.lower() or 'departamento' in url_absoluta.lower():
                categories.append((nome, url_absoluta))
                logging.debug(f"Categoria encontrada: {nome} - {url_absoluta}")
        
        if not categories:
            logging.warning("Nenhuma categoria válida encontrada após filtragem")
        
        return categories
    
    except Exception as e:
        logging.error(f"Erro ao coletar categorias: {str(e)}", exc_info=True)
        return []

def scrape_products_from_category(category_name, category_url):
    """Raspagem de produtos por categoria"""
    products = []
    page_url = category_url
    
    for page_count in range(1, MAX_PAGES_PER_CATEGORY + 1):
        try:
            logging.info(f"Acessando pagina {page_count}: {category_name}")
            response = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 404:
                logging.warning(f"Categoria nao encontrada (404): {category_name}")
                break
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # DEBUG: Salvar HTML da categoria
            if page_count == 1:
                with open(f'debug_{category_name}.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logging.info(f"HTML da categoria salvo em 'debug_{category_name}.html'")
            
            # Seletores alternativos para produtos
            product_cards = (
                soup.find_all('div', {'data-testid': 'product-card'}) or
                soup.find_all('div', class_='product-card') or
                soup.find_all('li', class_='product-item')
            )
            
            if not product_cards:
                logging.warning(f"Nenhum produto encontrado na pagina {page_count}")
                break
                
            for card in product_cards:
                try:
                    # Extração com tratamento robusto
                    name = card.find(['h3', 'h2'], class_=lambda x: x and 'title' in x.lower()).text.strip()
                    price = card.find('span', class_=lambda x: x and 'price' in x.lower()).text.strip()
                    link = card.find('a')['href']
                    
                    # Tratamento do link
                    if not link.startswith('http'):
                        link = f"https://www.sodimac.com.br{link.lstrip('/')}"
                    
                    # Desconto (opcional)
                    discount_tag = card.find('span', class_=lambda x: x and 'discount' in x.lower())
                    discount = discount_tag.text.strip() if discount_tag else 'Sem desconto'
                    
                    products.append({
                        'Categoria': category_name,
                        'Nome': name,
                        'Preco': price,
                        'Desconto': discount,
                        'URL': link
                    })
                except Exception as e:
                    logging.warning(f"Erro ao processar produto: {str(e)}")
                    continue
            
            # Paginação
            next_button = soup.find('a', {'aria-label': lambda x: x and 'próxima' in x.lower()})
            if not next_button:
                break
                
            page_url = next_button['href']
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logging.error(f"Erro na pagina {page_count}: {str(e)}")
            break
    
    logging.info(f"Coletados {len(products)} produtos em '{category_name}'")
    return products

# ========== EXECUÇÃO PRINCIPAL ==========
def main():
    try:
        # Configuração inicial
        logging.info("\n" + "="*50)
        logging.info("INICIO DA EXECUCAO")
        logging.info(f"Horario: {time.strftime('%d/%m/%Y %H:%M:%S')}")
        logging.info("="*50 + "\n")

        etapas_tempo = {}
        global_start = time.time()
        
        # Fase 1: Coleta de categorias
        logging.info("[ETAPA 1] COLETANDO CATEGORIAS...")
        stage_start = time.time()
        
        categorias = get_categories("https://www.sodimac.com.br")
        if not categorias:
            logging.error("NENHUMA CATEGORIA VALIDA ENCONTRADA!")
            if not SKIP_FAILED_CATEGORIES:
                raise ValueError("Nenhuma categoria encontrada!")
            categorias = [('Debug', 'https://www.sodimac.com.br/sodimac-br/category/cat20001/ferramentas/')]
            logging.warning("Usando URL de debug para continuar")
        
        etapas_tempo['DOWNLOAD'] = time.time() - stage_start
        logging.info(f"Encontradas {len(categorias)} categorias")
        
        # Fase 2: Coleta de produtos
        logging.info("\n[ETAPA 2] COLETANDO PRODUTOS...")
        stage_start = time.time()
        all_products = []
        
        for nome, url in categorias:
            logging.info(f"\nProcessando: {nome}")
            produtos = scrape_products_from_category(nome, url)
            all_products.extend(produtos)
            logging.info(f"Progresso: {len(all_products)} produtos")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        etapas_tempo['EXTRACAO'] = time.time() - stage_start
        
        # Fase 3: Salvamento
        logging.info("\n[ETAPA 3] SALVANDO DADOS...")
        stage_start = time.time()
        
        if save_to_csv(all_products):
            report = generate_category_report(all_products)
            print(report)
            with open('relatorio_categorias.txt', 'w', encoding='utf-8') as f:
                f.write(report)
        
        etapas_tempo['SALVAMENTO'] = time.time() - stage_start
        
        # Relatório final
        print(log_execution_time(etapas_tempo))
        logging.info(f"TOTAL DE PRODUTOS: {len(all_products)}")
        
    except Exception as e:
        logging.error("ERRO FATAL:\n" + str(e), exc_info=True)
    finally:
        logging.info("\n" + "="*50)
        logging.info("EXECUCAO FINALIZADA")
        logging.info("="*50)

if __name__ == "__main__":
    main()