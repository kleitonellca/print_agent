import streamlit as st
import pandas as pd
import sys
import os
import time
import plotly.express as px
from supabase import create_client

# --- VARIÁVEIS DE CONFIGURAÇÃO COMERCIAL ---
CUSTO_POR_PAGINA = 0.15  

# --- LÓGICA DE PATH ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# --- CONFIGURAÇÕES DE PÁGINA (ESTILO PREMIUM VERCEL/SHADCN) ---
st.set_page_config(
    page_title="Ellca | Analytics Pro",
    page_icon="⚡",
    layout="wide"
)

# --- CSS HIGH-FIDELITY (Bento Grid, Sombras Soft, Sem Bordas Pesadas) ---
st.markdown("""
    <style>
        /* Importação de Fonte Moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Sidebar Minimalista Neutra */
        [data-testid="stSidebar"] {
            background-color: #FAFAFA;
            border-right: 1px solid #E5E5E5;
        }
        
        /* Título Executivo Clean */
        .main-title {
            color: #111827;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 4px;
        }
        .sub-title {
            color: #6B7280;
            font-size: 14px;
            margin-bottom: 25px;
        }
        
        /* Cards Estilo Bento Box (Shadcn/UI Design) */
        div.stMetric {
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            padding: 20px 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div.stMetric:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        
        /* Ajuste fino nas fontes dos KPIs */
        div[data-testid="stMetricLabel"] {
            font-weight: 500 !important;
            color: #4B5563 !important;
            font-size: 13px !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetricValue"] {
            font-weight: 700 !important;
            color: #111827 !important;
            font-size: 26px !important;
            letter-spacing: -0.02em;
        }
        
        /* Ajuste de Espaçamento das tabelas e inputs */
        .stTextInput>div>div>input {
            border-radius: 8px;
        }
        hr {
            margin: 30px 0 !important;
            border-top: 1px solid #E5E7EB !important;
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
                df['custo_estimado'] = df['pages'] * CUSTO_POR_PAGINA
            return df
        except Exception as e:
            st.error(f"Erro ao buscar dados: {e}")
            return pd.DataFrame()

    df_raw = fetch_analytics()

    # --- SIDEBAR E FILTROS CLEAN ---
    with st.sidebar:
        st.markdown("<h3 style='color: #111827; font-weight:700; letter-spacing:-0.02em;'>Ellca Print</h3>", unsafe_allow_html=True)
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
        st.caption("Admin: **Kleiton Braga**")

    if not df_raw.empty:
        mask = (df_raw['Data'] >= d_inicio) & (df_raw['Data'] <= d_fim)
        if filial_sel != "Todas":
            mask &= (df_raw['filial'] == filial_sel)
        if user_sel != "Todos":
            mask &= (df_raw['user_name'] == user_sel)
        
        df = df_raw.loc[mask].copy()

        # --- CABEÇALHO SUTIL ---
        st.markdown("<div class='main-title'>Visão Geral de Impressões</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Métricas de telemetria, custos acumulados e saúde dos ativos de impressão corporativos.</div>", unsafe_allow_html=True)

        if not df.empty:
            jobs_validos = df[~df['status'].isin(['Documento cancelado', 'Erro de impressão'])]
            t_paginas = int(jobs_validos['pages'].sum()) if not jobs_validos.empty else 0
            t_jobs = len(df)
            media_pag = round(jobs_validos['pages'].mean(), 1) if not jobs_validos.empty else 0
            custo_total = jobs_validos['custo_estimado'].sum() if not jobs_validos.empty else 0.0

            # Bento Grid - Linha 1 (KPIs Financeiros e Volume)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Volume de Páginas", f"{t_paginas:,}".replace(",", "."))
            m2.metric("Total Logs Capturados", f"{t_jobs:,}".replace(",", "."))
            m3.metric("Média Págs/Job", media_pag)
            m4.metric("Custo Estimado", f"R$ {custo_total:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))

            # Bento Grid - Linha 2 (Métricas de Saúde de Ativos)
            st.markdown("<p style='font-size:12px; font-weight:600; color:#6B7280; text-transform:uppercase; margin-top:20px; letter-spacing:0.05em;'>Status do Parque de Dispositivos</p>", unsafe_allow_html=True)
            col_t1, col_t2, col_t3 = st.columns(3)
            
            impressoras_offline = df[df['status'] == 'Offline']['printer_name'].nunique()
            toner_baixo = df[df['status'] == 'Toner baixo']['printer_name'].nunique()
            filas_travadas = df[df['status'] == 'Fila congestionada']['printer_name'].nunique()
            
            col_t1.metric("Impressoras Offline", impressoras_offline, delta="Verificar" if impressoras_offline > 0 else "Estável", delta_color="inverse" if impressoras_offline > 0 else "off")
            col_t2.metric("Alertas de Toner Baixo", toner_baixo, delta="Troca Pendente" if toner_baixo > 0 else "Estável", delta_color="inverse" if toner_baixo > 0 else "off")
            col_t3.metric("Filas Retidas", filas_travadas, delta="Congestionado" if filas_travadas > 0 else "Livre", delta_color="inverse" if filas_travadas > 0 else "off")

            st.divider()

            # --- GRÁFICOS MINIMALISTAS (ESTILO STRIPE/VERCEL) ---
            col_a, col_b = st.columns([2, 1])

            with col_a:
                df_day = jobs_validos.groupby('Data').agg({'pages': 'sum', 'custo_estimado': 'sum'}).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not df_day.empty:
                    df_day['Custo Formatado'] = df_day['custo_estimado'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
                    
                    # Gráfico de Linha Limpo (Invisível/Sem poluição de áreas densas)
                    fig_timeline = px.line(df_day, x='Data', y='pages', 
                                         title="<b>Tendência de Consumo Temporal</b>",
                                         color_discrete_sequence=['#111827'], # Linha quase preta ultra moderna
                                         hover_data={'pages': True, 'Custo Formatado': True})
                    
                    fig_timeline.update_traces(line_width=3)
                    fig_timeline.update_layout(
                        hovermode="x unified",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, title=None, color="#9CA3AF"),
                        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", title=None, color="#9CA3AF"),
                        title_font=dict(size=15, color='#111827', family='Inter'),
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})

            with col_b:
                df_status = df.groupby('status').size().reset_index(name='Quantidade')
                # Paleta Semântica Sóbria
                color_map = {
                    'Documento enviado': '#111827',
                    'Documento pausado': '#F59E0B',
                    'Documento cancelado': '#EF4444',
                    'Erro de impressão': '#DC2626',
                    'Fila congestionada': '#7C3AED',
                    'Toner baixo': '#F97316',
                    'Offline': '#6B7280'
                }
                
                fig_status = px.pie(df_status, values='Quantidade', names='status', 
                                    hole=0.6, color='status', color_discrete_map=color_map)
                
                fig_status.update_layout(
                    title="<b>Distribuição de Eventos</b>",
                    title_font=dict(size=15, color='#111827', family='Inter'),
                    margin=dict(t=40, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=11, color="#4B5563"))
                )
                fig_status.update_traces(textinfo='none') # Oculta porcentagens poluindo a rosca
                st.plotly_chart(fig_status, use_container_width=True, config={'displayModeBar': False})

            st.divider()

            # --- RANKINGS LADO A LADO SÉRIE HIGH-END ---
            st.markdown("<p style='font-size:14px; font-weight:600; color:#111827; text-transform:uppercase; letter-spacing:0.05em;'>Análise de Líderes de Consumo (Top 5)</p>", unsafe_allow_html=True)
            col_r1, col_r2 = st.columns(2)

            # Estilo das Barras: Bordas retas, sem grades, fonte interna discreta
            with col_r1:
                top_custo = jobs_validos.groupby('user_name')['custo_estimado'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_custo.empty:
                    top_custo['texto_barra'] = top_custo['custo_estimado'].apply(lambda x: f"R$ {x:,.2f} ")
                    fig_custo = px.bar(top_custo, x='custo_estimado', y='user_name', orientation='h',
                                       text='texto_barra', title="<b>Gasto Acumulado por Colaborador</b>")
                    fig_custo.update_traces(textposition='inside', insidetextanchor='end', marker_color='#1E3A8A', marker_line_color='rgba(0,0,0,0)', width=0.5)
                    fig_custo.update_layout(
                        showlegend=False, yaxis={'categoryorder':'total ascending', 'title': None, 'color': '#4B5563'},
                        xaxis={'showgrid': False, 'visible': False}, plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)', title_font=dict(size=14, color='#111827'),
                        margin=dict(l=10, r=10, t=35, b=10)
                    )
                    st.plotly_chart(fig_custo, use_container_width=True, config={'displayModeBar': False})

            with col_r2:
                top_paginas = jobs_validos.groupby('user_name')['pages'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_paginas.empty:
                    top_paginas['texto_barra'] = top_paginas['pages'].apply(lambda x: f"{int(x):,} pgs ")
                    fig_paginas = px.bar(top_paginas, x='pages', y='user_name', orientation='h',
                                       text='texto_barra', title="<b>Volume de Páginas Despachadas</b>")
                    fig_paginas.update_traces(textposition='inside', insidetextanchor='end', marker_color='#4B5563', marker_line_color='rgba(0,0,0,0)', width=0.5)
                    fig_paginas.update_layout(
                        showlegend=False, yaxis={'categoryorder':'total ascending', 'title': None, 'color': '#4B5563'},
                        xaxis={'showgrid': False, 'visible': False}, plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)', title_font=dict(size=14, color='#111827'),
                        margin=dict(l=10, r=10, t=35, b=10)
                    )
                    st.plotly_chart(fig_paginas, use_container_width=True, config={'displayModeBar': False})

            # --- AUDITORIA DE DOCUMENTOS EM ESTILO DATA-TABLE ---
            st.divider()
            st.markdown("<p style='font-size:15px; font-weight:700; color:#111827; margin-bottom:-5px;'>Histórico Geral de Auditoria</p>", unsafe_allow_html=True)
            search = st.text_input("Filtrar logs por qualquer palavra-chave...", placeholder="Digite o nome de um documento, usuário ou filial...")
            
            df_final = df[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'custo_estimado', 'printer_name', 'status']].copy()
            df_final['custo_estimado'] = df_final['custo_estimado'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
            df_final.columns = ['Data/Hora', 'Unidade', 'Usuário', 'Documento', 'Págs', 'Custo', 'Impressora', 'Status']
            
            if search:
                df_final = df_final[
                    df_final['Documento'].str.contains(search, case=False) | 
                    df_final['Usuário'].str.contains(search, case=False) |
                    df_final['Status'].str.contains(search, case=False)
                ]

            df_final = df_final.sort_values(by='Data/Hora', ascending=False)

            # Estilização Sutil da Tabela (Apenas linhas horizontais, sem cores gritantes)
            def highlight_status(row):
                styles = [''] * len(row)
                status_val = row['Status']
                if status_val in ['Erro de impressão', 'Documento cancelado']:
                    return ['background-color: #FEF2F2; color: #991B1B; font-weight: 500;'] * len(row)
                elif status_val in ['Toner baixo', 'Fila congestionada', 'Offline', 'Documento pausado']:
                    return ['background-color: #FFFBEB; color: #92400E;'] * len(row)
                return styles

            st.dataframe(
                df_final.style.apply(highlight_status, axis=1),
                use_container_width=True, 
                hide_index=True
            )

            csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 Exportar Relatório Consolidado", csv, "auditoria_ellca.csv", "text/csv")

        else:
            st.warning("Nenhum registro encontrado para os filtros selecionados.")
    else:
        st.info("Aguardando sincronização com o banco de dados...")

    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
