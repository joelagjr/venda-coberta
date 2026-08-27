import streamlit as st
import pandas as pd
import numpy as np

# Configuração visual otimizada para mobile
st.set_page_config(page_title="Venda Coberta Pro", layout="centered")

st.title("🎯 Venda Coberta (Covered Call)")
st.caption("Análise Quantitativa | Deltas, Vega & Rule of Thumb")

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

st.divider()

# Função para input dinâmico das opções
def entrada_opcao(num, rotulo_delta, d_def, premio_def, strike_def, ticker_def, vega_def):
    # Opções 1 e 2 vêm ativadas por padrão para garantir o mínimo de 2
    ativo_padrao = True if num in [1, 2] else False
    
    ativo = st.checkbox(f"Ativar Opção {num} (Ref. Delta ~{rotulo_delta})", value=ativo_padrao, key=f"chk_{num}")
    
    if ativo:
        c1, c2, c3 = st.columns(3)
        with c1:
            ticker = st.text_input(f"Ticker", value=ticker_def, key=f"t_{num}")
            strike = st.number_input(f"Strike", value=strike_def, key=f"s_{num}")
        with c2:
            premio = st.number_input(f"Prêmio", value=premio_def, key=f"p_{num}")
            delta = st.number_input(f"Delta", value=d_def, key=f"d_{num}")
        with c3:
            theta_pct = st.number_input(f"Theta/Dia (%)", value=-0.15, key=f"th_{num}")
            vega = st.number_input(f"Vega", value=vega_def, key=f"v_{num}")
            
        return {
            "Ticker": ticker, "Strike": strike, "Prêmio": premio, 
            "Delta": delta, "ThetaPct": theta_pct, "Vega": vega
        }
    return None

st.subheader("2. Opções Europeias (Selecione pelo menos 2)")
op1 = entrada_opcao(1, "30", 0.30, 1.20, 40.00, "PETRJ400", 0.08)
op2 = entrada_opcao(2, "20", 0.20, 0.65, 41.50, "PETRJ415", 0.06)
op3 = entrada_opcao(3, "15", 0.15, 0.35, 42.50, "PETRJ425", 0.04)

st.divider()

if st.button("🚀 Analisar Opções", use_container_width=True):
    # Filtra apenas as opções que foram ativadas no checkbox
    dados = [op for op in [op1, op2, op3] if op is not None]
    
    if len(dados) < 2:
        st.error("⚠️ Por favor, ative pelo menos DUAS opções para realizar a comparação.")
    else:
        df = pd.DataFrame(dados)

        # Métricas de Rendimento e Proteção
        df["Taxa Bruta (%)"] = (df["Prêmio"] / preco_acao) * 100
        df["Distância Strike (%)"] = ((df["Strike"] - preco_acao) / preco_acao) * 100
        df["Retorno Máx. (%)"] = df["Taxa Bruta (%)"] + df["Distância Strike (%)"]

        # Exibição Comparativa
        st.subheader("📊 Comparativo Técnico")
        st.dataframe(
            df[["Ticker", "Delta", "Vega", "Strike", "Prêmio", "Taxa Bruta (%)", "Retorno Máx. (%)"]],
            hide_index=True,
            use_container_width=True
        )

        st.subheader("🧠 Racional de Mercado (Natenberg, Sinclair & Taleb)")

        edge_vol = vol_implicita - vol_historica
        
        # Análise de Volatilidade e Vega
        st.markdown("### 1. Exposição ao Vega & Regime de Volatilidade")
        if iv_rank > 50:
            st.success(f"**FAVORÁVEL (Vol Crush):** IV Rank alto ({iv_rank:.1f}%). Ao lançar a opção, você fica **Short Vega**. Opções com Vega maior sofrerão desvalorização mais rápida se a volatilidade implícita cair para a média histórica, antecipando o lucro.")
        elif iv_rank < 30:
            st.warning(f"**RISCO DE VEGA:** IV Rank baixo ({iv_rank:.1f}%). Risco de expansão de volatilidade. Estar Short Vega agora significa que se a IV subir, o prêmio da opção vai encarecer contra você, dificultando a recompra.")
        else:
            st.info(f"**VEGA NEUTRO:** IV Rank em {iv_rank:.1f}%. A exposição ao Vega terá impacto marginal comparado ao Theta (passagem do tempo) e Delta (direção).")

        # Escolha Recomendada (Rule of Thumb)
        st.markdown("### 2. Veredito: Escolha da Opção")

        if iv_rank >= 60:
            # Alta vol -> delta menor, priorizar recolher prêmio seguro. Desempate por maior Vega relativo se quiser surfar o Vol Crush.
            rec = df[df["Delta"] <= 0.22].sort_values(by="Delta", ascending=False)
            if not rec.empty:
                rec = rec.iloc[0]
            else:
                rec = df.iloc[0]
            motivo = f"IV Rank alto. Coletamos prêmios inflados em Deltas mais seguros (15-20). Como estamos apostando na queda da volatilidade, a exposição Short Vega ({rec['Vega']}) desta opção vai acelerar a depreciação do prêmio a nosso favor."
        elif iv_rank <= 30:
            # Baixa vol -> delta 30 para ter taxa. 
            rec = df.loc[(df["Delta"] - 0.30).abs().idxmin()]
            motivo = f"IV Rank baixo. O prêmio em deltas fora do dinheiro é pífio. Buscamos o Delta mais próximo de 30 para garantir taxa. Cuidado com o Vega de {rec['Vega']}, pois um salto na volatilidade jogará o preço da opção contra a posição."
        else:
            # Vol média
            rec = df.loc[(df["Delta"] - 0.20).abs().idxmin()]
            motivo = "Regime de volatilidade moderada. O Delta ~20 oferece o 'Sweet Spot' entre taxa de retenção do prêmio e margem para alta do ativo subjacente sem grande stress no Vega."

        st.markdown(f"""
        > **Opção Recomendada:** `{rec['Ticker']}` (Delta {rec['Delta']} | Vega {rec['Vega']})
        > * **Prêmio:** R$ {rec['Prêmio']:.2f} ({rec['Taxa Bruta (%)']:.2f}%)
        > * **Retorno Máximo no Vencimento:** {rec['Retorno Máx. (%)']:.2f}%
        
        **Justificativa:** {motivo}
        """)
