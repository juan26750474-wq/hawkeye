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

# --- 2. MODERN CSS STYLES ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* Modern SITREP Report Box */
    .ia-report {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 8px;
        border-top: 4px solid #0056b3; /* Corporate Blue */
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        font-size: 1.05em;
        line-height: 1.6;
        color: #2c3e50;
    }
    .ia-report strong { color: #0056b3; font-weight: 600; }
    
    /* Inputs styling */
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
    }
    
    /* Custom Table Styling for readability */
    .news-row {
        padding: 15px 0;
        border-bottom: 1px solid #eee;
    }
    .news-headline {
        font-size: 1.1em;
        font-weight: 500;
        color: #2c3e50;
        line-height: 1.4;
    }
    .news-meta { font-size: 0.85em; color: #7f8c8d; }
    .news-link a { 
        color: #0056b3; 
        text-decoration: none; 
        font-weight: bold; 
        border: 1px solid #0056b3; 
        padding: 4px 10px; 
        border-radius: 4px;
    }
    .news-link a:hover { background-color: #0056b3; color: white; }
    
    /* Footer */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #ffffff; color: #95a5a6;
        text-align: center; padding: 12px; font-size: 0.8em;
        border-top: 1px solid #eaeaea; z-index: 999;
        letter-spacing: 0.5px;
    }
    
    .block-container { padding-top: 2rem; padding-bottom: 6rem; }
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
                            "pais": nombre_pais,
                            "fuente": entry.source.title,
                            "fecha": dt,
                            "fecha_str": dt.strftime("%Y-%m-%d"),
                            "titulo_es": tit_es,
                            "link": entry.link
                        })
        except: continue
            
    progreso.empty()
    return pd.DataFrame(lista_noticias)

def generar_sitrep(df_noticias, tema, rol):
    if df_noticias.empty: return "No intelligence data available."
    
    raw_text = ""
    df_sorted = df_noticias.sort_values(by="fecha", ascending=False)
    for _, row in df_sorted.head(70).iterrows(): 
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"
    
    hoy = datetime.now().strftime("%B %d, %Y")

    prompt = f"""
    ACT AS: Senior Business Intelligence Analyst.
    DATE: {hoy}.
    FOCUS: "{tema}"
    PROFILE: "{rol}"
    
    RAW INTEL (NEWS):
    {raw_text}
    
    INSTRUCTIONS:
    1. Generate a pure "SITUATION REPORT" (SITREP).
    2. FOCUS ONLY ON CURRENT FACTS & MARKET DYNAMICS. No predictions, no advice, no future threats.
    3. Cross-reference data between countries (e.g., "While NL supply tightens, MA export volumes increase...").
    4. Style: Dense, direct, professional English.
    
    OUTPUT FORMAT:
    Provide 3 solid paragraphs summarizing the current market reality based *strictly* on the provided news.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analysis Error: {str(e)}"

# --- 4. INTERFACE ---

st.title("🛡️ Strategic Intel Board")
st.caption("Global Competitor & Market Monitoring Unit")
st.markdown("---")

with st.form("main_form"):
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    
    with c1:
        st.write("**1. Focus Area**")
        tema = st.text_area("Focus", value="Tomate Exportación", height=85, label_visibility="collapsed")
    
    with c2:
        st.write("**2. Strategic Profile**")
        rol = st.text_area("Profile", value="Productor Almería. Competencia Marruecos/Holanda.", height=85, label_visibility="collapsed")
        
    with c3:
        st.write("**3. Timeframe**")
        st.write("") 
        periodo_map = {
            "24 Hours": 1, 
            "7 Days": 7, 
            "30 Days": 30, 
            "90 Days (Quarter)": 90, 
            "180 Days (Semester)": 180, 
            "365 Days (Year)": 365
        }
        periodo_sel = st.selectbox("Time", list(periodo_map.keys()), index=2, label_visibility="collapsed")
        
    with c4:
        st.write("") 
        st.write("") 
        btn_run = st.form_submit_button("RUN INTEL", type="primary", use_container_width=True)

dias = periodo_map[periodo_sel]

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Config Error: Please add your API Key to the code.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        st.write("")
        
        # --- TOP SECTION ---
        col_datos, col_ia = st.columns([1, 2.5])
        
        with col_datos:
            st.markdown("### 📊 Signal Volume")
            conteo = df['pais'].value_counts().reset_index()
            conteo.columns = ['Market', 'Signals']
            st.dataframe(conteo, hide_index=True, use_container_width=True)
            st.caption(f"Total processed: {len(df)} inputs")

        with col_ia:
            st.markdown("### ⚡ Situation Report (SITREP)")
            with st.spinner("Synthesizing intelligence..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        # --- CUSTOM READABLE TABLE SECTION ---
        st.markdown("---")
        st.markdown("### 📂 Source Intelligence Feed")
        st.caption("Verified inputs used for analysis.")
        st.write("")

        # Custom Header
        h1, h2, h3, h4 = st.columns([1, 1, 4, 1])
        h1.markdown("**Date / Market**")
        h2.markdown("**Source**")
        h3.markdown("**Headline Detected**")
        h4.markdown("**Reference**")
        st.divider()

        # Custom Data Rows (Allows full vertical reading)
        df_sorted = df.sort_values(by="fecha", ascending=False)
        for index, row in df_sorted.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 1, 4, 1])
                
                with c1:
                    st.markdown(f"<div class='news-meta'>📅 {row['fecha_str']}<br>📍 {row['pais']}</div>", unsafe_allow_html=True)
                with c2:
                     st.markdown(f"<div class='news-meta'>📰 {row['fuente']}</div>", unsafe_allow_html=True)
                with c3:
                    # Headline gets full space to wrap
                    st.markdown(f"<div class='news-headline'>{row['titulo_es']}</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<div class='news-link'><a href='{row['link']}' target='_blank'>Read Source</a></div>", unsafe_allow_html=True)
                
                st.markdown("<div class='news-row'></div>", unsafe_allow_html=True) # Spacer line

    else:
        st.info(f"No relevant intelligence signals detected for the selected period ({periodo_sel}).")

# --- FOOTER ---
st.markdown("""
    <div class="custom-footer">
        Development & (c) Family Meeting Pérez-Mesa | Strategic Intelligence Unit
    </div>
""", unsafe_allow_html=True)



























