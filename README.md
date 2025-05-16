# 🕷️ Web Scraper - Sodimac (Prateleiras e Módulos)

Automação para coleta de preços e disponibilidade de produtos na categoria "Prateleiras e Módulos" do [Sodimac](https://www.sodimac.com.br), com exportação para CSV.

## 🔎 Referência de Busca
[Categoria Prateleiras e Módulos](https://www.sodimac.com.br/sodimac-br/category/cat170549/prateleiras-e-modulos)

## ⚙️ Funcionalidades
- **🌐 Coleta automatizada** via Requests + BeautifulSoup  
- **📦 Extração de dados**:
  - Nome do produto
  - Preço atual e original
  - Disponibilidade
  - SKU e URL completa
- **🔄 Paginação automática** (até 20 páginas)
- **⚡ Resiliência**:
  - Fallback para regex quando o JSON está incompleto
  - Delay entre requisições para evitar bloqueio

## 📊 Saída Gerada
Arquivo `produtos_sodimac.csv` com estrutura:
Nome | Preco | Preco_Original | Desconto | URL | SKU | Disponibilidade

## 🏆 Destaques Técnicos
- **📝 Sistema de logging inteligente**:  
  - Arquivo completo com debug  
  - Terminal filtrado só para informações críticas  
- **🔍 Extração de dados híbrida**:  
  - Primário: JSON embutido (Next.js)  
  - Fallback: Regex no HTML quando necessário  
- **⏱️ Throttling automático** (1s entre requisições)
