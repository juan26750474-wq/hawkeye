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
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="🛡️")

# ⚠️ PON AQUÍ TU NUEVA API KEY (La antigua está bloqueada)
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
    
    /* Informe estilo SITREP */
    .ia-report {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 4px;
        border-top: 5px solid #004488; /* Azul corporativo fuerte */
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 30px;
        font-size: 1.05em;
        line-height: 1.6;
    }
    .ia-report strong { color: #004488; }
    
    /* Ajuste de inputs para que se vean modernos */
    .stTextArea textarea {
        background-color: #f9f9f9;
        border: 1px solid #ddd;
    }

    /* Footer */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #ffffff; color: #888;
        text-align: center; padding: 8px; font-size: 0.75em;
        border-top: 1px solid #eee; z-index: 999;
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
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
    df_sorted = df_noticias.sort_values(by="fecha", ascending=False)
    for _, row in df_sorted.head(60).iterrows(): # Leemos más noticias
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"
    
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Actúa como ANALISTA DE INTELIGENCIA ESTRATÉGICA.
    FECHA: {hoy}.
    
    OBJETIVO: "{tema}"
    PERFIL: "{rol}"
    
    DATOS BRUTOS:
    {raw_text}
    
    INSTRUCCIONES:
    1. Genera UNICAMENTE un "ESTADO DE SITUACIÓN" (Situation Report).
    2. NO incluyas proyecciones futuras, ni consejos, ni secciones de amenazas.
    3. Céntrate en describir la REALIDAD ACTUAL del mercado cruzando los datos de los diferentes países.
    4. Estilo periodístico/analítico de alto nivel. Denso en información, cero paja.
    
    FORMATO:
    Redacta un análisis fluido de 2 o 3 párrafos potentes que integren:
    - Movimientos de precios o volúmenes actuales.
    - Situación en mercados de origen (competencia) vs destino.
    - Factores climáticos o logísticos activos AHORA mismo.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error SITREP: {str(e)}"

# --- 4. INTERFAZ ---

st.title("🛡️ Strategic Intel Board")

with st.form("main_form"):
    # Columnas ajustadas para dar espacio a los text_area
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    
    with c1:
        st.write("**1. Foco**")
        # height=85 da espacio para 3 lineas cómodas
        tema = st.text_area("Foco", value="Tomate Exportación", height=85, label_visibility="collapsed")
    
    with c2:
        st.write("**2. Perfil Estratégico**")
        rol = st.text_area("Perfil", value="Productor Almería. Busco analizar competencia en Marruecos y Holanda.", height=85, label_visibility="collapsed")
        
    with c3:
        st.write("**3. Ventana**")
        # Usamos un espacio vacío arriba para alinear el selectbox con los text area visualmente
        st.write("") 
        periodo_map = {"24 Horas": 1, "7 Días": 7, "30 Días": 30, "Trimestre": 90}
        periodo_sel = st.selectbox("Tiempo", list(periodo_map.keys()), index=2, label_visibility="collapsed")
        
    with c4:
        st.write("") 
        st.write("") 
        # Botón grande
        btn_run = st.form_submit_button("🔎 ANALIZAR", type="primary", use_container_width=True)

dias = periodo_map[periodo_sel]

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error: Necesitas poner la NUEVA API Key en el código.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        st.write("")
        
        # --- ESTRUCTURA: DATOS IZQ | ANÁLISIS DCHA ---
        col_datos, col_ia = st.columns([1, 2.5])
        
        with col_datos:
            st.markdown("### 📊 Datos")
            # Tabla simple de conteo
            conteo = df['pais'].value_counts().reset_index()
            conteo.columns = ['Mercado', 'Noticias']
            st.dataframe(conteo, hide_index=True, use_container_width=True)
            
            st.info(f"Total: {len(df)} señales")

        with col_ia:
            st.markdown("### ⚡ Estado de Situación")
            with st.spinner("Sintetizando inteligencia de mercado..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        # --- TABLA INFERIOR ---
        st.markdown("### 📂 Fuentes Confirmadas")
        
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
        st.info(f"Sin actividad relevante sobre '{tema}' en el periodo seleccionado.")

# --- FOOTER ---
st.markdown("""
    <div class="custom-footer">
        Desarrollo y (c) Family Meeting Pérez-Mesa
    </div>
""", unsafe_allow_html=True)


























