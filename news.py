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

ASX_SUFFIX = ".AX"
TOP_AU_STOCKS = ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", 
                 "ANZ.AX", "WES.AX", "MQG.AX", "WOW.AX", "FMG.AX"]

# ---------------- MODERN CSS DESIGN ----------------
def load_custom_css():
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    
    <style>
        /* ===== RESET & BASE ===== */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0A0E27;
            --bg-secondary: #131829;
            --bg-tertiary: #1A1F3A;
            --accent-blue: #4F46E5;
            --accent-purple: #7C3AED;
            --accent-cyan: #06B6D4;
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
            --border: rgba(148, 163, 184, 0.1);
            --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.5);
            --gradient-primary: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            --gradient-secondary: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
        }
        
        /* ===== HIDE STREAMLIT ELEMENTS ===== */
        #MainMenu, footer, header, .stDeployButton {
            visibility: hidden;
            height: 0;
        }
        
        /* ===== BODY & MAIN ===== */
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
        }
        
        .main {
            background: var(--bg-primary);
            padding: 0;
        }
        
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        
        /* ===== NAVIGATION HEADER ===== */
        .nav-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 72px;
            background: rgba(10, 14, 39, 0.8);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
        }
        
        .nav-logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .nav-logo-icon {
            width: 40px;
            height: 40px;
            background: var(--gradient-primary);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .nav-logo-text {
            font-size: 1.5rem;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .nav-search {
            flex: 1;
            max-width: 500px;
            margin: 0 2rem;
        }
        
        .nav-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        /* ===== MAIN CONTENT AREA ===== */
        .content-wrapper {
            margin-top: 72px;
            padding: 2rem;
            min-height: calc(100vh - 72px);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* ===== HERO SECTION ===== */
        .hero {
            text-align: center;
            padding: 4rem 2rem;
            margin-bottom: 3rem;
        }
        
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
            line-height: 1.2;
        }
        
        .hero-subtitle {
            font-size: 1.25rem;
            color: var(--text-secondary);
            font-weight: 400;
        }
        
        /* ===== MARKET OVERVIEW CARDS ===== */
        .market-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        
        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
            border-color: var(--accent-blue);
        }
        
        .stat-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        
        .stat-card-label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .stat-card-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }
        
        .stat-card-icon.blue {
            background: rgba(79, 70, 229, 0.15);
            color: var(--accent-blue);
        }
        
        .stat-card-icon.green {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }
        
        .stat-card-icon.red {
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }
        
        .stat-card-value {
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        
        .stat-card-change {
            font-size: 0.875rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
        
        .stat-card-change.positive {
            color: var(--success);
        }
        
        .stat-card-change.negative {
            color: var(--danger);
        }
        
        /* ===== SECTION HEADERS ===== */
        .section {
            margin-bottom: 3rem;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
        }
        
        .section-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .section-action {
            font-size: 0.875rem;
            color: var(--accent-blue);
            text-decoration: none;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
        }
        
        .section-action:hover {
            color: var(--accent-cyan);
            transform: translateX(4px);
        }
        
        /* ===== STOCK CARDS GRID ===== */
        .stocks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }
        
        .stock-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .stock-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient-primary);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }
        
        .stock-card:hover {
            transform: translateY(-6px);
            box-shadow: var(--shadow-lg);
            border-color: var(--accent-blue);
        }
        
        .stock-card:hover::before {
            transform: scaleX(1);
        }
        
        .stock-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 1rem;
        }
        
        .stock-ticker {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }
        
        .stock-name {
            font-size: 0.875rem;
            color: var(--text-muted);
            font-weight: 500;
        }
        
        .stock-price {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }
        
        .stock-change {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .stock-change.positive {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }
        
        .stock-change.negative {
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }
        
        .stock-chart-mini {
            height: 60px;
            margin-top: 1rem;
            opacity: 0.7;
        }
        
        /* ===== CHART CARD ===== */
        .chart-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .chart-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2rem;
        }
        
        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .chart-controls {
            display: flex;
            gap: 0.5rem;
        }
        
        .chart-btn {
            padding: 0.5rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .chart-btn:hover,
        .chart-btn.active {
            background: var(--accent-blue);
            color: var(--text-primary);
            border-color: var(--accent-blue);
        }
        
        /* ===== ANALYSIS PAGE ===== */
        .analysis-header {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .analysis-stock-info {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .analysis-stock-icon {
            width: 80px;
            height: 80px;
            background: var(--gradient-primary);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            color: white;
        }
        
        .analysis-stock-details h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }
        
        .analysis-stock-details p {
            font-size: 1.125rem;
            color: var(--text-secondary);
        }
        
        .analysis-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 2rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
        }
        
        .metric {
            text-align: center;
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        /* ===== RECOMMENDATION BADGE ===== */
        .recommendation-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .recommendation-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 2.5rem;
            border-radius: 50px;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            margin-bottom: 1rem;
        }
        
        .recommendation-badge.buy {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 2px solid var(--success);
        }
        
        .recommendation-badge.sell {
            background: rgba(239, 68, 68, 0.2);
            color: var(--danger);
            border: 2px solid var(--danger);
        }
        
        .recommendation-badge.hold {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
            border: 2px solid var(--warning);
        }
        
        .recommendation-subtitle {
            font-size: 1rem;
            color: var(--text-secondary);
        }
        
        /* ===== ANALYSIS GRID ===== */
        .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .analysis-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
        }
        
        .analysis-card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .analysis-card-icon {
            width: 40px;
            height: 40px;
            background: rgba(79, 70, 229, 0.15);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-blue);
            font-size: 1.25rem;
        }
        
        .analysis-card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .analysis-card-content {
            color: var(--text-secondary);
            line-height: 1.7;
            font-size: 0.9375rem;
        }
        
        .insight-item {
            padding: 0.75rem;
            background: var(--bg-tertiary);
            border-left: 3px solid var(--accent-blue);
            border-radius: 4px;
            margin-bottom: 0.75rem;
            color: var(--text-secondary);
            font-size: 0.9375rem;
            line-height: 1.6;
        }
        
        .headline-item {
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.9375rem;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }
        
        .headline-item:last-child {
            border-bottom: none;
        }
        
        /* ===== SEARCH INPUT ===== */
        .stTextInput input {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 0.75rem 1rem !important;
            color: var(--text-primary) !important;
            font-size: 0.9375rem !important;
            transition: all 0.2s ease !important;
        }
        
        .stTextInput input:focus {
            border-color: var(--accent-blue) !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1) !important;
            outline: none !important;
        }
        
        .stTextInput input::placeholder {
            color: var(--text-muted) !important;
        }
        
        /* ===== BUTTONS ===== */
        .stButton button {
            background: var(--accent-blue) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 600 !important;
            font-size: 0.9375rem !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }
        
        .stButton button:hover {
            background: var(--accent-purple) !important;
            transform: translateY(-2px);
            box-shadow: var(--shadow-md) !important;
        }
        
        /* ===== BACK BUTTON ===== */
        .back-button {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 2rem;
            text-decoration: none;
        }
        
        .back-button:hover {
            background: var(--bg-tertiary);
            border-color: var(--accent-blue);
            transform: translateX(-4px);
        }
        
        /* ===== LOADING STATES ===== */
        .loading-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 3rem;
            text-align: center;
        }
        
        .loading-spinner {
            width: 48px;
            height: 48px;
            border: 4px solid var(--bg-tertiary);
            border-top-color: var(--accent-blue);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar {
            width: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--bg-tertiary);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-blue);
        }
        
        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            .nav-header {
                padding: 0 1rem;
            }
            
            .nav-search {
                display: none;
            }
            
            .content-wrapper {
                padding: 1rem;
            }
            
            .hero-title {
                font-size: 2.5rem;
            }
            
            .stocks-grid {
                grid-template-columns: 1fr;
            }
            
            .analysis-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* ===== ANIMATIONS ===== */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .fade-in {
            animation: fadeIn 0.5s ease-out;
        }
        
        /* ===== STREAMLIT OVERRIDES ===== */
        .element-container {
            margin: 0 !important;
        }
        
        div[data-testid="stVerticalBlock"] > div {
            gap: 0 !important;
        }
        
        /* ===== EXPANDER STYLING ===== */
        .streamlit-expanderHeader {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            color: var(--text-primary) !important;
            font-weight: 600 !important;
        }
        
        .streamlit-expanderContent {
            background: var(--bg-secondary) !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
            border-radius: 0 0 12px 12px !important;
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

        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
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
    volatility = returns.std() * np.sqrt(252) * 100
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
    hist = stock_info["history"]
    
    price_context = f"""
Recent 30-day price data:
- Current: ${stock_info['current_price']}
- 7-day change: {calculate_trend(hist, 7)}%
- 30-day change: {calculate_trend(hist, 30)}%
- Volatility: {calculate_volatility(hist)}%
- 52-week range: ${stock_info['52w_low']} - ${stock_info['52w_high']}
"""
    
    news_text = "\n\n---\n\n".join([
        f"Article {i+1} (Date: {art['date']}):\n{art['content'][:1500]}"
        for i, art in enumerate(news_articles[:10])
    ])
    
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

1. RECOMMENDATION: [BUY/SELL/HOLD] - one word only
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
        response = requests.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=45)
        data = response.json()
        
        if "choices" not in data:
            return {"error": True, "message": f"API Error: {data}"}
        
        analysis_text = data["choices"][0]["message"]["content"]
        parsed = parse_analysis(analysis_text)
        return parsed
        
    except Exception as e:
        return {"error": True, "message": f"Analysis failed: {str(e)}"}


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
            "purchase_price": 0.0,
            "quantity": 0
        }
    
    # Render navigation header
    render_nav_header()
    
    # Main content
    if not st.session_state.show_analysis:
        render_dashboard()
    else:
        render_analysis_page()


def render_nav_header():
    """Render the fixed navigation header"""
    st.markdown("""
        <div class="nav-header">
            <div class="nav-logo">
                <div class="nav-logo-icon">📊</div>
                <div class="nav-logo-text">STOCKIFY</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_dashboard():
    """Render the main dashboard"""
    
    st.markdown('<div class="content-wrapper"><div class="container">', unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
        <div class="hero">
            <h1 class="hero-title">Australian Stock Market Intelligence</h1>
            <p class="hero-subtitle">Real-time insights powered by AI</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Search Bar
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        ticker_input = st.text_input(
            "Search",
            placeholder="Enter ASX ticker (e.g., WOW, BHP, CBA)...",
            label_visibility="collapsed",
            key="ticker_search"
        )
        
        if ticker_input and len(ticker_input) > 0:
            if st.button("🔍 Analyze Stock", use_container_width=True):
                st.session_state.selected_ticker = format_ticker_for_australia(ticker_input)
                st.session_state.show_analysis = True
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Load market data
    with st.spinner("Loading market data..."):
        stock_data = load_market_overview()
        gainers, losers = get_top_movers(stock_data)
    
    # Market Overview Cards
    st.markdown('<div class="market-overview">', unsafe_allow_html=True)
    
    # Market Average
    avg_change = sum([g['change'] for g in gainers[:3]]) / 3 if gainers else 0
    change_class = "positive" if avg_change > 0 else "negative"
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-header">
                <span class="stat-card-label">Market Average</span>
                <div class="stat-card-icon blue">
                    <i class="bi bi-graph-up"></i>
                </div>
            </div>
            <div class="stat-card-value">{avg_change:+.2f}%</div>
            <div class="stat-card-change {change_class}">
                <i class="bi bi-arrow-{'up' if avg_change > 0 else 'down'}"></i>
                Today's Performance
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Top Gainer
    if gainers:
        top_gainer = gainers[0]
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-card-header">
                    <span class="stat-card-label">Top Gainer</span>
                    <div class="stat-card-icon green">
                        <i class="bi bi-arrow-up-circle-fill"></i>
                    </div>
                </div>
                <div class="stat-card-value">{top_gainer['ticker']}</div>
                <div class="stat-card-change positive">
                    <i class="bi bi-arrow-up"></i>
                    +{top_gainer['change']}% • ${top_gainer['price']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Top Loser
    if losers:
        top_loser = losers[-1]
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-card-header">
                    <span class="stat-card-label">Top Loser</span>
                    <div class="stat-card-icon red">
                        <i class="bi bi-arrow-down-circle-fill"></i>
                    </div>
                </div>
                <div class="stat-card-value">{top_loser['ticker']}</div>
                <div class="stat-card-change negative">
                    <i class="bi bi-arrow-down"></i>
                    {top_loser['change']}% • ${top_loser['price']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Tracked Stocks
    st.markdown(f"""
        <div class="stat-card">
            <div class="stat-card-header">
                <span class="stat-card-label">Tracked Stocks</span>
                <div class="stat-card-icon blue">
                    <i class="bi bi-building"></i>
                </div>
            </div>
            <div class="stat-card-value">{len(stock_data)}</div>
            <div class="stat-card-change">
                <i class="bi bi-check-circle"></i>
                Active Monitoring
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Price Trends Chart
    st.markdown("""
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Price Trends</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("""
        <div class="chart-card-header">
            <div class="chart-title">6-Month Performance</div>
        </div>
    """, unsafe_allow_html=True)
    
    price_data = {k: v["history"]["Close"] for k, v in stock_data.items()}
    st.line_chart(price_data, height=400)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stock Cards Section
    st.markdown("""
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">All Stocks</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="stocks-grid">', unsafe_allow_html=True)
    
    for ticker in stock_data.keys():
        data = stock_data[ticker]
        hist = data["history"]
        info = data["info"]
        
        current_price = hist["Close"].iloc[-1]
        change_30d = calculate_trend(hist, 30)
        change_class = "positive" if change_30d > 0 else "negative"
        arrow = "up" if change_30d > 0 else "down"
        
        company_name = info.get("longName", ticker)
        if len(company_name) > 30:
            company_name = company_name[:30] + "..."
        
        st.markdown(f"""
            <div class="stock-card fade-in" onclick="window.location.href='#'">
                <div class="stock-card-header">
                    <div>
                        <div class="stock-ticker">{ticker}</div>
                        <div class="stock-name">{company_name}</div>
                    </div>
                </div>
                <div class="stock-price">${current_price:.2f}</div>
                <div class="stock-change {change_class}">
                    <i class="bi bi-arrow-{arrow}"></i>
                    {change_30d:+.2f}% (30d)
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)


def render_analysis_page():
    """Render detailed stock analysis page"""
    
    ticker = st.session_state.selected_ticker
    
    st.markdown('<div class="content-wrapper"><div class="container">', unsafe_allow_html=True)
    
    # Back button
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.show_analysis = False
            st.session_state.selected_ticker = None
            st.rerun()
    
    # Get stock info
    with st.spinner("Fetching stock data..."):
        stock_info = get_stock_info(ticker)
    
    if not stock_info:
        st.error("Could not fetch stock data. Please check the ticker symbol.")
        st.stop()
    
    # Stock Header
    st.markdown(f"""
        <div class="analysis-header">
            <div class="analysis-stock-info">
                <div class="analysis-stock-icon">
                    📈
                </div>
                <div class="analysis-stock-details">
                    <h1>{stock_info['ticker'].replace('.AX', '')}</h1>
                    <p>{stock_info['company_name']}</p>
                </div>
            </div>
            
            <div class="analysis-metrics">
                <div class="metric">
                    <div class="metric-label">Current Price</div>
                    <div class="metric-value">${stock_info['current_price']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Market Cap</div>
                    <div class="metric-value">${stock_info['market_cap']/1e9:.2f}B</div>
                </div>
                <div class="metric">
                    <div class="metric-label">P/E Ratio</div>
                    <div class="metric-value">{stock_info['pe_ratio'] if isinstance(stock_info['pe_ratio'], (int, float)) else 'N/A'}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Sector</div>
                    <div class="metric-value" style="font-size: 1rem;">{stock_info['sector']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">7-Day Change</div>
                    <div class="metric-value" style="color: {'var(--success)' if calculate_trend(stock_info['history'], 7) > 0 else 'var(--danger)'}">{calculate_trend(stock_info['history'], 7):+.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Volatility</div>
                    <div class="metric-value">{calculate_volatility(stock_info['history'])}%</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Price Chart
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("""
        <div class="chart-card-header">
            <div class="chart-title">Price History (1 Year)</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.line_chart(stock_info['history']['Close'], height=400)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Fetch and analyze news
    st.markdown("""
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">AI-Powered Analysis</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.spinner("Searching for recent news articles..."):
        news_links = search_news(ticker.replace(".AX", ""), max_results=50)
    
    if news_links:
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
        
        if successful_articles and GROQ_API_KEY:
            with st.spinner("Generating AI analysis..."):
                user_position = None
                if st.session_state.user_settings["owns_stock"]:
                    user_position = {
                        "price": st.session_state.user_settings["purchase_price"],
                        "quantity": st.session_state.user_settings["quantity"]
                    }
                
                analysis = analyze_with_groq(successful_articles, stock_info, user_position)
            
            if not analysis.get("error"):
                # Recommendation
                rec = analysis.get("recommendation", "HOLD").upper()
                rec_class = "buy" if "BUY" in rec else ("sell" if "SELL" in rec else "hold")
                icon = "check-circle-fill" if "BUY" in rec else ("x-circle-fill" if "SELL" in rec else "dash-circle-fill")
                
                st.markdown(f"""
                    <div class="recommendation-card">
                        <div class="recommendation-badge {rec_class}">
                            <i class="bi bi-{icon}"></i>
                            {rec}
                        </div>
                        <div class="recommendation-subtitle">AI Recommendation based on recent news and market data</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Analysis Grid
                st.markdown('<div class="analysis-grid">', unsafe_allow_html=True)
                
                # Sentiment
                st.markdown(f"""
                    <div class="analysis-card">
                        <div class="analysis-card-header">
                            <div class="analysis-card-icon">
                                <i class="bi bi-emoji-smile"></i>
                            </div>
                            <div class="analysis-card-title">Sentiment</div>
                        </div>
                        <div class="analysis-card-content">
                            <strong>{analysis.get('sentiment', 'Neutral')}</strong>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Valuation
                st.markdown(f"""
                    <div class="analysis-card">
                        <div class="analysis-card-header">
                            <div class="analysis-card-icon">
                                <i class="bi bi-scale"></i>
                            </div>
                            <div class="analysis-card-title">Valuation</div>
                        </div>
                        <div class="analysis-card-content">
                            {analysis.get('valuation', 'N/A')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Price Justification
                st.markdown(f"""
                    <div class="analysis-card">
                        <div class="analysis-card-header">
                            <div class="analysis-card-icon">
                                <i class="bi bi-cash-stack"></i>
                            </div>
                            <div class="analysis-card-title">Price Justification</div>
                        </div>
                        <div class="analysis-card-content">
                            {analysis.get('price_justification', 'N/A')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Insights
                if analysis.get("insights"):
                    st.markdown("""
                        <div class="analysis-card" style="margin-top: 1.5rem;">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-lightbulb-fill"></i>
                                </div>
                                <div class="analysis-card-title">Actionable Insights</div>
                            </div>
                            <div class="analysis-card-content">
                    """, unsafe_allow_html=True)
                    
                    for insight in analysis.get("insights", []):
                        st.markdown(f'<div class="insight-item">{insight}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div></div>', unsafe_allow_html=True)
                
                # Headlines
                if analysis.get("headlines"):
                    st.markdown("""
                        <div class="analysis-card" style="margin-top: 1.5rem;">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-newspaper"></i>
                                </div>
                                <div class="analysis-card-title">Major Headlines</div>
                            </div>
                            <div class="analysis-card-content">
                    """, unsafe_allow_html=True)
                    
                    for headline in analysis.get("headlines", []):
                        st.markdown(f'<div class="headline-item"><i class="bi bi-dot"></i> {headline}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div></div>', unsafe_allow_html=True)
                
                # Additional Analysis
                st.markdown('<div class="analysis-grid" style="margin-top: 1.5rem;">', unsafe_allow_html=True)
                
                if analysis.get("volatility"):
                    st.markdown(f"""
                        <div class="analysis-card">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-exclamation-triangle"></i>
                                </div>
                                <div class="analysis-card-title">Volatility Alert</div>
                            </div>
                            <div class="analysis-card-content">
                                {analysis.get('volatility')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                if analysis.get("market_comparison"):
                    st.markdown(f"""
                        <div class="analysis-card">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-bar-chart-line"></i>
                                </div>
                                <div class="analysis-card-title">Market Comparison</div>
                            </div>
                            <div class="analysis-card-content">
                                {analysis.get('market_comparison')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                if analysis.get("sentiment_trend"):
                    st.markdown(f"""
                        <div class="analysis-card">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-graph-up"></i>
                                </div>
                                <div class="analysis-card-title">Sentiment Trend</div>
                            </div>
                            <div class="analysis-card-content">
                                {analysis.get('sentiment_trend')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Detailed Justification
                if analysis.get("justification"):
                    st.markdown(f"""
                        <div class="analysis-card" style="margin-top: 1.5rem;">
                            <div class="analysis-card-header">
                                <div class="analysis-card-icon">
                                    <i class="bi bi-file-text"></i>
                                </div>
                                <div class="analysis-card-title">Detailed Justification</div>
                            </div>
                            <div class="analysis-card-content">
                                {analysis.get('justification')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
