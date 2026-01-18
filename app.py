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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="FAMILY MEETING", layout="wide", page_icon="🏛️")

# ⚠️ PON AQUÍ TU API KEY
GEMINI_API_KEY = "AIzaSyAEwwwYurbGqNvgoNqfJ8cXU_BAXYA9wyU"

if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error de API: {e}")

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* TÍTULO PRINCIPAL: FAMILY MEETING */
    .main-title {
        font-family: 'Cinzel', serif; /* Fuente clásica y elegante */
        color: #1a1a1a;
        text-align: center;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0px;
        letter-spacing: 2px;
        text-transform: uppercase;
        border-bottom: 3px solid #bfa15f; /* Línea dorada sutil */
        padding-bottom: 15px;
    }
    .sub-title {
        text-align: center;
        color: #666;
        font-size: 1rem;
        margin-top: -10px;
        margin-bottom: 30px;
        font-style: italic;
    }
    
    /* Informe estilo SITREP */
    .ia-report {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 4px;
        border-top: 5px solid #004488;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        font-family: 'Segoe UI', sans-serif;
        font-size: 1.05em;
        line-height: 1.6;
        color: #333;
    }
    
    /* Inputs */
    .stTextArea textarea {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
    }
    
    /* Footer */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #f1f1f1; color: #555;
        text-align: center; padding: 10px; font-size: 0.8em;
        border-top: 1px solid #ddd; z-index: 999;
    }
    
    .block-container { padding-top: 2rem; padding-bottom: 6rem; }
</style>
""", unsafe_allow_html=True)

# --- 3. LÓGICA ---

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
            
            # Ajuste de búsqueda para periodos largos (when:1y cubre hasta el año)
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
    if df_noticias.empty: return "Sin inteligencia disponible."
    
    raw_text = ""
    # Leemos hasta 70 noticias si el periodo es largo para tener buena base
    df_sorted = df_noticias.sort_values(by="fecha", ascending=False)
    for _, row in df_sorted.head(70).iterrows(): 
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"
    
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Actúa como ANALISTA DE INTELIGENCIA DE NEGOCIO (Family Office).
    FECHA ACTUAL: {hoy}.
    
    FOCO DE ANÁLISIS: "{tema}"
    PERFIL DEL GRUPO: "{rol}"
    
    INTELIGENCIA OBTENIDA (NOTICIAS):
    {raw_text}
    
    INSTRUCCIONES ESTRATÉGICAS:
    1. Genera un "ESTADO DE SITUACIÓN" (SITREP) puro.
    2. CERO paja, CERO consejos obvios, CERO proyecciones inventadas.
    3. Describe la realidad actual del mercado basándote estrictamente en los hechos leídos.
    4. Cruza datos: Si Marruecos baja producción y Holanda sube precios, esa es la noticia clave.
    
    FORMATO DE SALIDA:
    Redacta 3 párrafos densos y directos con la situación actual, mencionando explícitamente qué medios o países reportan los hechos clave.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en Análisis: {str(e)}"

# --- 4. INTERFAZ ---

# Cabecera Personalizada
st.markdown('<div class="main-title">FAMILY MEETING</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Unidad de Inteligencia y Estrategia</div>', unsafe_allow_html=True)

with st.form("main_form"):
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    
    with c1:
        st.write("**1. Foco de Interés**")
        tema = st.text_area("Foco", value="Tomate Exportación", height=85, label_visibility="collapsed")
    
    with c2:
        st.write("**2. Perfil Estratégico**")
        rol = st.text_area("Perfil", value="Productor Almería. Análisis de competencia Marruecos/Holanda.", height=85, label_visibility="collapsed")
        
    with c3:
        st.write("**3. Horizonte**")
        st.write("") 
        # Nuevas opciones de tiempo añadidas
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
        btn_run = st.form_submit_button("EJECUTAR", type="primary", use_container_width=True)

dias = periodo_map[periodo_sel]

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error: Introduce tu nueva API KEY en el código.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        st.write("")
        
        col_datos, col_ia = st.columns([1, 2.5])
        
        with col_datos:
            st.markdown("### 📊 Señales Detectadas")
            conteo = df['pais'].value_counts().reset_index()
            conteo.columns = ['Mercado', 'Noticias']
            st.dataframe(conteo, hide_index=True, use_container_width=True)
            st.caption(f"Total procesado: {len(df)} inputs")

        with col_ia:
            st.markdown("### ⚡ Estado de Situación")
            with st.spinner("Analizando inteligencia..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        st.markdown("### 📂 Fuentes de Verificación")
        st.dataframe(
            df[['fecha_str', 'pais', 'fuente', 'titulo_es', 'link']],
            column_config={
                "fecha_str": st.column_config.TextColumn("Fecha", width="small"),
                "pais": st.column_config.TextColumn("Origen", width="small"),
                "fuente": st.column_config.TextColumn("Medio", width="medium"),
                "titulo_es": st.column_config.TextColumn("Titular Detectado", width="large"), 
                "link": st.column_config.LinkColumn("Ref", display_text="Leer") 
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(f"Sin actividad relevante en el periodo seleccionado ({periodo_sel}).")

# --- FOOTER ---
st.markdown("""
    <div class="custom-footer">
        Desarrollo y (c) Family Meeting Pérez-Mesa
    </div>
""", unsafe_allow_html=True)


























