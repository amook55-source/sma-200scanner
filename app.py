import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(
    page_title="Escáner SMA 200",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Escáner Bursátil - Proximidad a la Media de 200 Días")
st.markdown("Analiza en tiempo real qué acciones del S&P 500 cotizan más cerca de su media móvil de 200 períodos.")

@st.cache_data(ttl=3600)
def obtener_tickers_sp500():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        df = tables[0]
        return df['Symbol'].str.replace('.', '-', regex=False).tolist()
    except Exception:
        return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "V"]

@st.cache_data(ttl=18000)
def descargar_y_calcular_sma(tickers):
    batch_size = 100
    resultados = []
    
    for i in range(0, len(tickers), batch_size):
        lote = tickers[i:i + batch_size]
        try:
            data = yf.download(tickers=lote, period="1y", group_by='ticker', threads=True, progress=False)
            for ticker in lote:
                try:
                    df_ticker = data[ticker] if len(lote) > 1 else data
                    df_clean = df_ticker['Close'].dropna()
                    
                    if len(df_clean) >= 200:
                        sma200_series = df_clean.rolling(window=200).mean()
                        precio_actual = float(df_clean.iloc[-1])
                        sma200_actual = float(sma200_series.iloc[-1])
                        
                        distancia_pct = abs((precio_actual - sma200_actual) / sma200_actual) * 100
                        
                        if distancia_pct <= 25.0:
                            posicion = "ABOVE" if precio_actual >= sma200_actual else "BELOW"
                            resultados.append({
                                "Ticker": ticker,
                                "Precio Cierre ($)": round(precio_actual, 2),
                                "SMA 200 ($)": round(sma200_actual, 2),
                                "Distancia (%)": round(distancia_pct, 2),
                                "Posición": posicion
                            })
                except Exception:
                    continue
        except Exception:
            continue
            
    return pd.DataFrame(resultados)

# --- BARRA LATERAL ---
st.sidebar.header("🔍 Filtros")

rango_distancia = st.sidebar.slider(
    "Rango de Distancia a la SMA 200 (%)",
    min_value=0.0,
    max_value=25.0,
    value=(0.0, 5.0),
    step=0.5
)

posicion_filtro = st.sidebar.radio(
    "Posición respecto a la Media",
    ["Todas", "Por Encima (ABOVE)", "Por Debajo (BELOW)"]
)

# --- EJECUCIÓN ---
with st.spinner("Descargando y analizando acciones en tiempo real..."):
    tickers = obtener_tickers_sp500()
    df_todos = descargar_y_calcular_sma(tickers)

if not df_todos.empty:
    # Filtrar según controles
    mask = (df_todos["Distancia (%)"] >= rango_distancia[0]) & (df_todos["Distancia (%)"] <= rango_distancia[1])
    if posicion_filtro == "Por Encima (ABOVE)":
        mask = mask & (df_todos["Posición"] == "ABOVE")
    elif posicion_filtro == "Por Debajo (BELOW)":
        mask = mask & (df_todos["Posición"] == "BELOW")
        
    df_res = df_todos[mask].sort_values(by="Distancia (%)", ascending=True)

    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Acciones Encontradas", len(df_res))
    col2.metric("Más Cercana", df_res.iloc[0]['Ticker'] if not df_res.empty else "N/A")
    col3.metric("Distancia Mínima", f"{df_res.iloc[0]['Distancia (%)']}%" if not df_res.empty else "N/A")

    st.markdown("---")

    col_tabla, col_grafico = st.columns([1.2, 1])

    with col_tabla:
        st.subheader("📋 Lista Ordenada (Menor a Mayor Distancia)")
        st.dataframe(df_res, use_container_width=True, hide_index=True, height=450)

    with col_grafico:
        st.subheader("📊 Gráfico Interactivo")
        if not df_res.empty:
            ticker_sel = st.selectbox("Selecciona un Ticker:", df_res['Ticker'].tolist())
            if ticker_sel:
                stock = yf.Ticker(ticker_sel)
                hist = stock.history(period="1y")
                if not hist.empty:
                    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Cierre', line=dict(color='#1f77b4')))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], mode='lines', name='SMA 200', line=dict(color='#ff7f0e', width=2)))
                    fig.update_layout(title=f"{ticker_sel} vs SMA 200", template="plotly_dark", height=380, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No se pudieron obtener datos del mercado en este momento.")
