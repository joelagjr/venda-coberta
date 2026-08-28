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
st.caption("Framework Quantitativo Integrado: Natenberg, Sinclair, Taleb & Mercado B3 (Ajustado por Proventos, Volatilidade e Gregas)")

st.markdown("""
> **Fundamentação Teórica Integrada (Proventos & Volatilidade):**
> * **Sheldon Natenberg (*Option Volatility and Pricing*):** Ajuste do preço do ativo subjacente pelo valor presente dos dividendos futuros ($S^* = S - PV(D)$) e o impacto do *Volatility Crush* pós-data ex.
> * **Euan Sinclair (*Option Trading*):** Precificação teórica (*Fair Value*) incorporando dividendos para evitar distorções no cálculo do *Edge* ($Preço - Fair Value$).
> * **Nassim Nicholas Taleb (*Dynamic Hedging*):** Risco de exercício antecipado (*early exercise*) em Calls Americanas quando $Prêmio\ Temporal < Dividendo$, alterando o perfil não-linear de Gamma ($\Gamma$) e Theta ($\Theta$).
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
            titulo_box = f"Opção Call #{i+1}" if not modo_rolagem else (f"Opção Já Lançada na Carteira" if quantidade==1 else f"Opção Call #{i+1}")
            st.markdown(f"##### {titulo_box}")
            ticker_op = st.text_input(f"Ticker da Opção", value=f"{ticker_acao}_CALL{i+1}", key=f"{prefixo}_tick_{i}").upper()
            estilo_op = st.selectbox(f"Estilo do Exercício", options=["Europeia", "Americana"], index=0, key=f"{prefixo}_est_{i}")
            preco_op = st.number_input(f"Preço de Mercado (R$)", value=1.45 - (i * 0.30), step=0.05, format="%.2f", key=f"{prefixo}_p_{i}")
            strike_op = st.number_input(f"Preço de Strike (R$)", value=preco_acao + (i * 1.50), step=0.50, format="%.2f", key=f"{prefixo}_k_{i}")
            preco_teorico = st.number_input(f"Preço Teórico / Fair Value (R$)", value=1.38 - (i * 0.28), step=0.05, format="%.2f", key=f"{prefixo}_pt_{i}")
            
            val_du_default = 8 if (modo_rolagem and prefixo == "lanc") else int(21 + (i * 10))
            
            dias_uteis_input = st.number_input(
                f"Dias Úteis Faltantes (d.u.)",
                value=val_du_default,
                step=1,
                min_value=1,
                key=f"{prefixo}_du_{i}"
            )
            vencimento_calculado = date.today() + timedelta(days=int(dias_uteis_input * 1.45))
            
            st.caption("Gregas da Opção (Natenberg & Taleb)")
            delta = st.number_input(f"Delta (Δ)", value=0.4500 - (i * 0.10), step=0.0100, format="%.4f", key=f"{prefixo}_d_{i}")
            gamma = st.number_input(f"Gamma (γ)", value=0.0850 + (0.05 if val_du_default <= 10 else 0.0), step=0.0050, format="%.4f", key=f"{prefixo}_g_{i}")
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
# 2. SIMULAÇÃO I: LANÇAMENTO INICIAL DE CALLS
# ==============================================================================
st.subheader("🚀 2. SIMULAÇÃO I: Options Calls para Lançamento Inicial")
qtd_lanc = st.radio("Quantidade de opções a avaliar para Lançamento Inicial:", [1, 2, 3], horizontal=True, key="qtd_lanc")

# ==============================================================================
# 3. SIMULAÇÃO II: ROLAGEM DA OPÇÃO
# ==============================================================================
st.divider()
st.subheader("🔄 3. SIMULAÇÃO II: Corrida de Rolagem da Opção")

executar_rolagem = st.checkbox("Ativar corrida de simulação para Rolagem da Opção", value=False)

if executar_rolagem:
    st.warning("⚠️ **Regra de Rolagem Ativa:** Na Simulação I, insira **apenas 1 opção** (representando a opção vendida atualmente). Na Simulação II, insira as opções candidatas para a nova rolagem.")
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
        
        st.markdown("### 💡 Racional Técnico e Fundamentação Teórica Integrada:")
        st.write(f"• **Natenberg (Volatilidade & Proventos):** O *Variance Risk Premium* (IV - HV) está em `{vrp_geral:+.2f}%`. Natenberg destaca que o dividendo anunciado reduz o preço spot ex-provento ($S^* = S - PV(D)$), barateando o valor teórico de Calls. A venda de volatilidade se beneficia se o IV Rank (`{iv_rank:.2f}%`) estiver inflacionado por conta do anúncio do provento.")
        st.write(f"• **Sinclair (Edge & Fair Value Ajustado):** *Edge* estatístico de `R$ {diff_edge:+.2f}`. Sinclair enfatiza que a precificação teórica ($Fair\ Value = R\$ {melhor_lanc['preco_teorico']:.2f}$) deve obrigatoriamente descontar a taxa contínua de dividendos ($q$) para evitar calcular um falso *Edge* ao vender Calls antes da Data Ex.")
        st.write(f"• **Taleb (Risco de Exercício Antecipado e Gregas):** Opção do estilo **{melhor_lanc['estilo']}**. Taleb alerta que se a opção for Americana e o valor temporal do prêmio ($Extrinsic\ Value$) for inferior ao dividendo líquido de `R$ {provento_liq:.2f}`, o comprador **exercerá a Call na véspera da Data Ex**. Isso colapsa o Vega ($\nu$) e torna o Delta ($\Delta$) equivalente a $1.0$.")

    else:
        op_atual = opcoes_lancamento[0]
        dte_atual = op_atual['dte_uteis']
        estilo_atual = op_atual['estilo']
        
        st.markdown(f"### 📋 Posição Atual: `{op_atual['ticker']}` ({estilo_atual}) | Strike: R$ {op_atual['strike']:.2f} | DTE Restante: **{dte_atual} d.u.**")
        
        st.markdown("#### 🚨 Diagnóstico de Rolagem, Proventos e Timing")
        
        if 7 <= dte_atual <= 10:
            st.success(f"✅ **PERFEITO TIMING DE ROLAGEM ({dte_atual} d.u. restantes):** Janela ideal de mercado (7-10 d.u.). A captura de Theta já superou 80% e o Gamma começa a atingir níveis críticos.")
        elif dte_atual > 10:
            if estilo_atual == "Europeia":
                st.error(f"❌ **CRÍTICA TÉCNICA - ROLAGEM PREMATURA (Opção Europeia):** Como a opção é **Europeia**, não há risco de exercício antecipado na Data Ex-Provento. Rolar a {dte_atual} d.u. interrompe a aceleração do Theta ($\Theta$) descrita por Natenberg e introduz custos desnecessários de spread.")
            else:
                st.warning(f"⚠️ **ROLAGEM ANTECIPADA (Opção Americana):** Avalie o valor temporal restante. Se $Extrinsic\ Value < Dividendo\ Líquido$ (`R$ {provento_liq:.2f}`), a rolagem antecipada se justifica para evitar o exercício involuntário na Data Ex.")

        st.markdown("---")
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
        
        st.success(f"🔄 **RECOMENDAÇÃO DE ROLAGEM:** Rolar `{op_atual['ticker']}` ➔ `{melhor_rol['ticker']}` ({melhor_rol['estilo']} | Strike: R$ {melhor_rol['strike']:.2f} | Resultado Líquido: **R$ {credito_final:+.2f}**)")
            
        st.markdown("### 💡 Racional Técnico da Literatura sobre Proventos e Rolagem:")
        st.write(f"• **Natenberg & Proventos:** A rolagem estende o vencimento para `{melhor_rol['dte_uteis']} d.u.`. Se a nova opção cobrir a Data Ex ({data_ex.strftime('%d/%m/%Y') if data_ex else 'N/A'}), o preço de exercício é indiretamente protegido pela queda ex-dividendo do ativo subjacente.")
        st.write(f"• **Sinclair & Edge:** A nova estrutura captura um crédito líquido de `R$ {credito_final:+.2f}` e assegura um *Edge* estatístico de `R$ {melhor_rol['preco'] - melhor_rol['preco_teorico']:+.2f}`.")
        st.write(f"• **Taleb & Risco Gamma/Exercício:** A troca de séries atenua a aceleração de Gamma ($\Gamma$) de `{op_atual['gamma']:.4f}` para `{melhor_rol['gamma']:.4f}`. Caso a opção seja **Europeia**, o investidor elimina 100% do risco de ser exercido na véspera da Data Ex-Provento.")
                                  
