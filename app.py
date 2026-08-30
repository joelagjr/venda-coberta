import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date, datetime, timedelta
import holidays

# ==============================================================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Análise Avançada de Venda Coberta B3 - Calls Europeias",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Análise de Venda Coberta - Calls Europeias (Mesa Pro B3)")

# Inicialização do histórico na sessão
if "historico_simulacoes" not in st.session_state:
    st.session_state["historico_simulacoes"] = {}

feriados_br = holidays.BR()

@st.cache_data(ttl=300)
def obter_preco_acao_yfinance(ticker):
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
    defaults = {"BBAS3": 27.40, "BBDC4": 14.80, "ITUB4": 35.20, "PETR4": 38.50, "VALE3": 62.10}
    return defaults.get(ticker.upper(), 30.00)

# ==============================================================================
# 1. PARÂMETROS DO ATIVO SUBJACENTE E REGIME DE MERCADO
# ==============================================================================
st.subheader("📌 1. Ativo Subjacente, Volatilidade (OpçõesNet) & Macro B3")

lista_acoes = ["BBAS3", "BBDC4", "ITUB4", "PETR4", "VALE3"]
col_ac1, col_ac2, col_ac3, col_ac4 = st.columns(4)

with col_ac1:
    ticker_acao = st.selectbox("Ticker da Ação (B3)", options=lista_acoes, index=0)
    preco_auto = obter_preco_acao_yfinance(ticker_acao)
    preco_acao = st.number_input(f"Preço da Ação (R$) [{ticker_acao}]", value=float(preco_auto), step=0.10, format="%.2f")

with col_ac2:
    vol_implicita = st.number_input("Volatilidade Implícita IV (%)", value=34.50, step=0.50, format="%.2f")
    iv_rank = st.number_input("IV Rank (%)", value=68.00, step=1.00, format="%.2f")

with col_ac3:
    vol_historica = st.number_input("Volatilidade Histórica HV (%)", value=26.00, step=0.50, format="%.2f")
    taxa_cdi = st.number_input("Taxa CDI/Selic Anual (%)", value=10.75, step=0.25, format="%.2f")

with col_ac4:
    st.write("**Proventos no Período (Ajuste B3 Ex)**")
    flag_proventos = st.checkbox("Considerar Dividendos / JCP", value=True)
    if flag_proventos:
        provento_liq = st.number_input("Valor Líquido (R$)", value=0.85000000, step=0.01000000, format="%.8f")
        data_ex = st.date_input("Data Ex-Provento", value=date.today() + timedelta(days=15))
    else:
        provento_liq = 0.00000000
        data_ex = None

st.divider()

# ==============================================================================
# FUNÇÃO AUXILIAR DE CAPTURA DE OPÇÕES (EXCLUSIVO EUROPEIAS)
# ==============================================================================
def capturar_entradas_opcoes_call(prefixo, quantidade, modo_rolagem=False):
    opcoes = []
    cols = st.columns(quantidade)
    
    for i in range(quantidade):
        with cols[i]:
            titulo_box = f"Opção Call Europeia #{i+1}" if not modo_rolagem else ("Opção Lançada Atualmente" if quantidade==1 else f"Opção Call #{i+1}")
            st.markdown(f"##### {titulo_box}")
            ticker_op = st.text_input(f"Ticker da Opção", value=f"{ticker_acao}_CALL{i+1}", key=f"{prefixo}_tick_{i}").upper()
            preco_op = st.number_input(f"Preço de Mercado (R$)", value=1.45 - (i * 0.30), step=0.05, format="%.2f", key=f"{prefixo}_p_{i}")
            strike_op = st.number_input(f"Strike Nominal Atual (R$)", value=preco_acao + (i * 1.50), step=0.50, format="%.2f", key=f"{prefixo}_k_{i}")
            preco_teorico = st.number_input(f"Fair Value OpçõesNet (R$)", value=1.38 - (i * 0.28), step=0.05, format="%.2f", key=f"{prefixo}_pt_{i}")
            
            val_du_default = 8 if (modo_rolagem and prefixo == "lanc") else int(21 + (i * 10))
            dias_uteis_input = st.number_input(f"Dias Úteis Faltantes (d.u.)", value=val_du_default, step=1, min_value=1, key=f"{prefixo}_du_{i}")
            vencimento_calculado = date.today() + timedelta(days=int(dias_uteis_input * 1.45))
            
            st.caption("Gregas (OpçõesNet)")
            delta = st.number_input(f"Delta (Δ)", value=0.4500 - (i * 0.10), step=0.0100, format="%.4f", key=f"{prefixo}_d_{i}")
            gamma = st.number_input(f"Gamma (γ)", value=0.0850 + (0.05 if val_du_default <= 10 else 0.0), step=0.0050, format="%.4f", key=f"{prefixo}_g_{i}")
            theta_pct = st.number_input(f"Theta (%) [Diário]", value=-0.125 - (i * 0.020), step=0.005, format="%.3f", key=f"{prefixo}_t_{i}")
            vega = st.number_input(f"Vega (ν)", value=0.0420 + (i * 0.0050), step=0.0050, format="%.4f", key=f"{prefixo}_v_{i}")
            
            opcoes.append({
                'ticker': ticker_op,
                'estilo': 'Europeia',
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
# 2. SELEÇÃO DE MODALIDADE
# ==============================================================================
st.subheader("🚀 2. Seleção e Entrada das Opções Candidatas (Europeias)")
executar_rolagem = st.checkbox("Ativar Modo de Análise de Rolagem (Simulação II)", value=False)

if executar_rolagem:
    st.info("⚠️ Modo Rolagem: Insira os dados da opção europeia atualmente vendida e as opções candidatas para rolagem.")
    opcoes_lancamento = capturar_entradas_opcoes_call("lanc", 1, modo_rolagem=True)
    qtd_rol = st.radio("Quantidade de opções a avaliar para Rolagem:", [1, 2, 3], horizontal=True, key="qtd_rol")
    opcoes_rolagem = capturar_entradas_opcoes_call("rol", qtd_rol)
else:
    qtd_lanc = st.radio("Quantidade de opções a avaliar para Lançamento Inicial:", [1, 2, 3], horizontal=True, key="qtd_lanc")
    opcoes_lancamento = capturar_entradas_opcoes_call("lanc", qtd_lanc)
    opcoes_rolagem = []

st.divider()

# ==============================================================================
# 3. EXECUTAR DIAGNÓSTICO PROFISSIONAL
# ==============================================================================
if st.button("Executar Diagnóstico Profissional de Venda Coberta", type="primary", use_container_width=True):
    
    st.markdown("## 📊 Diagnóstico Quantitativo e Análise de Mesa")
    vrp_geral = vol_implicita - vol_historica
    timestamp_sim = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if not executar_rolagem:
        st.markdown("### 📋 Análise Comparativa: Lançamento Inicial (Calls Europeias)")
        dados_tab_lanc = []
        
        for op in opcoes_lancamento:
            edge = op['preco'] - op['preco_teorico']
            taxa_bruta = (op['preco'] / preco_acao) * 100.0
            taxa_anualizada = ((1 + (op['preco'] / preco_acao)) ** (252.0 / op['dte_uteis']) - 1) * 100.0
            
            # Ajuste Ex-Provento B3
            afeta_provento = flag_proventos and (data_ex is not None) and (data_ex <= op['vencimento'])
            strike_ajustado = op['strike'] - provento_liq if afeta_provento else op['strike']
            val_provento_efetivo = provento_liq if afeta_provento else 0.0
            
            break_even = preco_acao - op['preco'] - val_provento_efetivo
            lucro_max_bruto = ((strike_ajustado - preco_acao + op['preco'] + val_provento_efetivo) / preco_acao) * 100.0

            dados_tab_lanc.append({
                "Ticker": op['ticker'],
                "Preço": f"R$ {op['preco']:.2f}",
                "Strike Original": f"R$ {op['strike']:.2f}",
                "Strike Ex-Provento (B3)": f"R$ {strike_ajustado:.2f}" if afeta_provento else "N/A",
                "Fair Value": f"R$ {op['preco_teorico']:.2f}",
                "Edge": f"R$ {edge:+.2f}",
                "Taxa Período": f"{taxa_bruta:.2f}%",
                "Taxa Anual (252 d.u.)": f"{taxa_anualizada:.2f}%",
                "Lucro Máx (c/ Prov.)": f"{lucro_max_bruto:.2f}%",
                "Break-Even": f"R$ {break_even:.2f}"
            })
        
        st.table(pd.DataFrame(dados_tab_lanc))
        
        melhor_lanc = max(opcoes_lancamento, key=lambda x: x['preco'] - x['preco_teorico'])
        diff_edge = melhor_lanc['preco'] - melhor_lanc['preco_teorico']
        taxa_anual_melhor = ((1 + (melhor_lanc['preco'] / preco_acao)) ** (252.0 / melhor_lanc['dte_uteis']) - 1) * 100.0
        
        st.markdown("---")
        st.success(f"🎯 **RECOMENDAÇÃO PROFISSIONAL:** `{melhor_lanc['ticker']}` | Taxa Anualizada: **{taxa_anual_melhor:.2f}% a.a.** | Edge: **R$ {diff_edge:+.2f}**")
        
        st.markdown("### 💡 Racional Técnico da Literatura")
        st.write(f"• **Sheldon Natenberg & Paridade Europeia:** Como as opções são Europeias, não há risco de exercício antecipado no evento Ex-Provento. O ajuste de strike da B3 ($K_{{ex}} = R\$ {melhor_lanc['strike'] - (provento_liq if flag_proventos else 0):.2f}$) garante neutralidade perfeita de arbitragem.")
        st.write(f"• **Euan Sinclair (Edge e Proteção):** A venda acima do Fair Value capta um Edge de `R$ {diff_edge:+.2f}`. O ponto de equilíbrio (*Break-Even*) da estrutura recua para `R$ {preco_acao - melhor_lanc['preco'] - (provento_liq if flag_proventos else 0):.2f}`.")

        registro = {
            "Data/Hora": timestamp_sim,
            "Modalidade": "Lançamento Inicial",
            "Preço Ação": f"R$ {preco_acao:.2f}",
            "Opção Recomendada": melhor_lanc['ticker'],
            "Strike Nominal": f"R$ {melhor_lanc['strike']:.2f}",
            "Edge vs FV": f"R$ {diff_edge:+.2f}",
            "Taxa Anualizada": f"{taxa_anual_melhor:.2f}% a.a."
        }

    else:
        op_atual = opcoes_lancamento[0]
        dte_atual = op_atual['dte_uteis']
        
        st.markdown(f"### 📋 Posição Vendida Atual: `{op_atual['ticker']}` (Europeia) | Strike: R$ {op_atual['strike']:.2f} | DTE: **{dte_atual} d.u.**")
        
        if 7 <= dte_atual <= 10:
            st.success(f"✅ **TIMING IDEAL DE ROLAGEM ({dte_atual} d.u.):** Posição no ponto ideal de captura de Theta ($\Theta$).")
        elif dte_atual > 10:
            st.info(f"ℹ️ **POSIÇÃO EM DECAIMENTO:** Faltam {dte_atual} d.u. Como a opção é **Europeia**, você pode aguardar até a janela de 7-10 d.u. para extrair o decaimento do tempo sem risco de exercício antes do vencimento.")
        
        st.markdown("---")
        st.markdown("### 📋 Análise Comparativa para Rolagem")
        dados_tab_rol = []
        
        for op in opcoes_rolagem:
            credito = op['preco'] - op_atual['preco']
            edge = op['preco'] - op['preco_teorico']
            dados_tab_rol.append({
                "Ticker Rolagem": op['ticker'],
                "Preço": f"R$ {op['preco']:.2f}",
                "Strike Nominal": f"R$ {op['strike']:.2f}",
                "Resultado Líquido": f"R$ {credito:+.2f}",
                "Fair Value": f"R$ {op['preco_teorico']:.2f}",
                "Edge vs Fair Value": f"R$ {edge:+.2f}",
                "DTE Úteis": f"{op['dte_uteis']} d.u.",
                "Delta (Δ)": f"{op['delta']:.4f}",
                "Theta (%)": f"{op['theta_pct']:.3f}%"
            })
        
        st.table(pd.DataFrame(dados_tab_rol))
        
        melhor_rol = max(opcoes_rolagem, key=lambda x: (x['preco'] - op_atual['preco']) + (x['preco'] - x['preco_teorico']))
        credito_final = melhor_rol['preco'] - op_atual['preco']
        
        st.markdown("---")
        st.success(f"🔄 **RECOMENDAÇÃO DE ROLAGEM:** Rolar `{op_atual['ticker']}` ➔ `{melhor_rol['ticker']}` (Crédito Líquido: **R$ {credito_final:+.2f}**)")
        
        registro = {
            "Data/Hora": timestamp_sim,
            "Modalidade": "Rolagem",
            "Preço Ação": f"R$ {preco_acao:.2f}",
            "Opção Recomendada": f"{op_atual['ticker']} ➔ {melhor_rol['ticker']}",
            "Strike Nominal": f"R$ {melhor_rol['strike']:.2f}",
            "Edge vs FV": f"R$ {melhor_rol['preco'] - melhor_rol['preco_teorico']:+.2f}",
            "Taxa Anualizada": f"Crédito: R$ {credito_final:+.2f}"
        }

    # Historico das ultimas 20 simulações
    if ticker_acao not in st.session_state["historico_simulacoes"]:
        st.session_state["historico_simulacoes"][ticker_acao] = []

    st.session_state["historico_simulacoes"][ticker_acao].insert(0, registro)
    st.session_state["historico_simulacoes"][ticker_acao] = st.session_state["historico_simulacoes"][ticker_acao][:20]

# ==============================================================================
# 4. HISTÓRICO DAS ÚLTIMAS 20 SIMULAÇÕES
# ==============================================================================
st.divider()
with st.expander(f"📜 Histórico das Últimas Simulações - [{ticker_acao}]"):
    if ticker_acao in st.session_state["historico_simulacoes"] and len(st.session_state["historico_simulacoes"][ticker_acao]) > 0:
        df_hist = pd.DataFrame(st.session_state["historico_simulacoes"][ticker_acao])
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info(f"Nenhuma simulação salva ainda para **{ticker_acao}** nesta sessão.")
        
