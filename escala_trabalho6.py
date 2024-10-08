import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Função para verificar se pode lançar a folga
def pode_lancar_folga(escala_range, linha, coluna, horario_atual):
    if coluna >= escala_range.shape[1]:
        return False

    if escala_range.iloc[linha, coluna] == "":
        if (
            linha > 0
            and horario_atual == escala_range.iloc[linha - 1, 3]
            and escala_range.iloc[linha - 1, coluna] == "F"
        ):
            return False
        if (
            linha < escala_range.shape[0] - 1
            and horario_atual == escala_range.iloc[linha + 1, 3]
            and escala_range.iloc[linha + 1, coluna] == "F"
        ):
            return False
        return True
    return False

# Função para calcular o total de vazios
def calcular_total_vazios(df):
    total_vazios = []
    for col in df.columns[6:]:  # Começando da coluna 7
        total_vazios.append((df[col] == "").sum())
    return total_vazios

# Função para projetar escala
def projetar_escala(df_dados, df_apoio, data_inicial, dias_no_mes):
    # Definir os tipos de folgas disponíveis
    num_folgas_dict = {
        "6x1": df_apoio.iloc[0, 1],
        "5x2": df_apoio.iloc[1, 1],
        "12x36": 2,  # Para 12x36 sempre 2 folgas
    }

    for i in range(len(df_dados)):
        if "Total" in str(df_dados.iloc[i, 0]):
            # Calcular o total de vazios
            total_vazios = calcular_total_vazios(df_dados.iloc[:i])
            df_dados.iloc[i, 6:] = total_vazios
            continue  # Pula para a próxima iteração

        tipo_escala = df_dados.iloc[i, 4]
        ultima_folga = pd.to_datetime(
            df_dados.iloc[i, 5], format="%d/%m/%Y", errors="coerce"
        )  # Coluna 'F'
        folgas_lancadas = 0
        dias_trabalhados_consecutivos = 0

        if pd.isna(ultima_folga):
            ultima_folga = data_inicial - timedelta(days=5)

        num_folgas = num_folgas_dict.get(tipo_escala, 0)

        if tipo_escala == "6x1":
            intervalo_minimo = dias_no_mes // num_folgas
            for j in range(1, dias_no_mes + 1):
                data_atual = data_inicial + timedelta(days=j - 1)
                coluna_folga = 6 + j - 1  # A partir da coluna 7

                if (data_atual - ultima_folga).days >= intervalo_minimo:
                    if pode_lancar_folga(
                        df_dados, i, coluna_folga, df_dados.iloc[i, 3]
                    ):
                        df_dados.iloc[i, coluna_folga] = "F"
                        ultima_folga = data_atual
                        folgas_lancadas += 1
                        dias_trabalhados_consecutivos = 0
                    else:
                        dias_trabalhados_consecutivos += 1

                if folgas_lancadas == num_folgas:
                    break

        elif tipo_escala == "5x2":
            num_folgas = df_apoio.iloc[1, 1]
            if num_folgas == 8:
                folgas_regulares = 6
                folgas_flexiveis = 2
            else:
                folgas_regulares = num_folgas
                folgas_flexiveis = 0

            intervalo_max_trabalho = 5

            for j in range(1, dias_no_mes + 1):
                data_atual = data_inicial + timedelta(days=j - 1)
                coluna_folga = 6 + j - 1

                if pode_lancar_folga(df_dados, i, coluna_folga, df_dados.iloc[i, 3]):
                    if (
                        dias_trabalhados_consecutivos >= intervalo_max_trabalho
                        and folgas_lancadas >= folgas_regulares
                    ) or (
                        folgas_lancadas < folgas_regulares
                        and (data_atual - ultima_folga).days >= intervalo_max_trabalho
                    ):
                        if (
                            folgas_lancadas + 2 <= folgas_regulares
                            and pode_lancar_folga(
                                df_dados, i, coluna_folga + 1, df_dados.iloc[i, 3]
                            )
                        ):
                            df_dados.iloc[i, coluna_folga] = "F"
                            df_dados.iloc[i, coluna_folga + 1] = "F"
                            ultima_folga = data_atual + timedelta(days=1)
                            folgas_lancadas += 2
                            dias_trabalhados_consecutivos = 0
                            j += 1
                        else:
                            df_dados.iloc[i, coluna_folga] = "F"
                            ultima_folga = data_atual
                            folgas_lancadas += 1
                            dias_trabalhados_consecutivos = 0
                    else:
                        dias_trabalhados_consecutivos += 1

                else:
                    dias_trabalhados_consecutivos += 1

                if folgas_lancadas == num_folgas:
                    break

            # Lançar folgas flexíveis
            for j in range(1, dias_no_mes + 1):
                if folgas_lancadas == num_folgas:
                    break
                data_atual = data_inicial + timedelta(days=j - 1)
                coluna_folga = 6 + j - 1

                if (
                    pode_lancar_folga(df_dados, i, coluna_folga, df_dados.iloc[i, 3])
                    and dias_trabalhados_consecutivos >= 5
                ):
                    df_dados.iloc[i, coluna_folga] = "F"
                    ultima_folga = data_atual
                    folgas_lancadas += 1
                    dias_trabalhados_consecutivos = 0
                else:
                    dias_trabalhados_consecutivos += 1

        elif tipo_escala == "12x36":
            dia_ultima_folga = ultima_folga.day
            folga_primeira_quinzena = False
            folga_segunda_quinzena = False
            folgas_lancadas = 0

            for j in range(1, dias_no_mes + 1):
                data_atual = data_inicial + timedelta(days=j - 1)
                coluna_folga = 6 + j - 1

                if pode_lancar_folga(df_dados, i, coluna_folga, df_dados.iloc[i, 3]):
                    if data_atual.day % 2 == dia_ultima_folga % 2:
                        if j <= 15 and not folga_primeira_quinzena:
                            df_dados.iloc[i, coluna_folga] = "F"
                            folgas_lancadas += 1
                            folga_primeira_quinzena = True
                        elif j > 15 and not folga_segunda_quinzena:
                            df_dados.iloc[i, coluna_folga] = "F"
                            folgas_lancadas += 1
                            folga_segunda_quinzena = True

                if folgas_lancadas == 2:
                    break

        if folgas_lancadas != num_folgas:
            st.warning(
                f"Número de folgas lançadas para o funcionário na linha {i + 1} é diferente do esperado. Lançadas: {folgas_lancadas}, Esperadas: {num_folgas}"
            )

    return df_dados

# Função para centralizar os "F" e aplicar estilo aos fins de semana
def style_dataframe(df, data_inicial):
    def highlight_and_center_f(val):
        return 'color: blue; font-weight: bold; text-align: center;' if val == 'F' else ''

    def highlight_weekend(col):
        col_index = df.columns.get_loc(col.name)
        if col_index >= 6:  # Apenas para as colunas de dias
            day = data_inicial + timedelta(days=col_index - 6)
            return ['background-color: #f0f0f0;' if day.weekday() >= 5 else '' for _ in col]
        return ['' for _ in col]

    return (df.style
            .applymap(highlight_and_center_f, subset=df.columns[6:])
            .apply(highlight_weekend, axis=0, subset=df.columns[6:]))

# Configuração do Streamlit
st.title("Projeção de Escala de Trabalho")

# Inputs para o arquivo Excel e datas
caminho_arquivo = st.text_input("Informe o caminho do arquivo Excel:", "")
data_inicio = st.text_input("Data Início (dd/mm/aaaa):", "")
data_fim = st.text_input("Data Fim (dd/mm/aaaa):", "")

if caminho_arquivo and data_inicio and data_fim:
    try:
        # Carregar o arquivo Excel
        df_dados = pd.read_excel(caminho_arquivo, sheet_name="Dados")
        df_apoio = pd.read_excel(caminho_arquivo, sheet_name="Apoio")
        st.success("Dados carregados com sucesso!")

        # Converter as datas
        data_inicial = datetime.strptime(data_inicio, "%d/%m/%Y")
        data_final = datetime.strptime(data_fim, "%d/%m/%Y")
        dias_no_mes = (data_final - data_inicial).days + 1

        # Formatar a coluna "U.F" para dd/mm/aaaa
        df_dados["U.F"] = pd.to_datetime(df_dados["U.F"]).dt.strftime("%d/%m/%Y")

        # Adicionar colunas para os dias
        for i in range(dias_no_mes):
            data = data_inicial + timedelta(days=i)
            df_dados[data.strftime("%d")] = ""  # Apenas o dia

        # Botão para lançar folgas
        if st.button("Lançar Folgas"):
            df_projetada = projetar_escala(
                df_dados, df_apoio, data_inicial, dias_no_mes
            )

            # Aplicar o estilo e exibir o DataFrame
            st.write("Escala projetada:")
            styled_df = style_dataframe(df_projetada, data_inicial)
            st.dataframe(styled_df)

    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados: {e}")