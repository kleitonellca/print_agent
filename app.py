import streamlit as st
import pandas as pd
import sys
import os
import time
import plotly.express as px
from supabase import create_client

# --- LÓGICA DE CAMINHO ---
# Substitua o bloco de importação antigo por este:
try:
    # Tenta ler primeiro do Secrets (Ambiente de Produção na Nuvem)
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    # Caso não ache (Ambiente Local), tenta buscar do seu arquivo local que não vai para o GitHub
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

# --- ESTILIZAÇÃO CUSTOMIZADA (Sidebar Azul Claro e Estilos Gerais) ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #f0f7ff; /* Azul Corporativo Claro */
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
    @st.cache_data(ttl=30)  # Reduzido para 30s para acompanhar alertas de hardware em tempo real
    def fetch_analytics():
        try:
            res = supabase.table("print_logs").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('America/Sao_Paulo')
                df['Data'] = df['created_at'].dt.date
                df['Hora'] = df['created_at'].dt.hour
                df['created_at'] = df['created_at'].dt.tz_localize(None)
                # Garante que a coluna status existe para evitar quebras se o banco estiver vazio
                if 'status' not in df.columns:
                    df['status'] = 'Documento enviado'
                # Preenche valores nulos antigos com o status padrão padrão
                df['status'] = df['status'].fillna('Documento enviado')
            return df
        except Exception as e:
            st.error(f"Erro ao buscar dados: {e}")
            return pd.DataFrame()

    df_raw = fetch_analytics()

    # --- SIDEBAR (FILTROS) ---
   # --- BARRA LATERAL COM IDENTIDADE VISUAL ---
    with st.sidebar:
        
        URL_LOGO = "https://raw.githubusercontent.com/kleitonellca/print_agent/main/assets/logo_app_print.png"
        
        # Injeção centralizada com largura reduzida (65%) para dar mais sofisticação e respiro
        st.markdown(f"""
            <div style="text-align: center; padding: 10px 0 20px 0;">
                <img src="{URL_LOGO}" style="max-width: 65%; height: auto; border-radius: 12px;">
            </div>
        """, unsafe_allow_html=True)
        
        # Linha fina de separação elegante
        st.divider()
        
        # Auto Refresh
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

    # --- LÓGICA DE FILTRAGEM ---
    if not df_raw.empty:
        mask = (df_raw['Data'] >= d_inicio) & (df_raw['Data'] <= d_fim)
        if filial_sel != "Todas":
            mask &= (df_raw['filial'] == filial_sel)
        if user_sel != "Todos":
            mask &= (df_raw['user_name'] == user_sel)
        
        df = df_raw.loc[mask].copy()

        # --- DASHBOARD LAYOUT ---
        st.markdown(f"<div class='main-title'>Analytics de Impressão Corporativa</div>", unsafe_allow_html=True)

        if not df.empty:
            # 1. MÉTRICAS PRINCIPAIS (Filtra apenas jobs com sucesso ou pendentes para não inflar consumo real)
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

            # 2. SEÇÃO DE ALERTAS DE HARDWARE EM TEMPO REAL
            st.markdown("### ⚠️ Status e Alertas do Parque de Impressoras")
            col_t1, col_t2, col_t3 = st.columns(3)
            
            # Agrupa e contabiliza estados críticos atuais baseados no período
            impressoras_offline = df[df['status'] == 'Offline']['printer_name'].nunique()
            toner_baixo = df[df['status'] == 'Toner baixo']['printer_name'].nunique()
            filas_travadas = df[df['status'] == 'Fila congestionada']['printer_name'].nunique()
            
            col_t1.metric("🖨️ Impressoras em Offline", impressoras_offline, 
                        delta="Atenção" if impressoras_offline > 0 else "OK", delta_color="inverse")
            col_t2.metric("🧪 Alertas de Toner Baixo", toner_baixo, 
                        delta="Substituir" if toner_baixo > 0 else "OK", delta_color="inverse")
            col_t3.metric("⏳ Filas Congestionadas", filas_travadas, 
                        delta="Spooler Retido" if filas_travadas > 0 else "OK", delta_color="inverse")

            st.divider()

            # GRÁFICOS INTERATIVOS (PLOTLY)
            col_a, col_b = st.columns([2, 1])

            with col_a:
                # Volume por Dia - Gráfico de Área Interativo
                df_day = jobs_validos.groupby('Data')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame(columns=['Data', 'pages'])
                if not df_day.empty:
                    fig_timeline = px.area(df_day, x='Data', y='pages', 
                                         title="Histórico de Consumo Efetivo (Páginas)",
                                         color_discrete_sequence=['#0078D4'])
                    fig_timeline.update_layout(hovermode="x unified")
                    st.plotly_chart(fig_timeline, use_container_width=True)
                else:
                    st.info("Sem dados de consumo volumétrico para gerar a timeline.")

            with col_b:
                # Distribuição do Ciclo de Vida do Documento e Erros (Gráfico de Rosca)
                st.markdown("<p style='font-weight:bold; margin-bottom:-10px;'>Ciclo de Vida / Erros</p>", unsafe_allow_html=True)
                df_status = df.groupby('status').size().reset_index(name='Quantidade')
                
                # Mapeamento de cores fixas para manter a identidade de erro e sucesso
                color_map = {
                    'Documento enviado': '#0078D4',
                    'Documento pausado': '#FFB900',
                    'Documento cancelado': '#D83B01',
                    'Erro de impressão': '#E81123',
                    'Fila congestionada': '#A741A5',
                    'Toner baixo': '#F7630C',
                    'Offline': '#7A7A7A'
                }
                
                fig_status = px.pie(df_status, values='Quantidade', names='status', 
                                    hole=0.4, color='status', color_discrete_map=color_map)
                fig_status.update_layout(margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_status, use_container_width=True)

            st.divider()

            # RANKINGS E DISTRIBUIÇÃO POR UNIDADE
            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.subheader("👤 Ranking de Usuários (Top 5 Consumo)")
                top_u = jobs_validos.groupby('user_name')['pages'].sum().nlargest(5).reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not top_u.empty:
                    fig_u = px.bar(top_u, x='pages', y='user_name', orientation='h',
                                 text='pages', color='pages', color_continuous_scale='Blues')
                    fig_u.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_u, use_container_width=True)
                else:
                    st.info("Sem ranking de usuários disponível.")

            with col_r2:
                st.subheader("🏢 Distribuição Volumétrica por Unidade")
                df_un = jobs_validos.groupby('filial')['pages'].sum().reset_index() if not jobs_validos.empty else pd.DataFrame()
                if not df_un.empty:
                    fig_un = px.bar(df_un, x='filial', y='pages', 
                                   text='pages', color='filial', color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_un.update_layout(showlegend=False)
                    st.plotly_chart(fig_un, use_container_width=True)
                else:
                    st.info("Sem dados por filial.")

            # BUSCA E LOGS DETALHADOS COM HIGHLIGHTS DE STATUS
            st.divider()
            st.subheader("🔍 Auditoria de Documentos e Diagnósticos")
            search = st.text_input("Pesquisar por documento, usuário ou status do equipamento...")
            
            df_final = df[['created_at', 'filial', 'user_name', 'document_name', 'pages', 'printer_name', 'status']].copy()
            df_final.columns = ['Data/Hora', 'Unidade', 'Usuário', 'Documento', 'Págs', 'Impressora', 'Status']
            
            if search:
                df_final = df_final[
                    df_final['Documento'].str.contains(search, case=False) | 
                    df_final['Usuário'].str.contains(search, case=False) |
                    df_final['Status'].str.contains(search, case=False)
                ]

            # Ordenação padrão cronológica decrescente
            df_final = df_final.sort_values(by='Data/Hora', ascending=False)

            # Função de Estilização Condicional para destacar alertas na tabela do Streamlit
            def highlight_status(row):
                styles = [''] * len(row)
                status_val = row['Status']
                if status_val in ['Erro de impressão', 'Documento cancelado']:
                    return ['background-color: #fde8e8; color: #9b1c1c; font-weight: bold;'] * len(row)
                elif status_val in ['Toner baixo', 'Fila congestionada', 'Offline', 'Documento pausado']:
                    return ['background-color: #fef08a; color: #713f12;'] * len(row)
                elif status_val == 'Documento enviado':
                    return [''] * len(row)
                return styles

            # Renderização da tabela interativa utilizando o dataframe estilizado
            st.dataframe(
                df_final.style.apply(highlight_status, axis=1),
                use_container_width=True, 
                hide_index=True
            )

            # Exportação
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
