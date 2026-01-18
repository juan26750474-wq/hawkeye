import streamlit as st
import feedparser
import google.generativeai as genai
import urllib.parse
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from time import mktime
import html
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Inteligencia Estratégica", layout="centered")

# ⚠️ PON AQUÍ TU API KEY
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E" 

# Configuración API Google
if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error configuración API: {e}")

# --- 2. ESTILOS (Más profesional/sobrio) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .caja-noticia {
        padding: 10px;
        margin-bottom: 10px;
        border-left: 3px solid #ddd;
        background-color: #f9f9f9;
    }
    .fuente { font-size: 0.85em; color: #666; font-weight: bold;}
    .fecha { font-size: 0.85em; color: #888; }
    
    .informe-ia {
        background-color: #f0f7ff; /* Azul muy suave */
        padding: 30px;
        border-radius: 10px;
        border: 1px solid #cce5ff;
        margin-bottom: 30px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .titulo-informe {
        color: #004085;
        font-size: 1.3em;
        font-weight: bold;
        margin-bottom: 15px;
        border-bottom: 2px solid #b8daff;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIÓN DE INTELIGENCIA (El cerebro) ---
def consultar_gemini_estrategico(lista_noticias, tema, rol_usuario):
    if not lista_noticias:
        return "No hay suficientes datos para generar inteligencia."

    # Preparamos el "paquete de información" para la IA
    datos_contexto = ""
    # Leemos hasta 25 noticias para tener contexto
    for n in lista_noticias[:25]:
        datos_contexto += f"- [{n['pais']}] {n['fecha_str']}: {n['titulo']}\n"

    # PROMPT DINÁMICO (Aquí está la magia)
    prompt = f"""
    Actúa como un CONSULTOR ESTRATÉGICO DE ALTO NIVEL.
    
    1. PERFIL DEL USUARIO (CLIENTE): "{rol_usuario}"
    2. TEMA DE INVESTIGACIÓN: "{tema}"
    
    DATOS DE MERCADO (Noticias recientes detectadas):
    {datos_contexto}
    
    TU OBJETIVO:
    Analiza esta información EXCLUSIVAMENTE para ayudar al usuario en su rol. 
    No hagas un resumen genérico. Cruza los datos para darle valor.
    
    ESTRUCTURA DEL INFORME:
    1. **Situación Actual:** ¿Qué está pasando realmente en el mercado/tema?
    2. **Impacto en el Usuario:** Basado en su perfil ({rol_usuario}), ¿cómo le afecta esto (precios, riesgos, oportunidades)?
    3. **Señales de Alerta:** ¿Qué movimientos de la competencia o regulaciones se detectan en las noticias?
    4. **Recomendación Estratégica:** ¿Qué debería hacer el usuario ahora mismo?
    
    Usa un tono profesional, directo y orientado a negocio.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ No se pudo generar el informe: {str(e)}"

# Funciones auxiliares
def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

# --- 4. INTERFAZ DE USUARIO ---

st.title("🛡️ Panel de Inteligencia Estratégica")
st.caption("Monitorización de Competencia y Mercados (Multi-idioma)")

with st.form("form_estrategia"):
    # Campo 1: El Tema
    tema = st.text_input("📍 Tema / Competencia / Producto:", placeholder="Ej: Tomate Marruecos, Energía Fotovoltaica, Ford...")
    
    # Campo 2: El ROL (Nuevo y Crucial)
    rol = st.text_area("👤 Tu Contexto / Objetivo (Para enfocar el análisis):", 
                       placeholder="Ej: Soy un productor de tomate en Almería. Me preocupa la competencia de terceros países y quiero prever la tendencia de precios para la próxima campaña.",
                       height=80)
    
    col1, col2 = st.columns(2)
    with col1:
        periodo = st.selectbox("Ventana de Tiempo:", ["24 Horas", "7 Días", "30 Días", "1 Año"])
    with col2:
        st.write("") # Espaciador
        btn_analizar = st.form_submit_button("🔎 GENERAR INFORME ESTRATÉGICO", type="primary")

if btn_analizar and tema and rol:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Falta API KEY.")
        st.stop()
        
    with st.status("📡 Recopilando inteligencia de fuentes abiertas...", expanded=True) as status:
        
        todas_noticias = []
        
        # Configuración de mercados a vigilar (Añadido Marruecos 'MA' por el ejemplo agrícola)
        mercados = {
            "España 🇪🇸": {"gl": "ES", "hl": "es-419", "lang": "es"},
            "EEUU 🇺🇸":   {"gl": "US", "hl": "en-US",  "lang": "en"},
            "Reino Unido 🇬🇧": {"gl": "GB", "hl": "en-GB", "lang": "en"},
            "Francia 🇫🇷": {"gl": "FR", "hl": "fr-FR",  "lang": "fr"},
            "Alemania 🇩🇪": {"gl": "DE", "hl": "de-DE",  "lang": "de"},
            "Marruecos 🇲🇦": {"gl": "MA", "hl": "fr",     "lang": "fr"}, # Útil para agro
        }

        # Calcular fechas
        dias = 1
        if periodo == "7 Días": dias = 7
        elif periodo == "30 Días": dias = 30
        elif periodo == "1 Año": dias = 365
        
        fecha_limite = datetime.now() - timedelta(days=dias)

        # Bucle de búsqueda
        for nombre_mercado, params in mercados.items():
            st.write(f"🔍 Auditando prensa en {nombre_mercado}...")
            
            try:
                # 1. Traducir búsqueda al idioma del país
                query = tema
                if params['lang'] != 'es':
                    query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
                
                # 2. Construir URL Google News
                q_encoded = urllib.parse.quote(query)
                if dias == 365: q_encoded += "+when:1y"
                
                url = f"https://news.google.com/rss/search?q={q_encoded}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
                
                # 3. Descargar y procesar
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        if dt >= fecha_limite:
                            try:
                                titulo_orig = limpiar_texto(entry.title)
                                
                                # Traducir titular a Español para que lo leas tú y la IA
                                titulo_es = titulo_orig
                                if params['lang'] != 'es':
                                    titulo_es = GoogleTranslator(source=params['lang'], target='es').translate(titulo_orig)

                                todas_noticias.append({
                                    "titulo": titulo_es,
                                    "orig": titulo_orig,
                                    "fuente": entry.source.title,
                                    "pais": nombre_mercado,
                                    "fecha": dt,
                                    "fecha_str": dt.strftime("%d/%m/%Y"),
                                    "link": entry.link
                                })
                            except: pass
            except: pass
        
        status.update(label="✅ Inteligencia Generada", state="complete", expanded=False)

    # --- RESULTADOS ---
    if todas_noticias:
        # Ordenar por fecha reciente
        todas_noticias.sort(key=lambda x: x['fecha'], reverse=True)
        
        # 1. EL INFORME (Lo más importante arriba)
        st.markdown(f"""
        <div class="informe-ia">
            <div class="titulo-informe">🤖 Informe para: {rol}</div>
            {consultar_gemini_estrategico(todas_noticias, tema, rol)}
            <br>
            <small style="color:#666"><i>Análisis generado procesando {len(todas_noticias)} noticias en {len(mercados)} mercados.</i></small>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. LAS FUENTES (Abajo como anexo)
        with st.expander(f"📚 Ver las {len(todas_noticias)} noticias analizadas (Fuentes)", expanded=False):
            for n in todas_noticias:
                st.markdown(f"""
                <div class="caja-noticia">
                    <strong>{n['titulo']}</strong><br>
                    <span class="fecha">{n['pais']} | {n['fecha_str']} | {n['fuente']}</span>
                    <br><a href="{n['link']}" target="_blank" style="text-decoration:none; font-size:0.8em;">🔗 Leer original</a>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No se encontró información relevante para los parámetros indicados.")

elif btn_analizar:
    st.warning("Por favor, rellena tanto el TEMA como tu ROL/OBJETIVO.")




















