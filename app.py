import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, timedelta
import holidays

# ==============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Análise de Venda Coberta de Calls",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Análise de Venda Coberta de Calls")
st.caption("Framework Quantitativo Integrado: Natenberg, Sinclair, Taleb & Mercado B3 (Ajustado por Dias Úteis/Feriados BR)")

st.markdown("""
> **Fundamentação Teórica Integrada:**
> * **Sheldon Natenberg (*Option Volatility and Pricing*):** Explora a dinâmica de *Volatility Skew*, *Variance Risk Premium* ($VRP = IV - HV$) e a assimetria a favor do vendedor de volatilidade em regimes de IV Rank elevado.
> * **Euan Sinclair (*Option Trading* & *Positional Option Trading*):** Foco rigoroso na identificação de *Edge* estatístico comparando o preço de mercado da opção com o Preço Teórico (*Fair Value*) para garantir expectativa matemática positiva ($E[X] > 0$).
> * **Nassim Nicholas Taleb (*Dynamic Hedging*):** Gestão rigorosa de convexidade, risco de exercício antecipado em opções americanas e atenuação da fragilidade ao vender *Gamma* curto perto do vencimento.
""")

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
        if data_atual.weekday() < 5 and data_atual not in feriados_br:
            dias_uteis += 1
        data_atual += timedelta(days=1)
    return dias_uteis

@st.cache_data(ttl=300)
def obter_preco_acao_yfinance(ticker):
    """Obtém preço atualizado do ticker na B3 via Yahoo Finance"""
    try:
        ticker_b3 = f"{ticker.upper()}.SA"
        dados = yf.Ticker(ticker_b3)
        fast_info = dados.fast_info
        preco = fast_info.last_price
        if preco is not None and not np.isnan(preco):
            return float(preco)
        hist = dados.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    defaults = {"PETR4": 38.50, "VALE3": 62.10, "BBDC4": 14.80, "BBAS3": 27.40, "ITUB4": 35.20}
    return defaults.get(ticker.upper(), 30.00)

# ==============================================================================
# 1. PARÂMETROS DO ATIVO SUBJACENTE (AÇÃO) E REGIME DE VOLATILIDADE
# ==============================================================================
st.subheader("📌 1. Ativo Subjacente (Ação B3) & Regime de Volatilidade")

lista_acoes = ["PETR4", "VALE3", "BBDC4", "BBAS3", "ITUB4"]

col_ac1, col_ac2, col_ac3, col_ac4 = st.columns(4)

with col_ac1:
    ticker_acao = st.selectbox("Ticker da Ação (B3)", options=lista_acoes, index=0)
    preco_auto = obter_preco_acao_yfinance(ticker_acao)
    preco_acao = st.number_input(
        f"Preço da Ação (R$) [Fonte B3 / BVMF:{ticker_acao}]",
        value=float(preco_auto),
        step=0.10,
        format="%.2f",
        help="Preço puxado automaticamente da B3 via API. Editável."
    )

with col_ac2:
    vol_implicita = st.number_input("Volatilidade Implícita IV (%)", value=34.50, step=0.50, format="%.2f")
    iv_rank = st.number_input("IV Rank Call (%)", value=68.00, step=1.00, format="%.2f")

with col_ac3:
    vol_historica = st.number_input("Volatilidade Histórica HV (%)", value=26.00, step=0.50, format="%.2f")
    hv_rank = st.number_input("HV Rank (%)", value=42.00, step=1.00, format="%.2f")

with col_ac4:
    st.write("**Proventos no Período**")
    flag_proventos = st.checkbox("Considerar Dividendos / JCP no período", value=True)
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
def capturar_entradas_opcoes_call(prefixo, quantidade, modo_rolagem=False):
    opcoes = []
    cols = st.columns(quantidade)
    
    for i in range(quantidade):
        with cols[i]:
            titulo_box = f"Opção Call #{i+1}" if not modo_rolagem else (f"Opção Já Lançada" if quantidade==1 else f"Opção Call #{i+1}")
            st.markdown(f"##### {titulo_box}")
            ticker_op = st.text_input(f"Ticker da Opção", value=f"{ticker_acao}_CALL{i+1}", key=f"{prefixo}_tick_{i}").upper()
            estilo_op = st.selectbox(f"Estilo do Exercício", options=["Americana", "Europeia"], index=0, key=f"{prefixo}_est_{i}")
            preco_op = st.number_input(f"Preço de Mercado (R$)", value=1.45 - (i * 0.30), step=0.05, format="%.2f", key=f"{prefixo}_p_{i}")
            strike_op = st.number_input(f"Preço de Strike (R$)", value=preco_acao + (i * 1.50), step=0.50, format="%.2f", key=f"{prefixo}_k_{i}")
            preco_teorico = st.number_input(f"Preço Teórico / Fair Value (R$)", value=1.38 - (i * 0.28), step=0.05, format="%.2f", key=f"{prefixo}_pt_{i}", help="Modelo Black-Scholes (Europeia) ou Binarial/Bjerksund-Stensland (Americana)")
            
            dias_uteis_input = st.number_input(
                f"Dias Úteis Faltantes (d.u.)",
                value=int(21 + (i * 10)),
                step=1,
                min_value=1,
                key=f"{prefixo}_du_{i}"
            )
            vencimento_calculado = date.today() + timedelta(days=int(dias_uteis_input * 1.45))
            
            st.caption("Gregas da Opção (Natenberg & Taleb)")
            delta = st.number_input(f"Delta (Δ)", value=0.4500 - (i * 0.10), step=0.0100, format="%.4f", key=f"{prefixo}_d_{i}")
            gamma = st.number_input(f"Gamma (γ)", value=0.0850 - (i * 0.0100), step=0.0050, format="%.4f", key=f"{prefixo}_g_{i}")
            theta_pct = st.number_input(f"Theta (%) [Diário]", value=-0.125 - (i * 0.020), step=0.005, format="%.3f", key=f"{prefixo}_t_{i}")
            vega = st.number_input(f"Vega (ν)", value=0.0420 + (i * 0.0050), step=0.0050, format="%.4f", key=f"{prefixo}_v_{i}")
            
            opcoes.append({
                'ticker': ticker_op,
                'estilo': estilo_op,
                'preco': preco_op,
                'strike': strike_op,
                'preco_teorico': preco_teorico,
                'vencimento': vencimento_calculado,
                'dte_uteis': int(dias_uteis_input),
                'delta': delta,
                'gamma': gamma,
                'theta_pct': theta_pct,
                'vega': vega
            })
    return opcoes

# ==============================================================================
# 2. SIMULAÇÃO I: LANÇAMENTO INICIAL DE CALLS (ATÉ 3 OPÇÕES)
# ==============================================================================
st.subheader("🚀 2. SIMULAÇÃO I: Options Calls para Lançamento Inicial")
qtd_lanc = st.radio("Quantidade de opções a avaliar para Lançamento Inicial:", [1, 2, 3], horizontal=True, key="qtd_lanc")

# ==============================================================================
# 3. SIMULAÇÃO II: FLAG E ENTRADA PARA ROLAGEM DA OPÇÃO
# ==============================================================================
st.divider()
st.subheader("🔄 3. SIMULAÇÃO II: Corrida de Rolagem da Opção")

executar_rolagem = st.checkbox("Ativar corrida de simulação para Rolagem da Opção", value=False)

if executar_rolagem:
    st.warning("⚠️ **Regra de Rolagem Ativa:** Na Simulação I, insira **apenas 1 opção** (representando a opção já lançada na sua carteira). Na Simulação II abaixo, insira as opções candidatas para a rolagem.")
    opcoes_lancamento = capturar_entradas_opcoes_call("lanc", 1, modo_rolagem=True)
    
    qtd_rol = st.radio("Quantidade de opções a avaliar para Rolagem:", [1, 2, 3], horizontal=True, key="qtd_rol")
    opcoes_rolagem = capturar_entradas_opcoes_call("rol", qtd_rol)
else:
    opcoes_lancamento = capturar_entradas_opcoes_call("lanc", qtd_lanc)
    opcoes_rolagem = []

st.divider()

# ==============================================================================
# 4. BOTÃO ÚNICO DE EXECUÇÃO DA SIMULAÇÃO
# ==============================================================================
if st.button("Qual é a melhor call para venda coberta?", type="primary", use_container_width=True):
    
    st.markdown("## 📊 Diagnóstico Quantitativo e Recomendação da Literatura")
    
    vrp_geral = vol_implicita - vol_historica
    
    # --------------------------------------------------------------------------
    # MODALIDADE 1: APENAS SIMULAÇÃO I (LANÇAMENTO INICIAL)
    # --------------------------------------------------------------------------
    if not executar_rolagem:
        st.markdown("### 📋 Análise Comparativa: Lançamento Inicial de Calls")
        
        dados_tab_lanc = []
        for op in opcoes_lancamento:
            retorno_bruto = (op['preco'] / preco_acao) * 100.0
            diff_teorico = op['preco'] - op['preco_teorico']
            
            prov_afeta = flag_proventos and data_ex and (data_ex <= op['vencimento'])
            desc_prov = f"R$ {provento_liq:.2f} (Ex: {data_ex.strftime('%d/%m/%Y')})" if prov_afeta else "Nenhum no período"
            
            dados_tab_lanc.append({
                "Ticker Opção": op['ticker'],
                "Estilo": op['estilo'],
                "Preço Mercado": f"R$ {op['preco']:.2f}",
                "Strike (K)": f"R$ {op['strike']:.2f}",
                "Preço Teórico": f"R$ {op['preco_teorico']:.2f}",
                "Edge vs Teórico": f"R$ {diff_teorico:+.2f}",
                "DTE Úteis": f"{op['dte_uteis']} d.u.",
                "Delta (Δ)": f"{op['delta']:.4f}",
                "Gamma (γ)": f"{op['gamma']:.4f}",
                "Theta (%)": f"{op['theta_pct']:.3f}%",
                "Taxa Bruta": f"{retorno_bruto:.2f}%",
                "Provento": desc_prov
            })
        
        st.table(pd.DataFrame(dados_tab_lanc))
        
        melhor_lanc = None
        maior_score = -9999.0
        
        for op in opcoes_lancamento:
            edge_sinclair = op['preco'] - op['preco_teorico']
            taxa_retorno = (op['preco'] / preco_acao) * 100.0
            theta_capture = abs(op['theta_pct'])
            gamma_risk = op['gamma']
            
            score = (edge_sinclair * 3.0) + (taxa_retorno * 2.0) + (theta_capture * 10.0) + (vrp_geral * 0.4) - (gamma_risk * 25.0)
            if score > maior_score:
                maior_score = score
                melhor_lanc = op

        st.markdown("---")
        st.success(f"🎯 **RECOMENDAÇÃO DE LANÇAMENTO INICIAL:** `{melhor_lanc['ticker']}` ({melhor_lanc['estilo']} | Strike: R$ {melhor_lanc['strike']:.2f} | Prêmio: R$ {melhor_lanc['preco']:.2f})")
        
        diff_edge = melhor_lanc['preco'] - melhor_lanc['preco_teorico']
        taxa_op = (melhor_lanc['preco'] / preco_acao) * 100.0
        
        st.markdown("### 💡 Racional Técnico e Fundamentação Teórica:")
        st.write(f"• **Sheldon Natenberg (Volatilidade & VRP):** O IV Rank da ação está em `{iv_rank:.2f}%` e o *Variance Risk Premium* (IV - HV) está positivo em `{vrp_geral:+.2f}%`. O cenário valida a venda de volatilidade inflacionada.")
        st.write(f"• **Euan Sinclair (Edge Estatístico & Preço Teórico):** A opção `{melhor_lanc['ticker']}` entrega um *Edge* de `R$ {diff_edge:+.2f}` frente ao Preço Teórico (`R$ {melhor_lanc['preco_teorico']:.2f}`). Para Sinclair, vender acima do Fair Value é o requisito essencial para expectativa matemática positiva ($E[X] > 0$).")
        st.write(f"• **Nassim Nicholas Taleb (Estilo & Risco Gamma):** Opção do estilo **{melhor_lanc['estilo']}**. Taleb alerta que Calls Americanas com dividendos iminentes possuem risco de exercício antecipado (*early exercise*) se o valor temporal for inferior ao dividendo. Mantém-se o Gamma sob controle em `{melhor_lanc['gamma']:.4f}`.")
        st.write(f"• **Yield & Decaimento:** Retorno bruto imediato de `{taxa_op:.2f}%` sobre a ação com captura diária de Theta de `{melhor_lanc['theta_pct']:.3f}%`.")
        if flag_proventos and data_ex and (data_ex <= melhor_lanc['vencimento']):
            st.write(f"• **Impacto de Proventos:** A custódia assegura o fluxo de `R$ {provento_liq:.2f}` antes do exercício (Data Ex: {data_ex.strftime('%d/%m/%Y')}).")

    # --------------------------------------------------------------------------
    # MODALIDADE 2: SIMULAÇÃO II (ROLAGEM DA OPÇÃO LANCEI X OPÇÕES CANDIDATAS)
    # --------------------------------------------------------------------------
    else:
        op_atual = opcoes_lancamento[0]
        
        st.markdown(f"### 📋 Posição Atual (Opção Lançada): `{op_atual['ticker']}` ({op_atual['estilo']}) | Strike: R$ {op_atual['strike']:.2f} | Preço Mercado Atual: R$ {op_atual['preco']:.2f}")
        st.markdown("### 📋 Análise Comparativa para Rolagem da Opção")
        
        dados_tab_rol = []
        for op in opcoes_rolagem:
            credito_liquido = op['preco'] - op_atual['preco']
            diff_teorico = op['preco'] - op['preco_teorico']
            
            prov_afeta = flag_proventos and data_ex and (data_ex <= op['vencimento'])
            desc_prov = f"R$ {provento_liq:.2f} (Ex: {data_ex.strftime('%d/%m/%Y')})" if prov_afeta else "Nenhum no período"
            
            dados_tab_rol.append({
                "Ticker Rolagem": op['ticker'],
                "Estilo": op['estilo'],
                "Preço Mercado": f"R$ {op['preco']:.2f}",
                "Strike (K)": f"R$ {op['strike']:.2f}",
                "Crédito / Débito Líquido": f"R$ {credito_liquido:+.2f}",
                "Preço Teórico": f"R$ {op['preco_teorico']:.2f}",
                "Edge vs Teórico": f"R$ {diff_teorico:+.2f}",
                "DTE Úteis": f"{op['dte_uteis']} d.u.",
                "Delta (Δ)": f"{op['delta']:.4f}",
                "Gamma (γ)": f"{op['gamma']:.4f}",
                "Theta (%)": f"{op['theta_pct']:.3f}%",
                "Provento": desc_prov
            })
        
        st.table(pd.DataFrame(dados_tab_rol))
        
        melhor_rol = None
        maior_score_rol = -9999.0
        
        for op in opcoes_rolagem:
            credito = op['preco'] - op_atual['preco']
            edge_sinclair = op['preco'] - op['preco_teorico']
            gamma_risk = op['gamma']
            theta_capture = abs(op['theta_pct'])
            
            fator_credito = (credito * 10.0) if credito >= 0 else (credito * 50.0)
            
            score = fator_credito + (edge_sinclair * 3.0) + (theta_capture * 8.0) - (gamma_risk * 30.0)
            if score > maior_score_rol:
                maior_score_rol = score
                melhor_rol = op

        st.markdown("---")
        credito_final = melhor_rol['preco'] - op_atual['preco']
        
        if credito_final >= 0:
            st.success(f"🔄 **RECOMENDAÇÃO DE ROLAGEM A CRÉDITO:** Rolar `{op_atual['ticker']}` ➔ `{melhor_rol['ticker']}` ({melhor_rol['estilo']} | Strike: R$ {melhor_rol['strike']:.2f} | Crédito Líquido: **R$ {credito_final:+.2f}**)")
        else:
            st.warning(f"⚠️ **ATENÇÃO PARA ROLAGEM:** A opção `{melhor_rol['ticker']}` é a melhor opção entre as avaliadas, porém resulta em Débito Líquido de **R$ {credito_final:+.2f}**.")
            
        st.markdown("### 💡 Racional Técnico e Fundamentação Teórica da Rolagem:")
        st.write(f"• **Regra do Mercado (Roll for Credit):** Operação gerando `R$ {credito_final:+.2f}` por contrato. Evita-se rolar a débito para não consumir o *yield* base.")
        st.write(f"• **Nassim Nicholas Taleb (Atenuação do Risco Gamma & Exercício):** A substituição reduz o Gamma de `{op_atual['gamma']:.4f}` para `{melhor_rol['gamma']:.4f}` ao estender o prazo para `{melhor_rol['dte_uteis']} d.u.`. Como a nova Call é **{melhor_rol['estilo']}**, o risco de exercício antecipado deve ser monitorado se houver proventos superiores ao prêmio remanescente.")
        st.write(f"• **Sheldon Natenberg & Euan Sinclair (Edge em Novo Vencimento):** Explora a volatilidade inflacionada (IV Rank `{iv_rank:.2f}%`) capturando *Edge* de `R$ {melhor_rol['preco'] - melhor_rol['preco_teorico']:+.2f}` frente ao Preço Teórico.")
        
