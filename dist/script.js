document.addEventListener('DOMContentLoaded', () => {
    carregarDados();
});

const formatadores = {
    moeda: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }),
    numero: new Intl.NumberFormat('pt-BR'),
    percentual: (valor) => valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%'
};

async function carregarDados() {
    try {
        const resposta = await fetch('../recife_contador.json');
        if (!resposta.ok) throw new Error(`Status da Requisição: ${resposta.status}`);
        
        const dados = await resposta.json();
        
        if(dados.status_atualizacao === "SUCESSO") {
            atualizarInterface(dados);
        } else {
            document.getElementById('status_atualizacao').textContent = 'FALHA INTERNA';
            document.getElementById('status_atualizacao').style.backgroundColor = 'red';
        }
    } catch (erro) {
        console.error('Erro na API de Dados:', erro);
        document.getElementById('fonte_dados').textContent = 'Serviço Indisponível';
        document.getElementById('status_atualizacao').textContent = 'OFFLINE';
        document.getElementById('status_atualizacao').style.backgroundColor = 'red';
    }
}

function atualizarInterface(dados) {
    // Bloco Principal de Arrecadação Reai (Pagos)
    animarValor('valor_arrecadado', dados.valor_arrecadado, formatadores.moeda);
    document.getElementById('qtd_doacoes_efetivadas').textContent = `${formatadores.numero.format(dados.qtd_doacoes_efetivadas)} doações pagas (DARF) convertidas em repasses`;
    
    // Cards Inferiores
    document.getElementById('taxa_conversao').textContent = formatadores.percentual(dados.taxa_conversao_pagamento);
    document.getElementById('perc_crianca').textContent = formatadores.percentual(dados.percentual_crianca_adolescente);
    document.getElementById('perc_idoso').textContent = formatadores.percentual(dados.percentual_pessoa_idosa);

    // Campos Transparentes Adicionais
    document.getElementById('potencial_destinacao').textContent = formatadores.moeda.format(dados.potencial_destinacao);
    document.getElementById('destinacoes_por_localidade').textContent = formatadores.moeda.format(dados.destinacoes_por_localidade);
    document.getElementById('valor_destinado_declaracao').textContent = formatadores.moeda.format(dados.valor_destinado_declaracao);
    document.getElementById('qtd_doacoes_declaradas').textContent = formatadores.numero.format(dados.qtd_doacoes_declaradas);

    // Metadata & Datas Transparentes
    document.getElementById('fonte_dados').textContent = dados.fonte;
    document.getElementById('status_atualizacao').textContent = dados.status_atualizacao;
    
    document.getElementById('data_ref_declaracoes').textContent = dados.data_referencia_declaracoes;
    document.getElementById('data_ref_darfs').textContent = dados.data_referencia_darfs;

    const dataProc = new Date(dados.data_processamento);
    document.getElementById('data_processamento').textContent = dataProc.toLocaleDateString('pt-BR') + ' ' + dataProc.toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'});
}

function animarValor(elementoId, valorFinal, formatadorFunc) {
    const elemento = document.getElementById(elementoId);
    let inicio = null;
    const duracao = 1500; 
    
    function step(timestamp) {
        if (!inicio) inicio = timestamp;
        const progresso = Math.min((timestamp - inicio) / duracao, 1);
        const progressoEasing = progresso === 1 ? 1 : 1 - Math.pow(2, -10 * progresso);
        const valorAtual = progressoEasing * valorFinal;
        
        elemento.textContent = formatadorFunc.format(valorAtual);

        if (progresso < 1) {
            window.requestAnimationFrame(step);
        } else {
            elemento.textContent = formatadorFunc.format(valorFinal); 
        }
    }
    window.requestAnimationFrame(step);
}
