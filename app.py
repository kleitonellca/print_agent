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

# --- ESTILIZAÇÃO CUSTOMIZADA EVOLUÍDA ---
st.markdown("""
    <style>
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
        div[data-testid="stElementContainer"]:has(.filter-box) {
            margin-top: -5px !important;
        }
        .filter-box div[data-testid="stSubheader"] {
            display: none !important;
        }
        div[data-baseweb="select"], div[data-baseweb="input"], div[data-baseweb="calendar"] {
            border: 1.5px solid #002040 !important;
            border-radius: 6px !important;
            transition: all 0.2s ease-in-out !important;
            background-color: #FFFFFF !important;
        }
        div[data-baseweb="select"]:focus-within, div[data-baseweb="input"]:focus-within {
            border-color: #0078D4 !important;
            box-shadow: 0 0 0 3px rgba(0, 120, 212, 0.25) !important;
        }
        label p {
            color: #002040 !important;
            font-weight: 700 !important;
            font-size: 14px !important;
        }
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            padding: 20px 25px !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
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
    CLEAN_URL = SUPABASE_URL.split("/rest/v1/")[0]
    supabase = create_client(CLEAN_URL, SUPABASE_KEY)

    # --- 1. BUSCA DE METADADOS DOS DROPDOWNS (GLOBAL) ---
    @st.cache_data(ttl=30)
    def fetch_filters_metadata():
        try:
            filiais_res = supabase.table("print_logs").select("filial").execute()
            df_f = pd.DataFrame(filiais_res.data)
            lista_filiais = sorted(df_f['filial'].dropna().unique().tolist()) if not df_f.empty else []

            users_res = supabase.table("print_logs").select("user_name").execute()
            df_u = pd.DataFrame(users_res.data)
            lista_users = sorted(df_u['user_name'].dropna().unique().tolist()) if not df_u.empty else []

            dates_res = supabase.table("print_logs").select("created_at").order("created_at", desc=False).limit(1).execute()
            if dates_res.data:
                data_minima = pd.to_datetime(dates_res.data[0]['created_at']).tz_convert('America/Sao_Paulo').date()
            else:
                data_minima = pd.Timestamp.now(tz='America/Sao_Paulo').date() - pd.Timedelta(days=7)

            return lista_filiais, lista_users, data_minima
        except Exception as e:
            st.error(f"Erro ao carregar metadados dos filtros: {e}")
            return [], [], pd.Timestamp.now(tz='America/Sao_Paulo').date() - pd.Timedelta(days=7)

    # --- 2. ENGINE DE DADOS OTIMIZADO PARA EXPORTAÇÃO COMPLETA ---
    def fetch_dashboard_data(p_inicio, p_fim, f_sel, u_sel):
        try:
            iso_inicio = f"{p_inicio}T00:00:00.000000+00:00"
            iso_fim = f"{p_fim}T23:59:59.999999+00:00"

            # Query 1: Base de dados estatística e de Exportação (Traz todas as colunas necessárias de TODOS os registros do período)
            q_macro = supabase.table("print_logs").select("created_at, filial, user_name, document_name, pages, printer_name, hostname", count="exact")
            q_macro = q_macro.gte("created_at", iso_inicio).lte("created_at", iso_fim)
            if f_sel != "Todas":
                q_macro = q_macro.eq("filial", f_sel)
            if u_sel != "Todos":
                q_macro = q_macro.eq("user_name", u_sel)
            
            res_macro = q_macro.execute()
            total_logs = res_macro.count if res_macro.count is not None else 0
            df_macro = pd.DataFrame(res_macro.data)

            if not df_macro.empty:
                df_macro['created_at'] = pd.to_datetime(df_macro['created_at'], utc=True).dt.tz_convert('America/Sao_Paulo')
                df_macro['Data'] = df_macro['created_at'].dt.date
                df_macro['Hora'] = df_macro['created_at'].dt.hour
                df_macro['pages'] = pd.to_numeric(df_macro['pages'], errors='coerce').fillna(0).astype(int)

            # Query 2: Apenas uma visualização rápida limitada para a interface visual não travar
            df_audit = df_macro.head(1000).copy() if not df_macro.empty else pd.DataFrame()

            return df_macro, df_audit, total_logs
        except Exception as e:
            st.error(f"Erro no processamento lógico de dados: {e}")
            return pd.DataFrame(), pd.DataFrame(), 0

    lista_todas_filiais, lista_todos_usuarios, data_minima_banco = fetch_filters_metadata()
    hoje_local = pd.Timestamp.now(tz='America/Sao_Paulo').date()

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

    # --- FILTROS HORIZONTAIS ENVELOPADOS VIA INTERFACE ---
    with st.container(border=True):
        st.markdown('<div class="filter-box"></div>', unsafe_allow_html=True)
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 1.5, 2, 2, 1])
        
        with f_col1:
            d_inicio = st.date_input("De", value=data_minima_banco, format="DD/MM/YYYY")
        with f_col2:
            d_fim = st.date_input("Até", value=hoje_local, format="DD/MM/YYYY")
        with f_col3:
            filiais = ["Todas"] + lista_todas_filiais
            filial_sel = st.selectbox("Filial", filiais)
        with f_col4:
            users = ["Todos"] + lista_todos_usuarios
            user_sel = st.selectbox("Usuário", users)
        with f_col5:
            st.markdown("<label style='font-size:14px; font-weight:700; color:#002040;'>Configurações</label>", unsafe_allow_html=True)
            auto_refresh = st.checkbox("🔄 Auto-Refresh", value=True)

    # --- CAPTURA E RECONCILIAÇÃO ---
    df, df_tabela, exibir_total_logs = fetch_dashboard_data(d_inicio, d_fim, filial_sel, user_sel)

    if not df.empty:
        # --- SEÇÃO 1: MÉTRICAS DE VOLUMETRIA (BASE INTEGRAL DO PERÍODO) ---
        t_paginas = int(df['pages'].sum())
        media_pag = round(df['pages'].mean(), 1) if t_paginas > 0 else 0
        t_unidades = df['filial'].nunique()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Páginas Impressas", f"{t_paginas:,}".replace(",", "."))
        m2.metric("Total Logs Capturados", f"{exibir_total_logs:,}".replace(",", "."))
        m3.metric("Média Págs / Documento", media_pag)
        m4.metric("Unidades Ativas no Período", t_unidades)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SEÇÃO 2: BLOCO DE GRÁFICOS INTERATIVOS ---
        st.markdown("<div class='section-title'>Análise Gráfica Macroeconômica</div>", unsafe_allow_html=True)
        col_a, col_b = st.columns([2, 1])

        with col_a:
            df_day = df.groupby('Data')['pages'].sum().reset_index()
            if not df_day.empty:
                df_day['Data_Formato'] = df_day['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
                fig_timeline = px.area(df_day, x='Data', y='pages', 
                                       title="<b>Histórico de Volume de Impressão (Páginas)</b>",
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
            df_print = df.groupby('printer_name')['pages'].sum().reset_index()
            if not df_print.empty:
                fig_print = px.pie(df_print, values='pages', names='printer_name', hole=0.60,
                                   title="<b>Carga por Impressora (Páginas)</b>",
                                   color_discrete_sequence=px.colors.qualitative.Prism)
                
                fig_print.update_traces(
                    textinfo='none',
                    hovertemplate="<b>🖨️ Impressora:</b> %{label}<br><b>📄 Páginas:</b> %{value}<br><b>📊 Proporção:</b> %{percent}<extra></extra>"
                )
                
                fig_print.update_layout(
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
                st.plotly_chart(fig_print, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SEÇÃO 3: RANKINGS ---
        col_r1, col_r2 = st.columns(2)

        with col_r1:
            st.markdown("<div class='section-title'>👤 Top 5 Usuários de Maior Impacto</div>", unsafe_allow_html=True)
            top_u = df.groupby('user_name')['pages'].sum().nlargest(5).reset_index()
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
            st.markdown("<div class='section-title'>🏢 Distribuição de Volumetria por Unidade</div>", unsafe_allow_html=True)
            df_un = df.groupby('filial')['pages'].sum().reset_index()
            if not df_un.empty:
                fig_un = px.bar(df_un, x='filial', y='pages', text='pages',
                                color_discrete_sequence=['#0078D4'])
                fig_un.update_traces(
                    hovertemplate="<b>🏢 Unidade:</b> %{x}<br><b>📄 Total Páginas:</b> %{y}<extra></extra>",
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

        # --- SEÇÃO 4: TABELA DE AUDITORIA (RENDERIZA MÁXIMO 1000 LINHAS PARA EVITAR LENTIDÃO NA TELA) ---
        st.markdown("<br><div class='section-title'>🔍 Painel de Auditoria e Rastreamento de Filas (Amostragem Recente)</div>", unsafe_allow_html=True)
        search = st.text_input("Filtrar registros visíveis na tela por palavra-chave...")
        
        if not df_tabela.empty:
            df_final_tela = df_tabela[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'printer_name', 'hostname']].copy()
            df_final_tela.columns = ['Data/Hora', 'Unidade', 'Usuário', 'Nome do Documento', 'Págs', 'Impressora', 'Estação (Host)']
            df_final_tela['Data/Hora'] = df_final_tela['Data/Hora'].dt.tz_localize(None)
            
            if search:
                df_final_tela = df_final_tela[
                    df_final_tela['Nome do Documento'].str.contains(search, case=False) | 
                    df_final_tela['Usuário'].str.contains(search, case=False) |
                    df_final_tela['Unidade'].str.contains(search, case=False)
                ]

            df_final_tela = df_final_tela.sort_values(by='Data/Hora', ascending=False)
            st.dataframe(df_final_tela, use_container_width=True, hide_index=True)

        # --- SEÇÃO 5: MOTOR DE EXPORTAÇÃO COMPLETA (GERA O ARQUIVO USANDO A BASE TOTAL 'df' SEM LIMITES) ---
        if not df.empty:
            df_exportacao = df[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'printer_name', 'hostname']].copy()
            df_exportacao.columns = ['Data/Hora', 'Unidade', 'Usuário', 'Nome do Documento', 'Págs', 'Impressora', 'Estação (Host)']
            df_exportacao['Data/Hora'] = df_exportacao['Data/Hora'].dt.tz_localize(None)
            df_exportacao = df_exportacao.sort_values(by='Data/Hora', ascending=False)
            
            csv = df_exportacao.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.markdown("<br>", unsafe_allow_html=True)
            
            # O label do botão agora mostra dinamicamente a quantidade total real de registros que serão baixados
            st.download_button(
                label=f"📥 Exportar Relatório Consolidado Total ({len(df_exportacao):,} registros)".replace(",", "."),
                data=csv,
                file_name="relatorio_consolidado_ellca.csv",
                mime="text/csv"
            )
            
    else:
        st.warning("Nenhum registro correspondente encontrado para a combinação de filtros selecionada.")

    # LÓGICA DE REFRESH AUTOMÁTICO
    if 'auto_refresh' in locals() and auto_refresh:
        time.sleep(60)
        st.rerun()
