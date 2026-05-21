import streamlit as st
import pandas as pd
import sys
import os
import time
import plotly.express as px
from supabase import create_client

# --- CONFIGURAÇÃO DE CUSTO ---
CUSTO_POR_PAGINA = 0.15  

# --- LÓGICA DE DIRETÓRIO ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.config import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    try:
        from config import SUPABASE_URL, SUPABASE_KEY
    except ImportError:
        st.error("Erro: Arquivo config.py não encontrado.")
        st.stop()

# --- CONFIGURAÇÃO DA PÁGINA (ESTILO HIGH-CONTRAST SUTIL) ---
st.set_page_config(
    page_title="Ellca | Monitor de Impressão",
    page_icon="⚡",
    layout="wide"
)

# --- CSS PREMIUM: TRADUÇÃO DE INTERFACE E DESIGN DE BALÕES ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #FAFAFA;
        }
        
        /* Oculta links e textos nativos em inglês do Streamlit */
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Títulos e Identidade */
        .main-title {
            color: #0F172A;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 2px;
        }
        .sub-title {
            color: #64748B;
            font-size: 13px;
            margin-bottom: 25px;
        }
        
        /* Cards Estilo Containers Flutuantes (Minimalismo Absoluto) */
        div.stMetric {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            padding: 18px 22px;
            border-radius: 10px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
        }
        
        div[data-testid="stMetricLabel"] {
            font-weight: 600 !important;
            color: #64748B !important;
            font-size: 12px !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetricValue"] {
            font-weight: 700 !important;
            color: #0F172A !important;
            font-size: 24px !important;
        }
        
        /* Customização dos inputs para português */
        .stTextInput>div>div>input {
            border-radius: 6px;
            border: 1px solid #E2E8F0;
        }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE ACESSO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔐 Acesso Administrativo - Ellca")
    with st.form("login_form"):
        password = st.text_input("Senha de Acesso", type="password")
        submit = st.form_submit_button("Entrar no Painel")
        if submit:
            if password == "ellca2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
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
                
                # Tradução manual de termos de status vindos do banco
                if 'status' not in df.columns:
                    df['status'] = 'Sucesso'
                df['status'] = df['status'].fillna('Sucesso')
                
                # Mapeamento estrito para Português de todos os status possíveis
                mapa_status = {
                    'Documento enviado': 'Impressão Concluída',
                    'Documento pausado': 'Retido na Fila',
                    'Documento cancelado': 'Cancelado pelo Usuário',
                    'Erro de impressão': 'Falha Crítica',
                    'Fila congestionada': 'Spooler Sobrecarregado',
                    'Toner baixo': 'Insumo Crítico (Toner)',
                    'Offline': 'Dispositivo Desconectado'
                }
                df['status_pt'] = df['status'].map(mapa_status).fillna(df['status'])
                df['custo_estimado'] = df['pages'] * CUSTO_POR_PAGINA
            return df
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            return pd.DataFrame()

    df_raw = fetch_analytics()

    # --- BARRA LATERAL TOTALMENTE EM PORTUGUÊS ---
    with st.sidebar:
        st.markdown("<h3 style='color: #0F172A; font-weight:700;'>Painel Ellca</h3>", unsafe_allow_html=True)
        st.divider()
        
        auto_refresh = st.checkbox("🔄 Atualização Automática", value=True)
        refresh_interval = st.select_slider("Frequência (segundos)", options=[30, 60, 300], value=60)
        
        st.subheader("📅 Intervalo de Tempo")
        d_inicio = st.date_input("Data Inicial", value=pd.to_datetime("today") - pd.Timedelta(days=7), format="DD/MM/YYYY")
        d_fim = st.date_input("Data Final", value=pd.to_datetime("today"), format="DD/MM/YYYY")

        if not df_raw.empty:
            st.subheader("🏢 Unidades Corporativas")
            filiais = ["Todas"] + sorted(df_raw['filial'].unique().tolist())
            filial_sel = st.selectbox("Selecionar Filial", filiais)

            st.subheader("👤 Filtragem de Pessoal")
            users = ["Todos"] + sorted(df_raw['user_name'].unique().tolist())
            user_sel = st.selectbox("Selecionar Colaborador", users)
        
        st.divider()
        st.caption("Administrador: **Kleiton Braga**")

    if not df_raw.empty:
        mask = (df_raw['Data'] >= d_inicio) & (df_raw['Data'] <= d_fim)
        if filial_sel != "Todas":
            mask &= (df_raw['filial'] == filial_sel)
        if user_sel != "Todos":
            mask &= (df_raw['user_name'] == user_sel)
        
        df = df_raw.loc[mask].copy()

        # --- CABEÇALHO ---
        st.markdown("<div class='main-title'>Telemetria e Custos de Impressão</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Painel executivo focado em auditoria volumétrica, controle de insumos e rateio financeiro por unidade.</div>", unsafe_allow_html=True)

        if not df.empty:
            jobs_validos = df[~df['status_pt'].isin(['Cancelado pelo Usuário', 'Falha Crítica'])]
            t_paginas = int(jobs_validos['pages'].sum()) if not jobs_validos.empty else 0
            t_jobs = len(df)
            media_pag = round(jobs_validos['pages'].mean(), 1) if not jobs_validos.empty else 0
            custo_total = jobs_validos['custo_estimado'].sum() if not jobs_validos.empty else 0.0

            # LINHA 1 - BLOCOS DE MÉTRICAS (BENTO GRID CLEAN)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Produção de Páginas", f"{t_paginas:,}".replace(",", "."))
            m2.metric("Total de Requisições", f"{t_jobs:,}".replace(",", "."))
            m3.metric("Média de Páginas/Job", media_pag)
            m4.metric("Custo Estimado Total", f"R$ {custo_total:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))

            st.divider()

            # --- SEÇÃO DE GRÁFICOS COM BALÕES EXPLICATIVOS AVANÇADOS ---
            col_a, col_b = st.columns([2, 1])

            with col_a:
                df_day = jobs_validos.groupby('Data').agg({'pages': 'sum', 'custo_estimado': 'sum'}).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not df_day.empty:
                    df_day['Data_Formato'] = df_day['Data'].apply(lambda x: x.strftime('%d/%M/%Y'))
                    df_day['Custo_Formato'] = df_day['custo_estimado'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
                    
                    fig_timeline = px.line(df_day, x='Data', y='pages', title="<b>Evolução Diária de Consumo</b>",
                                         color_discrete_sequence=['#0F172A'])
                    
                    # Balão Explicativo Customizado (HTML para o Tooltip)
                    fig_timeline.update_traces(
                        line_width=2.5,
                        hovertemplate="<br>".join([
                            "<b>📅 Data:</b> %{customdata[0]}",
                            "<b>📄 Páginas Rodadas:</b> %{y}",
                            "<b>💰 Custo do Dia:</b> %{customdata[1]}",
                            "<extra>📈 Análise Temporal</extra>"
                        ]),
                        customdata=df_day[['Data_Formato', 'Custo_Formato']]
                    )
                    
                    fig_timeline.update_layout(
                        hovermode="x unified",
                        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Inter", bordercolor="#E2E8F0"),
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False, title=None, color="#94A3B8"),
                        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title=None, color="#94A3B8"),
                        title_font=dict(size=14, color='#0F172A'),
                        margin=dict(l=0, r=0, t=35, b=0)
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True, config={'displayModeBar': False})

            with col_b:
                df_status = df.groupby('status_pt').size().reset_index(name='Quantidade')
                
                color_map = {
                    'Impressão Concluída': '#0F172A',
                    'Retido na Fila': '#F59E0B',
                    'Cancelado pelo Usuário': '#EF4444',
                    'Falha Crítica': '#DC2626',
                    'Spooler Sobrecarregado': '#7C3AED',
                    'Insumo Crítico (Toner)': '#F97316',
                    'Dispositivo Desconectado': '#64748B'
                }
                
                fig_status = px.pie(df_status, values='Quantidade', names='status_pt', hole=0.55, color='status_pt', color_discrete_map=color_map)
                
                # Balão Explicativo Customizado para o Gráfico de Rosca
                fig_status.update_traces(
                    textinfo='none',
                    hovertemplate="<br>".join([
                        "<b>📌 Status:</b> %{label}",
                        "<b>📋 Total de Ocorrências:</b> %{value}",
                        "<b>📊 Representação:</b> %{percent}",
                        "<extra>Distribuição</extra>"
                    ])
                )
                
                fig_status.update_layout(
                    title="<b>Comportamento do Parque</b>",
                    title_font=dict(size=14, color='#0F172A'),
                    hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Inter", bordercolor="#E2E8F0"),
                    margin=dict(t=35, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10, color="#64748B"))
                )
                st.plotly_chart(fig_status, use_container_width=True, config={'displayModeBar': False})

            st.divider()

            # --- RANKINGS LADO A LADO ---
            st.markdown("<p style='font-size:13px; font-weight:600; color:#0F172A; text-transform:uppercase; letter-spacing:0.05em;'>Líderes de Consumo Executivo (Top 5)</p>", unsafe_allow_html=True)
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                top_custo = jobs_validos.groupby('user_name')['custo_estimado'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_custo.empty:
                    top_custo['texto_barra'] = top_custo['custo_estimado'].apply(lambda x: f"R$ {x:,.2f} ")
                    fig_custo = px.bar(top_custo, x='custo_estimado', y='user_name', orientation='h', text='texto_barra', title="<b>Gasto Gerado por Colaborador</b>")
                    
                    fig_custo.update_traces(
                        textposition='inside', insidetextanchor='end', marker_color='#1E3A8A', width=0.45,
                        hovertemplate="<b>Usuário:</b> %{y}<br><b>Despesa Gerada:</b> R$ %{x:,.2f}<extra>Finanças</extra>"
                    )
                    fig_custo.update_layout(
                        showlegend=False, yaxis={'categoryorder':'total ascending', 'title': None, 'color': '#64748B'},
                        xaxis={'showgrid': False, 'visible': False}, plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)', title_font=dict(size=13, color='#0F172A'),
                        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, bordercolor="#E2E8F0"),
                        margin=dict(l=10, r=10, t=35, b=10)
                    )
                    st.plotly_chart(fig_custo, use_container_width=True, config={'displayModeBar': False})

            with col_r2:
                top_paginas = jobs_validos.groupby('user_name')['pages'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_paginas.empty:
                    top_paginas['texto_barra'] = top_paginas['pages'].apply(lambda x: f"{int(x):,} pgs ")
                    fig_paginas = px.bar(top_paginas, x='pages', y='user_name', orientation='h', text='texto_barra', title="<b>Volume de Páginas Impressas</b>")
                    
                    fig_paginas.update_traces(
                        textposition='inside', insidetextanchor='end', marker_color='#475569', width=0.45,
                        hovertemplate="<b>Usuário:</b> %{y}<br><b>Páginas Rodadas:</b> %{x:,} pgs<extra>Volume</extra>"
                    )
                    fig_paginas.update_layout(
                        showlegend=False, yaxis={'categoryorder':'total ascending', 'title': None, 'color': '#64748B'},
                        xaxis={'showgrid': False, 'visible': False}, plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)', title_font=dict(size=13, color='#0F172A'),
                        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, bordercolor="#E2E8F0"),
                        margin=dict(l=10, r=10, t=35, b=10)
                    )
                    st.plotly_chart(fig_paginas, use_container_width=True, config={'displayModeBar': False})

            # --- HISTÓRICO DE AUDITORIA ---
            st.divider()
            st.markdown("<p style='font-size:14px; font-weight:700; color:#0F172A; margin-bottom:-5px;'>Registro Geral de Auditoria</p>", unsafe_allow_html=True)
            search = st.text_input("Filtrar registros...", placeholder="Pesquise por documento, colaborador ou filial...")
            
            df_final = df[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'custo_estimado', 'printer_name', 'status_pt']].copy()
            df_final['custo_estimado'] = df_final['custo_estimado'].apply(lambda x: f"R$ {x:,.2f}".replace(".", ","))
            df_final.columns = ['Data/Hora', 'Unidade', 'Colaborador', 'Documento', 'Págs', 'Custo', 'Impressora', 'Situação']
            
            if search:
                df_final = df_final[
                    df_final['Documento'].str.contains(search, case=False) | 
                    df_final['Colaborador'].str.contains(search, case=False) |
                    df_final['Situação'].str.contains(search, case=False)
                ]

            df_final = df_final.sort_values(by='Data/Hora', ascending=False)

            def highlight_status(row):
                styles = [''] * len(row)
                status_val = row['Situação']
                if status_val in ['Falha Crítica', 'Cancelado pelo Usuário']:
                    return ['background-color: #FEF2F2; color: #991B1B; font-weight: 500;'] * len(row)
                elif status_val in ['Retido na Fila', 'Spooler Sobrecarregado', 'Dispositivo Desconectado', 'Insumo Crítico (Toner)']:
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
        st.info("Aguardando pareamento de dados com o banco...")

    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
