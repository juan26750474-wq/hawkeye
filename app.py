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
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="📡")

# ⚠️⚠️⚠️ PON TU CLAVE AQUÍ ⚠️⚠️⚠️
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E"

if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error de API: {e}")

# --- 2. ESTILOS ---
st.markdown("""
<style>
    /* Tarjetas de métricas */
    .metric-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        background-color: white;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-number { font-size: 28px; font-weight: bold; color: #0066cc; }
    .metric-label { font-size: 14px; color: #666; font-weight: 500; text-transform: uppercase; }
    
    /* Informe IA */
    .ia-report {
        background-color: #f8f9fa;
        padding: 30px;
        border-radius: 10px;
        border-left: 5px solid #0066cc;
        margin-top: 20px;
        margin-bottom: 30px;
        font-family: 'Segoe UI', sans-serif;
    }
    .ia-report h3 { color: #004488; margin-top: 20px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
    .ia-report strong { color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    # Configuración de mercados
    mercados = {
        "🇪🇸 España":   {"gl": "ES", "hl": "es-419", "lang": "es"},
        "🇲🇦 Marruecos": {"gl": "MA", "hl": "fr",     "lang": "fr"}, 
        "🇳🇱 Holanda":   {"gl": "NL", "hl": "nl",     "lang": "nl"},
        "🇩🇪 Alemania":  {"gl": "DE", "hl": "de",     "lang": "de"},
        "🇫🇷 Francia":   {"gl": "FR", "hl": "fr",     "lang": "fr"},
        "🇬🇧 UK/Intl":   {"gl": "GB", "hl": "en",     "lang": "en"}
    }

    fecha_limite = datetime.now() - timedelta(days=dias)
    lista_noticias = []
    
    # Elementos de UI para el progreso
    progreso_texto = st.empty()
    barra_progreso = st.progress(0)
    total_mercados = len(mercados)
    
    for i, (nombre_pais, params) in enumerate(mercados.items()):
        progreso_texto.text(f"📡 Escaneando fuentes en {nombre_pais}...")
        barra_progreso.progress((i + 1) / total_mercados)
        
        try:
            # 1. Traducir búsqueda
            query = tema
            if params['lang'] != 'es':
                query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
            
            # 2. Construir URL
            q_enc = urllib.parse.quote(query) + (f"+when:{dias}d" if dias < 300 else "+when:1y")
            url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if dt >= fecha_limite:
                        tit_orig = limpiar_html(entry.title)
                        tit_es = tit_orig
                        # Traducir titular si no es español
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
        except Exception:
            continue
            
    progreso_texto.empty()
    barra_progreso.empty()
    return pd.DataFrame(lista_noticias)

def consultar_cerebro_digital(df_noticias, tema, rol):
    if df_noticias.empty: return "No hay datos para analizar."

    # Contexto para la IA (limitado a 40 titulares para eficiencia)
    raw_text = ""
    for _, row in df_noticias.head(40).iterrows():
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"

    prompt = f"""
    Actúa como un CONSULTOR DE ESTRATEGIA DE NEGOCIO Senior.
    
    PERFIL DEL CLIENTE: "{rol}"
    TEMA: "{tema}"
    
    NOTICIAS RECIENTES:
    {raw_text}
    
    ---
    INSTRUCCIONES: Genera un informe ejecutivo para la toma de decisiones.
    NO inventes datos. Usa solo las noticias proporcionadas.
    
    ESTRUCTURA DEL INFORME:
    
    ### ⚡ Situación Actual
    (Resumen breve de qué está pasando en los mercados analizados).
    
    ### 📅 Horizontes de Decisión
    
    **1. Corto Plazo (Acción Inmediata)**
    * **Recomendación:** [Acción concreta]
    * **Motivo:** (Cita qué medio o país reporta el dato clave).
    
    **2. Medio Plazo (Próximos meses)**
    * **Tendencia:** (¿Precios/Situación al alza o baja?)
    * **Alerta:** (Riesgos regulatorios o de competencia).
    
    **3. Largo Plazo (Estrategia)**
    * **Visión:** Cambios estructurales.
    
    ### 🎯 Conclusión Ejecutiva
    (Una sola frase final de consejo).
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

# --- 4. INTERFAZ ---

st.title("🛡️ Centro de Inteligencia Competitiva")
st.markdown("Monitorización estratégica de mercados internacionales.")

# --- BARRA LATERAL (CORREGIDA) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # IMPORTANTE: Todo input que afecte al botón debe ir dentro del form
    with st.form("formulario_inteligencia"):
        st.subheader("1. Objetivo")
        tema = st.text_input("Tema / Producto", value="Tomate")
        
        st.subheader("2. Tu Perfil")
        rol = st.text_area("Contexto para la IA", 
                           value="Soy exportador agrícola en Almería. Quiero saber si Marruecos tiene problemas de cosecha para decidir mis precios.",
                           height=120)
        
        st.subheader("3. Periodo")
        periodo_map = {"24 Horas": 1, "3 Días": 3, "7 Días": 7, "30 Días": 30}
        periodo_sel = st.selectbox("Ventana de análisis", list(periodo_map.keys()), index=2)
        
        # Botón DENTRO del formulario
        btn_run = st.form_submit_button("🚀 EJECUTAR INTELIGENCIA", type="primary")

    # Variable dias fuera del form para usarla después
    dias = periodo_map[periodo_sel]

# --- LÓGICA PRINCIPAL ---

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error: Configura la API KEY en el código.")
        st.stop()

    # 1. Obtención de datos
    df = obtener_noticias(tema, dias)

    if not df.empty:
        # --- SECCIÓN A: MÉTRICAS (Datos Reales) ---
        st.markdown("### 📊 Radiografía de Fuentes")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="metric-container"><div class="metric-number">{len(df)}</div><div class="metric-label">Noticias</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="metric-container"><div class="metric-number">{df["pais"].nunique()}</div><div class="metric-label">Países</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="metric-container"><div class="metric-number">{df["fuente"].nunique()}</div><div class="metric-label">Medios</div></div>', unsafe_allow_html=True)
        
        with col4:
            st.caption("Distribución")
            st.bar_chart(df['pais'].value_counts(), color="#0066cc", height=80)

        # --- SECCIÓN B: INFORME IA ---
        st.markdown("---")
        st.subheader("🧠 Informe de Decisión")
        
        with st.spinner("Analizando implicaciones estratégicas..."):
            analisis = consultar_cerebro_digital(df, tema, rol)
            
        st.markdown(f'<div class="ia-report">{analisis}</div>', unsafe_allow_html=True)

        # --- SECCIÓN C: EVIDENCIAS ---
        with st.expander("📂 Ver Tabla de Fuentes Originales", expanded=True):
            st.dataframe(
                df[['fecha_str', 'pais', 'fuente', 'titulo_es', 'link']],
                column_config={
                    "link": st.column_config.LinkColumn("Enlace"),
                    "titulo_es": "Titular (Traducido)"
                },
                use_container_width=True,
                hide_index=True
            )

    else:
        st.warning(f"No se encontraron noticias recientes sobre '{tema}'. Intenta ampliar el periodo o cambiar el término.")






















