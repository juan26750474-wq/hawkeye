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

# ⚠️ TU CLAVE AQUÍ
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E"

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
        border-top: 4px solid #2c3e50;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        font-family: 'Georgia', serif;
        margin-bottom: 30px;
    }
    .ia-report h3 { 
        color: #2c3e50; 
        font-family: 'Segoe UI', sans-serif;
        font-size: 1.1em; 
        text-transform: uppercase; 
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
        margin-top: 20px;
    }
    
    /* Footer */
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #ffffff; color: #888;
        text-align: center; padding: 8px; font-size: 0.75em;
        border-top: 1px solid #eee; z-index: 999;
    }
    
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
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
    for _, row in df_sorted.head(50).iterrows():
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"
    
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Actúa como ANALISTA DE INTELIGENCIA (SITREP MILITAR/ECONÓMICO).
    FECHA: {hoy}.
    OBJETIVO: "{tema}"
    PERFIL: "{rol}"
    
    INTELIGENCIA BRUTA:
    {raw_text}
    
    INSTRUCCIONES:
    1. CERO Consejos vacíos ("ahorre", "vigile"). Céntrate en CAUSA -> CONSECUENCIA.
    2. Identifica PATRONES (Si Alemania y Holanda dicen lo mismo, es tendencia confirmada).
    3. Estilo telegráfico y directivo.
    
    FORMATO SITREP:
    
    ### ⚡ Estado de Situación
    (Dinámica actual del mercado: Alcista/Bajista/Volátil. Cita fuentes).
    
    ### 📅 Proyecciones Tácticas & Estratégicas
    
    **Corto Plazo (Inmediato)**
    * **Dinámica:** [Análisis]
    * **Trigger:** [Hecho noticioso clave]
    
    **Medio Plazo (Tendencia)**
    * **Escenario Base:** [Proyección]
    * **Riesgos:** [Regulación/Clima]
    
    ### 🛑 Amenazas Críticas
    (Solo si existen peligros reales detectados).
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
    c1, c2, c3, c4 = st.columns([2, 4, 1.5, 1.5])
    
    with c1:
        st.write("**Foco**")
        tema = st.text_input("Tema", value="Tomate Exportación", label_visibility="collapsed")
    
    with c2:
        st.write("**Perfil**")
        rol = st.text_input("Rol", value="Productor Almería. Busco ventanas de precio.", label_visibility="collapsed")
        
    with c3:
        st.write("**Ventana**")
        periodo_map = {"24 Horas": 1, "7 Días": 7, "30 Días": 30, "Trimestre": 90}
        periodo_sel = st.selectbox("Tiempo", list(periodo_map.keys()), index=2, label_visibility="collapsed")
        
    with c4:
        st.write("") 
        st.write("") 
        btn_run = st.form_submit_button("🔎 ANALIZAR", type="primary", use_container_width=True)

dias = periodo_map[periodo_sel]

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Configura la API KEY.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        st.write("")
        
        # --- TOP: DATOS CRUDOS SIMPLES ---
        c_left, c_right = st.columns([1, 3])
        
        with c_left:
            st.subheader("📊 Distribución")
            # Tabla simple de conteo por país
            conteo = df['pais'].value_counts().reset_index()
            conteo.columns = ['Mercado', 'Noticias']
            st.dataframe(conteo, hide_index=True, use_container_width=True)

        with c_right:
            st.subheader("🧠 SITREP (Reporte de Situación)")
            with st.spinner("Procesando inteligencia..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        # --- FOOTER: TABLA PRINCIPAL ---
        st.subheader("📂 Fuentes de Inteligencia")
        
        st.dataframe(
            df[['fecha_str', 'pais', 'fuente', 'titulo_es', 'link']],
            column_config={
                "fecha_str": st.column_config.TextColumn("Fecha", width="small"),
                "pais": st.column_config.TextColumn("Mercado", width="small"),
                "fuente": st.column_config.TextColumn("Medio", width="medium"),
                # AQUÍ ESTÁ EL CAMBIO: Ancho grande para leer bien
                "titulo_es": st.column_config.TextColumn("Titular Detectado", width="large"), 
                # AQUÍ ESTÁ EL CAMBIO: Solo dice "Leer"
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

























