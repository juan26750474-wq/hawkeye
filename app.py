import streamlit as st
import feedparser
import google.generativeai as genai
import urllib.parse
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from time import mktime
import html
import re
import pandas as pd

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="📡")

# ⚠️ PON AQUÍ TU API KEY
GEMINI_API_KEY = "AIzaSyAEwwwYurbGqNvgoNqfJ8cXU_BAXYA9wyU"

if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"API Error: {e}")

# --- 2. CSS STYLES ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* SITREP Box */
    .ia-report {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 6px;
        border-top: 4px solid #0056b3; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        font-family: 'Segoe UI', sans-serif;
        font-size: 0.95em;
        line-height: 1.5;
        color: #2c3e50;
    }
    
    /* Inputs */
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
    }

    /* ESTILO DE NOTICIAS (Letra pequeña + Espacio Vertical) */
    .news-container {
        border-bottom: 1px solid #eee;
        padding: 8px 0;
    }
    .news-meta {
        font-size: 0.75em; /* Letra muy pequeña para fecha/pais */
        color: #888;
        margin-bottom: 2px;
        font-family: monospace;
    }
    .news-title {
        font-size: 0.85em; /* Letra contenida para el titular */
        font-weight: 600;
        color: #222;
        line-height: 1.4; /* Espacio entre lineas para leer bien */
        margin-bottom: 4px;
        display: block; /* Fuerza que ocupe su propio bloque */
    }
    .news-source {
        font-size: 0.75em;
        color: #0056b3;
        font-weight: bold;
    }
    .news-link a {
        font-size: 0.75em;
        text-decoration: none;
        color: #0056b3;
        border: 1px solid #eee;
        padding: 2px 6px;
        border-radius: 3px;
    }
    .news-link a:hover { background-color: #f0f0f0; }

    /* Footer */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #ffffff; color: #95a5a6;
        text-align: center; padding: 10px; font-size: 0.75em;
        border-top: 1px solid #eaeaea; z-index: 999;
        font-family: sans-serif;
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    mercados = {
        "🇪🇸 ES":   {"gl": "ES", "hl": "es-419", "lang": "es"},
        "🇲🇦 MA":   {"gl": "MA", "hl": "fr",     "lang": "fr"}, 
        "🇳🇱 NL":   {"gl": "NL", "hl": "nl",     "lang": "nl"},
        "🇩🇪 DE":   {"gl": "DE", "hl": "de",     "lang": "de"},
        "🇫🇷 FR":   {"gl": "FR", "hl": "fr",     "lang": "fr"},
        "🇬🇧 UK":   {"gl": "GB", "hl": "en",     "lang": "en"}
    }

    fecha_limite = datetime.now() - timedelta(days=dias)
    lista_noticias = []
    
    progreso = st.progress(0)
    
    for i, (nombre_pais, params) in enumerate(mercados.items()):
        progreso.progress((i + 1) / len(mercados))
        try:
            query = tema
            if params['lang'] != 'es':
                query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
            
            q_enc = urllib.parse.quote(query) + (f"+when:{dias}d" if dias < 300 else "+when:1y")
            url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if dt >= fecha_limite:
                        tit_orig = limpiar_html(entry.title)
                        tit_es = tit_orig
                        if params['lang'] != 'es':
                            tit_es = GoogleTranslator(source=params['lang'], target='es').translate(tit_orig)
                        
                        lista_noticias.append({
                            "Market": nombre_pais,
                            "Source": entry.source.title,
                            "Date": dt, 
                            "Date_Str": dt.strftime("%Y-%m-%d"),
                            "Headline": tit_es,
                            "Link": entry.link
                        })
        except: continue
            
    progreso.empty()
    return pd.DataFrame(lista_noticias)

def generar_sitrep(df_noticias, tema, rol):
    if df_noticias.empty: return "No hay información disponible."
    
    raw_text = ""
    df_sorted = df_noticias.sort_values(by="Date", ascending=False)
    for _, row in df_sorted.head(70).iterrows(): 
        raw_text += f"- [{row['Market']}] {row['Source']}: {row['Headline']}\n"
    
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Eres un ANALISTA DE INTELIGENCIA ESTRATÉGICA (Senior).
    FECHA: {hoy}.
    FOCO: "{tema}"
    PERFIL: "{rol}"
    
    INTELIGENCIA BRUTA:
    {raw_text}
    
    INSTRUCCIONES:
    1. Genera un "ESTADO DE SITUACIÓN" (SITREP) en ESPAÑOL.
    2. Céntrate SOLO EN HECHOS ACTUALES y DINÁMICAS DE MERCADO.
    3. Cero consejos, cero predicciones.
    4. Cruza datos entre países.
    
    FORMATO:
    3 párrafos densos en información y análisis directo en ESPAÑOL.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

# --- 4. INTERFACE ---

# HEADER EN INGLÉS
st.title("Strategic Intel Board")
st.caption("Global Competitor & Market Monitoring Unit")
st.markdown("---")

with st.form("main_form"):
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    
    with c1:
        st.write("**1. Foco de Análisis**") # Español
        tema = st.text_area("Foco", value="Tomate Exportación", height=85, label_visibility="collapsed")
    
    with c2:
        st.write("**2. Perfil Estratégico**") # Español
        rol = st.text_area("Perfil", value="Productor Almería. Competencia Marruecos/Holanda.", height=85, label_visibility="collapsed")
        
    with c3:
        st.write("**3. Ventana**") # Español
        st.write("") 
        periodo_map = {
            "24 Horas": 1, 
            "7 Días": 7, 
            "30 Días": 30, 
            "Trimestre": 90, 
            "Semestre": 180, 
            "Anual": 365
        }
        periodo_sel = st.selectbox("Tiempo", list(periodo_map.keys()), index=2, label_visibility="collapsed")
        
    with c4:
        st.write("") 
        st.write("") 
        btn_run = st.form_submit_button("ANALIZAR", type="primary", use_container_width=True) # Español

dias = periodo_map[periodo_sel]

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error: Falta la API Key en el código.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        st.write("")
        
        # --- TOP SECTION ---
        col_datos, col_ia = st.columns([1, 2.5])
        
        with col_datos:
            st.markdown("### 📊 Señales") # Español
            conteo = df['Market'].value_counts().reset_index()
            conteo.columns = ['Mercado', 'Noticias']
            st.dataframe(conteo, hide_index=True, use_container_width=True)

        with col_ia:
            st.markdown("### ⚡ Estado de Situación") # Español
            with st.spinner("Generando SITREP..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        # --- NEWS FEED (CUSTOM LIST) ---
        st.markdown("---")
        
        # Desplegable en Español
        with st.expander("📂 Fuentes de Inteligencia (Clic para desplegar)", expanded=False):
            
            # Selector de Ordenación (Ya que no usamos tabla interactiva, lo hacemos manual)
            c_sort, _ = st.columns([1, 4])
            with c_sort:
                orden = st.radio("Ordenar por:", ["Fecha (Más reciente)", "País (A-Z)"], horizontal=True)
            
            if "Fecha" in orden:
                df_view = df.sort_values(by="Date", ascending=False)
            else:
                df_view = df.sort_values(by="Market", ascending=True)

            st.write("")
            
            # Renderizado como lista HTML limpia
            for index, row in df_view.iterrows():
                st.markdown(f"""
                <div class="news-container">
                    <div class="news-meta">
                        {row['Date_Str']} | {row['Market']} | <span class="news-source">{row['Source']}</span>
                    </div>
                    <a href="{row['Link']}" target="_blank" class="news-title">
                        {row['Headline']}
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
    else:
        st.info(f"Sin señales relevantes para el periodo: {periodo_sel}.")

# --- FOOTER EN INGLÉS ---
st.markdown("""
    <div class="custom-footer">
        Development & (c) Family Meeting Pérez-Mesa | Strategic Intelligence Unit
    </div>
""", unsafe_allow_html=True)





























