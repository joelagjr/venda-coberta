import streamlit as st
import pandas as pd
import numpy as np

# Configuração visual otimizada para mobile
st.set_page_config(page_title="Venda Coberta Pro & Rolagem", layout="centered")

st.title("🎯 Venda Coberta & Gestão de Rolagem")
st.caption("Análise Quantitativa | Manutenção de Posição, Rolagem (Net Credit/Debit) & Gregas (4 casas)")

# Seleção de Modo: Nova Operação vs. Posição Aberta
modo = st.sidebar.radio(
    "Selecione o Modulo de Análise:",
    ["1. Nova Venda Coberta", "2. Gestão de Posição Aberta / Rolagem"]
)

# -----------------------------------------------------------------------------
# MÓDULO COMMON INPUTS: Subjacente & Macro
# -----------------------------------------------------------------------------
st.subheader("1. Ativo Subjacente & Macro")
col_a, col_b = st.columns(2)
with col_a:
    ticker_acao = st.text_input("Ticker Ação", value="PETR4")
    preco_acao = st.number_input("Preço Atual da Ação (R$)", value=38.50, step=0.10, format="%.2f")
    dte = st.number_input("Dias Úteis até Vencimento (DTE)", value=22, step=1)
with col_b:
    iv_rank = st.number_input("IV Rank (%)", value=65.0, step=1.0)
    vol_implicita = st.number_input("Vol Implícita Anual (%)", value=32.0, step=1.0)
    selic_anual = st.number_input("Taxa Selic Anual (%)", value=10.50, step=0.25)

col_c, col_d = st.columns(2)
with col_c:
    hv_rank = st.number_input("HV Rank (%)", value=45.0, step=1.0)
with col_d:
    vol_historica = st.number_input("Vol Histórica Anual (%)", value=24.0, step=1.0)

st.divider()

# Inputs de Proventos
st.subheader("2. Proventos no Período da Opção")
tem_provento = st.radio("Há pagamento de Dividendos/JCP até o vencimento?", ["Não", "Sim"], horizontal=True)

valor_provento = 0.0
data_ex = ""

if tem_provento == "Sim":
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        valor_provento = st.number_input("Valor Líquido por Ação (R$)", value=1.50, step=0.10, min_value=0.0, format="%.2f")
    with col_p2:
        data_ex = st.text_input("Data Ex-Provento (ex: 15/10)", value="15/10")

st.divider()

# Função auxiliar para renderizar entradas de opções com 4 casas decimais para gregas
def entrada_opcao_detalhada(prefixo, num, d_def, premio_def, strike_def, ticker_def, vega_def, theta_def, gamma_def=0.0150):
    c1, c2, c3 = st.columns(3)
    with c1:
        ticker = st.text_input(f"Ticker Opção {num}", value=ticker_def, key=f"{prefixo}_t_{num}")
        strike = st.number_input(f"Strike (R$)", value=strike_def, key=f"{prefixo}_s_{num}", format="%.2f")
    with c2:
        premio = st.number_input(f"Prêmio Atual (R$)", value=premio_def, key=f"{prefixo}_p_{num}", format="%.2f")
        delta = st.number_input(f"Delta", value=d_def, key=f"{prefixo}_d_{num}", format="%.4f", step=0.0001)
    with c3:
        theta = st.number_input(f"Theta/Dia (R$)", value=theta_def, key=f"{prefixo}_th_{num}", format="%.4f", step=0.0001)
        vega = st.number_input(f"Vega (R$)", value=vega_def, key=f"{prefixo}_v_{num}", format="%.4f", step=0.0001)
    
    return {
        "Ticker": ticker, "Strike": strike, "Prêmio": premio,
        "Delta": delta, "Theta": theta, "Vega": vega
    }

# =============================================================================
# MÓDULO 1: NOVA VENDA COBERTA
# =============================================================================
if modo == "1. Nova Venda Coberta":
    st.subheader("3. Opções Alvo para Lançamento Inicial")
    
    def entrada_opcao(num, rotulo_delta, d_def, premio_def, strike_def, ticker_def, vega_def, theta_def):
        ativo = st.checkbox(f"Ativar Opção {num} (Ref. Delta ~{rotulo_delta})", value=True if num in [1, 2] else False, key=f"chk_n_{num}")
        if ativo:
            return entrada_opcao_detalhada("nova", num, d_def, premio_def, strike_def, ticker_def, vega_def, theta_def)
        return None

    op1 = entrada_opcao(1, "30", 0.3012, 1.20, 40.00, "PETRJ400", 0.0815, -0.0152)
    op2 = entrada_opcao(2, "20", 0.2045, 0.65, 41.50, "PETRJ415", 0.0621, -0.0118)
    op3 = entrada_opcao(3, "15", 0.1480, 0.35, 42.50, "PETRJ425", 0.0432, -0.0079)

    st.divider()

    if st.button("🚀 Analisar Venda Inicial", use_container_width=True):
        dados = [op for op in [op1, op2, op3] if op is not None]
        if len(dados) < 2:
            st.error("⚠️ Ative pelo menos duas opções para comparação.")
        else:
            df = pd.DataFrame(dados)
            selic_periodo = ((1 + (selic_anual / 100)) ** (dte / 252) - 1) * 100

            df["Taxa Opção (%)"] = (df["Prêmio"] / preco_acao) * 100
            df["Yield Provento (%)"] = (valor_provento / preco_acao) * 100
            df["Distância Strike (%)"] = ((df["Strike"] - preco_acao) / preco_acao) * 100
            df["Rendimento Retido (%)"] = df["Taxa Opção (%)"] + df["Yield Provento (%)"]
            df["Retorno Máx. (%)"] = df["Rendimento Retido (%)"] + df["Distância Strike (%)"]

            st.subheader("📊 Comparativo das Opções (Gregas com 4 Decimais)")
            st.dataframe(
                df[["Ticker", "Strike", "Prêmio", "Delta", "Theta", "Vega", "Rendimento Retido (%)", "Retorno Máx. (%)"]].style.format({
                    "Strike": "R$ {:.2f}", "Prêmio": "R$ {:.2f}",
                    "Delta": "{:.4f}", "Theta": "{:.4f}", "Vega": "{:.4f}",
                    "Rendimento Retido (%)": "{:.2f}%", "Retorno Máx. (%)": "{:.2f}%"
                }),
                hide_index=True, use_container_width=True
            )

# =============================================================================
# MÓDULO 2: GESTÃO DE POSIÇÃO ABERTA E ROLAGEM
# =============================================================================
else:
    st.subheader("3. Dados da Opção Atualmente Vendida")
    
    col_pos1, col_pos2 = st.columns(2)
    with col_pos1:
        preco_entrada_opcao = st.number_input("Prêmio Recebido na Abertura (R$)", value=1.40, step=0.05, format="%.2f")
        ticker_pos = st.text_input("Ticker Opção Vendida", value="PETRJ400")
        strike_pos = st.number_input("Strike Opção Vendida (R$)", value=40.00, step=0.50, format="%.2f")
    with col_pos2:
        premio_atual_opcao = st.number_input("Prêmio Atual para Recompra (R$)", value=0.25, step=0.05, format="%.2f")
        delta_atual = st.number_input("Delta Atual", value=0.0825, format="%.4f", step=0.0001)
        theta_atual = st.number_input("Theta/Dia Atual (R$)", value=-0.0185, format="%.4f", step=0.0001)
        vega_atual = st.number_input("Vega Atual (R$)", value=0.0210, format="%.4f", step=0.0001)

    # Métricas de P&L da Posição
    lucro_premia_pct = ((preco_entrada_opcao - premio_atual_opcao) / preco_entrada_opcao) * 100
    lucro_monetario = preco_entrada_opcao - premio_atual_opcao
    valor_extrinseco_restante = premio_atual_opcao if preco_acao < strike_pos else max(0.01, premio_atual_opcao - (preco_acao - strike_pos))

    st.markdown("### 📈 Diagnóstico da Posição Atual")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Lucro Capturado no Prêmio", f"{lucro_premia_pct:.1f}%", f"R$ {lucro_monetario:.2f}/ação")
    col_m2.metric("Valor Extrínseco Restante", f"R$ {valor_extrinseco_restante:.2f}")
    col_m3.metric("Delta Atual", f"{delta_atual:.4f}")

    # Decisão Sistemática Baseada na Literatura (Passarel / Natenberg / Sinclair)
    recomenda_rolagem = False
    motivo_decisao = ""

    if lucro_premia_pct >= 80.0 or valor_extrinseco_restante <= (preco_entrada_opcao * 0.15):
        recomenda_rolagem = True
        motivo_decisao = f"**Regra dos 80% / Decaimento Esgotado:** Você já capturou {lucro_premia_pct:.1f}% do prêmio total. Manter a posição aberta expõe a custódia a risco de cauda por apenas R$ {valor_extrinseco_restante:.2f} de valor extrínseco restante. O custo-benefício do Theta enfraqueceu."
    elif delta_atual >= 0.65:
        recomenda_rolagem = True
        motivo_decisao = f"**Risco de Exercício Deep-ITM (Delta {delta_atual:.4f}):** A opção entrou fundo no dinheiro. O risco de atribuição e limitação do ganho de capital justifica a rolar para defender ou subir o strike."
    elif dte <= 5 and delta_atual > 0.40:
        recomenda_rolagem = True
        motivo_decisao = f"**Gamma Risk Pré-Vencimento:** Faltando apenas {dte} DTE e com Delta em {delta_atual:.4f}, a posição possui alto risco de Gamma. Flutuações mínimas no preço da ação alterarão drasticamente o prêmio."
    else:
        recomenda_rolagem = False
        motivo_decisao = f"**Manter Posição:** A opção ainda retém R$ {valor_extrinseco_restante:.2f} em valor extrínseco com captura de prêmio em {lucro_premia_pct:.1f}%. A relação Theta/Risco continua altamente favorável ao lançador."

    st.divider()

    if recomenda_rolagem:
        st.warning(f"⚠️ **RECOMENDAÇÃO: REALIZAR ROLAGEM OU ENCERRAMENTO**\n\n{motivo_decisao}")
    else:
        st.success(f"✅ **RECOMENDAÇÃO: PERMANECER NA OPERAÇÃO**\n\n{motivo_decisao}")

    # -----------------------------------------------------------------------------
    # SIMULADOR DE ROLAGEM (SÉRIE SEGUINTE - DTE PROLONGADO)
    # -----------------------------------------------------------------------------
    st.divider()
    st.subheader("4. Simulação de Rolagem (Série Seguinte)")
    st.caption("Insira até duas opções da próxima série de vencimento para calcular o Crédito Líquido (Net Credit / Net Debit).")

    dte_proxima = st.number_input("Dias Úteis até Vencimento da Próxima Série (DTE)", value=44, step=1)

    st.markdown("#### Opções Alvo para Venda (Série Seguinte)")
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("**Opção Alvo A (ex: Conservadora)**")
        op_rol_A = entrada_opcao_detalhada("rol", "A", 0.2215, 1.10, 42.00, "PETRK420", 0.0890, -0.0125)

    with col_r2:
        st.markdown("**Opção Alvo B (ex: Agressiva/Mesmo Strike)**")
        op_rol_B = entrada_opcao_detalhada("rol", "B", 0.3540, 1.75, 40.00, "PETRK400", 0.1120, -0.0160)

    if st.button("🔄 Simular e Comparar Rolagens", use_container_width=True):
        def calcular_rolagem(op_alvo):
            # Custo de Recompra da Posição Atual = premio_atual_opcao
            # Prêmio Recebido na Nova Venda = op_alvo["Prêmio"]
            credito_liquido = op_alvo["Prêmio"] - premio_atual_opcao
            taxa_liquida_rolagem = (credito_liquido / preco_acao) * 100
            novo_strike = op_alvo["Strike"]
            ganho_strike_adicional = (novo_strike - strike_pos) if novo_strike > strike_pos else 0.0
            
            return {
                "Ticker Novo": op_alvo["Ticker"],
                "Novo Strike": novo_strike, "Prêmio Novo": op_alvo["Prêmio"],
                "Custo Recompra": premio_atual_opcao,
                "Net Credit (R$)": credito_liquido,
                "Taxa Líq. Rolagem (%)": taxa_liquida_rolagem,
                "Delta Novo": op_alvo["Delta"], "Theta Novo": op_alvo["Theta"], "Vega Novo": op_alvo["Vega"],
                "Elevação de Strike (R$)": ganho_strike_adicional
            }

        res_a = calcular_rolagem(op_rol_A)
        res_b = calcular_rolagem(op_rol_B)
        df_rol = pd.DataFrame([res_a, res_b])

        st.markdown("### 📊 Resultado da Simulação de Rolagem")
        st.dataframe(
            df_rol[["Ticker Novo", "Novo Strike", "Prêmio Novo", "Custo Recompra", "Net Credit (R$)", "Taxa Líq. Rolagem (%)", "Delta Novo", "Theta Novo", "Vega Novo"]].style.format({
                "Novo Strike": "R$ {:.2f}", "Prêmio Novo": "R$ {:.2f}", "Custo Recompra": "R$ {:.2f}",
                "Net Credit (R$)": "R$ {:.2f}", "Taxa Líq. Rolagem (%)": "{:.2f}%",
                "Delta Novo": "{:.4f}", "Theta Novo": "{:.4f}", "Vega Novo": "{:.4f}"
            }),
            hide_index=True, use_container_width=True
        )

        st.markdown("### 🧠 Racional de Mercado sobre Rolagem (Natenberg & Sinclair)")
        st.info(f"""
        * **Regra do Crédito Líquido (Net Credit):** Sempre dê preferência a rolagens que gerem **crédito positivo** (`Net Credit > 0`). Pagar para rolar (`Net Debit`) consome o prêmio acumulado e reduz a margem de segurança da operação.
        * **Mapeamento de Gregas pós-Rolagem:**
          * **Delta:** Verifique se a rolagem resgata a assimetria defensiva da operação (idealmente reduzindo o Delta para a faixa de `0.15` a `0.25`).
          * **Theta (Decaimento Temporal):** Ao rolar para um DTE maior ({dte_proxima} dias úteis), o Theta absoluto diário por opção costuma diminuir ligeiramente, mas você reinicia a fase de aceleração da curva de valor extrínseco.
          * **Vega:** Atenção ao regime de IV Rank ({iv_rank:.1f}%). Se a IV estiver alta, a nova venda capturará um prêmio inflado pela volatilidade.
        """)
    
