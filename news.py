import streamlit as st
import requests
import trafilatura
import yfinance as yf
from ddgs import DDGS
import os
import time
from urllib.parse import urlparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# ---------------- CONFIG ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

BLOCKED_DOMAINS = (
    "globeandmail.com",
    "seekingalpha.com",
    "benzinga.com",
    "wsj.com",
    "ft.com",
)

# Australian Stock Exchanges
ASX_SUFFIX = ".AX"  # Australian Securities Exchange

# Top Australian Stocks
TOP_AU_STOCKS = ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", 
                 "ANZ.AX", "WES.AX", "MQG.AX", "WOW.AX", "FMG.AX"]

# ---------------- CUSTOM CSS ----------------
def load_custom_css():
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Questrial&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    
    <style>
        /* Base Styles */
        * {
            font-family: 'Questrial', sans-serif !important;
        }
        
        :root {
            --primary-bg: #FBFEF9;
            --primary-blue: #0C6291;
            --primary-dark: #000004;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .main {
            background-color: var(--primary-bg);
            padding: 0;
        }
        
        /* Hero Banner */
        .hero-banner {
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #0C6291 0%, #000004 100%);
            margin: -5rem -5rem 0 -5rem;
            position: relative;
            overflow: hidden;
        }
        
        .hero-banner::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(251,254,249,0.1) 1px, transparent 1px);
            background-size: 30px 30px;
            animation: drift 60s linear infinite;
        }
        
        @keyframes drift {
            0% { transform: translate(0, 0); }
            100% { transform: translate(30px, 30px); }
        }
        
        .hero-title {
            font-size: 8rem;
            color: var(--primary-bg);
            font-weight: 400;
            letter-spacing: 0.2em;
            text-align: center;
            z-index: 10;
            position: relative;
            text-shadow: 0 0 80px rgba(251,254,249,0.5);
            animation: fadeInScale 1.5s ease-out;
        }
        
        @keyframes fadeInScale {
            0% {
                opacity: 0;
                transform: scale(0.8);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        /* Dashboard Section */
        .dashboard-section {
            padding: 4rem 2rem;
            background-color: var(--primary-bg);
        }
        
        .section-title {
            font-size: 2.5rem;
            color: var(--primary-dark);
            margin-bottom: 2rem;
            text-align: center;
            letter-spacing: 0.05em;
        }
        
        /* Pill Inputs and Buttons */
        .stTextInput input {
            border-radius: 50px !important;
            border: 2px solid var(--primary-blue) !important;
            padding: 0.75rem 1.5rem !important;
            font-size: 1rem !important;
            background-color: white !important;
            color: var(--primary-dark) !important;
            transition: all 0.3s ease;
        }
        
        .stTextInput input:focus {
            box-shadow: 0 0 0 3px rgba(12, 98, 145, 0.2) !important;
            border-color: var(--primary-blue) !important;
        }
        
        .stButton button {
            border-radius: 50px !important;
            background-color: var(--primary-blue) !important;
            color: var(--primary-bg) !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            letter-spacing: 0.05em;
        }
        
        .stButton button:hover {
            background-color: var(--primary-dark) !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,4,0.3) !important;
        }
        
        /* Floating Toolbar */
        .floating-toolbar {
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            border-radius: 50px;
            padding: 1rem 2rem;
            box-shadow: 0 10px 40px rgba(0,0,4,0.2);
            display: flex;
            align-items: center;
            gap: 1rem;
            z-index: 1000;
            border: 2px solid var(--primary-blue);
        }
        
        /* Cards */
        .metric-card {
            background: white;
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,4,0.08);
            border: 1px solid rgba(12, 98, 145, 0.1);
            transition: all 0.3s ease;
            margin-bottom: 1rem;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,4,0.15);
        }
        
        .metric-label {
            color: var(--primary-blue);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            color: var(--primary-dark);
            font-size: 2rem;
            font-weight: 500;
        }
        
        /* Stock Analysis Page */
        .analysis-header {
            background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 25px;
            margin-bottom: 2rem;
        }
        
        .stock-name {
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        
        .company-name {
            font-size: 1.5rem;
            opacity: 0.9;
        }
        
        /* Recommendation Badge */
        .recommendation-badge {
            display: inline-block;
            padding: 1rem 2.5rem;
            border-radius: 50px;
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: 0.05em;
            margin: 1rem 0;
        }
        
        .rec-buy {
            background: linear-gradient(135deg, #00C851 0%, #007E33 100%);
            color: white;
        }
        
        .rec-sell {
            background: linear-gradient(135deg, #ff4444 0%, #CC0000 100%);
            color: white;
        }
        
        .rec-hold {
            background: linear-gradient(135deg, #ffbb33 0%, #FF8800 100%);
            color: white;
        }
        
        /* Chart Containers */
        .chart-container {
            background: white;
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,4,0.08);
            margin-bottom: 1.5rem;
        }
        
        .chart-title {
            color: var(--primary-blue);
            font-size: 1.2rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Expandable Section */
        .expandable-section {
            margin-top: 2rem;
            text-align: center;
        }
        
        /* Alert Boxes */
        .alert-box {
            border-radius: 15px;
            padding: 1rem 1.5rem;
            margin: 1rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .alert-warning {
            background: rgba(255, 193, 7, 0.1);
            border-left: 4px solid #FFC107;
            color: #856404;
        }
        
        .alert-info {
            background: rgba(12, 98, 145, 0.1);
            border-left: 4px solid var(--primary-blue);
            color: var(--primary-blue);
        }
        
        /* Progress Indicators */
        .progress-bar {
            height: 8px;
            background: rgba(12, 98, 145, 0.2);
            border-radius: 10px;
            overflow: hidden;
            margin: 1rem 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-blue) 0%, var(--primary-dark) 100%);
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        
        /* Stat Grid */
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        /* Hide default streamlit elements */
        .stSpinner > div {
            border-top-color: var(--primary-blue) !important;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 20px 20px 0 0;
            padding: 1rem 2rem;
            background-color: transparent;
            border: none;
            color: var(--primary-dark);
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-blue);
            color: white;
        }
        
        /* Number input styling */
        .stNumberInput input {
            border-radius: 50px !important;
            border: 2px solid var(--primary-blue) !important;
            padding: 0.75rem 1.5rem !important;
        }
        
        /* Selectbox styling */
        .stSelectbox select {
            border-radius: 50px !important;
            border: 2px solid var(--primary-blue) !important;
            padding: 0.75rem 1.5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ---------------- HELPER FUNCTIONS ----------------

def search_news(query, max_results=50):
    """Search for recent news articles"""
    links = []
    with DDGS() as ddgs:
        for r in ddgs.news(query, max_results=max_results):
            url = r.get("url")
            date = r.get("date")
            if url and url not in links:
                links.append({"url": url, "date": date})
    
    # Sort by date (most recent first)
    links.sort(key=lambda x: x.get("date", ""), reverse=True)
    return links


def is_blocked_domain(url):
    """Check if domain is blocked"""
    domain = urlparse(url).netloc.lower()
    return any(bad in domain for bad in BLOCKED_DOMAINS)


def crawl_article(url):
    """Extract article text from URL"""
    try:
        if is_blocked_domain(url):
            return None

        resp = requests.get(url, headers=HEADERS, timeout=20)

        if resp.status_code != 200 or len(resp.text) < 2000:
            return None

        text = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=False
        )

        if text and len(text.strip()) > 300:
            return text.strip()

        return None

    except Exception:
        return None


def format_ticker_for_australia(ticker):
    """Format ticker for Australian market"""
    ticker = ticker.strip().upper()
    if not ticker.endswith(".AX"):
        ticker = f"{ticker}.AX"
    return ticker


def get_stock_info(ticker):
    """Get comprehensive stock information"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        if hist.empty:
            return None
        
        current_price = round(float(hist["Close"].iloc[-1]), 2)
        
        return {
            "ticker": ticker,
            "company_name": info.get("longName", ticker),
            "current_price": current_price,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "dividend_yield": info.get("dividendYield", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "volume": info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "history": hist
        }
    except Exception as e:
        st.error(f"Error fetching stock info: {str(e)}")
        return None


def calculate_volatility(history):
    """Calculate price volatility"""
    returns = history['Close'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(252) * 100  # Annualized
    return round(volatility, 2)


def calculate_trend(history, days=7):
    """Calculate price trend over period"""
    if len(history) < days:
        return 0
    
    start_price = history['Close'].iloc[-days]
    end_price = history['Close'].iloc[-1]
    change = ((end_price - start_price) / start_price) * 100
    return round(change, 2)


def analyze_with_groq(news_articles, stock_info, user_position=None):
    """Enhanced AI analysis with historical context"""
    
    # Prepare historical price context
    hist = stock_info["history"]
    recent_prices = hist.tail(30)
    
    price_context = f"""
Recent 30-day price data:
- Current: ${stock_info['current_price']}
- 7-day change: {calculate_trend(hist, 7)}%
- 30-day change: {calculate_trend(hist, 30)}%
- Volatility: {calculate_volatility(hist)}%
- 52-week range: ${stock_info['52w_low']} - ${stock_info['52w_high']}
"""
    
    # Prepare news context
    news_text = "\n\n---\n\n".join([
        f"Article {i+1} (Date: {art['date']}):\n{art['content'][:1500]}"
        for i, art in enumerate(news_articles[:10])
    ])
    
    # User position context
    position_context = ""
    if user_position:
        purchase_price = user_position.get("price", 0)
        quantity = user_position.get("quantity", 0)
        current_value = stock_info['current_price'] * quantity
        purchase_value = purchase_price * quantity
        profit_loss = current_value - purchase_value
        profit_loss_pct = ((stock_info['current_price'] - purchase_price) / purchase_price) * 100
        
        position_context = f"""
USER POSITION:
- Purchased at: ${purchase_price}
- Quantity: {quantity}
- Current P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)
"""
    
    prompt = f"""
You are an expert financial analyst specializing in the Australian stock market.

STOCK: {stock_info['ticker']} - {stock_info['company_name']}
SECTOR: {stock_info['sector']}

{price_context}

{position_context}

RECENT NEWS ARTICLES (sorted by date, most recent first):
{news_text}

Based on the above information, provide a comprehensive analysis in the following format:

1. RECOMMENDATION: [BUY/SELL/HOLD/BUY MORE] - one word only
2. SENTIMENT: [Positive/Negative/Neutral]
3. PRICE JUSTIFICATION: Is the current price justified based on fundamentals and news? (2-3 sentences)
4. VALUATION: [Overvalued/Fairly Valued/Undervalued] - explain in 2 sentences
5. ACTIONABLE INSIGHTS: 3 specific bullet points
6. MAJOR NEWS HEADLINES: List 3-4 most important news items affecting the stock
7. VOLATILITY ALERT: Any unusual price movements? (1 sentence)
8. MARKET COMPARISON: How is this stock performing relative to its sector? (1 sentence)
9. SENTIMENT TREND: How has news sentiment changed over the past week? (1 sentence)
10. DETAILED JUSTIFICATION: A comprehensive 3-4 sentence explanation of your recommendation

Format your response clearly with these exact headings.
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=45
        )
        
        data = response.json()
        
        if "choices" not in data:
            return {
                "error": True,
                "message": f"API Error: {data}"
            }
        
        analysis_text = data["choices"][0]["message"]["content"]
        
        # Parse the response
        parsed = parse_analysis(analysis_text)
        return parsed
        
    except Exception as e:
        return {
            "error": True,
            "message": f"Analysis failed: {str(e)}"
        }


def parse_analysis(text):
    """Parse structured analysis from AI response"""
    lines = text.split('\n')
    result = {
        "recommendation": "",
        "sentiment": "",
        "price_justification": "",
        "valuation": "",
        "insights": [],
        "headlines": [],
        "volatility": "",
        "market_comparison": "",
        "sentiment_trend": "",
        "justification": ""
    }
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "RECOMMENDATION:" in line:
            result["recommendation"] = line.split("RECOMMENDATION:")[-1].strip()
        elif "SENTIMENT:" in line:
            result["sentiment"] = line.split("SENTIMENT:")[-1].strip()
        elif "PRICE JUSTIFICATION:" in line:
            current_section = "price_justification"
            content = line.split("PRICE JUSTIFICATION:")[-1].strip()
            if content:
                result["price_justification"] = content
        elif "VALUATION:" in line:
            current_section = "valuation"
            content = line.split("VALUATION:")[-1].strip()
            if content:
                result["valuation"] = content
        elif "ACTIONABLE INSIGHTS:" in line:
            current_section = "insights"
        elif "MAJOR NEWS HEADLINES:" in line:
            current_section = "headlines"
        elif "VOLATILITY ALERT:" in line:
            result["volatility"] = line.split("VOLATILITY ALERT:")[-1].strip()
        elif "MARKET COMPARISON:" in line:
            result["market_comparison"] = line.split("MARKET COMPARISON:")[-1].strip()
        elif "SENTIMENT TREND:" in line:
            result["sentiment_trend"] = line.split("SENTIMENT TREND:")[-1].strip()
        elif "DETAILED JUSTIFICATION:" in line:
            current_section = "justification"
            content = line.split("DETAILED JUSTIFICATION:")[-1].strip()
            if content:
                result["justification"] = content
        elif current_section == "insights" and (line.startswith("-") or line.startswith("*") or line.startswith("•")):
            result["insights"].append(line[1:].strip())
        elif current_section == "headlines" and (line.startswith("-") or line.startswith("*") or line.startswith("•")):
            result["headlines"].append(line[1:].strip())
        elif current_section in ["price_justification", "valuation", "justification"]:
            result[current_section] += " " + line
    
    return result


@st.cache_data(ttl=900)
def load_market_overview():
    """Load market overview data for Australian stocks"""
    data = {}
    for ticker in TOP_AU_STOCKS:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            if not hist.empty:
                data[ticker.replace(".AX", "")] = {
                    "history": hist,
                    "info": stock.info
                }
        except:
            continue
    return data


def get_top_movers(stock_data):
    """Get top gainers and losers"""
    movers = []
    for ticker, data in stock_data.items():
        hist = data["history"]
        if len(hist) >= 2:
            change = ((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2]) * 100
            movers.append({
                "ticker": ticker,
                "change": round(change, 2),
                "price": round(hist["Close"].iloc[-1], 2)
            })
    
    movers.sort(key=lambda x: x["change"], reverse=True)
    gainers = movers[:5]
    losers = movers[-5:]
    
    return gainers, losers


# ---------------- STREAMLIT APP ----------------

def main():
    st.set_page_config(
        page_title="Stockify - Australian Stock Analysis",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    load_custom_css()
    
    # Initialize session state
    if 'show_analysis' not in st.session_state:
        st.session_state.show_analysis = False
    if 'selected_ticker' not in st.session_state:
        st.session_state.selected_ticker = None
    if 'user_settings' not in st.session_state:
        st.session_state.user_settings = {
            "owns_stock": False,
            "purchase_price": 0,
            "quantity": 0
        }
    
    # Hero Banner
    st.markdown("""
        <div class="hero-banner">
            <h1 class="hero-title">STOCKIFY</h1>
        </div>
    """, unsafe_allow_html=True)
    
    # Dashboard Section
    if not st.session_state.show_analysis:
        st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
        
        st.markdown('<h2 class="section-title">Market Overview</h2>', unsafe_allow_html=True)
        
        # Load market data
        with st.spinner("Loading market data..."):
            stock_data = load_market_overview()
            gainers, losers = get_top_movers(stock_data)
        
        # Top Gainers and Losers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-arrow-up-circle-fill" style="color: #00C851;"></i> Top Gainers</div>', unsafe_allow_html=True)
            for g in gainers:
                st.markdown(f"""
                    <div class="metric-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.2rem; color: var(--primary-dark);">{g['ticker']}</span>
                            <span style="font-size: 1.5rem; color: #00C851; font-weight: 500;">+{g['change']}%</span>
                        </div>
                        <div style="color: var(--primary-blue); margin-top: 0.5rem;">${g['price']}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-arrow-down-circle-fill" style="color: #ff4444;"></i> Top Losers</div>', unsafe_allow_html=True)
            for l in losers:
                st.markdown(f"""
                    <div class="metric-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.2rem; color: var(--primary-dark);">{l['ticker']}</span>
                            <span style="font-size: 1.5rem; color: #ff4444; font-weight: 500;">{l['change']}%</span>
                        </div>
                        <div style="color: var(--primary-blue); margin-top: 0.5rem;">${l['price']}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Market Charts
        st.markdown('<h2 class="section-title" style="margin-top: 3rem;">Market Performance</h2>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Price Trends", "Trading Volume", "Comparative Analysis"])
        
        with tab1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-graph-up"></i> 6-Month Price Trends</div>', unsafe_allow_html=True)
            price_data = {k: v["history"]["Close"] for k, v in stock_data.items()}
            st.line_chart(price_data, height=400)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-bar-chart-fill"></i> Trading Volume</div>', unsafe_allow_html=True)
            volume_data = {k: v["history"]["Volume"] for k, v in stock_data.items()}
            st.area_chart(volume_data, height=400)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with tab3:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-columns-gap"></i> Top Stocks Comparison</div>', unsafe_allow_html=True)
            
            # Show top 5 stocks
            top_5 = list(stock_data.keys())[:5]
            comparison_data = {k: stock_data[k]["history"]["Close"] for k in top_5}
            st.line_chart(comparison_data, height=400)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Floating Toolbar
        st.markdown('<div style="height: 150px;"></div>', unsafe_allow_html=True)
        
        # Create toolbar at bottom
        toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([3, 1, 1])
        
        with toolbar_col1:
            ticker_input = st.text_input(
                "Search Stock",
                placeholder="Enter ticker (e.g., WOW, TLS, BHP)",
                label_visibility="collapsed",
                key="ticker_search"
            )
        
        with toolbar_col2:
            search_button = st.button("🔍 Analyze", use_container_width=True)
        
        with toolbar_col3:
            if st.button("⚙️ Settings", use_container_width=True):
                st.session_state.show_settings = not st.session_state.get('show_settings', False)
        
        # Settings Panel
        if st.session_state.get('show_settings', False):
            st.markdown("---")
            st.markdown("### Settings")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                owns_stock = st.checkbox(
                    "I already own this stock",
                    value=st.session_state.user_settings["owns_stock"]
                )
                st.session_state.user_settings["owns_stock"] = owns_stock
            
            if owns_stock:
                with col2:
                    purchase_price = st.number_input(
                        "Purchase Price ($)",
                        min_value=0.0,
                        value=st.session_state.user_settings["purchase_price"],
                        step=0.01
                    )
                    st.session_state.user_settings["purchase_price"] = purchase_price
                
                with col3:
                    quantity = st.number_input(
                        "Quantity",
                        min_value=0,
                        value=st.session_state.user_settings["quantity"],
                        step=1
                    )
                    st.session_state.user_settings["quantity"] = quantity
        
        # Handle search
        if search_button and ticker_input:
            st.session_state.selected_ticker = format_ticker_for_australia(ticker_input)
            st.session_state.show_analysis = True
            st.rerun()
    
    # Analysis Page
    else:
        ticker = st.session_state.selected_ticker
        
        # Back button
        if st.button("← Back to Dashboard"):
            st.session_state.show_analysis = False
            st.session_state.selected_ticker = None
            st.rerun()
        
        # Get stock info
        with st.spinner("Fetching stock data..."):
            stock_info = get_stock_info(ticker)
        
        if not stock_info:
            st.error("Could not fetch stock data. Please check the ticker symbol.")
            if st.button("Try Another Stock"):
                st.session_state.show_analysis = False
                st.rerun()
            st.stop()
        
        # Analysis Header
        st.markdown(f"""
            <div class="analysis-header">
                <div class="stock-name">{stock_info['ticker'].replace('.AX', '')}</div>
                <div class="company-name">{stock_info['company_name']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Key Stats Grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label"><i class="bi bi-cash-coin"></i> Current Price</div>
                    <div class="metric-value">${stock_info['current_price']}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label"><i class="bi bi-building"></i> Sector</div>
                    <div class="metric-value" style="font-size: 1.2rem;">{stock_info['sector']}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            pe_ratio = stock_info['pe_ratio']
            pe_display = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label"><i class="bi bi-graph-up-arrow"></i> P/E Ratio</div>
                    <div class="metric-value">{pe_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            market_cap_b = stock_info['market_cap'] / 1e9 if stock_info['market_cap'] else 0
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label"><i class="bi bi-pie-chart-fill"></i> Market Cap</div>
                    <div class="metric-value">${market_cap_b:.2f}B</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Additional Stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-graph-up"></i> Price Performance</div>', unsafe_allow_html=True)
            
            change_7d = calculate_trend(stock_info['history'], 7)
            change_30d = calculate_trend(stock_info['history'], 30)
            
            st.markdown(f"""
                <div style="padding: 1rem 0;">
                    <div style="margin-bottom: 1rem;">
                        <span style="color: var(--primary-blue);">7-Day Change:</span>
                        <span style="color: {'#00C851' if change_7d > 0 else '#ff4444'}; font-size: 1.3rem; font-weight: 500; margin-left: 1rem;">
                            {change_7d:+.2f}%
                        </span>
                    </div>
                    <div>
                        <span style="color: var(--primary-blue);">30-Day Change:</span>
                        <span style="color: {'#00C851' if change_30d > 0 else '#ff4444'}; font-size: 1.3rem; font-weight: 500; margin-left: 1rem;">
                            {change_30d:+.2f}%
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-speedometer2"></i> Volatility</div>', unsafe_allow_html=True)
            
            volatility = calculate_volatility(stock_info['history'])
            
            st.markdown(f"""
                <div style="padding: 1rem 0;">
                    <div style="font-size: 2rem; color: var(--primary-dark); font-weight: 500;">
                        {volatility}%
                    </div>
                    <div style="color: var(--primary-blue); margin-top: 0.5rem;">
                        Annualized Volatility
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown('<div class="chart-title"><i class="bi bi-arrow-down-up"></i> 52-Week Range</div>', unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="padding: 1rem 0;">
                    <div style="margin-bottom: 0.5rem;">
                        <span style="color: var(--primary-blue);">High:</span>
                        <span style="font-size: 1.3rem; margin-left: 1rem;">${stock_info['52w_high']:.2f}</span>
                    </div>
                    <div>
                        <span style="color: var(--primary-blue);">Low:</span>
                        <span style="font-size: 1.3rem; margin-left: 1rem;">${stock_info['52w_low']:.2f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Price Chart
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title"><i class="bi bi-graph-up"></i> Price History (1 Year)</div>', unsafe_allow_html=True)
        st.line_chart(stock_info['history']['Close'], height=300)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Fetch and analyze news
        st.markdown("---")
        st.markdown('<h2 class="section-title">AI-Powered Analysis</h2>', unsafe_allow_html=True)
        
        with st.spinner("Searching for recent news articles..."):
            news_links = search_news(ticker.replace(".AX", ""), max_results=50)
        
        if not news_links:
            st.warning("No recent news found for this stock.")
        else:
            # Crawl articles
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful_articles = []
            
            for idx, link_data in enumerate(news_links):
                if len(successful_articles) >= 10:
                    break
                
                status_text.text(f"Analyzing article {idx + 1}...")
                progress_bar.progress(min((idx + 1) / 15, 1.0))
                
                content = crawl_article(link_data["url"])
                
                if content:
                    successful_articles.append({
                        "url": link_data["url"],
                        "date": link_data.get("date", ""),
                        "content": content
                    })
                
                time.sleep(0.5)
            
            progress_bar.empty()
            status_text.empty()
            
            if not successful_articles:
                st.error("Could not extract content from any news source.")
            else:
                st.success(f"Successfully analyzed {len(successful_articles)} articles")
                
                # Analyze with AI
                if not GROQ_API_KEY:
                    st.error("GROQ_API_KEY not configured. Please set your API key.")
                else:
                    with st.spinner("Generating AI analysis..."):
                        user_position = None
                        if st.session_state.user_settings["owns_stock"]:
                            user_position = {
                                "price": st.session_state.user_settings["purchase_price"],
                                "quantity": st.session_state.user_settings["quantity"]
                            }
                        
                        analysis = analyze_with_groq(successful_articles, stock_info, user_position)
                    
                    if analysis.get("error"):
                        st.error(analysis["message"])
                    else:
                        # Display Recommendation
                        rec = analysis.get("recommendation", "HOLD").upper()
                        rec_class = "rec-buy" if "BUY" in rec else ("rec-sell" if "SELL" in rec else "rec-hold")
                        
                        st.markdown(f"""
                            <div style="text-align: center; margin: 2rem 0;">
                                <div class="recommendation-badge {rec_class}">
                                    <i class="bi bi-{'check-circle' if 'BUY' in rec else ('x-circle' if 'SELL' in rec else 'dash-circle')}"></i>
                                    {rec}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Analysis Details
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.markdown('<div class="chart-title"><i class="bi bi-emoji-smile"></i> Sentiment Analysis</div>', unsafe_allow_html=True)
                            sentiment = analysis.get("sentiment", "Neutral")
                            sentiment_color = "#00C851" if "Positive" in sentiment else ("#ff4444" if "Negative" in sentiment else "#ffbb33")
                            st.markdown(f"""
                                <div style="padding: 1rem; text-align: center;">
                                    <div style="font-size: 2rem; color: {sentiment_color}; font-weight: 500;">
                                        {sentiment}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            # Valuation
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.markdown('<div class="chart-title"><i class="bi bi-scale"></i> Valuation</div>', unsafe_allow_html=True)
                            st.markdown(f"<p style='line-height: 1.6;'>{analysis.get('valuation', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.markdown('<div class="chart-title"><i class="bi bi-cash-stack"></i> Price Justification</div>', unsafe_allow_html=True)
                            st.markdown(f"<p style='line-height: 1.6;'>{analysis.get('price_justification', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Advanced Metrics
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        st.markdown('<div class="chart-title"><i class="bi bi-speedometer"></i> Advanced Metrics</div>', unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if analysis.get("volatility"):
                                st.markdown(f"""
                                    <div class="alert-box alert-warning">
                                        <i class="bi bi-exclamation-triangle-fill" style="font-size: 1.5rem;"></i>
                                        <div>{analysis['volatility']}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                        
                        with col2:
                            if analysis.get("market_comparison"):
                                st.markdown(f"""
                                    <div class="alert-box alert-info">
                                        <i class="bi bi-bar-chart-line-fill" style="font-size: 1.5rem;"></i>
                                        <div>{analysis['market_comparison']}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                        
                        with col3:
                            if analysis.get("sentiment_trend"):
                                st.markdown(f"""
                                    <div class="alert-box alert-info">
                                        <i class="bi bi-graph-up-arrow" style="font-size: 1.5rem;"></i>
                                        <div>{analysis['sentiment_trend']}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Actionable Insights
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        st.markdown('<div class="chart-title"><i class="bi bi-lightbulb-fill"></i> Actionable Insights</div>', unsafe_allow_html=True)
                        
                        for insight in analysis.get("insights", []):
                            st.markdown(f"""
                                <div style="padding: 0.75rem; margin: 0.5rem 0; background: rgba(12, 98, 145, 0.05); border-left: 3px solid var(--primary-blue); border-radius: 5px;">
                                    <i class="bi bi-check2-circle" style="color: var(--primary-blue); margin-right: 0.5rem;"></i>
                                    {insight}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Major Headlines
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        st.markdown('<div class="chart-title"><i class="bi bi-newspaper"></i> Major News Headlines</div>', unsafe_allow_html=True)
                        
                        for headline in analysis.get("headlines", []):
                            st.markdown(f"""
                                <div style="padding: 0.75rem; margin: 0.5rem 0; border-bottom: 1px solid rgba(12, 98, 145, 0.1);">
                                    <i class="bi bi-dot" style="color: var(--primary-blue); margin-right: 0.5rem;"></i>
                                    {headline}
                                </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Detailed Justification
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        st.markdown('<div class="chart-title"><i class="bi bi-file-text-fill"></i> Detailed Analysis</div>', unsafe_allow_html=True)
                        st.markdown(f"<p style='line-height: 1.8; font-size: 1.05rem;'>{analysis.get('justification', 'N/A')}</p>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Show Analysis Button
                        st.markdown('<div class="expandable-section">', unsafe_allow_html=True)
                        
                        if st.button("📊 Show Detailed Article Analysis", use_container_width=False):
                            st.session_state.show_articles = not st.session_state.get('show_articles', False)
                        
                        if st.session_state.get('show_articles', False):
                            st.markdown("---")
                            st.markdown('<h3 style="color: var(--primary-blue); margin: 2rem 0;">Articles Analyzed</h3>', unsafe_allow_html=True)
                            
                            for idx, article in enumerate(successful_articles):
                                with st.expander(f"Article {idx + 1} - {article.get('date', 'Unknown date')}", expanded=False):
                                    st.markdown(f"**URL:** {article['url']}")
                                    st.markdown(f"**Date:** {article.get('date', 'N/A')}")
                                    st.markdown("**Content Preview:**")
                                    st.text(article['content'][:500] + "...")
                        
                        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
