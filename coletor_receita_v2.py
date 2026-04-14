import json
import csv
import re
import os
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime
import logging

# Configuração Padrão de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL_RECEITA = "https://servicos.receita.fazenda.gov.br/publico/EstatisticaIRPF/doacoesDIRPF_PE_2026.HTML"
ARQUIVO_CACHE_LOCAL = "receita_cache.html" # Fallback caso o site trave
ARQUIVO_CSV_BI = "municipios_pe.csv"
ARQUIVO_JSON_BI = "municipios_pe.json"
ARQUIVO_JSON_SITE = "recife_contador.json"

def baixar_html(url):
    logger.info(f"Iniciando requisição para: {url}")
    
    # Cabeçalhos mais realistas para evitar bloqueios triviais e tarpitting
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        # Timeout reduzido para 12s para evitar percepção de "travamento" total
        with urllib.request.urlopen(req, timeout=12) as response:
            logger.info(f"Resposta recebida. Status: {response.getcode()}. Lendo conteúdo...")
            html = response.read().decode('utf-8', errors='ignore')
            
            # Salva cache local para uso em emergências futuras
            with open(ARQUIVO_CACHE_LOCAL, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return html
    except Exception as e:
        logger.warning(f"Falha ao acessar URL oficial: {str(e)}")
        
        # Tenta carregar do cache local se existir
        if os.path.exists(ARQUIVO_CACHE_LOCAL):
            logger.info("Tentando carregar dados do cache local (receita_cache.html)...")
            try:
                with open(ARQUIVO_CACHE_LOCAL, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e_cache:
                logger.error(f"Erro ao ler cache local: {str(e_cache)}")
        
        return None

def extrair_datas_referencia(soup):
    """
    Tenta encontrar as datas de referência literais do texto da página HTML.
    Caso a Receita mude o label levemente, a extração regex procura por datas DD/MM/AAAA.
    """
    texto_pagina = soup.get_text()
    data_declaracoes = "13/04/2026" # Fallback conservador temporal no caso de erro de regex específico
    data_darfs = "13/04/2026"
    
    match_dec = re.search(r'(?:recupera|declara).*?(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE | re.DOTALL)
    match_darf = re.search(r'(?:darfs|pago).*?(\d{2}/\d{2}/\d{4})', texto_pagina, re.IGNORECASE | re.DOTALL)
    
    if match_dec:
        data_declaracoes = match_dec.group(1)
    if match_darf:
        data_darfs = match_darf.group(1)
        
    return data_declaracoes, data_darfs

def converter_moeda(valor_texto):
    if not valor_texto: return 0.0
    texto_limpo = re.sub(r'[^\d,-]', '', valor_texto).replace('.', '').replace(',', '.')
    try: return float(texto_limpo)
    except ValueError: return 0.0

def converter_percentual(valor_texto):
    if not valor_texto: return 0.0
    texto_limpo = re.sub(r'[^\d,-]', '', valor_texto).replace(',', '.')
    try: return float(texto_limpo)
    except ValueError: return 0.0

def localizar_tabela(soup):
    tabelas = soup.find_all("table")
    # Identifica a tabela correta buscando por municípios de PE
    for tabela in tabelas:
        if "RECIFE" in tabela.get_text().upper() and "JABOATAO" in tabela.get_text().upper():
            return tabela
    return None

def normalizar_cabecalhos(tabela):
    """Embora os cabeçalhos possam variar, extraímos de forma bruta via ordem padrão assumida na documentação"""
    pass

def extrair_municipios(tabela):
    linhas = tabela.find_all("tr")
    municipios = []
    
    for tr in linhas:
        colunas = tr.find_all(["td", "th"])
        if len(colunas) >= 11:
            textos = [td.get_text(strip=True) for td in colunas]
            nome_col1 = textos[0].upper().strip()
            
            if nome_col1 and nome_col1 != "MUNICÍPIO" and "TOTAL" not in nome_col1:
                try:
                    mun = {
                        "municipio": textos[0].strip(),
                        "potencial_destinacao_valor": converter_moeda(textos[1]),
                        "potencial_destinacao_contribuintes": converter_moeda(textos[2]),
                        "destinacoes_por_localidade_valor": converter_moeda(textos[3]),
                        "destinacoes_por_localidade_contribuintes": converter_moeda(textos[4]),
                        "valor_destinado_fundo": converter_moeda(textos[5]),
                        "quantidade_doacoes_declaradas": converter_moeda(textos[6]),
                        "percentual_crianca_adolescente": converter_percentual(textos[7]),
                        "percentual_pessoa_idosa": converter_percentual(textos[8]),
                        "darfs_pagos_valor": converter_moeda(textos[9]),
                        "quantidade_doacoes_pagas": converter_moeda(textos[10])
                    }
                    municipios.append(mun)
                except Exception as e:
                    logger.warning(f"Ignorando linha possivelmente inválida ({nome_col1}): {str(e)}")
                    continue
    return municipios

def gerar_base_bi(municipios, data_dec, data_darfs):
    base = []
    for m in municipios:
        m_copy = dict(m)
        m_copy["data_referencia_declaracoes"] = data_dec
        m_copy["data_referencia_darfs"] = data_darfs
        m_copy["fonte"] = "Receita Federal do Brasil"
        m_copy["data_processamento"] = datetime.now().isoformat()
        base.append(m_copy)
    return base

def gerar_json_recife(base_bi):
    recife_data = next((m for m in base_bi if "RECIFE" in m["municipio"].upper()), None)
    if not recife_data:
        return None
    
    pago = recife_data["darfs_pagos_valor"]
    potencial = recife_data["potencial_destinacao_valor"]
    destinado = recife_data["valor_destinado_fundo"]
    perc_crianca = recife_data["percentual_crianca_adolescente"]
    perc_idoso = recife_data["percentual_pessoa_idosa"]
    
    # METODOLOGIA: Opção B (Percentuais aplicados sobre DARFs PAGO). 
    # Justificativa: O valor pago é o montante financeiro efetivo que o fundo recebe.
    # Aplicar o percentual sobre a intenção da declaração geraria distorção contábil no dashboard financeiro final.
    est_crianca = round(pago * (perc_crianca / 100), 2)
    est_idoso = round(pago * (perc_idoso / 100), 2)
    
    taxa_conversao = (pago / destinado * 100) if destinado > 0 else 0.0
    taxa_aproveitamento = (pago / potencial * 100) if potencial > 0 else 0.0
    
    return {
        "municipio": recife_data["municipio"],
        "valor_arrecadado": pago,
        "qtd_doacoes_efetivadas": int(recife_data["quantidade_doacoes_pagas"]),
        "potencial_destinacao": potencial,
        "destinacoes_por_localidade": recife_data["destinacoes_por_localidade_valor"],
        "valor_destinado_declaracao": destinado,
        "qtd_doacoes_declaradas": int(recife_data["quantidade_doacoes_declaradas"]),
        "percentual_crianca_adolescente": perc_crianca,
        "percentual_pessoa_idosa": perc_idoso,
        "valor_estimado_crianca_adolescente": est_crianca,
        "valor_estimado_pessoa_idosa": est_idoso,
        "taxa_conversao_pagamento": round(taxa_conversao, 2),
        "taxa_aproveitamento_potencial": round(taxa_aproveitamento, 2),
        "data_referencia_declaracoes": recife_data["data_referencia_declaracoes"],
        "data_referencia_darfs": recife_data["data_referencia_darfs"],
        "fonte": recife_data["fonte"],
        "data_processamento": recife_data["data_processamento"],
        "status_atualizacao": "SUCESSO"
    }

def salvar_arquivos(base_bi, recife_json):
    """Salva os três formatos requeridos, sobrescrevendo apenas se houver sucesso."""
    try:
        # 1. Analítico JSON Completo
        with open(ARQUIVO_JSON_BI, 'w', encoding='utf-8') as f:
            json.dump(base_bi, f, ensure_ascii=False, indent=2)
            
        # 2. Analítico CSV Completo
        if base_bi:
            with open(ARQUIVO_CSV_BI, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=base_bi[0].keys())
                writer.writeheader()
                writer.writerows(base_bi)
                
        # 3. Frontend JSON Recife
        with open(ARQUIVO_JSON_SITE, 'w', encoding='utf-8') as f:
            json.dump(recife_json, f, ensure_ascii=False, indent=2)
            
        # 4. Frontend JSON Recife (Pasta Dist)
        caminho_dist = os.path.join("dist", ARQUIVO_JSON_SITE)
        if os.path.exists("dist"):
            with open(caminho_dist, 'w', encoding='utf-8') as f:
                json.dump(recife_json, f, ensure_ascii=False, indent=2)
            
        logger.info("Todos os artefatos salvos com sucesso na versão 2 (incluindo dist).")
        return True
    except Exception as e:
        logger.error({'error': str(e)}, "Erro gravíssimo ao persistir JSON/CSV no sistema de arquivos.")
        return False

def main():
    logger.info("Iniciando extração V2 do Contador do Bem")
    html = baixar_html(URL_RECEITA)
    
    if not html:
        logger.error(None, "Abordando fluxo. Falha no download. Arquivos locais anteriores serão mantidos intocados.")
        logger.error("Abordando fluxo. Falha no download. Arquivos locais anteriores serão mantidos intocados.")
        return
        
    soup = BeautifulSoup(html, "html.parser")
    tabela = localizar_tabela(soup)
    
    if not tabela:
        logger.error("Tabela base não existe ou estrutura mudou fortemente na Receita. Fluxo cancelado.")
        return
        
    data_dec, data_darfs = extrair_datas_referencia(soup)
    municipios = extrair_municipios(tabela)
    
    if len(municipios) < 10:
        logger.error("Quantidade anormalmente baixa de municípios. Bloqueando sobrescrita.")
        return
        
    base_bi = gerar_base_bi(municipios, data_dec, data_darfs)
    recife_json = gerar_json_recife(base_bi)
    
    if not recife_json or (recife_json["valor_arrecadado"] == 0 and "cache" not in html.lower()):
        logger.error("Recife não localizado ou dados zerados. Cancelando fluxo para evitar corrupção.")
        return
        
    salvar_arquivos(base_bi, recife_json)

if __name__ == "__main__":
    main()
