import json
import re
from datetime import datetime
import urllib.request
from bs4 import BeautifulSoup
import logging

# Configuração de Log (Regra de Código Limpo e Tratamento de Erros)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações do Projeto
URL_RECEITA = "https://servicos.receita.fazenda.gov.br/publico/EstatisticaIRPF/doacoesDIRPF_PE_2026.HTML"
META_CAMPANHA_RECIFE = 10000000.00  # Exemplo parametrizável: R$ 10.000.000,00
ARQUIVO_SAIDA = "dados.json"

def converter_moeda_br_para_float(valor_texto):
    """Converte um valor em reais para float. Ex: 'R$ 233.899.868,34' -> 233899868.34"""
    if not valor_texto:
        return 0.0
    texto_limpo = re.sub(r'[^\d,-]', '', valor_texto)
    texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
    try:
        return float(texto_limpo)
    except ValueError:
        return 0.0

def converter_percentual_para_float(valor_texto):
    """Converte string percentual para float. Ex: '58,0%' -> 58.0"""
    if not valor_texto:
        return 0.0
    texto_limpo = valor_texto.replace('%', '').replace(',', '.').strip()
    try:
        return float(texto_limpo)
    except ValueError:
        return 0.0

def calcular_indicadores(dados_brutos, meta):
    """Calcula todos os indicadores exigidos pelas regras de negócio."""
    
    darfs_pagos = dados_brutos.get("darfs_pagos", 0.0)
    potencial = dados_brutos.get("potencial_destinacao", 0.0)
    valor_destinado = dados_brutos.get("valor_destinado_declaracao", 0.0)
    perc_crianca = dados_brutos.get("percentual_crianca_adolescente", 0.0)
    perc_idoso = dados_brutos.get("percentual_pessoa_idosa", 0.0)
    
    taxa_meta = (darfs_pagos / meta * 100) if meta > 0 else 0.0
    taxa_conversao = (darfs_pagos / valor_destinado * 100) if valor_destinado > 0 else 0.0
    taxa_aproveitamento = (darfs_pagos / potencial * 100) if potencial > 0 else 0.0

    return {
        "municipio": dados_brutos.get("municipio", "RECIFE"),
        "valor_arrecadado": darfs_pagos,
        "qtd_doacoes_efetivadas": int(dados_brutos.get("qtd_doacoes_efetivadas", 0)),
        "meta": meta,
        "percentual_meta_atingida": round(taxa_meta, 2),
        "potencial_destinacao": potencial,
        "valor_destinado_declaracao": valor_destinado,
        "percentual_crianca_adolescente": perc_crianca,
        "percentual_pessoa_idosa": perc_idoso,
        "valor_estimado_crianca_adolescente": round(darfs_pagos * (perc_crianca / 100), 2),
        "valor_estimado_pessoa_idosa": round(darfs_pagos * (perc_idoso / 100), 2),
        "taxa_conversao_pagamento": round(taxa_conversao, 2),
        "taxa_aproveitamento_potencial": round(taxa_aproveitamento, 2),
        "data_referencia_receita": str(datetime.now().date()), # Mock para exemplo (deve ser extraído da página)
        "fonte": "Receita Federal do Brasil",
        "data_processamento": datetime.now().isoformat()
    }

def realizar_scraping_receita():
    """Baixa o HTML e tenta encontrar a linha do Recife para extrair os dados básicos."""
    logger.info("Iniciando requisição para a página da Receita Federal.")
    try:
        req = urllib.request.Request(URL_RECEITA, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error({'error': str(e)}, "Erro ao acessar a página da Receita.")
        return None

    soup = BeautifulSoup(html, "html.parser")
    
    # Busca por linhas de tabela que possuam a palavra RECIFE
    linhas = soup.find_all("tr")
    linha_recife = None
    
    for tr in linhas:
        colunas = tr.find_all(["td", "th"])
        textos = [td.get_text(strip=True) for td in colunas]
        if textos and "RECIFE" in textos[0].upper():
            linha_recife = textos
            break

    if not linha_recife:
        logger.error(None, "Município RECIFE não encontrado na tabela.")
        return None

    # Como as tabelas web da Receita variam, mapeamos por índice baseando-se na estrutura esperada
    # ATENÇÃO: Os índices exatos dependem do HTML real. Estes são ilustrativos conforme a referência.
    try:
        dados_extraidos = {
            "municipio": "RECIFE",
            "potencial_destinacao": converter_moeda_br_para_float(linha_recife[1]),
            "valor_destinado_declaracao": converter_moeda_br_para_float(linha_recife[5]),
            "percentual_crianca_adolescente": converter_percentual_para_float(linha_recife[7]),
            "percentual_pessoa_idosa": converter_percentual_para_float(linha_recife[8]),
            "darfs_pagos": converter_moeda_br_para_float(linha_recife[9]),
            "qtd_doacoes_efetivadas": converter_moeda_br_para_float(linha_recife[10]) # Quantidades geralmente inteiras com formato br
        }
        logger.info("Dados de Recife extraídos com sucesso do HTML.")
        return dados_extraidos
    except IndexError:
        logger.error(None, "Estrutura da tabela diferente da esperada (índices inválidos).")
        return None

def mocar_dados_referencia():
    """Retorna dados baseados na referência do prompt caso o scraping falhe (Fallback)."""
    return {
        "municipio": "RECIFE",
        "potencial_destinacao": 233899868.34,
        "valor_destinado_declaracao": 3881678.50,
        "percentual_crianca_adolescente": 58.0,
        "percentual_pessoa_idosa": 42.0,
        "darfs_pagos": 3802355.68,
        "qtd_doacoes_efetivadas": 2794
    }

def main():
    logger.info("Iniciando extração e processamento dos dados do Contador do Bem.")
    
    dados_brutos = realizar_scraping_receita()
    if not dados_brutos:
        logger.info("Usando dados de fallback da referência.")
        dados_brutos = mocar_dados_referencia()
        
    indicadores = calcular_indicadores(dados_brutos, META_CAMPANHA_RECIFE)
    
    try:
        with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
            json.dump(indicadores, f, ensure_ascii=False, indent=2)
            logger.info({'arquivo': ARQUIVO_SAIDA}, "JSON gerado com sucesso.")
    except Exception as e:
        logger.error({'error': str(e)}, "Erro ao salvar o arquivo JSON.")

if __name__ == "__main__":
    main()
