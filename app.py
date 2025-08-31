# app.py — Dashboard de RH (versão ajustada com tratamento de erros visível)
# Como rodar:python -m venv venv
# 0) Crie um ambiente virtual  -> python -m venv .venv
# 1) Ative a venv  ->  .venv\Scripts\Activate.ps1   (Windows)  |  source .venv/bin/activate  (Mac/Linux)
# 2) Instale deps  ->  pip install -r requirements.txt
# 3) Rode          ->  streamlit run app.py

# --------------------- Importações ---------------------
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import date
from io import BytesIO

# --------------------- Configuração básica ---------------------
st.set_page_config(page_title="Dashboard de RH", layout="wide")
st.title("Dashboard de RH")

# --------------------- Injeção de CSS para a fonte e a cor de fundo ---------------------
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        
        /* Aplica a nova cor de fundo */
        body {
            background-color: #1A2436; /* Azul-escuro acinzentado */
        }

        /* Aplica a fonte apenas a elementos de texto, títulos e KPIs */
        body, h1, h2, h3, h4, h5, h6, .stMetric, p, div {
            font-family: 'Poppins', sans-serif;
        }

        /* Mantém o ajuste do título para maior impacto */
        h1 {
            font-weight: 700;
        }

        .stMetric {
            font-weight: 600;
        }

        /* Melhorias para a tabela */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid #334466; /* Borda sutil */
        }

        /* Cores vibrantes para a tabela */
        .stDataFrame table {
            background-color: #2E3A52;
        }

        .stDataFrame table tbody tr {
            background-color: #2E3A52;
        }

        .stDataFrame table tbody tr:nth-child(odd) {
            background-color: #38455C;
        }
        
        /* Cor de destaque para as linhas selecionadas */
        .stDataFrame table tbody tr:hover {
            background-color: #FF69B4; /* Rosa vibrante */
        }

        /* Estilização da barra de rolagem */
        .stDataFrame::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }

        .stDataFrame::-webkit-scrollbar-track {
            background: #2E3A52;
            border-radius: 10px;
        }

        .stDataFrame::-webkit-scrollbar-thumb {
            background-color: #FF69B4; /* Rosa vibrante */
            border-radius: 10px;
            border: 3px solid #2E3A52;
        }

    </style>
    """, unsafe_allow_html=True)

# Se o arquivo estiver na mesma pasta do app.py, pode deixar assim.
# Ajuste para o caminho local caso esteja em outra pasta (ex.: r"C:\...\BaseFuncionarios.xlsx")
DEFAULT_EXCEL_PATH = "BaseFuncionarios.xlsx"
DATE_COLS = ["Data de Nascimento", "Data de Contratacao", "Data de Demissao"]

# --------------------- Funções utilitárias ---------------------
def brl(x: float) -> str:
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    # Padroniza textos
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()

    # Datas
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")

    # Padroniza Sexo
    if "Sexo" in df.columns:
        df["Sexo"] = (
            df["Sexo"].str.upper()
            .replace({"MASCULINO": "M", "FEMININO": "F"})
        )

    # Garante numéricos
    for col in ["Salario Base", "Impostos", "Beneficios", "VT", "VR"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Colunas derivadas
    today = pd.Timestamp(date.today())

    if "Data de Nascimento" in df.columns:
        df["Idade"] = ((today - df["Data de Nascimento"]).dt.days // 365).clip(lower=0)

    if "Data de Contratacao" in df.columns:
        meses = (today.year - df["Data de Contratacao"].dt.year) * 12 + \
                (today.month - df["Data de Contratacao"].dt.month)
        df["Tempo de Casa (meses)"] = meses.clip(lower=0)

    if "Data de Demissao" in df.columns:
        df["Status"] = np.where(df["Data de Demissao"].notna(), "Desligado", "Ativo")
    else:
        df["Status"] = "Ativo"

    df["Custo Total Mensal"] = df[["Salario Base", "Impostos", "Beneficios", "VT", "VR"]].sum(axis=1)
    return df

@st.cache_data
def load_from_path(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    return prepare_df(df)

@st.cache_data
def load_from_bytes(uploaded_bytes) -> pd.DataFrame:
    df = pd.read_excel(uploaded_bytes, sheet_name=0, engine="openpyxl")
    return prepare_df(df)

# --------------------- Sidebar: fonte de dados ---------------------
with st.sidebar:
    st.header("Fonte de dados")
    st.caption("Use **Upload** ou informe o caminho do arquivo .xlsx")
    up = st.file_uploader("Carregar Excel (.xlsx)", type=["xlsx"])
    caminho_manual = st.text_input("Ou caminho do Excel", value=DEFAULT_EXCEL_PATH)
    st.divider()
    if up is None:
        existe = os.path.exists(caminho_manual)
        st.write(f"Arquivo em caminho: **{caminho_manual}**")
        st.write("Existe: ", "✅ Sim" if existe else "❌ Não")

# --------------------- Carregamento com erros visíveis ---------------------
df = None
fonte = None
if up is not None:
    try:
        # Ação de Upload: Envio de um arquivo de um dispositivo para o dashboard.
        df = load_from_bytes(up)
        fonte = "Upload"
        st.caption(f"Dados carregados via **{fonte}**. Linhas: {len(df)} | Colunas: {len(df.columns)}")
    except Exception as e:
        st.error(f"Erro ao ler Excel (Upload): {e}")
        st.stop()
else:
    try:
        if not os.path.exists(caminho_manual):
            st.error(f"Arquivo não encontrado em: {caminho_manual}")
            st.info("Dica: coloque o .xlsx na mesma pasta do app.py ou ajuste o caminho acima.")
            st.stop()
        df = load_from_path(caminho_manual)
        fonte = "Caminho"
        st.caption(f"Dados carregados via **{fonte}**. Linhas: {len(df)} | Colunas: {len(df.columns)}")
    except Exception as e:
        st.error(f"Erro ao ler Excel (Caminho): {e}")
        st.stop()
        
# --------------------- AVISO IMPORTANTE ---------------------
if df is None:
    st.info("Por favor, carregue um arquivo Excel válido para continuar.")
    st.stop()

# Mostra colunas detectadas (ajuda no debug)
with st.expander("Ver colunas detectadas"):
    st.write(list(df.columns))

# --------------------- Filtros ---------------------
st.sidebar.header("Filtros")

def msel(col_name: str):
    if col_name in df.columns:
        vals = sorted([v for v in df[col_name].dropna().unique()])
        return st.sidebar.multiselect(col_name, vals)
    return []

area_sel   = msel("Área")
nivel_sel  = msel("Nível")
cargo_sel  = msel("Cargo")
sexo_sel   = msel("Sexo")
status_sel = msel("Status")
nome_busca = st.sidebar.text_input("Buscar por Nome Completo")

# Períodos
def date_bounds(series: pd.Series):
    s = series.dropna()
    if s.empty:
        return None
    return (s.min().date(), s.max().date())

contr_bounds = date_bounds(df["Data de Contratacao"]) if "Data de Contratacao" in df.columns else None
demis_bounds = date_bounds(df["Data de Demissao"]) if "Data de Demissao" in df.columns else None

if contr_bounds:
    d1, d2 = st.sidebar.date_input("Período de Contratação", value=contr_bounds)
else:
    d1, d2 = None, None

if demis_bounds:
    d3, d4 = st.sidebar.date_input("Período de Demissão", value=demis_bounds)
else:
    d3, d4 = None, None

# Sliders (idade e salário)
if "Idade" in df.columns and not df["Idade"].dropna().empty:
    ida_min, ida_max = int(df["Idade"].min()), int(df["Idade"].max())
    faixa_idade = st.sidebar.slider("Faixa Etária", ida_min, ida_max, (ida_min, ida_max))
else:
    faixa_idade = None

if "Salario Base" in df.columns and not df["Salario Base"].dropna().empty:
    sal_min, sal_max = float(df["Salario Base"].min()), float(df["Salario Base"].max())
    faixa_sal = st.sidebar.slider("Faixa de Salário Base", float(sal_min), float(sal_max), (float(sal_min), float(sal_max)))
else:
    faixa_sal = None

# Aplica filtros
df_f = df.copy()

def apply_in(df_, col, values):
    if values and col in df_.columns:
        return df_[df_[col].isin(values)]
    return df_

df_f = apply_in(df_f, "Área", area_sel)
df_f = apply_in(df_f, "Nível", nivel_sel)
df_f = apply_in(df_f, "Cargo", cargo_sel)
df_f = apply_in(df_f, "Sexo", sexo_sel)
df_f = apply_in(df_f, "Status", status_sel)

if nome_busca and "Nome Completo" in df_f.columns:
    df_f = df_f[df_f["Nome Completo"].str.contains(nome_busca, case=False, na=False)]

if faixa_idade and "Idade" in df_f.columns:
    df_f = df_f[(df_f["Idade"] >= faixa_idade[0]) & (df_f["Idade"] <= faixa_idade[1])]

if faixa_sal and "Salario Base" in df_f.columns:
    df_f = df_f[(df_f["Salario Base"] >= faixa_sal[0]) & (df_f["Salario Base"] <= faixa_sal[1])]

if d1 and d2 and "Data de Contratacao" in df_f.columns:
    df_f = df_f[(df_f["Data de Contratacao"].isna()) |
                ((df_f["Data de Contratacao"] >= pd.to_datetime(d1)) &
                 (df_f["Data de Contratacao"] <= pd.to_datetime(d2)))]

if d3 and d4 and "Data de Demissao" in df_f.columns:
    df_f = df_f[(df_f["Data de Demissao"].isna()) |
                ((df_f["Data de Demissao"] >= pd.to_datetime(d3)) &
                 (df_f["Data de Demissao"] <= pd.to_datetime(d4)))]

# --------------------- KPIs (Key Performance Indicators) ---------------------
# KPI é a sigla para 'Key Performance Indicator', que significa 'Indicador-Chave de Desempenho'.
# São métricas usadas para medir o sucesso ou o desempenho de uma atividade.
def k_headcount_ativo(d):
    # Headcount Ativo: a contagem total de funcionários que estão trabalhando ativamente na empresa.
    return int((d["Status"] == "Ativo").sum()) if "Status" in d.columns else 0

def k_desligados(d):
    # Desligados: o número de funcionários que não fazem mais parte da empresa.
    return int((d["Status"] == "Desligado").sum()) if "Status" in d.columns else 0

def k_folha(d):
    return float(d.loc[d["Status"] == "Ativo", "Salario Base"].sum()) \
        if ("Status" in d.columns and "Salario Base" in d.columns) else 0.0

def k_custo_total(d):
    return float(d.loc[d["Status"] == "Ativo", "Custo Total Mensal"].sum()) \
        if ("Status" in d.columns and "Custo Total Mensal" in d.columns) else 0.0

def k_idade_media(d):
    return float(d["Idade"].mean()) if "Idade" in d.columns and len(d) > 0 else 0.0

def k_tempo_casa_medio(d):
    col = "Tempo de Casa (meses)"
    return float(d[col].mean()) if col in d.columns and len(d) > 0 else 0.0

def k_avaliacao_media(d):
    col = "Avaliação do Funcionário"
    return float(d[col].mean()) if col in d.columns and len(d) > 0 else 0.0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Headcount Ativo", k_headcount_ativo(df_f))
c2.metric("Desligados", k_desligados(df_f))
c3.metric("Folha Salarial", brl(k_folha(df_f)))
c4.metric("Custo Total", brl(k_custo_total(df_f)))
c5.metric("Idade Média", f"{k_idade_media(df_f):.1f} anos")
c6.metric("Avaliação Média", f"{k_avaliacao_media(df_f):.2f}")

st.divider()

# --------------------- Gráficos ---------------------
colA, colB = st.columns(2)
with colA:
    if "Área" in df_f.columns:
        d = df_f.groupby("Área").size().reset_index(name="Headcount")
        if not d.empty:
            # Altera a cor do gráfico para laranja vibrante
            fig = px.bar(d, x="Área", y="Headcount", title="Headcount por Área",
                         color_discrete_sequence=["#FF7F00"])
            st.plotly_chart(fig, use_container_width=True)

with colB:
    if "Cargo" in df_f.columns and "Salario Base" in df_f.columns:
        d = df_f.groupby("Cargo", as_index=False)["Salario Base"].mean().sort_values("Salario Base", ascending=False)
        if not d.empty:
            fig = px.bar(d, y="Cargo", x="Salario Base", title="Salário Médio por Cargo", orientation='h',
                         color_discrete_sequence=["#FFA500"])
            fig.update_traces(texttemplate='R$%{x:.2f}', textposition='outside')
            fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)

colC, colD = st.columns(2)
with colC:
    if "Idade" in df_f.columns and not df_f["Idade"].dropna().empty:
        fig = px.histogram(df_f, x="Idade", nbins=20, title="Distribuição de Idade", 
                           color_discrete_sequence=["#0080FF"])
        
        fig.update_traces(texttemplate='%{y}', textposition='outside')
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.2)')

        fig.update_layout(
            font=dict(family="Poppins"),
            xaxis_title="Idade",
            yaxis_title="Contagem",
            bargap=0.1
        )
        st.plotly_chart(fig, use_container_width=True)


with colD:
    if "Sexo" in df_f.columns:
        d = df_f["Sexo"].value_counts().reset_index()
        d.columns = ["Sexo", "Contagem"]
        if not d.empty:
            fig = go.Figure(data=[go.Pie(
                labels=d['Sexo'],
                values=d['Contagem'],
                hole=.4, # Cria o buraco para o gráfico de rosca
                pull=[0.02, 0.02], # Adiciona um espaçamento entre as fatias
                marker_colors=["#1E90FF", "#87CEFA"] # Cores azuis vibrantes e harmoniosas
            )])

            # Adiciona o texto central
            total_count = d['Contagem'].sum()
            fig.add_annotation(
                text=f'Total:<br>{total_count}',
                x=0.5, y=0.5, font_size=20, showarrow=False
            )
            
            # Atualiza o layout para ter um visual mais limpo
            fig.update_layout(
                title_text="Distribuição por Sexo",
                title_x=0.5,
                legend=dict(x=1.1, y=0.5),
                uniformtext_minsize=12,
                uniformtext_mode='hide'
            )

            st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------- Tabela e Downloads ---------------------
st.subheader("Tabela (dados filtrados)")
# Adicionando um campo de busca
nome_busca_tabela = st.text_input("Buscar na Tabela por Nome Completo")
if nome_busca_tabela:
    df_tabela = df_f[df_f["Nome Completo"].str.contains(nome_busca_tabela, case=False, na=False)]
else:
    df_tabela = df_f

st.dataframe(df_tabela, use_container_width=True)

csv_bytes = df_f.to_csv(index=False).encode("utf-8")
st.download_button(
    "Baixar CSV filtrado",
    data=csv_bytes,
    file_name="funcionarios_filtrado.csv",
    mime="text/csv"
)

# Exportar Excel filtrado (opcional)
to_excel = st.toggle("Gerar Excel filtrado para download")
if to_excel:
    from io import BytesIO
    buff = BytesIO()
    with pd.ExcelWriter(buff, engine="openpyxl") as writer:
        df_f.to_excel(writer, index=False, sheet_name="Filtrado")
    st.download_button(
        "Baixar Excel filtrado",
        data=buff.getvalue(),
        file_name="funcionarios_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )