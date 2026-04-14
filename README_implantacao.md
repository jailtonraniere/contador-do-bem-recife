# Projeto BI e Contador do Bem - Versão 2.0 (Transparência Oficial)
Solução de arquitetura de dados e interface para coleta da base *"Recibo de Destinações e Pagamentos - IRPF"* da Receita Federal.

## 🎯 Objetivo da Versão 2
- Eliminação do conceito de "Meta", focando 100% em transparência na prestação de contas real.
- Maior robustez garantindo que *NENHUM dado fictício/mock* entra no ambiente. Se a coleta falha (exemplo: site da receita do governo cai), o pipeline congela (bloqueia gravação), mantendo a integridade da data da última coleta bem-sucedida.
- Criação de uma matriz dupla de saída: O Front-end web ficou extremamente leve puxando apenas as linhas da cidade "Recife", enquanto as equipes de tecnologia ganharam uma base CSV/JSON analítica de todos os +180 municípios do estado para jogar no ambiente de Business Intelligence (PowerBI/Metabase).

## 📊 Metodologia de Cálculo 
**Distribuição dos Públicos "Idoso" vs "Crianças"**:
Conforme documentado no script pipeline `coletor_receita_v2.py`, optou-se expressamente seguir a **Opção B (Percentuais aplicados sobre o valor pago via DARF, e não sobre o potencial/declarado)**. 

*Razão da Decisão Institucional*: Quando cruzamos percentuais de campanhas sociais na gestão pública, aplicar sobre métricas de "Declaração" que muitas vezes o cidadão não paga seria distorcer e inflar em dezenas de milhares de reais o dinheiro no cofre real dos Conselhos do Município. Aplicando 50% de idosos e 50% crianças diretamente em cima daqueles DARFs que **comprovadamente creditaram (foram pagos)**, o gestor de dados terá uma projeção contábil quase exata da conta final dos Fundos do município.

## 🖥️ Como Implantar
1. **Pipeline de Coleta Diário**:
   Suba o script `coletor_receita_v2.py` num servidor próprio via Cron, numa Lambda na nuvem, ou no Airflow/n8n da PCR. Exemplo de cron para rodar diariamente 18:00h:
   `0 18 * * * /usr/bin/python3 /caminho/coletor_receita_v2.py`
   *Dependências:* BeautifulSoup4.

2. **Componente Web (Widget)**:
   - Toda lógica estática institucional e CSS unificado estão nas 3 páginas (`index.html`, `style.css` e `script.js`). 
   - A equipe do site do Recife só precisará referenciar nas páginas de campanha a URL de onde os arquivos `recife_contador.json` estarão abrigados e expostos ao ar (via bucket S3 CDN por ex.), de forma totalmente imune ao tráfego.

3. **Dashboard/BI**:
   Aponte o driver de entrada do software de Dataviz da prefeitura diretamente para o `municipios_pe.csv`. Todos os dados essenciais estarão convertidos de string para formatação FLOAT compatível com SQL normalizado, prontos para dashboards dinâmicos.
