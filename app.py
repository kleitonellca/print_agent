import streamlit as st
import pandas as pd
import sys
import os
import time
import plotly.express as px
from supabase import create_client

# --- LÓGICA DE CAMINHO ---
try:
    # Tenta ler primeiro do Secrets (Ambiente de Produção na Nuvem)
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    # Caso não ache (Ambiente Local), tenta buscar do seu arquivo local
    try:
        from config import SUPABASE_URL, SUPABASE_KEY
    except ImportError:
        st.error("Erro: Credenciais de banco de dados não configuradas.")
        st.stop()

# --- CONFIGURAÇÕES DE PÁGINA ---
st.set_page_config(
    page_title="Ellca Tecnologia - Analytics Pro",
    page_icon="📊",
    layout="wide"
)

# --- ESTILIZAÇÃO CUSTOMIZADA (Sidebar e Ajuste do Topo) ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #f0f7ff; /* Azul Corporativo Claro */
        }
        /* Remove o recuo padrão do topo da sidebar para alinhar a logo */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0rem !important;
        }
        div[data-testid="stSidebarHeader"] {
            display: none !important;
        }
        .main-title {
            color: #1E3A8A;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        div.stMetric {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
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
    @st.cache_data(ttl=30)
    def fetch_analytics():
        try:
            res = supabase.table("print_logs").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('America/Sao_Paulo')
                df['Data'] = df['created_at'].dt.date
                df['Hora'] = df['created_at'].dt.hour
                df['created_at'] = df['created_at'].dt.tz_localize(None)
                
                if 'status' not in df.columns:
                    df['status'] = 'Documento enviado'
                df['status'] = df['status'].fillna('Documento enviado')
                
                # Tradução e mapeamento amigável para exibição no App
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

    # --- SIDEBAR (FILTROS) ---
    with st.sidebar:
        URL_LOGO = "https://raw.githubusercontent.com/kleitonellca/print_agent/main/assets/logo_print.png?v=2"
        
        st.markdown(f"""
            <div style="text-align: center; padding: 10px 0 10px 0;">
                <img src="{URL_LOGO}" style="max-width: 55%; height: auto; border-radius: 12px;">
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        auto_refresh = st.checkbox("🔄 Auto-Refresh", value=True)
        refresh_interval = st.select_slider("Atualizar a cada (s)", options=[30, 60, 300], value=60)
        
        st.subheader("📅 Período")
        d_inicio = st.date_input("De", value=pd.to_datetime("today") - pd.Timedelta(days=7), format="DD/MM/YYYY")
        d_fim = st.date_input("Até", value=pd.to_datetime("today"), format="DD/MM/YYYY")

        if not df_raw.empty:
            st.subheader("🏢 Unidades")
            filiais = ["Todas"] + sorted(df_raw['filial'].unique().tolist())
            filial_sel = st.selectbox("Filtrar por Filial", filiais)

            st.subheader("👤 Usuários")
            users = ["Todos"] + sorted(df_raw['user_name'].unique().tolist())
            user_sel = st.selectbox("Filtrar por Usuário", users)
        
        st.divider()
        st.markdown("<div style='color: #64748B; font-size: 12px;'>Admin: <b>Kleiton Braga</b></div>", unsafe_allow_html=True)

    # --- LÓGICA DE FILTRAGEM ---
    if not df_raw.empty:
        mask = (df_raw['Data'] >= d_inicio) & (df_raw['Data'] <= d_fim)
        if filial_sel != "Todas":
            mask &= (df_raw['filial'] == filial_sel)
        if user_sel != "Todos":
            mask &= (df_raw['user_name'] == user_sel)
        
        df = df_raw.loc[mask].copy()

        # --- DASHBOARD LAYOUT ---
        st.markdown("<div class='main-title'>Analítico de Impressão Corporativa</div>", unsafe_allow_html=True)

        if not df.empty:
            # 1. MÉTRICAS PRINCIPAIS
            jobs_validos = df[~df['status'].isin(['Documento cancelado', 'Erro de impressão'])]
            t_paginas = int(jobs_validos['pages'].sum()) if not jobs_validos.empty else 0
            t_jobs = len(df)
            media_pag = round(jobs_validos['pages'].mean(), 1) if not jobs_validos.empty else 0
            t_unidades = df['filial'].nunique()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📄 Total Páginas (Sucesso)", f"{t_paginas:,}".replace(",", "."))
            m2.metric("📋 Total Logs Capturados", f"{t_jobs:,}".replace(",", "."))
            m3.metric("📊 Média Págs/Doc", media_pag)
            m4.metric("🏢 Unidades Ativas", t_unidades)

            # 2. SEÇÃO DE ALERTAS
            st.markdown("### ⚠️ Status e Alertas do Parque de Impressoras")
            col_t1, col_t2, col_t3 = st.columns(3)
            
            impressoras_offline = df[df['status'] == 'Offline']['printer_name'].nunique()
            toner_baixo = df[df['status'] == 'Toner baixo']['printer_name'].nunique()
            filas_travadas = df[df['status'] == 'Fila congestionada']['printer_name'].nunique()
            
            col_t1.metric("🖨️ Impressoras Offline", impressoras_offline, 
                        delta="Atenção" if impressoras_offline > 0 else "OK", delta_color="inverse")
            col_t2.metric("🧪 Alertas de Toner Baixo", toner_baixo, 
                        delta="Substituir" if toner_baixo > 0 else "OK", delta_color="inverse")
            col_t3.metric("⏳ Filas Congestionadas", filas_travadas, 
                        delta="Spooler Retido" if filas_travadas > 0 else "OK", delta_color="inverse")

            st.divider()

            # --- GRÁFICOS INTERATIVOS ---
            col_a, col_b = st.columns([2, 1])

            with col_a:
                df_day = jobs_validos.groupby('Data')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame(columns=['Data', 'pages'])
                if not df_day.empty:
                    df_day['Data_Formato'] = df_day['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
                    fig_timeline = px.area(df_day, x='Data', y='pages', 
                                           title="<b>Histórico de Consumo Efetivo (Páginas)</b>",
                                           color_discrete_sequence=['#0078D4'])
                    
                    # Balão explicativo customizado em português
                    fig_timeline.update_traces(
                        hovertemplate="<b>📅 Data:</b> %{customdata[0]}<br><b>📄 Páginas:</b> %{y}<extra>Linha do Tempo</extra>",
                        customdata=df_day[['Data_Formato']]
                    )
                    fig_timeline.update_layout(
                        hovermode="x unified",
                        title_font=dict(size=14, color='#0F172A'),
                        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, bordercolor="#E2E8F0")
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem dados de consumo volumétrico para gerar a timeline.")

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
                    
                    # CORREÇÃO CRÍTICA: Instanciação correta do gráfico de rosca antes do layout
                    fig_status = px.pie(df_status, values='Quantidade', names='status_pt', hole=0.55,
                                        color='status_pt', color_discrete_map=color_map)
                    
                    # Balão explicativo customizado em português
                    fig_status.update_traces(
                        textinfo='none',
                        hovertemplate="<b>📌 Status:</b> %{label}<br><b>📋 Ocorrências:</b> %{value}<br><b>📊 Porcentagem:</b> %{percent}<extra>Distribuição</extra>"
                    )
                    
                    fig_status.update_layout(
                        title={
                            'text': "<b>Ciclo de Vida / Erros</b>",
                            'y': 0.95,
                            'x': 0.0,
                            'xanchor': 'left',
                            'yanchor': 'top'
                        },
                        title_font=dict(size=14, color='#0F172A'),
                        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, bordercolor="#E2E8F0"),
                        margin=dict(t=90, b=15, l=10, r=10), 
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=-0.35, 
                            xanchor="center", 
                            x=0.5, 
                            font=dict(size=10, color="#64748B")
                        )
                    )
                    st.plotly_chart(fig_status, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem logs de status para exibir.")

            st.divider()

            # --- RANKINGS ---
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.subheader("👤 Ranking de Usuários (Top 5 Consumo)")
                top_u = jobs_validos.groupby('user_name')['pages'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_u.empty:
                    fig_u = px.bar(top_u, x='pages', y='user_name', orientation='h',
                                   text='pages', color='pages', color_continuous_scale='Blues')
                    
                    fig_u.update_traces(
                        hovertemplate="<b>👤 Usuário:</b> %{y}<br><b>📄 Páginas Impressas:</b> %{x}<extra>Volume</extra>"
                    )
                    fig_u.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, hoverlabel=dict(bgcolor="#FFFFFF"))
                    st.plotly_chart(fig_u, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem ranking de usuários disponível.")

            with col_r2:
                st.subheader("🏢 Distribuição Volumétrica por Unidade")
                df_un = jobs_validos.groupby('filial')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not df_un.empty:
                    fig_un = px.bar(df_un, x='filial', y='pages', 
                                   text='pages', color='filial', color_discrete_sequence=px.colors.qualitative.Pastel)
                    
                    fig_un.update_traces(
                        hovertemplate="<b>🏢 Unidade:</b> %{x}<br><b>📄 Total do Setor:</b> %{y}<extra>Filiais</extra>"
                    )
                    fig_un.update_layout(showlegend=False, hoverlabel=dict(bgcolor="#FFFFFF"))
                    st.plotly_chart(fig_un, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem dados por filial.")

            # --- HISTÓRICO DE AUDITORIA ---
            st.divider()
            st.subheader("🔍 Auditoria de Documentos e Diagnósticos")
            search = st.text_input("Pesquisar por documento, usuário ou status do equipamento...")
            
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
                    return ['background-color: #fde8e8; color: #9b1c1c; font-weight: bold;'] * len(row)
                elif status_val in ['Toner Baixo', 'Spooler Sobrecarregado', 'Dispositivo Offline', 'Retido na Fila']:
                    return ['background-color: #fef08a; color: #713f12;'] * len(row)
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
            st.warning("Nenhum registro encontrado para os filtros selecionados.")
    else:
        st.info("Aguardando sincronização com o banco de dados...")

    # LÓGICA DE REFRESH
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
