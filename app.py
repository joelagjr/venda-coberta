import streamlit as st
import pandas as pd
import numpy as np

# Configuração visual otimizada para mobile
st.set_page_config(page_title="Venda Coberta Pro", layout="centered")

st.title("🎯 Venda Coberta (Covered Call)")
st.caption("Análise Quantitativa & Rule of Thumb | Natenberg, Sinclair & Taleb")

# Inputs Principais da Ação
st.subheader("1. Ativo Subjacente")
col_a, col_b = st.columns(2)
with col_a:
    ticker_acao = st.text_input("Ticker Ação", value="PETR4")
    preco_acao = st.number_input("Preço Ação (R$/$)", value=38.50, step=0.10)
with col_b:
    iv_rank = st.number_input("IV Rank (%)", value=65.0, step=1.0)
    vol_implicita = st.number_input("Vol Implícita Anual (%)", value=32.0, step=1.0)

col_c, col_d = st.columns(2)
with col_c:
    hv_rank = st.number_input("HV Rank (%)", value=45.0, step=1.0)
with col_d:
    vol_historica = st.number_input("Vol Histórica Anual (%)", value=24.0, step=1.0)

dias_vencimento = st.number_input("Dias Úteis até o Vencimento (DTE)", value=22, step=1)

st.divider()

# Função para input das opções
def entrada_opcao(rotulo_delta, d_def, premio_def, strike_def, ticker_def):
    st.subheader(f"Opção - Referência Delta ~{rotulo_delta}")
    c1, c2, c3 = st.columns(3)
    with c1:
        ticker = st.text_input(f"Ticker", value=ticker_def, key=f"t_{rotulo_delta}")
        strike = st.number_input(f"Strike", value=strike_def, key=f"s_{rotulo_delta}")
    with c2:
        premio = st.number_input(f"Prêmio", value=premio_def, key=f"p_{rotulo_delta}")
        delta = st.number_input(f"Delta", value=d_def, key=f"d_{rotulo_delta}")
    with c3:
        gamma = st.number_input(f"Gamma", value=0.04, key=f"g_{rotulo_delta}")
        theta_pct = st.number_input(f"Theta/Dia (%)", value=-0.15, key=f"th_{rotulo_delta}")
    return {
        "Ticker": ticker, "Strike": strike, "Prêmio": premio, 
        "Delta": delta, "Gamma": gamma, "ThetaPct": theta_pct
    }

# Cadastro das 3 Opções
op1 = entrada_opcao("30", 0.30, 1.20, 40.00, "PETRJ400")
op2 = entrada_opcao("20", 0.20, 0.65, 41.50, "PETRJ415")
op3 = entrada_opcao("15", 0.15, 0.35, 42.50, "PETRJ425")

st.divider()

if st.button("🚀 Analisar Opções", use_container_width=True):
    # Processamento de Dados
    dados = [op1, op2, op3]
    df = pd.DataFrame(dados)

    # Métricas de Rendimento e Proteção
    df["Taxa Bruta (%)"] = (df["Prêmio"] / preco_acao) * 100
    df["Proteção de Queda (%)"] = df["Taxa Bruta (%)"]
    df["Distância do Strike (%)"] = ((df["Strike"] - preco_acao) / preco_acao) * 100
    df["Retorno Máx. (Com Exercício) (%)"] = df["Taxa Bruta (%)"] + df["Distância do Strike (%)"]

    # Exibição Comparativa
    st.subheader("📊 Comparativo Técnico")
    st.dataframe(
        df[["Ticker", "Delta", "Strike", "Prêmio", "Taxa Bruta (%)", "Distância do Strike (%)", "Retorno Máx. (Com Exercício) (%)"]],
        hide_index=True,
        use_container_width=True
    )

    # Raciocínio Quantitativo / Racional dos Autores
    st.subheader("🧠 Racional de Mercado & Literatura")

    edge_vol = vol_implicita - vol_historica
    
    # 1. Análise de Regime de Volatilidade (Natenberg & Sinclair)
    st.markdown("### 1. Volatilidade & Edge (Natenberg / Sinclair)")
    if iv_rank > 50 and edge_vol > 0:
        st.success(f"**EDGE POSITIVO:** IV Rank em {iv_rank:.1f}% e Vol Implícita está {edge_vol:.1f}% acima da Histórica. Vender volatilidade cara favorece estatisticamente o lançador.")
    elif iv_rank < 30:
        st.warning(f"**ALERTA DE VOLATILIDADE BAIXA:** IV Rank em {iv_rank:.1f}%. O prêmio coletado é reduzido em termos absolutos. A relação risco/retorno para venda coberta piora.")
    else:
        st.info(f"**VOLATILIDADE NEUTRA:** IV Rank em {iv_rank:.1f}%. A precificação está em linha com as médias históricas.")

    # 2. Avaliação de Convexidade e Risco de Calda (Taleb)
    st.markdown("### 2. Gestão de Risco de Calda (Taleb)")
    st.write("A venda de Call possui distribuição de retornos assimétrica negativa (ganho limitado, risco ilimitado na queda do subjacente). As opções sendo europeias eliminam o risco de exercício antecipado, mas mantêm a exposição integral ao *delta* em quedas acentuadas.")

    # 3. Escolha Recomendada (Rule of Thumb)
    st.markdown("### 3. Veredito: Escolha da Opção")

    # Seleção baseada em heurística clássica de mesas quantitativas
    if iv_rank >= 60:
        # Alta vol -> delta menor recolhe bom prêmio mantendo maior margem de segurança
        rec = df[df["Delta"] <= 0.22].sort_values(by="Delta", ascending=False).iloc[0]
        motivo = "Com IV Rank alto, preferimos coletar prêmios elevados com menor probabilidade de ser exercido (Delta 15-20), ampliando a margem de segurança do ativo."
    elif iv_rank <= 30:
        # Baixa vol -> delta 30 para compensar o prêmio baixo
        rec = df.loc[df["Delta"].abs_sub(0.30).idxmin()]
        motivo = "Com IV Rank baixo, deltas menores oferecem prêmios irrelevantes. O Delta ~30 garante a taxa mínima necessária para rentabilizar a custódia."
    else:
        # Vol média -> delta 20/25 intermediário
        rec = df.loc[df["Delta"].abs_sub(0.20).idxmin()]
        motivo = "Em regime de volatilidade moderada, o Delta ~20 oferece o melhor equilíbrio entre taxa de retenção do prêmio e espaço para valorização do papel."

    st.markdown(f"""
    > **Opção Recomendada:** `{rec['Ticker']}` (Delta {rec['Delta']})
    > * **Prêmio:** R$ {rec['Prêmio']:.2f} ({rec['Taxa Bruta (%)']:.2f}%)
    > * **Distância do Strike:** {rec['Distância do Strike (%)']:.2f}%
    > * **Retorno Máximo no Vencimento:** {rec['Retorno Máx. (Com Exercício) (%)']:.2f}%
    
    **Justificativa Técnica:** {motivo}
    """)
                                    
