import streamlit as st
import pandas as pd
import sys
import os
import time
import plotly.express as px
from supabase import create_client

# --- LÓGICA DE CAMINHO ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    try:
        from config import SUPABASE_URL, SUPABASE_KEY
    except ImportError:
        st.error("Erro: Credenciais de banco de dados não configuradas.")
        st.stop()

# --- CONFIGURAÇÕES DE PÁGINA ---
st.set_page_config(
    page_title="Ellca Tecnologia - Monitor de Impressões",
    page_icon="📊",
    layout="wide"
)

# --- ESTILIZAÇÃO CUSTOMIZADA EVOLUÍDA (Filtros Blindados e Efeito Hover Neon) ---
st.markdown("""
    <style>
        /* Ajustes de tela e reset de espaços no topo */
        .stApp {
            background-color: #F3F4F6 !important;
        }
        
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 2rem !important;
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            margin-top: 0rem !important;
        }
        
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            z-index: -1 !important;
            display: none !important;
        }
        
        /* Header Superior - Azul Marinho Corporativo */
        .corporate-header {
            background-color: #002040;
            padding: 18px 30px;
            margin-left: -3rem;
            margin-right: -3rem;
            margin-top: 0rem !important;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #0078D4;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }
        .header-title-box {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-main-title {
            color: #FFFFFF;
            font-size: 24px;
            font-weight: 700;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            margin: 0;
        }
        .header-subtitle {
            color: #38BDF8;
            font-size: 24px;
            font-weight: 300;
            margin: 0;
        }
        
        /* Estilização do Container Nativo de Filtros */
        div[data-testid="stElementContainer"]:has(.filter-box) {
            margin-top: -5px !important;
        }
        .filter-box div[data-testid="stSubheader"] {
            display: none !important;
        }
        
        /* Input do Streamlit Customizado com Contorno Forte Azul Marinho */
        div[data-baseweb="select"], div[data-baseweb="input"], div[data-baseweb="calendar"] {
            border: 1.5px solid #002040 !important;
            border-radius: 6px !important;
            transition: all 0.2s ease-in-out !important;
            background-color: #FFFFFF !important;
        }
        
        /* Foco ativo com efeito Glow */
        div[data-baseweb="select"]:focus-within, div[data-baseweb="input"]:focus-within {
            border-color: #0078D4 !important;
            box-shadow: 0 0 0 3px rgba(0, 120, 212, 0.25) !important;
        }
        
        /* Forçar labels dos filtros em Azul Escuro Negrito */
        label p {
            color: #002040 !important;
            font-weight: 700 !important;
            font-size: 14px !important;
        }
        
        /* Cards de Métricas com Animação e Brilho Neon no Hover */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            padding: 20px 25px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        
        /* Efeito Hover Neon em Azul Escuro/Azul Principal */
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px) !important;
            border-color: #0078D4 !important;
            box-shadow: 0 0 20px rgba(0, 32, 64, 0.2), 
                        0 0 15px rgba(0, 120, 212, 0.45) !important;
        }
        
        div[data-testid="stMetric"] label {
            color: #4B5563 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #002040 !important;
            font-size: 28px !important;
            font-weight: 700 !important;
        }
        
        /* Títulos das Seções */
        .section-title {
            color: #002040;
            font-size: 15px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 18px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-left: 4px solid #0078D4;
            padding-left: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN PERSISTENTE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔐 Acesso Administrativo - Ellca")
    with st.form("login_form"):
        password = st.text_input("Digite a senha", type="password")
        submit = st.form_submit_button("Acessar Painel")
        if submit:
            if password == "ellca2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Senha incorreta")
    return False

if check_password():
    # CONEXÃO SUPABASE
    CLEAN_URL = SUPABASE_URL.split("/rest/v1/")[0]
    supabase = create_client(CLEAN_URL, SUPABASE_KEY)

    # --- 1. BUSCA DE METADADOS DOS DROPDOWNS (SEMPRE TRAZ TUDO) ---
    @st.cache_data(ttl=30)
    def fetch_filters_metadata():
        try:
            # Lista todas as filiais distintas no banco
            filiais_res = supabase.table("print_logs").select("filial").execute()
            df_f = pd.DataFrame(filiais_res.data)
            lista_filiais = sorted(df_f['filial'].dropna().unique().tolist()) if not df_f.empty else []

            # Lista todos os usuários distintos no banco
            users_res = supabase.table("print_logs").select("user_name").execute()
            df_u = pd.DataFrame(users_res.data)
            lista_users = sorted(df_u['user_name'].dropna().unique().tolist()) if not df_u.empty else []

            # Captura a data do primeiro log histórico do banco
            dates_res = supabase.table("print_logs").select("created_at").order("created_at", desc=False).limit(1).execute()
            if dates_res.data:
                data_minima = pd.to_datetime(dates_res.data[0]['created_at']).tz_convert('America/Sao_Paulo').date()
            else:
                data_minima = pd.Timestamp.now(tz='America/Sao_Paulo').date() - pd.Timedelta(days=7)

            return lista_filiais, lista_users, data_minima
        except Exception as e:
            st.error(f"Erro ao carregar metadados dos filtros: {e}")
            return [], [], pd.Timestamp.now(tz='America/Sao_Paulo').date() - pd.Timedelta(days=7)

    # --- 2. CONSULTA DINÂMICA FILTRADA DIRETO NO SUPABASE ---
    def fetch_filtered_data(p_inicio, p_fim, f_sel, u_sel):
        try:
            # Inicia a query base
            query = supabase.table("print_logs").select("*", count="exact")
            
            # Converte as datas locais para o formato de string ISO esperado pelo banco timestampz
            iso_inicio = f"{p_inicio}T00:00:00.000000+00:00"
            iso_fim = f"{p_fim}T23:59:59.999999+00:00"
            
            query = query.gte("created_at", iso_inicio).lte("created_at", iso_fim)
            
            # Aplica filtros condicionais direto na query do Supabase
            if f_sel != "Todas":
                query = query.eq("filial", f_sel)
            if u_sel != "Todos":
                query = query.eq("user_name", u_sel)
                
            # Ordena e limita o retorno de linhas
            res = query.order("created_at", desc=True).limit(1000).execute()
            
            total_linhas_filtradas = res.count if res.count is not None else 0
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                df['created_at'] = df['created_at'].dt.tz_convert('America/Sao_Paulo')
                df['Data'] = df['created_at'].dt.date
                df['Hora'] = df['created_at'].dt.hour
                df['created_at'] = df['created_at'].dt.tz_localize(None)
                
                if 'status' not in df.columns:
                    df['status'] = 'Documento enviado'
                df['status'] = df['status'].fillna('Documento enviado')
                
                mapa_status = {
                    'Documento enviado': 'Impressão Concluída',
                    'Documento pausado': 'Retido na Fila',
                    'Documento cancelado': 'Cancelado pelo Usuário',
                    'Erro de impressão': 'Falha Crítica',
                    'Fila congestionada': 'Spooler Sobrecarregado',
                    'Toner baixo': 'Toner Baixo',
                    'Offline': 'Dispositivo Offline'
                }
                df['status_pt'] = df['status'].map(mapa_status).fillna(df['status'])
                
            return df, total_linhas_filtradas
        except Exception as e:
            st.error(f"Erro na execução da consulta filtrada: {e}")
            return pd.DataFrame(), 0

    # Carrega as opções dos dropdowns de forma global
    lista_todas_filiais, lista_todos_usuarios, data_minima_banco = fetch_filters_metadata()
    hoje_local = pd.Timestamp.now(tz='America/Sao_Paulo').date()

    # --- HEADER CORPORATIVO SUPERIOR ---
    st.markdown("""
        <div class='corporate-header'>
