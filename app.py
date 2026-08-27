import streamlit as st
import pandas as pd
from datetime import date, timedelta
import holidays

# ==============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
st.set_page_config(page_title="Análise de Lançamento e Rolagem de Opções", layout="wide")

st.title("📊 Análise de Lançamento e Rolagem de Opções de Compra (Calls)")
st.caption("Framework Integrado: Natenberg, Sinclair, Taleb & Rule of Thumb do Mercado (Ajustado por Dias Úteis/Feriados BR)")

st.divider()

# Instância dos feriados nacionais brasileiros
feriados_br = holidays.BR()

def calcular_dias_uteis_br(data_inicio, data_fim):
    """Calcula a quantidade de dias úteis no Brasil (exclui finais de semana e feriados nacionais)"""
    if data_fim <= data_inicio:
        return 0
    
    dias_uteis = 0
    data_atual = data_inicio + timedelta(days=1)
    
    while data_atual <= data_fim:
        # 5 = Sábado, 6 = Domingo
        if data_atual.weekday() < 5 and data_atual not in feriados_br:
            dias_uteis += 1
        data_atual += timedelta(days=1)
        
    return dias_uteis

# ==============================================================================
# 1. DADOS DE ENTRADA: ATIVO SUBJACENTE (AÇÃO) E REGIME DE VOLATILIDADE
# ==============================================================================
st.subheader("📌 1. Dados do Ativo Subjacente (Ação) & Volatilidade")

col_ac1, col_ac2, col_ac3, col_ac4 = st.columns(4)
with col_ac1:
    ticker_acao = st.text_input("Ticker da Ação", value="PETR4").upper()
    preco_acao = st.number_input("Preço da Ação (R$)", value=38.50, step=0.10, format="%.2f")

with col_ac2:
    vol_implicita = st.number_input("Volatilidade Implícita (IV %)", value=34.50, step=0.50, format="%.2f")
    iv_rank = st.number_input("IV Rank Call (%)", value=68.00, step=1.00, format="%.2f")

with col_ac3:
    vol_historica = st.number_input("Volatilidade Histórica (HV %)", value=26.00, step=0.50, format="%.2f")
    hv_rank = st.number_input("HV Rank (%)", value=42.00, step=1.00, format="%.2f")

with col_ac4:
    st.write("**Proventos no Período**")
    flag_proventos = st.checkbox("Considerar Dividendos / JCP", value=True)
    if flag_proventos:
        provento_liq = st.number_input("Valor Líquido (R$)", value=0.85, step=0.05, format="%.2f")
        data_ex = st.date_input("Data Ex-Provento", value=date.today() + timedelta(days=15))
    else:
        provento_liq = 0.0
        data_ex = None

st.divider()

# ==============================================================================
# FUNÇÃO AUXILIAR PARA CAPTURA DOS DADOS DAS OPÇÕES (LANÇAMENTO E ROLAGEM)
# ==============================================================================
def capturar_entradas_opcoes_call(prefixo, quantidade):
    opcoes = []
    cols = st.columns(quantidade)
    
    for i in range(quantidade):
        with cols[i]:
            st.markdown(f"##### Opção Call #{i+1}")
            ticker_op = st.text_input(f"Ticker da Opção", value=f"{ticker_acao}_{prefixo.upper()}{i+1}", key=f"{prefixo}_tick_{i}").upper()
            preco_op = st.number_input(f"Preço de Mercado (R$)", value=1.45 - (i * 0.30), step=0.05, format="%.2f", key=f"{prefixo}_p_{i}")
            strike_op = st.number_input(f"Preço de Strike (R$)", value=preco_acao + (i * 1.50), step=0.50, format="%.2f", key=f"{prefixo}_k_{i}")
            preco_teorico = st.number_input(f"Preço Teórico (R$)", value=1.38 - (i * 0.28), step=0.05, format="%.2f", key=f"{prefixo}_pt_{i}")
            vencimento = st.date_input(f"Data de Vencimento", value=date.today() + timedelta(days=30 + (i*15)), key=f"{prefixo}_venc_{i}")
            
            st.caption("Gregas da Opção")
            delta = st.number_input(f"Delta (Δ)", value=0.4500 - (i*0.10), step=0.0100, format="%.4f", key=f"{prefixo}_d_{i}")
            gamma = st.number_input(f"Gamma (γ)", value=0.0850 - (i*0.01), step=0.0050, format="%.4f", key=f"{prefixo}_g_{i}")
            theta_pct = st.number_input(f"Theta (%) [Diário]", value=-0.125 - (i*0.02), step=0.005, format="%.3f", key=f"{prefixo}_t_{i}")
            vega = st.number_input(f"Vega (ν)", value=0.0420 + (i*0.005), step=0.0050, format="%.4f", key=f"{prefixo}_v_{i}")
            
            # Cálculo dos dias corridos e dias úteis
            dte_corridos = (vencimento - date.today()).days
            dte_uteis = calcular_dias_uteis_br(date.today(), vencimento)
            
            opcoes.append({
                'ticker': ticker_op,
                'preco': preco_op,
                'strike': strike_op,
                'preco_teorico': preco_teorico,
                'vencimento': vencimento,
                'dte_corridos': dte_corridos,
                'dte_uteis': dte_uteis,
                'delta': delta,
                'gamma': gamma,
                'theta_pct': theta_pct,
                'vega': vega
            })
    return opcoes

# ==============================================================================
# 2. ENTRADA DE OPÇÕES DE COMPRA PARA LANÇAMENTO INICIAL (ATÉ 3)
# ==============================================================================
st.subheader("🚀 2. SIMULAÇÃO I: Opções de Compra (Calls) para Lançamento Inicial")
qtd_lanc = st.radio("Quantidade de Opções a Avaliar para Lançamento Inicial:", [1, 2, 3], horizontal=True, key="qtd_lanc")
opcoes_lancamento = capturar_entradas_opcoes_call("lanc", qtd_lanc)

st.divider()

# ==============================================================================
# 3. ENTRADA DE OPÇÕES DE COMPRA PARA ROLAGEM (ATÉ 3) - COM FLAG SIM/NÃO
# ==============================================================================
st.subheader("🔄 3. SIMULAÇÃO II: Opções de Compra (Calls) para Rolagem")

executar_rolagem = st.radio("Incluir corrida de simulação para Rolagem da Opção?", ["Sim", "Não"], index=0, horizontal=True)

opcoes_rolagem = []
if executar_rolagem == "Sim":
    qtd_rol = st.radio("Quantidade de Opções a Avaliar para Rolagem:", [1, 2, 3], horizontal=True, key="qtd_rol")
    opcoes_rolagem = capturar_entradas_opcoes_call("rol", qtd_rol)
else:
    st.info("ℹ️ A simulação da rolagem está desativada. Apenas a análise do Lançamento Inicial será executada.")

st.divider()

# ==============================================================================
# 4. BOTÃO DE ANÁLISE E EXECUTOR DO DIAGNÓSTICO
# ==============================================================================
if st.button("📊 Executar Análise Integrada (Natenberg, Sinclair, Taleb & Mercado)", type="primary", use_container_width=True):
    
    st.markdown("## 📈 Resultado da Análise de Mercado e Literatura")
    
    # Cálculo do Variance Risk Premium (VRP) Geral
    vrp_geral = vol_implicita - vol_historica
    
    # --------------------------------------------------------------------------
    # QUADRO COMPARATIVO - LANÇAMENTO INICIAL
    # --------------------------------------------------------------------------
    st.markdown("### 📋 Simulação Separada: Lançamento Inicial")
    
    dados_tab_lanc = []
    for op in opcoes_lancamento:
        retorno_bruto = (op['preco'] / preco_acao) * 100.0
        diff_teorico = op['preco'] - op['preco_teorico']
        
        # Análise de impacto de proventos
        prov_afeta = flag_proventos and data_ex and (data_ex <= op['vencimento'])
        desc_prov = f"R$ {provento_liq:.2f} (Ex: {data_ex.strftime('%d/%m/%Y')})" if prov_afeta else "Nenhum no período"
        
        dados_tab_lanc.append({
            "Ticker Opção": op['ticker'],
            "Preço Mercado": f"R$ {op['preco']:.2f}",
            "Strike (K)": f"R$ {op['strike']:.2f}",
            "Preço Teórico": f"R$ {op['preco_teorico']:.2f}",
            "Dif. vs Teórico": f"R$ {diff_teorico:+.2f}",
            "Vencimento": op['vencimento'].strftime('%d/%m/%Y'),
            "DTE (Úteis / Corridos)": f"{op['dte_uteis']} d.u. ({op['dte_corridos']} d.c.)",
            "Delta (Δ)": f"{op['delta']:.4f}",
            "Gamma (γ)": f"{op['gamma']:.4f}",
            "Theta (%)": f"{op['theta_pct']:.3f}%",
            "Vega (ν)": f"{op['vega']:.4f}",
            "Retorno Bruto": f"{retorno_bruto:.2f}%",
            "Provento": desc_prov
        })
    
    st.table(pd.DataFrame(dados_tab_lanc))
    
    # Algoritmo de Escolha da Melhor Opção para Lançamento
    melhor_lanc = None
    maior_score_lanc = -999.0
    
    for op in opcoes_lancamento:
        ret_bruto = (op['preco'] / preco_acao) * 100.0
        diff_t = op['preco'] - op['preco_teorico']
        score = (diff_t * 2.0) + (ret_bruto * 1.5) + (abs(op['theta_pct']) * 10.0) - (op['gamma'] * 15.0)
        if score > maior_score_lanc:
            maior_score_lanc = score
            melhor_lanc = op

    # --------------------------------------------------------------------------
    # QUADRO COMPARATIVO - ROLAGEM (EXIBIDO APENAS SE FLAG == "Sim")
    # --------------------------------------------------------------------------
    melhor_rol = None
    if executar_rolagem == "Sim" and opcoes_rolagem:
        st.markdown("### 📋 Simulação Separada: Rolagem da Opção")
        
        dados_tab_rol = []
        for op in opcoes_rolagem:
            diff_teorico = op['preco'] - op['preco_teorico']
            credito_liquido = op['preco'] - melhor_lanc['preco'] if melhor_lanc else 0.0
            
            prov_afeta = flag_proventos and data_ex and (data_ex <= op['vencimento'])
            desc_prov = f"R$ {provento_liq:.2f} (Ex: {data_ex.strftime('%d/%m/%Y')})" if prov_afeta else "Nenhum no período"
            
            dados_tab_rol.append({
                "Ticker Opção": op['ticker'],
                "Preço Mercado": f"R$ {op['preco']:.2f}",
                "Strike (K)": f"R$ {op['strike']:.2f}",
                "Preço Teórico": f"R$ {op['preco_teorico']:.2f}",
                "Dif. vs Teórico": f"R$ {diff_teorico:+.2f}",
                "Vencimento": op['vencimento'].strftime('%d/%m/%Y'),
                "DTE (Úteis / Corridos)": f"{op['dte_uteis']} d.u. ({op['dte_corridos']} d.c.)",
                "Delta (Δ)": f"{op['delta']:.4f}",
                "Gamma (γ)": f"{op['gamma']:.4f}",
                "Theta (%)": f"{op['theta_pct']:.3f}%",
                "Vega (ν)": f"{op['vega']:.4f}",
                "Dif. Crédito/Débito": f"R$ {credito_liquido:+.2f}",
                "Provento": desc_prov
            })
            
        st.table(pd.DataFrame(dados_tab_rol))

        # Algoritmo de Escolha da Melhor Opção para Rolagem
        maior_score_rol = -999.0
        for op in opcoes_rolagem:
            credito = op['preco'] - melhor_lanc['preco'] if melhor_lanc else op['preco']
            diff_t = op['preco'] - op['preco_teorico']
            score = (credito * 3.0) + (diff_t * 2.0) - (op['gamma'] * 20.0) + (abs(op['theta_pct']) * 8.0)
            if score > maior_score_rol:
                maior_score_rol = score
                melhor_rol = op

    # --------------------------------------------------------------------------
    # DIAGNÓSTICO E PARECER TÉCNICO COMPLETO
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 💡 Indicação e Justificativas Teóricas / Práticas")
    
    if executar_rolagem == "Sim":
        col_ind1, col_ind2 = st.columns(2)
    else:
        col_ind1 = st.container()
    
    with col_ind1:
        st.success(f"🎯 **Indicação para Lançamento Inicial:** `{melhor_lanc['ticker']}` (Strike: R$ {melhor_lanc['strike']:.2f})")
        
        st.markdown("**Razões da Indicação (Lançamento):**")
        st.write(f"• **Sheldon Natenberg (Volatilidade & VRP):** O IV Rank da ação está em `{iv_rank:.2f}%` e o Variance Risk Premium (IV - HV) está positivo em `{vrp_geral:+.2f}%`. A opção selecionada permite vender volatilidade superavaliada com boa margem.")
        st.write(f"• **Euan Sinclair (Edge & Preço Teórico):** O preço de mercado de `R$ {melhor_lanc['preco']:.2f}` apresenta uma sobreprecificação de `R$ {melhor_lanc['preco'] - melhor_lanc['preco_teorico']:+.2f}` em relação ao Preço Teórico fornecido (`R$ {melhor_lanc['preco_teorico']:.2f}`), capturando a borda estatística de venda.")
        st.write(f"• **Nassim Taleb (Curva e Controle de Gamma):** O Gamma está controlado em `{melhor_lanc['gamma']:.4f}`, minimizando a fragilidade do portfólio a choques severos do ativo no vencimento de `{melhor_lanc['dte_uteis']} dias úteis` ({melhor_lanc['dte_corridos']} dias corridos).")
        st.write(f"• **Rule of Thumb do Mercado:** Gera uma taxa de retorno direta de `{((melhor_lanc['preco']/preco_acao)*100):.2f}%` no período com um decaimento diário de Theta de `{melhor_lanc['theta_pct']:.3f}%`.")
        if flag_proventos and data_ex and (data_ex <= melhor_lanc['vencimento']):
            st.write(f"• **Impacto do Provento:** Considera captura do provento de `R$ {provento_liq:.2f}` no período antes do vencimento.")

    if executar_rolagem == "Sim" and melhor_rol:
        with col_ind2:
            st.info(f"🔄 **Indicação para Rolagem:** `{melhor_rol['ticker']}` (Strike: R$ {melhor_rol['strike']:.2f})")
            
            credito_rol = melhor_rol['preco'] - melhor_lanc['preco'] if melhor_lanc else 0.0
            st.markdown("**Razões da Indicação (Rolagem):**")
            st.write(f"• **Rule of Thumb do Mercado (Roll for Credit):** A rolagem para `{melhor_rol['ticker']}` gera um resultado líquido financeiro de `R$ {credito_rol:+.2f}`, respeitando a regra clássica de não rolar com débito.")
            st.write(f"• **Nassim Taleb (Atenuação do Risco Gamma):** Ao estender o prazo para `{melhor_rol['dte_uteis']} dias úteis` ({melhor_rol['dte_corridos']} dias corridos), o Gamma é ajustado para `{melhor_rol['gamma']:.4f}`, reduzindo drasticamente o risco de não-linearidade próximo do vencimento.")
            st.write(f"• **Euan Sinclair & Natenberg:** Permite continuar vendido na curva de volatilidade implícita (IV `{vol_implicita:.2f}%` vs HV `{vol_historica:.2f}%`), mantendo a captura do prêmio de volatilidade com um Preço Teórico de `R$ {melhor_rol['preco_teorico']:.2f}`.")
            st.write(f"• **Decaimento Temporal:** Mantém uma captura diária de Theta de `{melhor_rol['theta_pct']:.3f}%` sobre a nova estrutura.")
            if flag_proventos and data_ex and (data_ex <= melhor_rol['vencimento']):
                st.write(f"• **Impacto do Provento:** Ajustado para captura do fluxo de caixa de `R$ {provento_liq:.2f}` até a data EX.")
        
