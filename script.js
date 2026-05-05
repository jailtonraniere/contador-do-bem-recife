document.addEventListener('DOMContentLoaded', () => {
    carregarDados();
});

const formatadores = {
    moedaNum: new Intl.NumberFormat('pt-BR', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
    }),
    numero: new Intl.NumberFormat('pt-BR'),
    percentual: (valor) => {
        const decimals = valor % 1 === 0 ? 0 : 1;
        return valor.toLocaleString('pt-BR', { 
            minimumFractionDigits: decimals, 
            maximumFractionDigits: decimals 
        }) + '%';
    }
};

async function carregarDados() {
    console.log('Iniciando carga de dados...');
    try {
        const paths = ['./recife_contador.json', 'recife_contador.json'];
        let resposta = null;
        let dados = null;
        
        const cacheBuster = '?t=' + new Date().getTime();
        for (const path of paths) {
            try {
                resposta = await fetch(path + cacheBuster, { cache: "no-store" });
                if (resposta.ok) {
                    dados = await resposta.json();
                    break;
                }
            } catch (e) {}
        }

        if (!dados) throw new Error('Falha ao carregar dados.');
        
        if(dados.status_atualizacao === "SUCESSO") {
            atualizarInterface(dados);
        }
    } catch (erro) {
        console.error('Erro no carregamento:', erro);
    }
}

function atualizarInterface(dados) {
    // 1. Bloco Principal
    animarValor('valor_arrecadado', dados.valor_arrecadado, formatadores.moedaNum, '.amount');
    document.getElementById('qtd_doacoes_efetivadas').textContent = `${formatadores.numero.format(dados.qtd_doacoes_efetivadas)} doações pagas`;

    // 2. Cards de Distribuição
    animarValor('perc_crianca', dados.percentual_crianca_adolescente, { format: formatadores.percentual });
    document.getElementById('bar_crianca').style.width = `${dados.percentual_crianca_adolescente}%`;

    animarValor('perc_idoso', dados.percentual_pessoa_idosa, { format: formatadores.percentual });
    document.getElementById('bar_idoso').style.width = `${dados.percentual_pessoa_idosa}%`;

    // 3. Gauge de Conversão
    animarValor('taxa_conversao', dados.taxa_conversao_pagamento, { format: formatadores.percentual });
    atualizarGauge(dados.taxa_conversao_pagamento);

    // 4. Destinado na declaração 2026
    animarValor('valor_destinado', dados.valor_destinado_declaracao, formatadores.moedaNum, '.amount');

    // 5. Footer
    document.getElementById('fonte_dados').textContent = dados.fonte;
    const dataProc = new Date(dados.data_processamento);
    document.getElementById('data_processamento').textContent = dataProc.toLocaleDateString('pt-BR');
}

function atualizarGauge(percentual) {
    const gaugeBody = document.querySelector('.gauge-body');
    if (!gaugeBody) return;
    const graus = (percentual / 100) * 180;
    gaugeBody.style.background = `conic-gradient(from 270deg, var(--gauge-green) 0deg, var(--gauge-green) ${graus}deg, var(--gauge-track) ${graus}deg)`;
}

function animarValor(elementoId, valorFinal, formatador, seletorInterno = null) {
    const elementoPai = document.getElementById(elementoId);
    if (!elementoPai) return;

    const elementoAlvo = seletorInterno ? elementoPai.querySelector(seletorInterno) : elementoPai;
    if (!elementoAlvo) return;

    let inicio = null;
    const duracao = 1500;
    
    function step(timestamp) {
        if (!inicio) inicio = timestamp;
        const progresso = Math.min((timestamp - inicio) / duracao, 1);
        const progressoEasing = 1 - Math.pow(1 - progresso, 4);
        const valorAtual = progressoEasing * valorFinal;
        
        elementoAlvo.textContent = typeof formatador.format === 'function' ? 
            formatador.format(valorAtual) : formatador(valorAtual);

        if (progresso < 1) {
            window.requestAnimationFrame(step);
        } else {
            elementoAlvo.textContent = typeof formatador.format === 'function' ? 
                formatador.format(valorFinal) : formatador(valorFinal); 
        }
    }
    window.requestAnimationFrame(step);
}
