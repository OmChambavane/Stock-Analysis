import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, date
import feedparser
import urllib.parse

# --- Configuration ---
st.set_page_config(page_title="Indian Markets & Geopolitics Dashboard", layout="wide")

# Indian Major Indices
INDICES = {
    "NIFTY 50 (NSE)": "^NSEI",
    "SENSEX (BSE)": "^BSESN"
}

EVENT_START_DATE = "2022-02-24"

# --- Data Fetching Functions ---
@st.cache_data(ttl=300) 
def fetch_market_data(ticker, start_date):
    """Fetches historical data from Yahoo Finance."""
    data = yf.download(ticker, start=start_date, end=date.today().strftime("%Y-%m-%d"))
    return data

@st.cache_data(ttl=900) # Cache news for 15 minutes
def fetch_financial_news(query="Indian stock market geopolitical impact"):
    """Fetches recent news from Google News RSS focusing on major financial sources."""
    # We restrict the search to trusted financial domains
    advanced_query = f"{query} (site:moneycontrol.com OR site:cnbc.com OR site:cnn.com OR site:economictimes.indiatimes.com)"
    encoded_query = urllib.parse.quote(advanced_query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    feed = feedparser.parse(url)
    articles = []
    # Grab the top 8 recent articles
    for entry in feed.entries[:8]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return articles

# --- UI Layout ---
st.title("📊 Indian Markets Macro-Event Dashboard")
st.markdown(f"**Tracking the impact of geopolitical events on major Indian indices since: {EVENT_START_DATE}**")
st.write("---")

# Sidebar for controls
st.sidebar.header("Controls")
selected_index = st.sidebar.selectbox("Select Major Index", list(INDICES.keys()))
ticker_symbol = INDICES[selected_index]

# Fetch Data
with st.spinner("Fetching market & news data..."):
    df = fetch_market_data(ticker_symbol, EVENT_START_DATE)
    news_articles = fetch_financial_news()

if df.empty:
    st.error("Failed to fetch market data.")
else:
    # Create the main split layout: Left (Charts) - Right (Timeline & News)
    col_main, col_sidebar = st.columns([2.5, 1], gap="large")

    # ==========================================
    # LEFT COLUMN: Market Data & Charts
    # ==========================================
    with col_main:
        st.subheader(f"Current State: {selected_index}")
        
        # Flatten MultiIndex columns if yfinance returned them
        if isinstance(df.columns, pd.MultiIndex):
            df_flat = df.copy()
            df_flat.columns = df_flat.columns.droplevel(1)
        else:
            df_flat = df.copy()
            
        latest_data = df_flat.iloc[-1]
        prev_data = df_flat.iloc[-2]
        
        # Ensure we extract scalar values (floats) for Streamlit metrics
        current_price = float(latest_data['Close'])
        prev_price = float(prev_data['Close'])
        high_price = float(latest_data['High'])
        volume = float(latest_data['Volume'])

        price_change = current_price - prev_price
        pct_change = (price_change / prev_price) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Latest Close", f"₹{current_price:,.2f}", f"{price_change:,.2f} ({pct_change:.2f}%)")
        c2.metric("Today's High", f"₹{high_price:,.2f}")
        c3.metric("Trading Volume", f"{volume:,.0f}")
        
        # Candlestick Chart
        st.write("---")
        st.subheader("Market Progression Since Event Start")
        fig = go.Figure(data=[go.Candlestick(x=df_flat.index,
                            open=df_flat['Open'], high=df_flat['High'],
                            low=df_flat['Low'], close=df_flat['Close'],
                            name="Market Data")])

        fig.add_vline(x=datetime.strptime(EVENT_START_DATE, "%Y-%m-%d").timestamp() * 1000, 
                      line_dash="dash", line_color="red", 
                      annotation_text="Event Start", annotation_position="top right")

        fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # Trend Analysis
        st.write("---")
        df_flat['50_MA'] = df_flat['Close'].rolling(window=50).mean()
        df_flat['200_MA'] = df_flat['Close'].rolling(window=200).mean()
        
        latest_50_ma = float(df_flat['50_MA'].iloc[-1])
        latest_200_ma = float(df_flat['200_MA'].iloc[-1])
        
        if latest_50_ma > latest_200_ma:
            st.success(f"🟢 **Bullish Trend (Golden Cross)**: 50-Day MA (₹{latest_50_ma:,.2f}) > 200-Day MA (₹{latest_200_ma:,.2f})")
        elif latest_50_ma < latest_200_ma:
            st.error(f"🔴 **Bearish Trend (Death Cross)**: 50-Day MA (₹{latest_50_ma:,.2f}) < 200-Day MA (₹{latest_200_ma:,.2f})")
        else:
            st.warning("🟡 **Neutral / Consolidating**")

    # ==========================================
    # RIGHT COLUMN: News & Daily Impact Timeline
    # ==========================================
    with col_sidebar:
        # 1. Financial News Aggregator
        st.subheader("📰 Live Global Headlines")
        st.caption("Sourced from CNN, CNBC, MoneyControl")
        
        if news_articles:
            for article in news_articles:
                with st.expander(article["title"][:75] + "..."):
                    st.write(f"*{article['published']}*")
                    st.markdown(f"[Read full article here]({article['link']})")
        else:
            st.write("No recent news found.")
            
        st.write("---")
        
        # 2. Daily Impact Timeline (Last 10 Days)
        st.subheader("📅 Recent Daily Impact")
        st.caption("How the market reacted day-by-day recently:")
        
        # Calculate daily percentage change
        df_flat['Daily_Pct_Change'] = df_flat['Close'].pct_change() * 100
        
        # Get the last 10 trading days, sort descending (newest first)
        recent_timeline = df_flat.tail(10).sort_index(ascending=False)
        
        for date_index, row in recent_timeline.iterrows():
            date_str = date_index.strftime('%b %d, %Y')
            pct = float(row['Daily_Pct_Change'])
            
            if pd.isna(pct):
                continue
                
            # Determine color and icon based on severity of market move
            if pct <= -1.5:
                icon, color = "🚨", "red"
                sentiment = "Severe Sell-off"
            elif pct < 0:
                icon, color = "📉", "orange"
                sentiment = "Negative"
            elif pct >= 1.5:
                icon, color = "🚀", "green"
                sentiment = "Strong Rally"
            elif pct > 0:
                icon, color = "📈", "green"
                sentiment = "Positive"
            else:
                icon, color = "➖", "gray"
                sentiment = "Flat"
                
            st.markdown(f"**{date_str}**")
            st.markdown(f"{icon} :{color}[{pct:+.2f}%] - *{sentiment}*")
            st.write("")
