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
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="🛡️")

# --- GESTIÓN DE SECRETOS (SEGURIDAD) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("⚠️ Error Crítico: No se encontró el archivo de secretos (.streamlit/secrets.toml).")
    st.stop()
except KeyError:
    st.error("⚠️ Error Crítico: La clave 'GEMINI_API_KEY' no está definida en los secretos.")
    st.stop()

# Configuración de Google Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Error al configurar la API de Gemini: {e}")
    st.stop()

# --- 2. CSS & DESIGN ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* CABECERA ESTILO DASHBOARD */
    .header-container {
        display: flex;
        align-items: center;
        background: linear-gradient(90deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .logo-img {
        font-size: 3rem;
        margin-right: 20px;
    }
    .header-text h1 {
        margin: 0;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
        font-size: 2rem;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .header-text p {
        margin: 5px 0 0 0;
        font-size: 0.9rem;
        color: #a8c0ff;
        font-weight: 300;
    }

    /* CAJA SITREP */
    .ia-report {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 8px;
        border-left: 6px solid #2c5364;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        font-family: 'Segoe UI', sans-serif;
        font-size: 1rem;
        line-height: 1.6;
        color: #333;
        margin-bottom: 20px;
    }
    
    /* FOOTER */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #f8f9fa; color: #6c757d;
        text-align: center; padding: 12px; font-size: 0.75em;
        border-top: 1px solid #e9ecef; z-index: 999;
        font-family: monospace;
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }

    /* TOOLTIP HELP */
    .help-icon {
        cursor: help;
        color: #2c5364;
        font-size: 0.9rem;
        margin-left: 5px;
    }
</style>

<div style="position: fixed; top: 0; left: 0; width: 100%; padding: 5px 15px; z-index: 999999; font-size: 10px; color: #888; font-family: sans-serif; background-color: rgba(255,255,255,0.8); pointer-events: none;">
    Desarrollo Family Meeting Pérez-Mesa (c)
</div>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    # He incluido 'ar' (árabe) para el mercado de Marruecos
    mercados = {
        "🇪🇸 ES":   {"gl": "ES", "hl": "es-419", "lang": "es"},
        "🇲🇦 MA":   {"gl": "MA", "hl": "ar",      "lang": "ar"}, 
        "🇳🇱 NL":   {"gl": "NL", "hl": "nl",      "lang": "nl"},
        "🇩🇪 DE":   {"gl": "DE", "hl": "de",      "lang": "de"},
        "🇫🇷 FR":   {"gl": "FR", "hl": "fr",      "lang": "fr"},
        "🇬🇧 UK":   {"gl": "GB", "hl": "en",      "lang": "en"}
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
                            # Usamos 'auto' para asegurar que detecte el árabe u otros correctamente al traducir de vuelta
                            tit_es = GoogleTranslator(source='auto', target='es').translate(tit_orig)
                        
                        lista_noticias.append({
                            "Mercado": nombre_pais,
                            "Fuente": entry.source.title,
                            "Fecha": dt, 
                            "Fecha_Texto": dt.strftime("%Y-%m-%d"),
                            "Titular": tit_es,
                            "Link": entry.link
                        })
        except: continue
            
    progreso.empty()
    return pd.DataFrame(lista_noticias)

def generar_sitrep(df_noticias, tema, rol):
    if df_noticias.empty: return "Sin datos para generar informe."
    
    raw_text = ""
    df_sorted = df_noticias.sort_values(by="Fecha", ascending=False)
    for _, row in df_sorted.head(70).iterrows(): 
        raw_text += f"- [{row['Mercado']}] {row['Fuente']}: {row['Titular']}\n"
    
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Eres ANALISTA DE INTELIGENCIA ESTRATÉGICA.
    FECHA: {hoy}.
    FOCO: "{tema}"
    PERFIL: "{rol}"
    
    NOTICIAS:
    {raw_text}
    
    INSTRUCCIONES:
    1. Redacta un SITREP (Informe de Situación) en ESPAÑOL.
    2. Estilo ejecutivo, directo y basado puramente en los hechos recientes.
    3. Cruza información de orígenes y destinos.
    4. Sólo hacer análisis de situación. No hacer recomendaciones.
    5. Filtra las noticias para  hacer informe, si se te pide información de países y temas concretos no des información superflua.
    
    SALIDA:
    3 párrafos de análisis de alto nivel.
    4. Nombra las fuentes en las que te basas para opinar sobre un asunto.
    5. Si se es capaz, enlazar fuente con el link de la noticia. 
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

# --- 4. INTERFACE ---

st.markdown("""
<div class="header-container">
    <div class="logo-img">🛡️</div>
    <div class="header-text">
        <h1>STRATEGIC INTEL BOARD</h1>
        <p>Global Competitor & Market Monitoring Unit</p>
    </div>
</div>
""", unsafe_allow_html=True)

with st.form("main_form"):
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    
    with c1:
        st.markdown('**1. Foco de Análisis** <span class="help-icon" title=\'Palabra exacta: "Tomate cherry"\nOperador OR: Tomate OR Pepino\nExcluir palabras: Tomate -subasta\'>ℹ️</span>', unsafe_allow_html=True)
        tema = st.text_area("Foco", value="Tomate Exportación", height=85, label_visibility="collapsed")
    
    with c2:
        st.write("**2. Perfil Estratégico**")
        rol = st.text_area("Perfil", value="Productor Almería. Competencia Marruecos/Holanda.", height=85, label_visibility="collapsed")
        
    with c3:
        st.write("**3. Ventana**")
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
        btn_run = st.form_submit_button("ANALIZAR", type="primary", use_container_width=True)

dias = periodo_map[periodo_sel]

if btn_run:
    df = obtener_noticias(tema, dias)
    if not df.empty:
        st.write("")
        col_datos, col_ia = st.columns([1, 2.5])
        with col_datos:
            st.markdown("### 📊 Señales")
            conteo = df['Mercado'].value_counts().reset_index()
            conteo.columns = ['Mercado', 'Noticias']
            st.dataframe(conteo, hide_index=True, use_container_width=True)
        with col_ia:
            st.markdown("### ⚡ Estado de Situación")
            with st.spinner("Generando SITREP..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)
        st.markdown("---")
        with st.expander("📂 Fuentes de Inteligencia (Tabla)", expanded=True):
            st.dataframe(
                df[['Fecha', 'Mercado', 'Fuente', 'Titular', 'Link']],
                column_config={
                    "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", width="small"),
                    "Mercado": st.column_config.TextColumn("Mercado", width="small"),
                    "Fuente": st.column_config.TextColumn("Fuente", width="medium"),
                    "Titular": st.column_config.TextColumn("Titular", width="large"), 
                    "Link": st.column_config.LinkColumn("Ref", display_text="Leer")
                },
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info(f"Sin resultados para: {periodo_sel}.")

st.markdown("""
    <div class="custom-footer">
        Development & (c) Family Meeting Pérez-Mesa | Strategic Intelligence Unit
    </div>
""", unsafe_allow_html=True)






































