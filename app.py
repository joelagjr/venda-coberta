import streamlit as st
import pandas as pd
import numpy as np

# Configuração visual otimizada para mobile
st.set_page_config(page_title="Venda Coberta Pro & Rolagem", layout="centered")

st.title("🎯 Venda Coberta & Gestão de Rolagem")
st.caption("Análise Quantitativa | Deltas, Gamma, Theta (%), Vega, Proventos & Tabela de Payoff do Net Credit")

# Seleção de Modo
modo = st.sidebar.radio(
    "Selecione o Módulo de Análise:",
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

# Função auxiliar para renderizar entradas de opções com Gamma e Theta em % (3 casas)
def entrada_opcao_detalhada(prefixo, num, d_def, premio_def, strike_def, ticker_def, vega_def, theta_pct_def, gamma_def=0.0215):
    c1, c2, c3 = st.columns(3)
    with c1:
        ticker = st.text_input(f"Ticker Opção {num}", value=ticker_def, key=f"{prefixo}_t_{num}")
        strike = st.number_input(f"Strike (R$)", value=strike_def, key=f"{prefixo}_s_{num}", format="%.2f")
    with c2:
        premio = st.number_input(f"Prêmio Atual (R$)", value=premio_def, key=f"{prefixo}_p_{num}", format="%.2f")
        delta = st.number_input(f"Delta", value=d_def, key=f"{prefixo}_d_{num}", format="%.4f", step=0.0001)
    with c3:
        theta_pct = st.number_input(f"Theta/Dia (%)", value=theta_pct_def, key=f"{prefixo}_th_{num}", format="%.3f", step=0.001)
        gamma = st.number_input(f"Gamma", value=gamma_def, key=f"{prefixo}_g_{num}", format="%.4f", step=0.0001)
        vega = st.number_input(f"Vega (R$)", value=vega_def, key=f"{prefixo}_v_{num}", format="%.4f", step=0.0001)
    
    return {
        "Ticker": ticker, "Strike": strike, "Prêmio": premio,
        "Delta": delta, "Gamma": gamma, "ThetaPct": theta_pct, "Vega": vega
    }

# =============================================================================
# MÓDULO 1: NOVA VENDA COBERTA
# =============================================================================
if modo == "1. Nova Venda Coberta":
    st.subheader("3. Opções Alvo para Lançamento Inicial")
    
    def entrada_opcao(num, rotulo_delta, d_def, premio_def, strike_def, ticker_def, vega_def, theta_pct_def, gamma_def):
        ativo = st.checkbox(f"Ativar Opção {num} (Ref. Delta ~{rotulo_delta})", value=True if num in [1, 2] else False, key=f"chk_n_{num}")
        if ativo:
            return entrada_opcao_detalhada("nova", num, d_def, premio_def, strike_def, ticker_def, vega_def, theta_pct_def, gamma_def)
        return None

    op1 = entrada_opcao(1, "30", 0.3012, 1.20, 40.00, "PETRJ400", 0.0815, -0.395, 0.0245)
    op2 = entrada_opcao(2, "20", 0.2045, 0.65, 41.50, "PETRJ415", 0.0621, -0.306, 0.0182)
    op3 = entrada_opcao(3, "15", 0.1480, 0.35, 42.50, "PETRJ425", 0.0432, -0.205, 0.0115)

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

            st.subheader("📊 Comparativo das Opções (Gregas Ajustadas)")
            st.dataframe(
                df[["Ticker", "Strike", "Prêmio", "Delta", "Gamma", "ThetaPct", "Vega", "Rendimento Retido (%)", "Retorno Máx. (%)"]].style.format({
                    "Strike": "R$ {:.2f}", "Prêmio": "R$ {:.2f}",
                    "Delta": "{:.4f}", "Gamma": "{:.4f}", "ThetaPct": "{:.3f}%", "Vega": "{:.4f}",
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
        gamma_atual = st.number_input("Gamma Atual", value=0.0120, format="%.4f", step=0.0001)
        theta_pct_atual = st.number_input("Theta/Dia Atual (%)", value=-0.481, format="%.3f", step=0.001)
        vega_atual = st.number_input("Vega Atual (R$)", value=0.0210, format="%.4f", step=0.0001)

    # Métricas de P&L da Posição
    lucro_premia_pct = ((preco_entrada_opcao - premio_atual_opcao) / preco_entrada_opcao) * 100
    lucro_monetario = preco_entrada_opcao - premio_atual_opcao
    valor_extrinseco_restante = premio_atual_opcao if preco_acao < strike_pos else max(0.01, premio_atual_opcao - (preco_acao - strike_pos))

    st.markdown("### 📈 Diagnóstico da Posição Atual")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Lucro no Prêmio", f"{lucro_premia_pct:.1f}%", f"R$ {lucro_monetario:.2f}/ação")
    col_m2.metric("Extrínseco Restante", f"R$ {valor_extrinseco_restante:.2f}")
    col_m3.metric("Delta Atual", f"{delta_atual:.4f}")
    col_m4.metric("Gamma Atual", f"{gamma_atual:.4f}")

    # Decisão Sistemática Baseada na Literatura (Natenberg / Sinclair)
    recomenda_rolagem = False
    motivo_decisao = ""

    if lucro_premia_pct >= 80.0 or valor_extrinseco_restante <= (preco_entrada_opcao * 0.15):
        recomenda_rolagem = True
        motivo_decisao = f"**Regra dos 80% / Decaimento Esgotado:** Você capturou {lucro_premia_pct:.1f}% do prêmio. Manter a posição expõe ao risco de cauda por apenas R$ {valor_extrinseco_restante:.2f} extrínsecos restantes."
    elif gamma_atual >= 0.0500 and dte <= 7:
        recomenda_rolagem = True
        motivo_decisao = f"**Risco Extremo de Gamma ({gamma_atual:.4f}) Pré-Vencimento ({dte} DTE):** A aceleração do Delta por variação no ativo está altíssima, tornando o prêmio instável."
    elif delta_atual >= 0.65:
        recomenda_rolagem = True
        motivo_decisao = f"**Risco de Exercício Deep-ITM (Delta {delta_atual:.4f}):** A opção entrou fundo no dinheiro. Recomenda-se rolar para subir o strike e capturar ganho de capital extra."
    else:
        recomenda_rolagem = False
        motivo_decisao = f"**Manter Posição:** A opção ainda possui R$ {valor_extrinseco_restante:.2f} extrínsecos e Theta diário de {theta_pct_atual:.3f}%. Relação risco/retorno favorável."

    st.divider()

    if recomenda_rolagem:
        st.warning(f"⚠️ **RECOMENDAÇÃO: REALIZAR ROLAGEM OU ENCERRAMENTO**\n\n{motivo_decisao}")
    else:
        st.success(f"✅ **RECOMENDAÇÃO: PERMANECER NA OPERAÇÃO**\n\n{motivo_decisao}")

    # -----------------------------------------------------------------------------
    # SIMULADOR DE ROLAGEM & TABELA DINÂMICA DE PAYOFF
    # -----------------------------------------------------------------------------
    st.divider()
    st.subheader("4. Simulação de Rolagem & Tabela Dinâmica de Payoff")
    st.caption("Insira os alvos da próxima série e analise a matriz de payoff combinando Net Credit e Proventos.")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("**Opção Alvo A (Série Seguinte)**")
        op_rol_A = entrada_opcao_detalhada("rol", "A", 0.2215, 1.10, 42.00, "PETRK420", 0.0890, -0.320, 0.0165)
    with col_r2:
        st.markdown("**Opção Alvo B (Série Seguinte)**")
        op_rol_B = entrada_opcao_detalhada("rol", "B", 0.3540, 1.75, 40.00, "PETRK400", 0.1120, -0.410, 0.0230)

    # Input adicional do provento esperado na PRÓXIMA série
    provento_proxima_serie = st.number_input("Provento Estimado na PRÓXIMA Série (R$/ação)", value=0.00, step=0.10, format="%.2f")

    if st.button("🔄 Simular Rolagem e Gerar Tabela Dinâmica", use_container_width=True):
        def calcular_rolagem(op_alvo):
            credito_liquido = op_alvo["Prêmio"] - premio_atual_opcao
            taxa_liquida_rolagem = (credito_liquido / preco_acao) * 100
            novo_strike = op_alvo["Strike"]
            ganho_strike = max(0.0, novo_strike - strike_pos)
            
            # Retornos
            retorno_sem_exercicio = credito_liquido + valor_provento + provento_proxima_serie
            retorno_maximo_total = retorno_sem_exercicio + (novo_strike - preco_acao)
            
            return {
                "Ticker Novo": op_alvo["Ticker"],
                "Novo Strike": novo_strike, "Prêmio Novo": op_alvo["Prêmio"],
                "Net Credit (R$)": credito_liquido,
                "Taxa Líq. (%)": taxa_liquida_rolagem,
                "Delta Novo": op_alvo["Delta"], "Gamma Novo": op_alvo["Gamma"],
                "Theta (%) Novo": op_alvo["ThetaPct"], "Vega Novo": op_alvo["Vega"],
                "Retorno Sem Exercício (R$)": retorno_sem_exercicio,
                "Retorno Máx Total (R$)": retorno_maximo_total
            }

        res_a = calcular_rolagem(op_rol_A)
        res_b = calcular_rolagem(op_rol_B)
        df_rol = pd.DataFrame([res_a, res_b])

        st.markdown("### 📊 Comparativo Técnico das Rolagens")
        st.dataframe(
            df_rol[["Ticker Novo", "Novo Strike", "Prêmio Novo", "Net Credit (R$)", "Taxa Líq. (%)", "Delta Novo", "Gamma Novo", "Theta (%) Novo", "Vega Novo"]].style.format({
                "Novo Strike": "R$ {:.2f}", "Prêmio Novo": "R$ {:.2f}", "Net Credit (R$)": "R$ {:.2f}",
                "Taxa Líq. (%)": "{:.2f}%", "Delta Novo": "{:.4f}", "Gamma Novo": "{:.4f}",
                "Theta (%) Novo": "{:.3f}%", "Vega Novo": "{:.4f}"
            }),
            hide_index=True, use_container_width=True
        )

        # -------------------------------------------------------------------------
        # TABELA DINÂMICA DE PAYOFF
        # -------------------------------------------------------------------------
        st.markdown("### 📊 Tabela Dinâmica de Payoff no Vencimento (Net Credit + Proventos)")
        st.caption("Simulação do resultado financeiro total (R$/ação) para diferentes cenários do preço da ação no vencimento futuro.")

        # Variação simulada do preço da ação
        cenarios_pct = np.array([-10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0])
        precos_cenarios = preco_acao * (1 + cenarios_pct / 100)

        dados_payoff = []

        for p_fim in precos_cenarios:
            linha = {"Preço Ação No Vencimento": p_fim, "Variação Ação (%)": ((p_fim - preco_acao) / preco_acao) * 100}
            
            # Cálculo Payoff Posição Sem Rolagem (Mantida até o fim)
            val_intrinsic_atual = max(0.0, p_fim - strike_pos)
            payoff_mantida = (p_fim - preco_acao) + (preco_entrada_opcao - val_intrinsic_atual) + valor_provento
            linha["Payoff Mantida (R$)"] = payoff_mantida

            # Payoff Rolagem A
            val_intrinsic_A = max(0.0, p_fim - op_rol_A["Strike"])
            payoff_rol_A = (p_fim - preco_acao) + (preco_entrada_opcao - premio_atual_opcao) + op_rol_A["Prêmio"] - val_intrinsic_A + valor_provento + provento_proxima_serie
            linha[f"Payoff Rolagem {op_rol_A['Ticker']} (R$)"] = payoff_rol_A

            # Payoff Rolagem B
            val_intrinsic_B = max(0.0, p_fim - op_rol_B["Strike"])
            payoff_rol_B = (p_fim - preco_acao) + (preco_entrada_opcao - premio_atual_opcao) + op_rol_B["Prêmio"] - val_intrinsic_B + valor_provento + provento_proxima_serie
            linha[f"Payoff Rolagem {op_rol_B['Ticker']} (R$)"] = payoff_rol_B

            dados_payoff.append(linha)

        df_payoff = pd.DataFrame(dados_payoff)

        # Exibição com formatação dinâmica
        st.dataframe(
            df_payoff.style.format({
                "Preço Ação No Vencimento": "R$ {:.2f}",
                "Variação Ação (%)": "{:+.1f}%",
                "Payoff Mantida (R$)": "R$ {:+.2f}",
                f"Payoff Rolagem {op_rol_A['Ticker']} (R$)": "R$ {:+.2f}",
                f"Payoff Rolagem {op_rol_B['Ticker']} (R$)": "R$ {:+.2f}"
            }),
            hide_index=True, use_container_width=True
        )

        st.info(f"""
        **Como ler a Tabela de Payoff:**
        * **Net Credit Efetivo:** O lucro acumulado das opções considera o ganho da posição anterior (`R$ {lucro_monetario:.2f}`) somado ao prêmio recebido na nova venda, menos proventos retidos no período (`R$ {valor_provento + provento_proxima_serie:.2f}`).
        * **Efeito Gamma na Rolagem:** Opções com **Gamma maior** aumentam o Delta rapidamente caso a ação suba, travando o ganho de capital no strike escolhido mais cedo.
        """)
        
