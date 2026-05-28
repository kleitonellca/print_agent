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

    # --- BUSCA DE DADOS ---
    @st.cache_data(ttl=15)  # Reduzido para 15s para dar mais agilidade no tempo real
    def fetch_analytics():
        try:
            # CORREÇÃO: Usando desc=True em vez de ascending=False
            res = supabase.table("print_logs").select("*").order("created_at", desc=True).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Tratamento explícito de conversão e fuso horário paulista
                df['created_at'] = pd.to_datetime(df['created_at'])
                if df['created_at'].dt.tz is None:
                    df['created_at'] = df['created_at'].dt.tz_localize('UTC')
                
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
            return df
        except Exception as e:
            st.error(f"Erro ao buscar dados: {e}")
            return pd.DataFrame()
            
    df_raw = fetch_analytics()

    if not df_raw.empty:
        # --- HEADER CORPORATIVO SUPERIOR ---
        st.markdown("""
            <div class='corporate-header'>
                <div class='header-title-box'>
                    <span class='header-main-title'>Ellca Tecnologia</span>
                    <span class='header-subtitle'>| Monitor de Impressões</span>
                </div>
                <div style='color: #9CA3AF; font-size: 12px; text-align: right; font-family: sans-serif; line-height: 1.4;'>
                    Admin: <b style='color: #FFFFFF;'>Kleiton Braga</b><br>
                    <span style='color: #38BDF8;'>Plataforma de Telemetria Ativa</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- FILTROS HORIZONTAIS ENVELOPADOS ---
        # Definindo datas locais dinâmicas para evitar congelamento de fuso
        hoje_local = pd.Timestamp.now(tz='America/Sao_Paulo').date()
        set_dias_atras = hoje_local - pd.Timedelta(days=7)

        with st.container(border=True):
            st.markdown('<div class="filter-box"></div>', unsafe_allow_html=True)
            f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 1.5, 2, 2, 1])
            
            with f_col1:
                d_inicio = st.date_input("De", value=set_dias_atras, format="DD/MM/YYYY")
            with f_col2:
                d_fim = st.date_input("Até", value=hoje_local, format="DD/MM/YYYY")
            with f_col3:
                filiais = ["Todas"] + sorted(df_raw['filial'].dropna().unique().tolist())
                filial_sel = st.selectbox("Filial", filiais)
            with f_col4:
                users = ["Todos"] + sorted(df_raw['user_name'].dropna().unique().tolist())
                user_sel = st.selectbox("Usuário", users)
            with f_col5:
                st.markdown("<label style='font-size:14px; font-weight:700; color:#002040;'>Configurações</label>", unsafe_allow_html=True)
                auto_refresh = st.checkbox("🔄 Auto-Refresh", value=True)

        # --- FILTRAGEM DOS DADOS ---
        mask = (df_raw['Data'] >= d_inicio) & (df_raw['Data'] <= d_fim)
        if filial_sel != "Todas":
            mask &= (df_raw['filial'] == filial_sel)
        if user_sel != "Todos":
            mask &= (df_raw['user_name'] == user_sel)
        
        df = df_raw.loc[mask].copy()

        if not df.empty:
            # --- SEÇÃO 1: METRICAS DE VOLUMETRIA ---
            jobs_validos = df[~df['status'].isin(['Documento cancelado', 'Erro de impressão'])]
            t_paginas = int(jobs_validos['pages'].sum()) if not jobs_validos.empty else 0
            t_jobs = len(df)
            media_pag = round(jobs_validos['pages'].mean(), 1) if not jobs_validos.empty else 0
            t_unidades = df['filial'].nunique()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Páginas (Sucesso)", f"{t_paginas:,}".replace(",", "."))
            m2.metric("Total Logs Capturados", f"{t_jobs:,}".replace(",", "."))
            m3.metric("Média Págs / Doc", media_pag)
            m4.metric("Unidades Ativas", t_unidades)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- SEÇÃO 2: ALERTA DO PARQUE ---
            st.markdown("<div class='section-title'>Alertas e Integridade do Parque</div>", unsafe_allow_html=True)
            col_t1, col_t2, col_t3 = st.columns(3)
            
            impressoras_offline = df[df['status'] == 'Offline']['printer_name'].nunique()
            toner_baixo = df[df['status'] == 'Toner baixo']['printer_name'].nunique()
            filas_travadas = df[df['status'] == 'Fila congestionada']['printer_name'].nunique()
            
            col_t1.metric("Impressoras Offline", impressoras_offline, 
                        delta="Atenção" if impressoras_offline > 0 else "OK", delta_color="inverse")
            col_t2.metric("Alertas de Toner Baixo", toner_baixo, 
                        delta="Substituir" if toner_baixo > 0 else "OK", delta_color="inverse")
            col_t3.metric("Filas Congestionadas", filas_travadas, 
                        delta="Spooler Retido" if filas_travadas > 0 else "OK", delta_color="inverse")

            st.markdown("<br>", unsafe_allow_html=True)

            # --- SEÇÃO 3: BLOCO DE GRÁFICOS INTERATIVOS ---
            st.markdown("<div class='section-title'>Análise Gráfica Macroeconômica</div>", unsafe_allow_html=True)
            col_a, col_b = st.columns([2, 1])

            with col_a:
                df_day = jobs_validos.groupby('Data')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame(columns=['Data', 'pages'])
                if not df_day.empty:
                    df_day['Data_Formato'] = df_day['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
                    fig_timeline = px.area(df_day, x='Data', y='pages', 
                                           title="<b>Histórico de Consumo Efetivo (Páginas)</b>",
                                           color_discrete_sequence=['#0078D4'])
                    
                    fig_timeline.update_traces(
                        hovertemplate="<b>📅 Data:</b> %{customdata[0]}<br><b>📄 Páginas:</b> %{y}<extra></extra>",
                        customdata=df_day[['Data_Formato']],
                        line=dict(width=3),
                        fillcolor='rgba(0, 120, 212, 0.12)'
                    )
                    fig_timeline.update_layout(
                        hovermode="x unified",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        title_font=dict(size=14, color='#002040', family="Arial"),
                        xaxis=dict(showgrid=True, gridcolor='#E5E7EB', title=""),
                        yaxis=dict(showgrid=True, gridcolor='#E5E7EB', title=""),
                        margin=dict(t=50, b=20, l=20, r=20)
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem dados volumétricos suficientes para gerar a linha temporal.")

            with col_b:
                df_status = df.groupby('status_pt').size().reset_index(name='Quantidade')
                if not df_status.empty:
                    color_map = {
                        'Impressão Concluída': '#0078D4',
                        'Retido na Fila': '#FFB900',
                        'Cancelado pelo Usuário': '#D83B01',
                        'Falha Crítica': '#E81123',
                        'Spooler Sobrecarregado': '#A741A5',
                        'Toner Baixo': '#F7630C',
                        'Dispositivo Offline': '#7A7A7A'
                    }
                    
                    fig_status = px.pie(df_status, values='Quantidade', names='status_pt', hole=0.60,
                                        color='status_pt', color_discrete_map=color_map)
                    
                    fig_status.update_traces(
                        textinfo='none',
                        hovertemplate="<b>📌 Status:</b> %{label}<br><b>📋 Ocorrências:</b> %{value}<br><b>📊 Porcentagem:</b> %{percent}<extra></extra>"
                    )
                    
                    fig_status.update_layout(
                        title={"text": "<b>Ciclo de Vida / Erros</b>", "y": 0.95, "x": 0.0, "xanchor": 'left', "yanchor": 'top'},
                        title_font=dict(size=14, color='#002040', family="Arial"),
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        margin=dict(t=80, b=40, l=10, r=10), 
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=-0.25, 
                            xanchor="center", 
                            x=0.5, 
                            font=dict(size=10, color="#4B5563")
                        )
                    )
                    st.plotly_chart(fig_status, use_container_width=True, config={'displayModeBar': False})

            st.markdown("<br>", unsafe_allow_html=True)

            # --- SEÇÃO 4: RANKINGS ---
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.markdown("<div class='section-title'>👤 Top 5 Usuários (Consumo Efetivo)</div>", unsafe_allow_html=True)
                top_u = jobs_validos.groupby('user_name')['pages'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_u.empty:
                    fig_u = px.bar(top_u, x='pages', y='user_name', orientation='h',
                                   text='pages', color='pages', color_continuous_scale=['#D0E1FD', '#0078D4'])
                    fig_u.update_traces(
                        hovertemplate="<b>👤 Usuário:</b> %{y}<br><b>📄 Páginas:</b> %{x}<extra></extra>",
                        textposition='outside'
                    )
                    fig_u.update_layout(
                        showlegend=False, 
                        coloraxis_showscale=False,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, visible=False),
                        yaxis={'categoryorder':'total ascending', 'showgrid':False},
                        margin=dict(t=10, b=10, l=10, r=40)
                    )
                    st.plotly_chart(fig_u, use_container_width=True, config={'displayModeBar': False})

            with col_r2:
                st.markdown("<div class='section-title'>🏢 Distribuição por Setor / Unidade</div>", unsafe_allow_html=True)
                df_un = jobs_validos.groupby('filial')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not df_un.empty:
                    fig_un = px.bar(df_un, x='filial', y='pages', text='pages',
                                    color_discrete_sequence=['#0078D4'])
                    fig_un.update_traces(
                        hovertemplate="<b>🏢 Unidade:</b> %{x}<br><b>📄 Total:</b> %{y}<extra></extra>",
                        textposition='outside'
                    )
                    fig_un.update_layout(
                        showlegend=False,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, title=""),
                        yaxis=dict(showgrid=False, visible=False),
                        margin=dict(t=10, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig_un, use_container_width=True, config={'displayModeBar': False})

            # --- SEÇÃO 5: TABELA DE AUDITORIA ---
            st.markdown("<br><div class='section-title'>🔍 Auditoria de Documentos e Diagnósticos</div>", unsafe_allow_html=True)
            search = st.text_input("Filtrar registros por palavra-chave...")
            
            df_final = df[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'printer_name', 'status_pt']].copy()
            df_final.columns = ['Data/Hora', 'Unidade', 'Usuário', 'Documento', 'Págs', 'Impressora', 'Status']
            
            if search:
                df_final = df_final[
                    df_final['Documento'].str.contains(search, case=False) | 
                    df_final['Usuário'].str.contains(search, case=False) |
                    df_final['Status'].str.contains(search, case=False)
                ]

            df_final = df_final.sort_values(by='Data/Hora', ascending=False)

            def highlight_status(row):
                styles = [''] * len(row)
                status_val = row['Status']
                if status_val in ['Falha Crítica', 'Cancelado pelo Usuário']:
                    return ['background-color: #FEE2E2; color: #991B1B; font-weight: 500;'] * len(row)
                elif status_val in ['Toner Baixo', 'Spooler Sobrecarregado', 'Dispositivo Offline', 'Retido na Fila']:
                    return ['background-color: #FEF3C7; color: #92400E;'] * len(row)
                return styles

            st.dataframe(
                df_final.style.apply(highlight_status, axis=1),
                use_container_width=True, 
                hide_index=True
            )

            csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 Exportar Planilha Consolidada (Excel/CSV)", csv, "auditoria_impressao_ellca.csv", "text/csv")

        else:
            st.warning("Nenhum registro correspondente encontrado para a combinação de filtros selecionada.")
    else:
        st.info("Aguardando sincronização de dados estruturados na nuvem...")

   # LOGICA DE REFRESH AUTOMÁTICO BLINDADA
    # Verifica se a variável auto_refresh existe no escopo local antes de tentar ler
    if 'auto_refresh' in locals() and auto_refresh:
        time.sleep(60)
        st.rerun()
