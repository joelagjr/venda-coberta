import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import norm

# ==============================================================================
# 1. FUNÇÕES DE MENSURAÇÃO E MODELAGEM MATEMÁTICA (Black-Scholes-Merton)
# ==============================================================================

def bsm_price_greeks(S, K, T, r, sigma, q, option_type='call'):
    """
    Calcula o Preço Teórico e as Gregas da Opção pelo Modelo Black-Scholes-Merton
    incorporando Taxa Continuada de Dividendos (q).
    """
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        return {
            'price': intrinsic, 'delta': 1.0 if (option_type == 'call' and S > K) else 0.0,
            'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0
        }
    
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = np.exp(-q * T) * norm.cdf(d1)
        theta = (- (S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T)) 
                 - r * K * np.exp(-r * T) * norm.cdf(d2) 
                 + q * S * np.exp(-q * T) * norm.cdf(d1)) / 365.0
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
        delta = -np.exp(-q * T) * norm.cdf(-d1)
        theta = (- (S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T)) 
                 + r * K * np.exp(-r * T) * norm.cdf(-d2) 
                 - q * S * np.exp(-q * T) * norm.cdf(-d1)) / 365.0

    gamma = (np.exp(-q * T) * norm.pdf(d1)) / (S * sigma * np.sqrt(T))
    vega = (S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)) / 100.0  # Variação para 1% de IV
    rho = (K * T * np.exp(-r * T) * norm.cdf(d2 if option_type == 'call' else -d2)) / 100.0

    return {
        'price': price,
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'rho': rho
    }

def collect_option_inputs(prefix, label_suffix=""):
    """Função auxiliar para padronizar e capturar os campos de entrada de opções."""
    st.markdown(f"#### Parâmetros da Opção {label_suffix}")
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo = st.selectbox(f"Tipo ({prefix})", ['Call', 'Put'], key=f"{prefix}_tipo").lower()
        strike = st.number_input(f"Strike / K ({prefix})", value=30.0, step=0.5, key=f"{prefix}_strike")
        mkt_price = st.number_input(f"Preço de Mercado ({prefix})", value=1.20, step=0.05, key=f"{prefix}_mkt_price")
    with col2:
        dte = st.number_input(f"Dias até Vencimento / DTE ({prefix})", value=30, step=1, key=f"{prefix}_dte")
        iv = st.number_input(f"Vol. Implícita - IV % ({prefix})", value=35.0, step=0.5, key=f"{prefix}_iv") / 100.0
        iv_rank = st.number_input(f"IV Rank % ({prefix})", value=65.0, step=1.0, key=f"{prefix}_iv_rank")
    with col3:
        hv = st.number_input(f"Vol. Histórica - HV % ({prefix})", value=25.0, step=0.5, key=f"{prefix}_hv") / 100.0
        hv_rank = st.number_input(f"HV Rank % ({prefix})", value=40.0, step=1.0, key=f"{prefix}_hv_rank")
    
    return {
        'tipo': tipo, 'strike': strike, 'mkt_price': mkt_price,
        'dte': dte, 'iv': iv, 'iv_rank': iv_rank,
        'hv': hv, 'hv_rank': hv_rank
    }

# ==============================================================================
# 2. INTERFACE E INPUTS GERAIS
# ==============================================================================

st.set_page_config(page_title="Análise de Opções: Natenberg, Sinclair & Taleb", layout="wide")
st.title("📊 Análise de Lançamento e Rolagem de Opções")
st.caption("Visão Integrada: Sheldon Natenberg, Euan Sinclair, Nassim Taleb & Regras de Algoritmo de Mercado")

st.sidebar.header("⚙️ Ativo Objeto e Macro")
S = st.sidebar.number_input("Preço do Ativo Objeto (S)", value=30.00, step=0.50)
r = st.sidebar.number_input("Taxa Livre de Risco - SELIC/CDI (%)", value=10.5, step=0.25) / 100.0
q = st.sidebar.number_input("Dividend Yield Estimado (%)", value=2.0, step=0.25) / 100.0

st.divider()

# ==============================================================================
# 3. MÓDULO I: LANÇAMENTO INICIAL
# ==============================================================================
st.subheader("1️⃣ Lançamento Inicial de Opção")
op_init = collect_option_inputs("init", "(Lançamento Inicial)")

# Cálculo de BSM e Gregas para a Opção Inicial
T_init = op_init['dte'] / 365.0
greeks_init = bsm_price_greeks(S, op_init['strike'], T_init, r, op_init['iv'], q, op_init['tipo'])

# Diagnóstico Teórico e Prático do Lançamento
vrp_init = (op_init['iv'] - op_init['hv']) * 100
diff_price_init = op_init['mkt_price'] - greeks_init['price']

col_res1, col_res2, col_res3, col_res4 = st.columns(4)
col_res1.metric("Preço Teórico (BSM)", f"R$ {greeks_init['price']:.2f}")
col_res2.metric("Preço de Mercado", f"R$ {op_init['mkt_price']:.2f}", delta=f"{diff_price_init:+.2f} vs Teórico")
col_res3.metric("Variance Risk Premium (IV - HV)", f"{vrp_init:+.1f}%")
col_res4.metric("Delta (Δ)", f"{greeks_init['delta']:.3f}")

# Tabela de Gregas e Volatilidade
df_init_metrics = pd.DataFrame({
    'Métrica / Grega': ['Preço Teórico', 'Preço Mercado', 'IV %', 'IV Rank', 'HV %', 'HV Rank', 'Delta', 'Gamma', 'Theta (diário)', 'Vega'],
    'Valor': [
        f"R$ {greeks_init['price']:.2f}", f"R$ {op_init['mkt_price']:.2f}",
        f"{op_init['iv']*100:.1f}%", f"{op_init['iv_rank']:.1f}%",
        f"{op_init['hv']*100:.1f}%", f"{op_init['hv_rank']:.1f}%",
        f"{greeks_init['delta']:.4f}", f"{greeks_init['gamma']:.4f}",
        f"{greeks_init['theta']:.4f}", f"{greeks_init['vega']:.4f}"
    ]
})
st.dataframe(df_init_metrics.set_index('Métrica / Grega').T, use_container_width=True)

# Análise de Literatura e Mercado (Lançamento)
with st.expander("📖 Parecer Técnico da Literatura (Natenberg, Sinclair, Taleb) & Rule of Thumb", expanded=True):
    # Sinclair & Natenberg (VRP & Mean Reversion)
    st.write("**• Visão Sinclair & Natenberg (Volatilidade & Pricing):**")
    if vrp_init > 0 and op_init['iv_rank'] >= 50:
        st.success(f"✔️ **Borda Estatística Presente:** O prêmio de volatilidade (VRP = {vrp_init:.1f}%) está positivo e o IV Rank ({op_init['iv_rank']:.0f}%) está elevado. Segundo Natenberg e Sinclair, há vantagem estatística na **venda de volatilidade**, pois o mercado está sobre-precificando a incerteza futura em relação ao histórico.")
    else:
        st.warning(f"⚠️ **Vantagem Limitada:** IV Rank ({op_init['iv_rank']:.0f}%) baixo ou IV inferior à HV. Vender opção neste contexto oferece prêmio reduzido para o risco assumido.")

    # Taleb (Gamma & Convexidade)
    st.write("**• Visão Taleb (Risco de Cauda e Convexidade):**")
    if op_init['dte'] < 15 and abs(greeks_init['delta']) > 0.3:
        st.error(f"🚨 **Alerta de Gamma (Taleb):** DTE curto ({op_init['dte']} dias) com Gamma elevado ({greeks_init['gamma']:.4f}). Curvas curtas apresentam alta não-linearidade e fragilidade severe contra movimentos abruptos do ativo.")
    else:
        st.info(f"ℹ️ **Gestão de Risco:** Gamma controlado ({greeks_init['gamma']:.4f}). Monitorar o risco de aceleração de Delta conforme o vencimento aproxima.")

    # Rule of Thumb do Mercado
    ret_direto = (op_init['mkt_price'] / S) * 100
    st.write("**• Rule of Thumb do Mercado:**")
    st.write(f"- Taxa de Retorno Bruta sobre o ativo: **{ret_direto:.2f}%** para {op_init['dte']} dias.")
    st.write(f"- Ponto de Equilíbrio (Break-Even): **R$ {(S - op_init['mkt_price'] if op_init['tipo']=='call' else S + op_init['mkt_price']):.2f}**")

st.divider()

# ==============================================================================
# 4. MÓDULO II: ANÁLISE DE ROLAGEM (COM FLAG DE EXPANSÃO ATE 2 OPÇÕES)
# ==============================================================================
st.subheader("2️⃣ Análise e Diagnóstico de Rolagem")

flag_rolagem = st.checkbox("🚩 Ativar Análise de Rolagem da Operação", value=True)

if flag_rolagem:
    num_opcoes = st.radio("Selecione a quantidade de opções envolvidas na rolagem:", [1, 2], horizontal=True, 
                          help="1 Opção = Recompra/Substituição simples; 2 Opções = Estrutura de rolagem dupla / Legged Roll.")

    op_rol_1 = collect_option_inputs("rol1", "1 da Rolagem (Recompra ou Nova Pernada A)")
    greeks_rol_1 = bsm_price_greeks(S, op_rol_1['strike'], op_rol_1['dte']/365.0, r, op_rol_1['iv'], q, op_rol_1['tipo'])

    greeks_rol_2 = None
    op_rol_2 = None
    if num_opcoes == 2:
        op_rol_2 = collect_option_inputs("rol2", "2 da Rolagem (Nova Pernada B)")
        greeks_rol_2 = bsm_price_greeks(S, op_rol_2['strike'], op_rol_2['dte']/365.0, r, op_rol_2['iv'], q, op_rol_2['tipo'])

    # Exibição Comparativa das Opções da Rolagem
    st.markdown("### 📊 Quadro Comparativo da Rolagem & Preços Teóricos")
    
    data_rol = {
        'Métrica / Grega': ['Tipo', 'Strike (K)', 'Preço Mercado', 'Preço Teórico (BSM)', 'DTE', 'IV %', 'IV Rank', 'HV %', 'HV Rank', 'Delta (Δ)', 'Gamma (γ)', 'Theta (θ)', 'Vega (ν)'],
        'Opção Rolagem 1': [
            op_rol_1['tipo'].upper(), f"R$ {op_rol_1['strike']:.2f}", f"R$ {op_rol_1['mkt_price']:.2f}", f"R$ {greeks_rol_1['price']:.2f}",
            f"{op_rol_1['dte']}d", f"{op_rol_1['iv']*100:.1f}%", f"{op_rol_1['iv_rank']:.1f}%", f"{op_rol_1['hv']*100:.1f}%", f"{op_rol_1['hv_rank']:.1f}%",
            f"{greeks_rol_1['delta']:.4f}", f"{greeks_rol_1['gamma']:.4f}", f"{greeks_rol_1['theta']:.4f}", f"{greeks_rol_1['vega']:.4f}"
        ]
    }
    
    if num_opcoes == 2:
        data_rol['Opção Rolagem 2'] = [
            op_rol_2['tipo'].upper(), f"R$ {op_rol_2['strike']:.2f}", f"R$ {op_rol_2['mkt_price']:.2f}", f"R$ {greeks_rol_2['price']:.2f}",
            f"{op_rol_2['dte']}d", f"{op_rol_2['iv']*100:.1f}%", f"{op_rol_2['iv_rank']:.1f}%", f"{op_rol_2['hv']*100:.1f}%", f"{op_rol_2['hv_rank']:.1f}%",
            f"{greeks_rol_2['delta']:.4f}", f"{greeks_rol_2['gamma']:.4f}", f"{greeks_rol_2['theta']:.4f}", f"{greeks_rol_2['vega']:.4f}"
        ]

    st.table(pd.DataFrame(data_rol).set_index('Métrica / Grega'))

    # Parecer Integrado de Rolagem
    with st.expander("📖 Parecer da Rolagem: Literatura (Natenberg, Sinclair, Taleb) + Mercado", expanded=True):
        
        # Crédito / Débito da Rolagem (Prática)
        if num_opcoes == 1:
            resultado_financeiro = op_rol_1['mkt_price'] - op_init['mkt_price']
            st.write(f"**• Resultado Financeiro Líquido (Mercado):** {'Crédito de R$' if resultado_financeiro >= 0 else 'Débito de R$'} {abs(resultado_financeiro):.2f}")
        else:
            # Assumindo Recompra da Inicial + Venda da Rol1 + Venda/Compra da Rol2
            resultado_financeiro = op_rol_2['mkt_price'] + op_rol_1['mkt_price'] - op_init['mkt_price']
            st.write(f"**• Resultado Financeiro Combinado:** {'Crédito Estimado de R$' if resultado_financeiro >= 0 else 'Débito Estimado de R$'} {abs(resultado_financeiro):.2f}")

        # Análise Sinclair / Natenberg para a Rolagem
        st.write("**• Avaliação de Volatilidade na Rolagem (Sinclair & Natenberg):**")
        if op_rol_1['iv_rank'] > op_init['iv_rank']:
            st.success(f"✔️ **Rolagem Favorável em Volatilidade:** A opção da rolagem possui IV Rank superior ({op_rol_1['iv_rank']:.0f}% vs {op_init['iv_rank']:.0f}% inicial). Você está vendendo/rolando para uma estrutura com maior prêmio de risco.")
        else:
            st.warning(f"⚠️ **Atenção:** A opção de rolagem possui IV Rank menor ou igual ({op_rol_1['iv_rank']:.0f}% vs {op_init['iv_rank']:.0f}% inicial). Avalie se o diferimento do prazo compensa a redução da taxa de volatilidade implícita.")

        # Análise Taleb para a Rolagem
        st.write("**• Avaliação de Fragilidade e Gregas (Taleb):**")
        delta_net = greeks_rol_1['delta'] + (greeks_rol_2['delta'] if greeks_rol_2 else 0.0)
        gamma_net = greeks_rol_1['gamma'] + (greeks_rol_2['gamma'] if greeks_rol_2 else 0.0)
        
        st.write(f"- **Delta Combinado:** `{delta_net:.4f}` | **Gamma Combinado:** `{gamma_net:.4f}`")
        if gamma_net > greeks_init['gamma']:
            st.error("🚨 **Aumento de Fragilidade (Taleb):** A rolagem está aumentando o risco de Gamma da carteira. Rolagens que aumentam o Gamma expõem o investidor a um risco de convexidade desproporcional caso ocorra um choque no preço do ativo.")
        else:
            st.info("🛡️ **Controle de Risk Management:** O Gamma da rolagem está igual ou inferior ao inicial, suavizando o risco de cauda e mantendo a exposição direcional sob controle.")

        # Rule of Thumb
        st.write("**• Rule of Thumb do Mercado para Rolagem:**")
        st.write("1. **Nunca rolar para débito:** Buscar sempre rolagem no mínimo com crédito zero ou positivo (*Roll for a credit*).")
        st.write("2. **Prazo / DTE:** Rolagens eficientes buscam prazos entre 30 e 60 dias para otimizar a curva de decaimento temporal (Theta).")
        
