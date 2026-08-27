import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime, date

# ==============================================================================
# 1. MOTOR DE CÁLCULO DE BLACK-SCHOLES-MERTON & GREGAS FORMATEDAS
# ==============================================================================

def calcular_bsm_e_gregas(S, K, dte, r, sigma, provento_liq=0.0):
    """
    Calcula o Preço Teórico e as Gregas para Opções de Compra (Calls) Europeias.
    Ajusta o preço da ação pelo valor presente do provento no período (se houver).
    """
    T = max(dte, 1) / 365.0
    
    # Ajuste de Provento no Ativo Objeto (S_adj) para precificação de Call
    S_adj = max(0.01, S - provento_liq * np.exp(-r * T))
    
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, S_adj - K)
        return {
            'preco_teorico': intrinsic,
            'delta': 1.0 if S_adj > K else 0.0,
            'gamma': 0.0,
            'theta_pct': 0.0,
            'vega': 0.0
        }
    
    d1 = (np.log(S_adj / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Preço Teórico Call BSM
    preco_teorico = S_adj * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    # Gregas
    delta = norm.cdf(d1)
    gamma = norm.pdf(d1) / (S_adj * sigma * np.sqrt(T))
    
    # Theta em R$/dia e conversão para Percentual ao dia (%) em relação ao preço do ativo
    theta_diario_brl = (- (S_adj * sigma * norm.pdf(d1)) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365.0
    theta_pct_dia = (theta_diario_brl / S_adj) * 100.0  # Em %
    
    # Vega por 1% de alteração na volatilidade implícita
    vega = (S_adj * norm.pdf(d1) * np.sqrt(T)) / 100.0
    
    return {
        'preco_teorico': preco_teorico,
        'delta': delta,
        'gamma': gamma,
        'theta_pct': theta_pct_dia,
        'vega': vega
    }

def capturar_entradas_opcoes(prefixo, qtd, dte_default=30):
    """Gera blocos dinâmicos para entrada de dados de até 3 opções (Lançamento ou Rolagem)."""
    opcoes = []
    cols = st.columns(qtd)
    
    for i in range(qtd):
        with cols[i]:
            st.markdown(f"##### Opção Call #{i+1}")
            ticker = st.text_input(f"Ticker/Código", value=f"CALL_{prefixo.upper()}_{i+1}", key=f"{prefixo}_tick_{i}")
            strike = st.number_input(f"Strike (K)", value=30.0 + (i * 1.0), step=0.5, key=f"{prefixo}_strike_{i}")
            preco_mkt = st.number_input(f"Preço Mercado (Prêmio)", value=1.20 - (i * 0.25), step=0.05, key=f"{prefixo}_mkt_{i}")
            vencimento = st.date_input(f"Data de Vencimento", value=date.today() + pd.Timedelta(days=dte_default + (i*15)), key=f"{prefixo}_venc_{i}")
            
            # Volatilidades para cada opção
            st.caption("Volatilidades & Ranks")
            iv = st.number_input(f"Vol Implícita (IV %)", value=35.0, step=0.5, key=f"{prefixo}_iv_{i}") / 100.0
            iv_rank = st.number_input(f"IV Rank (%)", value=60.0 + (i*5), step=1.0, key=f"{prefixo}_iv_rank_{i}")
            hv = st.number_input(f"Vol Histórica (HV %)", value=25.0, step=0.5, key=f"{prefixo}_hv_{i}") / 100.0
            hv_rank = st.number_input(f"HV Rank (%)", value=45.0, step=1.0, key=f"{prefixo}_hv_rank_{i}")
            
            dte = (vencimento - date.today()).days
            
            opcoes.append({
                'ticker': ticker, 'strike': strike, 'preco_mkt': preco_mkt,
                'vencimento': vencimento, 'dte': dte, 'iv': iv, 'iv_rank': iv_rank,
                'hv': hv, 'hv_rank': hv_rank
            })
    return opcoes

# ==============================================================================
# 2. PAINEL PRINCIPAL & INPUTS DO ATIVO SUBJACENTE E PROVENTOS
# ==============================================================================

st.set_page_config(page_title="Análise Avançada: Lançamento e Rolagem de Opções", layout="wide")
st.title("📈 Análise de Lançamento e Rolagem de Opções (Até 3 Calls)")
st.caption("Integração: Natenberg, Sinclair, Taleb & Rule of Thumb do Mercado")

st.sidebar.header("⚙️ Ativo Subjacente & Macro")
S = st.sidebar.number_input("Preço da Ação (S)", value=30.00, step=0.50, format="%.2f")
r = st.sidebar.number_input("Taxa Livre de Risco / SELIC (%)", value=10.5, step=0.25) / 100.0

st.sidebar.subheader("💰 Dividendos / JCP no Período")
flag_proventos = st.sidebar.checkbox("Considerar Proventos no Período", value=True)

if flag_proventos:
    provento_liq = st.sidebar.number_input("Valor Líquido do Provento (R$)", value=0.50, step=0.10)
    data_ex = st.sidebar.date_input("Data Ex-Provento", value=date.today() + pd.Timedelta(days=15))
else:
    provento_liq = 0.0
    data_ex = None

st.divider()

# ==============================================================================
# 3. MÓDULO I: OPÇÕES DE COMPRA A SEREM LANÇADAS (ATÉ 3)
# ==============================================================================

st.subheader("1️⃣ Opções de Compra (Calls) para Lançamento Inicial")
qtd_lanc = st.radio("Quantidade de opções a avaliar para Lançamento:", [1, 2, 3], horizontal=True, key="qtd_lanc")
opcoes_lanc = capturar_entradas_opcoes("lanc", qtd_lanc, dte_default=30)

# Processamento e Tabela comparativa dos Lançamentos
dados_lanc_processados = []
for op in opcoes_lanc:
    # Verificação se a data EX ocorre antes do vencimento
    prov_aplicado = provento_liq if (flag_proventos and data_ex and data_ex <= op['vencimento']) else 0.0
    
    g = calcular_bsm_e_gregas(S, op['strike'], op['dte'], r, op['iv'], prov_aplicado)
    vrp = (op['iv'] - op['hv']) * 100.0
    retorno_imediato = (op['preco_mkt'] / S) * 100.0
    
    dados_lanc_processados.append({
        'Ticker': op['ticker'],
        'Strike': f"R$ {op['strike']:.2f}",
        'Preço Mercado': f"R$ {op['preco_mkt']:.2f}",
        'Preço Teórico': f"R$ {g['preco_teorico']:.2f}",
        'Vencimento': op['vencimento'].strftime('%d/%m/%Y'),
        'DTE': op['dte'],
        'IV %': f"{op['iv']*100:.2f}%",
        'IV Rank': f"{op['iv_rank']:.1f}%",
        'HV %': f"{op['hv']*100:.2f}%",
        'HV Rank': f"{op['hv_rank']:.1f}%",
        'VRP (IV-HV)': f"{vrp:+.2f}%",
        'Delta (Δ)': f"{g['delta']:.4f}",
        'Gamma (γ)': f"{g['gamma']:.4f}",
        'Theta (%/dia)': f"{g['theta_pct']:.3f}%",
        'Vega (ν)': f"{g['vega']:.4f}",
        'Taxa Bruta': f"{retorno_imediato:.2f}%",
        # Guarda valores numéricos brutos para algoritmo de decisão
        '_raw': {**op, **g, 'vrp': vrp, 'retorno_imediato': retorno_imediato}
    })

df_lanc = pd.DataFrame(dados_lanc_processados)
st.dataframe(df_lanc.drop(columns=['_raw']), use_container_width=True)

# Algoritmo de Decisão e Recomendação para Lançamento
st.markdown("#### 💬 Recomendação de Lançamento (Literatura + Mercado)")

best_lanc = None
best_score = -999.0

for d in dados_lanc_processados:
    raw = d['_raw']
    # Score ponderado: VRP + IV Rank + Decay Theta - Risco Gamma exagerado
    score = (raw['vrp'] * 1.5) + (raw['iv_rank'] * 0.8) + (abs(raw['theta_pct']) * 20.0) - (raw['gamma'] * 10.0)
    if score > best_score:
        best_score = score
        best_lanc = raw

if best_lanc:
    st.success(f"📌 **Opção Recomendada para Lançamento:** `{best_lanc['ticker']}` (Strike R$ {best_lanc['strike']:.2f})")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Natenberg (VRP & Edge):** VRP em `{best_lanc['vrp']:+.2f}%` e IV Rank em `{best_lanc['iv_rank']:.1f}%`. Indica prêmio de volatilidade rico frente ao histórico.")
    c2.write(f"**Sinclair (Preço Teórico):** Mercado a `R$ {best_lanc['preco_mkt']:.2f}` vs Teórico a `R$ {best_lanc['preco_teorico']:.2f}`. Venda com margem sobre o modelo.")
    c3.write(f"**Taleb (Gama e Cauda):** Gamma em `{best_lanc['gamma']:.4f}` e DTE de `{best_lanc['dte']}d`. Nível de aceleração direcional dentro da margem de controle.")
    c4.write(f"**Rule of Thumb:** Retorno bruto sobre a ação de `{best_lanc['retorno_imediato']:.2f}%` no período com taxa diária de Theta de `{best_lanc['theta_pct']:.3f}%`.")

st.divider()

# ==============================================================================
# 4. MÓDULO II: ANÁLISE DE ROLAGEM (ATÉ 3 CALLS COM FLAG DE EXPANSÃO)
# ==============================================================================

st.subheader("2️⃣ Análise de Rolagem de Opções de Compra (Calls)")
flag_rolagem = st.checkbox("🚩 Ativar / Expandir Campos de Análise para Rolagem", value=True)

if flag_rolagem:
    qtd_rol = st.radio("Quantidade de opções a avaliar para Rolagem:", [1, 2, 3], horizontal=True, key="qtd_rol")
    opcoes_rol = capturar_entradas_opcoes("rol", qtd_rol, dte_default=60)
    
    dados_rol_processados = []
    for op in opcoes_rol:
        prov_aplicado = provento_liq if (flag_proventos and data_ex and data_ex <= op['vencimento']) else 0.0
        g = calcular_bsm_e_gregas(S, op['strike'], op['dte'], r, op['iv'], prov_aplicado)
        vrp = (op['iv'] - op['hv']) * 100.0
        
        # Comparativo direto de crédito/débito contra a opção recomendada do lançamento inicial
        credito_liquido = op['preco_mkt'] - (best_lanc['preco_mkt'] if best_lanc else 0.0)
        
        dados_rol_processados.append({
            'Ticker': op['ticker'],
            'Strike': f"R$ {op['strike']:.2f}",
            'Preço Mercado': f"R$ {op['preco_mkt']:.2f}",
            'Preço Teórico': f"R$ {g['preco_teorico']:.2f}",
            'Vencimento': op['vencimento'].strftime('%d/%m/%Y'),
            'DTE': op['dte'],
            'IV %': f"{op['iv']*100:.2f}%",
            'IV Rank': f"{op['iv_rank']:.1f}%",
            'HV %': f"{op['hv']*100:.2f}%",
            'HV Rank': f"{op['hv_rank']:.1f}%",
            'VRP (IV-HV)': f"{vrp:+.2f}%",
            'Delta (Δ)': f"{g['delta']:.4f}",
            'Gamma (γ)': f"{g['gamma']:.4f}",
            'Theta (%/dia)': f"{g['theta_pct']:.3f}%",
            'Vega (ν)': f"{g['vega']:.4f}",
            'Dif. Crédito/Débito': f"R$ {credito_liquido:+.2f}",
            '_raw': {**op, **g, 'vrp': vrp, 'credito_liquido': credito_liquido}
        })
        
    df_rol = pd.DataFrame(dados_rol_processados)
    st.dataframe(df_rol.drop(columns=['_raw']), use_container_width=True)
    
    # Algoritmo de Decisão para Rolagem
    st.markdown("#### 💬 Recomendação de Rolagem (Literatura + Mercado)")
    
    best_rol = None
    best_rol_score = -999.0
    
    for d in dados_rol_processados:
        raw = d['_raw']
        # Score de rolagem favorece crédito positivo, redução de Gamma e alto IV Rank
        score = (raw['credito_liquido'] * 5.0) + (raw['iv_rank'] * 0.5) - (raw['gamma'] * 15.0) + (abs(raw['theta_pct']) * 10.0)
        if score > best_rol_score:
            best_rol_score = score
            best_rol = raw

    if best_rol:
        st.info(f"🔄 **Opção Recomendada para Rolagem:** `{best_rol['ticker']}` (Strike R$ {best_rol['strike']:.2f})")
        
        r1, r2, r3, r4 = st.columns(4)
        r1.write(f"**Natenberg (Regressão à Média):** Manutenção do trade com IV Rank em `{best_rol['iv_rank']:.1f}%`. Captura o prêmio de volatilidade diferido no tempo.")
        r2.write(f"**Sinclair (Precificação BSM):** Preço de mercado `R$ {best_rol['preco_mkt']:.2f}` comparado ao teórico de `R$ {best_rol['preco_teorico']:.2f}`.")
        r3.write(f"**Taleb (Redução de Fragilidade):** Gamma reduzido para `{best_rol['gamma']:.4f}` ao estender o DTE para `{best_rol['dte']}d`, atenuando o risco de cauda de vencimento curto.")
        r4.write(f"**Rule of Thumb do Mercado:** Genera um diferencial líquido financeiro de `{best_rol['credito_liquido']:+.2f} R$` (regra do *Roll for a Credit*).")
    
