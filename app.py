"""
========================================================================================
SISTEMA DE INTELIGÊNCIA TRIBUTÁRIA - SEFIN PALMAS (TO)
PAINEL MVP INTERATIVO: PRIORIZAÇÃO DA COBRANÇA DA DÍVIDA ATIVA
Sprint 4 - Projeto Integrador Eixo II | BIINAR - Universidade Federal do Tocantins (UFT)
Coordenação: Prof. Dr. David Nadler Prata
Equipe Executora: Hyag, Ludmylla, Maiara, Sofia e Vitória
========================================================================================
"""

import os
import glob
import json
import io
import numpy as np
import pandas as pd
import joblib
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk

from src.pipeline.carregamento_inferencia import (
    get_pipeline_inferencia_singleton,
    GerenciadorModelos,
)
from src.scoring.recuperabilidade import (
    ScoringRecuperabilidade,
    FaixaRecuperabilidade,
)

# ======================================================================================
# 1. CONFIGURAÇÃO INICIAL E ESTILIZAÇÃO (LAYOUT WIDE & CSS CORPORATIVO SEFIN)
# ======================================================================================

st.set_page_config(
    page_title="SEFIN Palmas | Inteligência Tributária",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Personalizada com Identidade Visual da SEFIN Palmas
CUSTOM_CSS = """
<style>
    /* Estilo geral e tipografia */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Header Institucional */
    .sefin-header {
        background: linear-gradient(135deg, #0b2545 0%, #134074 50%, #0077b6 100%);
        color: #ffffff;
        padding: 24px 30px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    }
    .sefin-header h1 {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    .sefin-header p {
        margin: 6px 0 0 0;
        font-size: 0.95rem;
        color: #e0f2fe;
        opacity: 0.95;
    }
    .badge-sprint {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 8px;
    }

    /* Cartões de Métricas (KPIs) */
    .kpi-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.06);
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .kpi-sub {
        font-size: 0.80rem;
        color: #10b981;
        font-weight: 500;
    }

    /* Badges de Faixa de Recuperabilidade */
    .badge-alta {
        background-color: #dcfce7;
        color: #15803d;
        padding: 3px 10px;
        border-radius: 14px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-media {
        background-color: #fef3c7;
        color: #b45309;
        padding: 3px 10px;
        border-radius: 14px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-baixa {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 3px 10px;
        border-radius: 14px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }

    /* Avisos e Rodapés LGPD */
    .lgpd-box {
        background-color: #f8fafc;
        border-left: 4px solid #0284c7;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        font-size: 0.82rem;
        color: #334155;
        margin-top: 15px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ======================================================================================
# 2. CARREGAMENTO E GERENCIAMENTO DE DADOS E MODELOS (CACHE OTIMIZADO)
# ======================================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
DEFAULT_DATA_FILE = os.path.join(DATA_DIR, "divida_ativa_palmas.csv")

@st.cache_data(show_spinner="Carregando base de dados tributários...")
def load_data(file_source=None):
    """
    Carrega a base de dados tratada de dívida ativa da SEFIN Palmas.
    Se o arquivo não existir fisicamente, aciona dinamicamente a geração sintética.
    """
    if file_source is not None:
        if isinstance(file_source, str) and os.path.exists(file_source):
            df = pd.read_csv(file_source)
        else:
            df = pd.read_csv(file_source)
        return df

    if os.path.exists(DEFAULT_DATA_FILE):
        return pd.read_csv(DEFAULT_DATA_FILE)

    # Fallback automático: gera sinteticamente respeitando Palmas-TO
    try:
        import sys
        sys.path.append(DATA_DIR)
        from generate_synthetic_data import generate_sefin_data
        df = generate_sefin_data(n_samples=2500)
        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(DEFAULT_DATA_FILE, index=False, encoding="utf-8")
        return df
    except Exception:
        # Mini gerador de contingência caso os módulos externos não estejam no path
        np.random.seed(42)
        n = 1000
        return pd.DataFrame({
            "id_devedor": [f"SEFIN-PMW-{100000+i}" for i in range(n)],
            "contribuinte": [f"Contribuinte Anonimizado {i} (PF/PJ)" for i in range(n)],
            "documento_mascarado": [f"***.{100+i%899}.***-**" for i in range(n)],
            "tipo_pessoa": np.random.choice(["Pessoa Física (PF)", "Pessoa Jurídica (PJ)"], n),
            "numero_cda": [f"2023/CDA-{10000+i}" for i in range(n)],
            "tributo": np.random.choice(["IPTU", "ISSQN", "ITBI", "Taxas de Licenciamento"], n),
            "ano_inscricao": np.random.choice([2020, 2021, 2022, 2023, 2024], n),
            "tempo_inscricao_meses": np.random.randint(12, 72, n),
            "valor_principal": np.random.exponential(4500, n).round(2),
            "juros_multas": np.random.exponential(1200, n).round(2),
            "valor_total_divida": np.random.exponential(5700, n).round(2),
            "quantidade_debitos": np.random.randint(1, 8, n),
            "historico_parcelamentos": np.random.randint(0, 3, n),
            "execucao_ajuizada": np.random.choice(["Sim", "Não"], n),
            "possui_bens": np.random.choice(["Sim", "Não"], n),
            "contato_atualizado": np.random.choice(["Sim", "Não"], n),
            "faixa_renda": np.random.choice(["Até 2 SM", "2 a 5 SM", "5 a 10 SM", "Acima de 10 SM"], n),
            "regiao": np.random.choice(["Plano Diretor Sul", "Plano Diretor Norte", "Região Sul (Taquaralto)", "Jardins Aureny"], n),
            "bairro_setor": np.random.choice(["Quadra 104 Sul", "Quadra 110 Norte", "Taquaralto", "Jardim Aureny III"], n),
            "latitude": np.random.uniform(-10.33, -10.16, n),
            "longitude": np.random.uniform(-48.34, -48.29, n),
            "score_recuperabilidade": np.random.uniform(10, 95, n).round(1),
            "faixa_recuperabilidade": np.random.choice(["Alta", "Média", "Baixa"], n),
            "canal_recomendado": "Cobrança Digital (WhatsApp / DDA)"
        })

@st.cache_resource(show_spinner="Carregando modelo preditivo serializado...")
def load_ml_model(model_path_or_bytes):
    """
    Carrega pipeline de machine learning previamente serializado (.joblib ou .pkl).
    """
    try:
        if isinstance(model_path_or_bytes, str):
            model = joblib.load(model_path_or_bytes)
        else:
            model = joblib.load(io.BytesIO(model_path_or_bytes))
        return model, "OK"
    except Exception as e:
        return None, str(e)

def load_metrics_audit():
    """Carrega as métricas de auditoria da Sprint 4 caso disponíveis."""
    metrics_file = os.path.join(MODELS_DIR, "model_metrics.json")
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None



@st.cache_data(show_spinner="Executando pipeline de inferência preditiva e scoring...")
def run_pipeline_inference(df_input: pd.DataFrame, model_name: str):
    """
    Executa o pipeline de inferência e scoring com cache do Streamlit,
    garantindo velocidade e rastreabilidade nas interações.
    """
    pipeline = get_pipeline_inferencia_singleton()
    df_result, metadata = pipeline.executar_inferencia(df_input, model_name)
    return df_result, metadata

# ======================================================================================
# 3. BARRA LATERAL (SIDEBAR): GESTÃO DE ARTEFATOS, MODELOS E FILTROS TRIBUTÁRIOS
# ======================================================================================

st.sidebar.image(
    "https://img.icons8.com/fluency/96/courthouse.png", 
    width=64
)
st.sidebar.markdown("## **SEFIN Palmas**")
st.sidebar.caption("Inteligência Tributária • Dívida Ativa | Sprint 4 (UFT BIINAR)")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Modelos Preditivos (/models)")

# Busca automática por modelos disponíveis no diretório /models
available_models = []
if os.path.exists(MODELS_DIR):
    available_models = [os.path.basename(p) for p in glob.glob(os.path.join(MODELS_DIR, "*.joblib")) + glob.glob(os.path.join(MODELS_DIR, "*.pkl"))]

model_options = ["Carregar do repositório (/models)", "Fazer Upload de Modelo (.joblib / .pkl)"]
model_mode = st.sidebar.radio("Origem do Modelo:", model_options, label_visibility="collapsed")

active_model = None
active_model_name = "Nenhum modelo ativo"

if model_mode == "Carregar do repositório (/models)":
    if available_models:
        selected_model_file = st.sidebar.selectbox("Selecione o modelo treinado:", available_models)
        model_path = os.path.join(MODELS_DIR, selected_model_file)
        active_model, err = load_ml_model(model_path)
        if active_model:
            active_model_name = selected_model_file
            st.sidebar.success(f"Modelo Ativo: `{selected_model_file}`", icon="✅")
        else:
            st.sidebar.error(f"Erro ao carregar modelo: {err}")
    else:
        st.sidebar.warning("Nenhum modelo (.joblib/.pkl) encontrado em `/models`.")
else:
    uploaded_model_file = st.sidebar.file_uploader("Upload do modelo serializado:", type=["joblib", "pkl"])
    if uploaded_model_file is not None:
        active_model, err = load_ml_model(uploaded_model_file.read())
        if active_model:
            active_model_name = uploaded_model_file.name
            st.sidebar.success(f"Modelo carregado: `{uploaded_model_file.name}`", icon="✅")
        else:
            st.sidebar.error(f"Erro ao carregar: {err}")

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Base de Dados Tributária")
data_source_mode = st.sidebar.radio(
    "Base de dados ativa:", 
    ["Padrão SEFIN (Palmas-TO Tratada)", "Fazer Upload de CSV/Excel"],
    label_visibility="collapsed"
)

df_raw = None
if data_source_mode == "Padrão SEFIN (Palmas-TO Tratada)":
    df_raw = load_data()
else:
    uploaded_data_file = st.sidebar.file_uploader("Envie arquivo CSV ou Excel:", type=["csv", "xlsx"])
    if uploaded_data_file is not None:
        try:
            if uploaded_data_file.name.endswith(".csv"):
                df_raw = pd.read_csv(uploaded_data_file)
            else:
                df_raw = pd.read_excel(uploaded_data_file)
            st.sidebar.success(f"Base carregada: {len(df_raw)} registros", icon="📊")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler arquivo: {e}")
            df_raw = load_data()
    else:
        df_raw = load_data()

# Garantia de integridade das colunas
if "valor_total_divida" not in df_raw.columns and "valor_principal" in df_raw.columns:
    df_raw["valor_total_divida"] = df_raw["valor_principal"] + df_raw.get("juros_multas", 0)

# Integração do Pipeline de Inferência e Scoring (Hyag - Sprint 4)
inference_meta = None
if active_model_name and active_model_name != "Nenhum modelo ativo":
    try:
        df_raw, inference_meta = run_pipeline_inference(df_raw, active_model_name)
    except Exception as e:
        st.sidebar.warning(f"Inferência automática em contingência: {e}")

# ======================================================================================
# FILTROS GLOBAIS DE PERFIL TRIBUTÁRIO (SIDEBAR)
# ======================================================================================
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtros Globais Fiscais")

# 1. Filtro de Tributos
todos_tributos = sorted(list(df_raw["tributo"].dropna().unique()))
filtro_tributos = st.sidebar.multiselect(
    "Espécie Tributária:",
    options=todos_tributos,
    default=todos_tributos
)

# 2. Filtro de Regiões de Palmas
todas_regioes = sorted(list(df_raw["regiao"].dropna().unique()))
filtro_regioes = st.sidebar.multiselect(
    "Região de Palmas-TO:",
    options=todas_regioes,
    default=todas_regioes
)

# 3. Filtro Tipo de Pessoa
filtro_pessoa = st.sidebar.selectbox(
    "Perfil do Contribuinte:",
    options=["Todos", "Pessoa Física (PF)", "Pessoa Jurídica (PJ)"]
)

# 4. Filtro Faixa de Valor (Slider Dinâmico)
min_val = float(df_raw["valor_total_divida"].min())
max_val = float(df_raw["valor_total_divida"].max())
filtro_valor = st.sidebar.slider(
    "Faixa de Valor da Dívida (R$):",
    min_value=round(min_val, 0),
    max_value=round(max_val, 0),
    value=(round(min_val, 0), round(max_val, 0)),
    step=500.0,
    format="R$ %.0f"
)

# 5. Filtro Tempo de Inscrição (meses)
if "tempo_inscricao_meses" in df_raw.columns:
    max_meses = int(df_raw["tempo_inscricao_meses"].max())
    filtro_meses = st.sidebar.slider(
        "Tempo em Dívida Ativa (meses):",
        min_value=1,
        max_value=max_meses,
        value=(1, max_meses)
    )
else:
    filtro_meses = (1, 120)

# 6. Filtro Situação da Execução Fiscal
filtro_execucao = st.sidebar.radio(
    "Execução Fiscal Ajuizada:",
    options=["Todos", "Somente Ajuizados", "Não Ajuizados"],
    horizontal=True
)

# Aplicação dos Filtros Globais
df_filtered = df_raw.copy()

if filtro_tributos:
    df_filtered = df_filtered[df_filtered["tributo"].isin(filtro_tributos)]

if filtro_regioes:
    df_filtered = df_filtered[df_filtered["regiao"].isin(filtro_regioes)]

if filtro_pessoa != "Todos":
    df_filtered = df_filtered[df_filtered["tipo_pessoa"] == filtro_pessoa]

df_filtered = df_filtered[
    (df_filtered["valor_total_divida"] >= filtro_valor[0]) &
    (df_filtered["valor_total_divida"] <= filtro_valor[1])
]

if "tempo_inscricao_meses" in df_filtered.columns:
    df_filtered = df_filtered[
        (df_filtered["tempo_inscricao_meses"] >= filtro_meses[0]) &
        (df_filtered["tempo_inscricao_meses"] <= filtro_meses[1])
    ]

if filtro_execucao == "Somente Ajuizados" and "execucao_ajuizada" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["execucao_ajuizada"] == "Sim"]
elif filtro_execucao == "Não Ajuizados" and "execucao_ajuizada" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["execucao_ajuizada"] == "Não"]

# Rodapé de Conformidade LGPD na Sidebar
st.sidebar.markdown(
    """
    <div class="lgpd-box">
        <strong>🔒 Conformidade Ética & LGPD</strong><br>
        Ambiente homologado com anonimização de dados pessoais e identificadores sintéticos 
        (Art. 13 da Lei 13.709/2018).
    </div>
    """,
    unsafe_allow_html=True
)


# ======================================================================================
# 4. CABEÇALHO PRINCIPAL E PAINEL DE KPIS EXECUTIVOS
# ======================================================================================

st.markdown(
    f"""
    <div class="sefin-header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
            <div>
                <h1>Secretaria Municipal de Finanças de Palmas — SEFIN</h1>
                <p>Painel Inteligente de Priorização e Scoring de Recuperabilidade da Dívida Ativa</p>
                <span class="badge-sprint">Sprint 4 • MVP Operacional de IA (UFT BIINAR)</span>
            </div>
            <div style="text-align: right; margin-top: 8px;">
                <span style="font-size: 0.85rem; color: #bae6fd;">Modelo Ativo no Backend:</span><br>
                <strong style="color: #ffffff; font-size: 0.95rem;">{active_model_name}</strong>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Cálculo dos Indicadores-Chave Globais
total_divida = df_filtered["valor_total_divida"].sum()
total_devedores = len(df_filtered)
ticket_medio = total_divida / total_devedores if total_devedores > 0 else 0.0

df_alta = df_filtered[df_filtered["faixa_recuperabilidade"] == "Alta"]
total_potencial_alta = df_alta["valor_total_divida"].sum()
score_medio = df_filtered["score_recuperabilidade"].mean() if total_devedores > 0 else 0.0

col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

with col_kpi1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Volume Total em Dívida</div>
            <div class="kpi-value">R$ {total_divida:,.2f}</div>
            <div class="kpi-sub" style="color: #0284c7;">Base Selecionada</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_kpi2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Potencial Imediato (Alta)</div>
            <div class="kpi-value" style="color: #15803d;">R$ {total_potencial_alta:,.2f}</div>
            <div class="kpi-sub">{len(df_alta)} contribuintes prioritários</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_kpi3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Devedores Filtrados</div>
            <div class="kpi-value">{total_devedores:,}</div>
            <div class="kpi-sub" style="color: #64748b;">De {len(df_raw):,} registros totais</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_kpi4:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Ticket Médio</div>
            <div class="kpi-value">R$ {ticket_medio:,.2f}</div>
            <div class="kpi-sub" style="color: #64748b;">Por certidão ativa</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_kpi5:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Score Médio da IA</div>
            <div class="kpi-value" style="color: #0369a1;">{score_medio:.1f} <span style="font-size: 1rem;">/ 100</span></div>
            <div class="kpi-sub" style="color: #0284c7;">Índice de Recuperabilidade</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)


# ======================================================================================
# ESTRUTURAÇÃO POR ABAS FUNCIONAIS (MÓDULOS 1, 2, 3 E GOVERNANÇA)
# ======================================================================================

tab_ranking, tab_mapa, tab_simulador, tab_governanca = st.tabs([
    "📋 Módulo 1: Ranking de Devedores",
    "🗺️ Módulo 2: Mapa de Calor de Inadimplência",
    "💰 Módulo 3: Projeção de Arrecadação",
    "🔬 Metodologia & Auditoria Algorítmica"
])


# ======================================================================================
# MÓDULO 1: RANKING DE DEVEDORES E PRIORIZAÇÃO DA COBRANÇA
# ======================================================================================

with tab_ranking:
    st.subheader("📋 Ranking Estratégico de Recuperabilidade da Dívida")
    st.caption("Ordenação inteligente baseada em inteligência preditiva para acionamento operacional imediato da fiscalização tributária.")

    # Filtros e controles rápidos do ranking
    c_filt1, c_filt2, c_filt3 = st.columns([2, 2, 2])
    
    with c_filt1:
        faixas_selecionadas = st.multiselect(
            "Filtrar por Faixa de Recuperabilidade:",
            options=["Alta", "Média", "Baixa"],
            default=["Alta", "Média", "Baixa"],
            help="Alta: Score >= 68 | Média: 42 a 67 | Baixa: < 42"
        )
    
    with c_filt2:
        search_query = st.text_input(
            "Pesquisar Contribuinte, CDA ou Documento:",
            placeholder="Digite parte do nome, CDA ou ID...",
            help="Busca dinâmica em tempo real"
        )

    with c_filt3:
        ordem_ranking = st.selectbox(
            "Critério de Ordenação:",
            options=[
                "Score de Recuperabilidade (Decrescente)",
                "Fila Priorizada Heap Máximo SEFIN (O(log n))",
                "Valor Total da Dívida (Decrescente)",
                "Menor Tempo em Dívida (Mais Recente)",
                "Maior Tempo em Dívida (Mais Antigo)"
            ]
        )

    # Filtragem interna do Ranking
    df_rank = df_filtered.copy()
    if faixas_selecionadas:
        df_rank = df_rank[df_rank["faixa_recuperabilidade"].isin(faixas_selecionadas)]

    if search_query:
        q = search_query.strip().lower()
        mask = (
            df_rank["contribuinte"].astype(str).str.lower().str.contains(q) |
            df_rank["id_devedor"].astype(str).str.lower().str.contains(q) |
            df_rank["numero_cda"].astype(str).str.lower().str.contains(q) |
            df_rank["documento_mascarado"].astype(str).str.lower().str.contains(q)
        )
        df_rank = df_rank[mask]

    # Ordenação
    if ordem_ranking == "Fila Priorizada Heap Máximo SEFIN (O(log n))":
        pipeline_heap = get_pipeline_inferencia_singleton()
        ranking_heap = pipeline_heap.priorizar_fila_cobranca(df_rank)
        map_ordem = {item["id_divida"]: item["posicao"] for item in ranking_heap}
        id_col = "id_devedor" if "id_devedor" in df_rank.columns else "numero_cda"
        df_rank["posicao_heap"] = df_rank[id_col].map(map_ordem)
        df_rank = df_rank.dropna(subset=["posicao_heap"]).sort_values(by="posicao_heap")
    elif ordem_ranking == "Score de Recuperabilidade (Decrescente)":
        df_rank = df_rank.sort_values(by="score_recuperabilidade", ascending=False)
    elif ordem_ranking == "Valor Total da Dívida (Decrescente)":
        df_rank = df_rank.sort_values(by="valor_total_divida", ascending=False)
    elif ordem_ranking == "Menor Tempo em Dívida (Mais Recente)":
        df_rank = df_rank.sort_values(by="tempo_inscricao_meses", ascending=True)
    else:
        df_rank = df_rank.sort_values(by="tempo_inscricao_meses", ascending=False)

    # Exibição do resumo do segmento
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Registros no Ranking", f"{len(df_rank):,}")
    col_c2.metric("Total Financeiro do Ranking", f"R$ {df_rank['valor_total_divida'].sum():,.2f}")
    col_c3.metric("Score Máximo", f"{df_rank['score_recuperabilidade'].max() if len(df_rank) > 0 else 0:.1f}")
    
    # Botão de exportação
    csv_buffer = io.StringIO()
    df_rank.to_csv(csv_buffer, index=False, encoding="utf-8")
    col_c4.download_button(
        label="📥 Exportar Lista de Cobrança (CSV)",
        data=csv_buffer.getvalue(),
        file_name="sefin_palmas_cobranca_prioritaria.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Configuração de Colunas do Dataframe Dinâmico
    cols_display = [
        "id_devedor", "contribuinte", "documento_mascarado", "numero_cda", "tributo",
        "regiao", "bairro_setor", "tempo_inscricao_meses", "valor_total_divida",
        "score_recuperabilidade", "faixa_recuperabilidade", "canal_recomendado"
    ]
    cols_display = [c for c in cols_display if c in df_rank.columns]

    st.dataframe(
        df_rank[cols_display],
        column_config={
            "id_devedor": st.column_config.TextColumn("ID Registro", width="small"),
            "contribuinte": st.column_config.TextColumn("Contribuinte (Anonimizado)", width="medium"),
            "documento_mascarado": st.column_config.TextColumn("CPF/CNPJ", width="small"),
            "numero_cda": st.column_config.TextColumn("Certidão CDA", width="small"),
            "tributo": st.column_config.TextColumn("Tributo", width="small"),
            "regiao": st.column_config.TextColumn("Região", width="medium"),
            "bairro_setor": st.column_config.TextColumn("Setor / Quadra", width="medium"),
            "tempo_inscricao_meses": st.column_config.NumberColumn("Tempo (Meses)", format="%d m"),
            "valor_total_divida": st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
            "score_recuperabilidade": st.column_config.ProgressColumn(
                "Score IA",
                help="Score de Recuperabilidade calculado pelo modelo (0 a 100)",
                format="%.1f",
                min_value=0,
                max_value=100
            ),
            "faixa_recuperabilidade": st.column_config.TextColumn("Faixa de Risco", width="small"),
            "canal_recomendado": st.column_config.TextColumn("Canal de Cobrança Sugerido", width="large")
        },
        use_container_width=True,
        height=450,
        hide_index=True
    )

    # RAIO-X DETALHADO DO DEVEDOR SELECIONADO
    st.markdown("---")
    st.subheader("🔍 Raio-X Detalhado do Contribuinte Selecionado")
    
    if len(df_rank) > 0:
        lista_devedores = df_rank["id_devedor"].tolist()
        devedor_selecionado_id = st.selectbox(
            "Selecione um contribuinte do ranking para auditoria detalhada:",
            options=lista_devedores,
            format_func=lambda x: f"{x} - {df_rank[df_rank['id_devedor']==x]['contribuinte'].values[0]} (R$ {df_rank[df_rank['id_devedor']==x]['valor_total_divida'].values[0]:,.2f})"
        )

        row_dev = df_rank[df_rank["id_devedor"] == devedor_selecionado_id].iloc[0]

        cx1, cx2, cx3 = st.columns([1.2, 1.2, 1.6])
        
        with cx1:
            st.markdown(f"**Identificação:** `{row_dev['id_devedor']}`")
            st.markdown(f"**Nome:** {row_dev['contribuinte']}")
            st.markdown(f"**Documento:** `{row_dev['documento_mascarado']}`")
            st.markdown(f"**Tipo:** {row_dev.get('tipo_pessoa', 'N/A')}")
            st.markdown(f"**Localização:** {row_dev.get('bairro_setor', 'N/A')} ({row_dev.get('regiao', 'N/A')})")

        with cx2:
            st.markdown(f"**CDA Inscrição:** `{row_dev.get('numero_cda', 'N/A')}`")
            st.markdown(f"**Tributo:** {row_dev.get('tributo', 'N/A')}")
            st.markdown(f"**Exercício Fiscal:** {row_dev.get('ano_inscricao', 'N/A')} ({row_dev.get('tempo_inscricao_meses', 'N/A')} meses em atraso)")
            st.markdown(f"**Valor Principal:** R$ {row_dev.get('valor_principal', 0):,.2f}")
            st.markdown(f"**Juros e Multas:** R$ {row_dev.get('juros_multas', 0):,.2f}")
            st.markdown(f"**Total Consolidado:** :red[**R$ {row_dev['valor_total_divida']:,.2f}**]")

        with cx3:
            faixa = row_dev["faixa_recuperabilidade"]
            badge_class = "badge-alta" if faixa == "Alta" else ("badge-media" if faixa == "Média" else "badge-baixa")
            
            st.markdown(f"### Score: **{row_dev['score_recuperabilidade']:.1f} / 100** <span class='{badge_class}'>{faixa} Recuperabilidade</span>", unsafe_allow_html=True)
            st.progress(row_dev["score_recuperabilidade"] / 100.0)
            
            st.markdown(f"**Canal de Atuação Recomendado:**")
            st.info(f"👉 **{row_dev.get('canal_recomendado', 'Cobrança Administrativa')}**")
            
            st.markdown(f"- Bens penhoráveis identificados: **{row_dev.get('possui_bens', 'Não informado')}**")
            st.markdown(f"- Cadastro de contato atualizado: **{row_dev.get('contato_atualizado', 'Sim')}**")
            st.markdown(f"- Ajuizamento de execução fiscal: **{row_dev.get('execucao_ajuizada', 'Não')}**")

            # Interpretabilidade Local: Decomposição de Fatores (Hyag - Sprint 4)
            try:
                scoring_eng = get_pipeline_inferencia_singleton().scoring
                calc_exp = scoring_eng.calcular_score_individual(
                    probabilidade_recuperacao=float(row_dev.get("probabilidade_recuperacao", row_dev["score_recuperabilidade"]/100.0)),
                    tempo_inscricao_meses=float(row_dev.get("tempo_inscricao_meses", 24)),
                    valor_total_divida=float(row_dev["valor_total_divida"]),
                    possui_bens=str(row_dev.get("possui_bens", "Não")),
                    contato_atualizado=str(row_dev.get("contato_atualizado", "Sim")),
                    historico_parcelamentos=int(row_dev.get("historico_parcelamentos", 0)),
                    execucao_ajuizada=str(row_dev.get("execucao_ajuizada", "Não")),
                    faixa_renda=str(row_dev.get("faixa_renda", "2 a 5 SM")),
                    isencao_iptu_social=bool(row_dev.get("isencao_iptu_social", False))
                )
                df_fat = pd.DataFrame([
                    {"Fator": "Modelo IA (50%)", "Pontos": calc_exp.fatores_contribuicao.get("contribuicao_modelo_ia", 0)},
                    {"Fator": "Antiguidade", "Pontos": calc_exp.fatores_contribuicao.get("contribuicao_antiguidade", 0)},
                    {"Fator": "Valor Dívida", "Pontos": calc_exp.fatores_contribuicao.get("contribuicao_valor_divida", 0)},
                    {"Fator": "Garantias/Contato", "Pontos": calc_exp.fatores_contribuicao.get("contribuicao_garantias_contato", 0)},
                    {"Fator": "Renda Setorial", "Pontos": calc_exp.fatores_contribuicao.get("contribuicao_capacidade_renda", 0)},
                ])
                fig_fat = px.bar(
                    df_fat, x="Pontos", y="Fator", orientation="h",
                    title="<b>Interpretabilidade: Contribuição dos Fatores</b>",
                    color="Pontos", color_continuous_scale="Blues"
                )
                fig_fat.update_layout(height=180, margin=dict(l=10, r=10, t=25, b=10), showlegend=False)
                st.plotly_chart(fig_fat, use_container_width=True)
            except Exception:
                pass
    else:
        st.info("Nenhum devedor encontrado com os critérios de filtro selecionados.")

    # SIMULADOR INDIVIDUAL DE CONTRIBUINTE / DÍVIDA ATIVA (INTERPRETABILIDADE EM TEMPO REAL)
    st.markdown("---")
    with st.expander("🧪 Simulador Individual de Contribuinte / Dívida Ativa (Interpretabilidade em Tempo Real)", expanded=False):
        st.caption("Simule o cálculo de score e a recomendação operacional para um contribuinte específico preenchendo os atributos fiscais:")
        sim_col1, sim_col2, sim_col3 = st.columns(3)
        with sim_col1:
            sim_tributo = st.selectbox("Tributo:", ["IPTU", "ISSQN", "ITBI", "Taxas de Licenciamento"], key="sim_trib")
            sim_tempo = st.slider("Idade da Dívida (Meses em Atraso):", 1, 96, 18, key="sim_tmp")
            sim_renda = st.selectbox("Faixa de Renda:", ["Até 2 SM", "2 a 5 SM", "5 a 10 SM", "Acima de 10 SM"], index=1, key="sim_rnd")
        with sim_col2:
            sim_valor = st.number_input("Valor Total da Dívida (R$):", min_value=100.0, max_value=500000.0, value=4800.0, step=500.0, key="sim_vlr")
            sim_bens = st.radio("Possui Bens Penhoráveis?", ["Sim", "Não"], horizontal=True, key="sim_bns")
            sim_contato = st.radio("Contato Cadastral Atualizado?", ["Sim", "Não"], horizontal=True, key="sim_cnt")
        with sim_col3:
            sim_parc = st.slider("Histórico de Parcelamentos Prévios:", 0, 5, 1, key="sim_prc")
            sim_ajz = st.radio("Execução Fiscal Já Ajuizada?", ["Não", "Sim"], horizontal=True, key="sim_ajz")
            sim_social = st.checkbox("Beneficiário do IPTU Social (Vulnerável)", value=False, key="sim_soc")

        if st.button("🚀 Calcular Score com Explicabilidade", type="primary", use_container_width=True):
            pipeline_ind = get_pipeline_inferencia_singleton()
            df_sim_ind = pd.DataFrame([{
                "tributo": sim_tributo,
                "tipo_pessoa": "Pessoa Física (PF)",
                "tempo_inscricao_meses": sim_tempo,
                "valor_principal": sim_valor * 0.8,
                "juros_multas": sim_valor * 0.2,
                "valor_total_divida": sim_valor,
                "quantidade_debitos": 1,
                "historico_parcelamentos": sim_parc,
                "execucao_ajuizada": sim_ajz,
                "possui_bens": sim_bens,
                "contato_atualizado": sim_contato,
                "faixa_renda": sim_renda,
                "regiao": "Plano Diretor Sul",
                "isencao_iptu_social": sim_social
            }])
            df_out_sim, _ = pipeline_ind.executar_inferencia(df_sim_ind, active_model_name)
            res_row = df_out_sim.iloc[0]

            st.divider()
            r_c1, r_c2, r_c3, r_c4 = st.columns(4)
            r_c1.metric("Score de Recuperabilidade", f"{res_row['score_recuperabilidade']:.1f} / 100")
            r_c2.metric("Faixa de Risco", res_row["faixa_recuperabilidade"])
            r_c3.metric("Prob. de Recuperação P(recup)", f"{res_row['probabilidade_recuperacao']*100:.1f}%")
            r_c4.metric("Prob. Inadimplência P(inad)", f"{res_row['probabilidade_inadimplencia']*100:.1f}%")

            st.info(f"👉 **Ação Operacional Recomendada SEFIN:** {res_row['canal_recomendado']}")


# ======================================================================================
# MÓDULO 2: MAPA DE CALOR DE INADIMPLÊNCIA (VISUALIZAÇÃO ESPACIAL DE PALMAS-TO)
# ======================================================================================

with tab_mapa:
    st.subheader("🗺️ Mapa de Concentração e Calor da Inadimplência Tributária")
    st.caption("Distribuição geoespacial das dívidas ativas pelas quadras e regiões administrativas de Palmas-TO.")

    c_map_ctrl1, c_map_ctrl2, c_map_ctrl3 = st.columns([2, 2, 2])
    
    with c_map_ctrl1:
        tipo_camada = st.selectbox(
            "Modo de Visualização Geoespacial:",
            options=["Mapa de Calor (Heatmap Density)", "Agrupamento Hexagonal 3D (HexagonLayer)", "Dispersão Pontual com Score (Scatterplot)"]
        )
    
    with c_map_ctrl2:
        metrica_peso = st.selectbox(
            "Ponderação do Mapa:",
            options=["Volume Financeiro da Dívida (R$)", "Densidade de Contribuintes Devedores"]
        )

    with c_map_ctrl3:
        faixa_mapa = st.multiselect(
            "Filtrar Faixas no Mapa:",
            options=["Alta", "Média", "Baixa"],
            default=["Alta", "Média", "Baixa"]
        )

    # Filtrar dados para o mapa
    df_geo = df_filtered.dropna(subset=["latitude", "longitude"]).copy()
    if faixa_mapa:
        df_geo = df_geo[df_geo["faixa_recuperabilidade"].isin(faixa_mapa)]

    if len(df_geo) > 0:
        # Ponderação do peso para visualização
        if metrica_peso == "Volume Financeiro da Dívida (R$)":
            df_geo["map_weight"] = df_geo["valor_total_divida"] / df_geo["valor_total_divida"].max()
        else:
            df_geo["map_weight"] = 1.0

        # Centro de Palmas-TO (Praça dos Girassóis e Plano Diretor)
        center_lat = float(df_geo["latitude"].median())
        center_lon = float(df_geo["longitude"].median())

        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=11.2,
            pitch=45 if "Hexagonal" in tipo_camada else 0,
            bearing=0
        )

        layers = []

        if "Heatmap" in tipo_camada:
            heat_layer = pdk.Layer(
                "HeatmapLayer",
                data=df_geo,
                get_position=["longitude", "latitude"],
                get_weight="map_weight",
                radius_pixels=40,
                intensity=1.5,
                threshold=0.08
            )
            layers.append(heat_layer)

        elif "Hexagonal" in tipo_camada:
            hex_layer = pdk.Layer(
                "HexagonLayer",
                data=df_geo,
                get_position=["longitude", "latitude"],
                radius=350,
                elevation_scale=50 if metrica_peso.startswith("Volume") else 25,
                elevation_range=[0, 1500],
                extruded=True,
                coverage=0.88,
                get_fill_color=[240, 100, 0, 180]
            )
            layers.append(hex_layer)

        else: # Scatterplot
            # Atribuição de cores RGB com base na faixa
            def get_rgb(faixa):
                if faixa == "Alta": return [22, 163, 74, 200]
                if faixa == "Média": return [217, 119, 6, 200]
                return [220, 38, 38, 200]

            df_geo["color_rgb"] = df_geo["faixa_recuperabilidade"].apply(get_rgb)

            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_geo,
                get_position=["longitude", "latitude"],
                get_color="color_rgb",
                get_radius=120,
                pickable=True
            )
            layers.append(scatter_layer)

        deck = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={"text": "Contribuinte: {contribuinte}\nBairro: {bairro_setor}\nValor: R$ {valor_total_divida}\nScore: {score_recuperabilidade}"} if "Scatterplot" in tipo_camada else True,
            map_style="light"
        )

        st.pydeck_chart(deck, use_container_width=True)

        # Gráficos Analíticos Territoriais Complementares
        st.markdown("#### 📊 Diagnóstico Territorial da Inadimplência em Palmas-TO")
        col_geo1, col_geo2 = st.columns(2)

        with col_geo1:
            # Volume de Dívida por Região Administrativa
            reg_summary = df_geo.groupby("regiao")["valor_total_divida"].sum().reset_index()
            reg_summary = reg_summary.sort_values(by="valor_total_divida", ascending=True)

            fig_reg = px.bar(
                reg_summary,
                x="valor_total_divida",
                y="regiao",
                orientation="h",
                title="<b>Montante Total Devido por Macro-Região de Palmas</b>",
                labels={"valor_total_divida": "Total em Dívida (R$)", "regiao": "Região"},
                color="valor_total_divida",
                color_continuous_scale="Blues"
            )
            fig_reg.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20), height=320)
            st.plotly_chart(fig_reg, use_container_width=True)

        with col_geo2:
            # Top 7 Bairros / Setores com Maior Inadimplência
            top_bairros = df_geo.groupby("bairro_setor")["valor_total_divida"].sum().reset_index()
            top_bairros = top_bairros.sort_values(by="valor_total_divida", ascending=False).head(7)

            fig_bairros = px.bar(
                top_bairros,
                x="bairro_setor",
                y="valor_total_divida",
                title="<b>Top 7 Bairros / Setores com Maior Passivo Tributário</b>",
                labels={"valor_total_divida": "Total Devido (R$)", "bairro_setor": "Setor/Bairro"},
                color="valor_total_divida",
                color_continuous_scale="Reds"
            )
            fig_bairros.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20), height=320)
            st.plotly_chart(fig_bairros, use_container_width=True)
            
    else:
        st.warning("Nenhum dado georreferenciado disponível com os filtros aplicados.")


# ======================================================================================
# MÓDULO 3: PROJEÇÃO DE ARRECADAÇÃO POTENCIAL (SIMULADOR FINANCEIRO INTERATIVO)
# ======================================================================================

with tab_simulador:
    st.subheader("💰 Simulador Financeiro de Arrecadação e Recuperação de Ativos")
    st.caption("Projeção dinâmica do montante financeiro recuperável a partir de estratégias operacionais focalizadas nos grupos de maior score.")

    st.markdown(
        """
        O simulador estima a receita recuperável considerando as probabilidades da IA e o esforço de cobrança 
        por faixa de risco, incluindo o impacto de políticas públicas fiscais (como o **Programa REFIS Palmas**).
        """
    )

    col_sim_ctrl1, col_sim_ctrl2 = st.columns(2)

    with col_sim_ctrl1:
        st.markdown("#### 🎯 Parâmetros de Efetividade Operacional por Faixa")
        taxa_alta = st.slider(
            "Efetividade de Cobrança - Faixa ALTA (%):",
            min_value=10, max_value=95, value=75, step=5,
            help="Taxa esperada de conversão com canais digitais amigáveis (WhatsApp, Pix, Notificação DDA)"
        ) / 100.0

        taxa_media = st.slider(
            "Efetividade de Cobrança - Faixa MÉDIA (%):",
            min_value=5, max_value=70, value=35, step=5,
            help="Taxa esperada de conversão com protesto notarial e cobrança administrativa intensiva"
        ) / 100.0

        taxa_baixa = st.slider(
            "Efetividade de Cobrança - Faixa BAIXA (%):",
            min_value=1, max_value=30, value=8, step=1,
            help="Taxa esperada com execução fiscal, bloqueio judicial e leilões de bens"
        ) / 100.0

    with col_sim_ctrl2:
        st.markdown("#### 🏛️ Parâmetros da Política Fiscal (REFIS Palmas)")
        desconto_juros_multas = st.slider(
            "Desconto em Juros e Multas para Liquidação (%):",
            min_value=0, max_value=90, value=40, step=5,
            help="Percentual concedido na campanha de regularização municipal sobre os encargos moratórios"
        ) / 100.0

        adesao_refis_faixa_alta = st.slider(
            "Adesão Esperada à Campanha de Regularização (%):",
            min_value=10, max_value=100, value=65, step=5,
            help="Percentual de devedores que aceitam negociar com o benefício de desconto nos encargos"
        ) / 100.0

    # CÁLCULOS DINÂMICOS DO SIMULADOR
    # Separação por faixas
    df_sim_alta = df_filtered[df_filtered["faixa_recuperabilidade"] == "Alta"]
    df_sim_media = df_filtered[df_filtered["faixa_recuperabilidade"] == "Média"]
    df_sim_baixa = df_filtered[df_filtered["faixa_recuperabilidade"] == "Baixa"]

    # Valores brutos
    v_alta_total = df_sim_alta["valor_total_divida"].sum()
    v_alta_juros = df_sim_alta["juros_multas"].sum() if "juros_multas" in df_sim_alta.columns else v_alta_total * 0.25

    v_media_total = df_sim_media["valor_total_divida"].sum()
    v_media_juros = df_sim_media["juros_multas"].sum() if "juros_multas" in df_sim_media.columns else v_media_total * 0.30

    v_baixa_total = df_sim_baixa["valor_total_divida"].sum()
    v_baixa_juros = df_sim_baixa["juros_multas"].sum() if "juros_multas" in df_sim_baixa.columns else v_baixa_total * 0.35

    # Aplicação dos descontos de juros/multas
    v_alta_liquido = v_alta_total - (v_alta_juros * desconto_juros_multas * adesao_refis_faixa_alta)
    v_media_liquido = v_media_total - (v_media_juros * desconto_juros_multas * (adesao_refis_faixa_alta * 0.7))
    v_baixa_liquido = v_baixa_total - (v_baixa_juros * desconto_juros_multas * (adesao_refis_faixa_alta * 0.4))

    # Projeção Realista
    recup_alta_realista = v_alta_liquido * taxa_alta
    recup_media_realista = v_media_liquido * taxa_media
    recup_baixa_realista = v_baixa_liquido * taxa_baixa
    total_recup_realista = recup_alta_realista + recup_media_realista + recup_baixa_realista

    # Cenário Conservador (-20% de eficiência)
    total_recup_conservador = total_recup_realista * 0.80

    # Cenário Otimista (+25% de eficiência)
    total_recup_otimista = min(total_recup_realista * 1.25, total_divida)

    # Renúncia Fiscal estimada concedida no REFIS
    renuncia_fiscal = (
        (v_alta_juros * desconto_juros_multas * adesao_refis_faixa_alta) +
        (v_media_juros * desconto_juros_multas * (adesao_refis_faixa_alta * 0.7)) +
        (v_baixa_juros * desconto_juros_multas * (adesao_refis_faixa_alta * 0.4))
    )

    st.markdown("---")
    st.markdown("### 📈 Projeção do Montante Recuperável aos Cofres Municipais")

    col_sim_res1, col_sim_res2, col_sim_res3, col_sim_res4 = st.columns(4)
    
    with col_sim_res1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-top: 4px solid #64748b;">
                <div class="kpi-label">Cenário Conservador</div>
                <div class="kpi-value" style="color: #475569;">R$ {total_recup_conservador:,.2f}</div>
                <div class="kpi-sub" style="color: #64748b;">-20% de aderência</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_sim_res2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-top: 4px solid #0284c7;">
                <div class="kpi-label">Cenário Realista (Alvo)</div>
                <div class="kpi-value" style="color: #0369a1;">R$ {total_recup_realista:,.2f}</div>
                <div class="kpi-sub" style="color: #0284c7;">Meta operacional Sefin</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_sim_res3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-top: 4px solid #16a34a;">
                <div class="kpi-label">Cenário Otimista</div>
                <div class="kpi-value" style="color: #15803d;">R$ {total_recup_otimista:,.2f}</div>
                <div class="kpi-sub" style="color: #15803d;">+25% com força-tarefa</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_sim_res4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-top: 4px solid #f59e0b;">
                <div class="kpi-label">Renúncia Est. (Desconto)</div>
                <div class="kpi-value" style="color: #b45309;">R$ {renuncia_fiscal:,.2f}</div>
                <div class="kpi-sub" style="color: #b45309;">Adesão REFIS Palmas</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráficos Financeiros de Visualização
    col_gf1, col_gf2 = st.columns(2)

    with col_gf1:
        # Gráfico de Barras: Comparativo de Potencial por Faixa
        df_faixas_comp = pd.DataFrame({
            "Faixa de Risco": ["Alta Recuperabilidade", "Média Recuperabilidade", "Baixa Recuperabilidade"],
            "Dívida Total (R$)": [v_alta_total, v_media_total, v_baixa_total],
            "Projeção Recuperável (R$)": [recup_alta_realista, recup_media_realista, recup_baixa_realista]
        })

        fig_bar_comp = go.Figure(data=[
            go.Bar(name='Estoque da Dívida (R$)', x=df_faixas_comp["Faixa de Risco"], y=df_faixas_comp["Dívida Total (R$)"], marker_color='#cbd5e1'),
            go.Bar(name='Recuperável Realista (R$)', x=df_faixas_comp["Faixa de Risco"], y=df_faixas_comp["Projeção Recuperável (R$)"], marker_color='#0284c7')
        ])
        fig_bar_comp.update_layout(
            title="<b>Estoque em Dívida Ativa vs. Potencial de Recuperação por Faixa</b>",
            barmode='group',
            margin=dict(l=20, r=20, t=40, b=20),
            height=340,
            yaxis_tickformat="R$ "
        )
        st.plotly_chart(fig_bar_comp, use_container_width=True)

    with col_gf2:
        # Curva de Sensibilidade: Arrecadação vs Desconto REFIS
        descontos_teste = np.linspace(0.0, 0.9, 10)
        arrec_sensibilidade = []
        for d in descontos_teste:
            val = (
                (v_alta_total - (v_alta_juros * d * adesao_refis_faixa_alta)) * taxa_alta +
                (v_media_total - (v_media_juros * d * (adesao_refis_faixa_alta * 0.7))) * taxa_media +
                (v_baixa_total - (v_baixa_juros * d * (adesao_refis_faixa_alta * 0.4))) * taxa_baixa
            )
            arrec_sensibilidade.append(val)

        fig_sens = px.line(
            x=descontos_teste * 100,
            y=arrec_sensibilidade,
            markers=True,
            title="<b>Curva de Sensibilidade: Arrecadação Líquida x Desconto REFIS</b>",
            labels={"x": "% Desconto em Encargos (REFIS)", "y": "Arrecadação Projetada (R$)"}
        )
        fig_sens.update_traces(line_color="#0d9488", line_width=3)
        fig_sens.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=340)
        st.plotly_chart(fig_sens, use_container_width=True)


# ======================================================================================
# MÓDULO 4: METODOLOGIA, AUDITORIA ALGORÍTMICA & CONFORMIDADE LGPD (SPRINT 4)
# ======================================================================================

with tab_governanca:
    st.subheader("🔬 Metodologia de IA, Auditoria Algorítmica e Conformidade Ética")
    st.caption("Documentação técnica e científica referente à Sprint 4 do Projeto Integrador Eixo II (BIINAR / UFT - SEFIN Palmas).")

    st.markdown(
        """
        Em conformidade com as diretrizes do Projeto Integrador, o treinamento dos modelos preditivos e a 
        validação das hipóteses de cobrança obedeceram a rigorosos critérios técnicos para prevenir vícios estatísticos 
        e garantir total segurança jurídica e conformidade à LGPD.
        """
    )

    # 1. Metodologia Anti-Leakage (Split Temporal)
    st.markdown("#### ⏳ 1. Metodologia de Partição Temporal (*Anti-Data Leakage*)")
    st.info(
        """
        **Partição Temporal Rigorosa (Entregável E1):**  
        A divisão dos conjuntos de treinamento, validação e teste não utilizou divisão aleatória (*random split*), 
        pois isso causaria vazamento temporal de dados futuros (*data leakage*). Em vez disso, adotou-se a ordenação 
        cronológica dos exercícios fiscais:
        - **Treinamento (Exercícios até 2022):** Ajuste de pesos e parâmetros dos algoritmos.
        - **Validação Temporal (Exercício 2023):** Tunagem de hiperparâmetros e seleção do modelo campeão.
        - **Teste Cego Temporal (Exercício 2024):** Avaliação de generalização fora da amostra no ambiente operacional real.
        """
    )

    # 2. Comparativo de Modelos (Baselines vs Random Forest / XGBoost)
    st.markdown("#### 📊 2. Tabela Comparativa de Desempenho no Teste Temporal (E2 & E3)")
    metrics_data = load_metrics_audit()
    
    if metrics_data:
        comp_rows = []
        for model_name, m in metrics_data.items():
            comp_rows.append({
                "Modelo": model_name,
                "Acurácia": f"{m.get('acuracia', 0)*100:.2f}%",
                "Precisão": f"{m.get('precisao', 0)*100:.2f}%",
                "Recall (Sensibilidade)": f"{m.get('recall', 0)*100:.2f}%",
                "F1-Score": f"{m.get('f1_score', 0)*100:.2f}%",
                "ROC-AUC": f"{m.get('roc_auc', 0):.4f}"
            })
        st.table(pd.DataFrame(comp_rows))

        # Matriz de Confusão Interativa
        st.markdown("#### 🎯 Matriz de Confusão no Conjunto de Teste")
        cm_cols = st.columns(len(metrics_data))
        for idx, (model_name, m) in enumerate(metrics_data.items()):
            if "matriz_confusao" in m:
                cm = np.array(m["matriz_confusao"])
                fig_cm = px.imshow(
                    cm,
                    text_auto=True,
                    color_continuous_scale="Blues",
                    labels=dict(x="Predito pela IA", y="Real Histórico", color="Ocorrências"),
                    x=["Não Recuperado", "Recuperado"],
                    y=["Não Recuperado", "Recuperado"],
                    title=f"<b>{model_name}</b>"
                )
                fig_cm.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
                with cm_cols[idx]:
                    st.plotly_chart(fig_cm, use_container_width=True)
    else:
        st.warning("Métricas de auditoria não encontradas em `models/model_metrics.json`. Execute `models/train_models.py` para gerar.")

    # 2.1 Metodologia do Scoring de Recuperabilidade & Pipeline (Eixos 1 e 2 - Hyag)
    st.markdown("#### 🎯 2.1 Metodologia do Score de Recuperabilidade & Pipeline de Inferência (Eixos 1 e 2)")
    st.markdown(
        r"""
        O sistema adota um modelo complementar de **Scoring de Recuperabilidade** matematicamente formulado 
        para converter predições estatísticas e atributos materiais da dívida ativa em faixas operacionais 
        compreensíveis para os analistas tributários da SEFIN Palmas:

        - **Diferenciação Semântica Rigorosa:**
          - $P(\text{inadimplência})$: Probabilidade de persistência no não pagamento do tributo.
          - $P(\text{recuperação}) = 1 - P(\text{inadimplência})$: Propensão estatística de quitação estimada pelo comitê de árvores/modelos preditivos.
          - **Score de Recuperabilidade ($S \in [0, 100]$):** Indicador composto ponderando propensão estatística ($50\%$) e atributos materiais ($50\%$) — antiguidade (Art. 174 CTN), faixa de valor, garantias/bens penhoráveis e renda média setorial (Censo IBGE).
        - **Faixas Operacionais de Priorização Fazendária:**
          - **Alta Recuperabilidade ($S \ge 68.0$):** Canal digital de baixo custo (WhatsApp/E-mail/DDA); alta resposta em até 90 dias.
          - **Média Recuperabilidade ($42.0 \le S < 68.0$):** Notificação postal, protesto cartorário e incentivo de regularização (REFIS Palmas).
          - **Baixa Recuperabilidade ($S < 42.0$):** Débitos antigos, litigiosos ou sem patrimônio localizado; triagem jurídica e averiguação patrimonial.
        - **Proteção Social Obrigatória (IPTU Social):** Contribuintes em vulnerabilidade socioeconômica extrema recebem bloqueio automático de cobrança coercitiva e encaminhamento social.
        """
    )

    # 3. Conformidade LGPD e Auditoria de Equidade (Fairness)
    st.markdown("#### 🔒 3. Conformidade Ética, LGPD e Minimização de Dados")
    st.markdown(
        """
        - **Anonimização & Minimização:** Nenhum dado pessoal não anonimizado de munícipes é armazenado ou trafegado na camada web.
        - **Camada Sintética Homologada:** A base individual utilizada para testes e homologação possui natureza estritamente sintética e calibrada com as estatísticas agregadas de Palmas-TO.
        - **Preparação para a Sprint 5 (Auditoria de Fairness & RIA):** As métricas do modelo já estão particionadas por subgrupos sociodemográficos e territoriais (renda e setor geográfico) para garantir a elaboração do Relatório de Impacto Algorítmico (RIA) sem viés discriminatório contra regiões periféricas.
        """
    )

    # 4. Rastreabilidade da Equipe
    st.markdown("---")
    st.caption(
        """
        **Equipe Executora (Sprint 4):** Hyag, Ludmylla, Maiara, Sofia e Vitória  
        **Coordenação do Módulo 6 (Introdução à IA):** Prof. Dr. David Nadler Prata  
        Universidade Federal do Tocantins (UFT) • Bacharelado Interdisciplinar em Inteligência Artificial (BIINAR)
        """
    )


# ======================================================================================
# RODAPÉ INFORMATIVO
# ======================================================================================

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.82rem; padding: 10px 0;">
        SEFIN Palmas — Secretaria Municipal de Finanças de Palmas (TO) & UFT BIINAR &copy; 2026. Todos os direitos reservados.
    </div>
    """,
    unsafe_allow_html=True
)
