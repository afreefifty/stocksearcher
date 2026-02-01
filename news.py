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
    <link href="https://fonts.googleapis.com/css2?family=Cal+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    
    <style>
        /* Base Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Questrial', sans-serif !important;
        }
        
        :root {
            --primary-bg: #FFFCF9;
            --secondary-bg: #e8e5e1;
            --primary-blue: #235789;
            --primary-dark: #080705;
            --glass-bg: rgba(255, 252, 249, 0.6);
            --glass-border: rgba(35, 87, 137, 0.12);
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {visibility: hidden;}
        
        /* Body and Main Container */
        body {
            background: linear-gradient(135deg, var(--primary-bg) 0%, var(--secondary-bg) 100%);
            color: var(--primary-dark);
            overflow-x: hidden;
        }
        
        .main {
            background: transparent;
            padding: 0;
        }
        
        .block-container {
            padding: 0;
            max-width: 100%;
        }
        
        /* Welcome Hero - Fixed Position */
        .hero-section {
            position: sticky;
            top: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1;
            pointer-events: none;
        }
        
        .hero-title {
            font-size: 8rem;
            color: var(--primary-blue);
            font-weight: 600;
            letter-spacing: 0.05em;
            text-shadow: 0 4px 20px rgba(35, 87, 137, 0.2);
            animation: fadeIn 1.2s ease-out;
        }
        
        .hero-subtitle {
            font-size: 1.5rem;
            color: var(--primary-dark);
            opacity: 0.6;
            margin-top: 1rem;
            animation: fadeIn 1.5s ease-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Content Feed Container */
        .content-feed {
            position: relative;
            z-index: 10;
            max-width: 1400px;
            margin: -50vh auto 0;
            padding: 2rem;
            min-height: 100vh;
        }
        
        /* Masonry Grid for Cards */
        .card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        /* Card Sizes */
        .card-small {
            grid-row: span 1;
        }
        
        .card-medium {
            grid-row: span 2;
        }
        
        .card-large {
            grid-row: span 3;
        }
        
        .card-full {
            grid-column: 1 / -1;
        }
        
        /* Glass Card Base */
        .feed-card {
            background: var(--glass-bg);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 1.5rem;
            box-shadow: 0 8px 32px rgba(8, 7, 5, 0.08);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            animation: cardFadeIn 0.6s ease-out backwards;
        }
        
        @keyframes cardFadeIn {
            from {
                opacity: 0;
                transform: translateY(30px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        .feed-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 16px 48px rgba(8, 7, 5, 0.12);
            border-color: rgba(35, 87, 137, 0.25);
        }
        
        /* Card Header */
        .card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(35, 87, 137, 0.1);
        }
        
        .card-icon {
            width: 40px;
            height: 40px;
            background: rgba(35, 87, 137, 0.1);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-blue);
            font-size: 1.2rem;
        }
        
        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--primary-blue);
            flex: 1;
        }
        
        .card-badge {
            background: rgba(35, 87, 137, 0.1);
            color: var(--primary-blue);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Card Content Variations */
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(35, 87, 137, 0.06);
        }
        
        .stat-row:last-child {
            border-bottom: none;
        }
        
        .stat-label {
            color: var(--primary-dark);
            opacity: 0.7;
            font-size: 0.9rem;
        }
        
        .stat-value {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--primary-dark);
        }
        
        .stat-value.positive {
            color: #10B981;
        }
        
        .stat-value.negative {
            color: #EF4444;
        }
        
        /* Big Number Display */
        .big-stat {
            text-align: center;
            padding: 2rem 1rem;
        }
        
        .big-stat-value {
            font-size: 3rem;
            font-weight: 600;
            color: var(--primary-blue);
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        
        .big-stat-label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--primary-dark);
            opacity: 0.6;
        }
        
        /* Chart Card */
        .chart-card {
            min-height: 300px;
        }
        
        /* Floating Action Toolbar */
        .floating-toolbar {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--glass-bg);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border: 1px solid var(--glass-border);
            border-radius: 50px;
            padding: 12px;
            box-shadow: 0 16px 48px rgba(8, 7, 5, 0.25);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 1000;
            opacity: 0;
            pointer-events: none;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .floating-toolbar.visible {
            opacity: 1;
            pointer-events: all;
        }
        
        .toolbar-input {
            background: rgba(255, 252, 249, 0.8);
            border: 1px solid rgba(35, 87, 137, 0.15);
            border-radius: 50px;
            padding: 12px 24px;
            font-size: 15px;
            color: var(--primary-dark);
            outline: none;
            transition: all 0.3s ease;
            width: 300px;
        }
        
        .toolbar-input:focus {
            background: rgba(255, 252, 249, 1);
            border-color: var(--primary-blue);
            box-shadow: 0 0 0 3px rgba(35, 87, 137, 0.1);
        }
        
        .toolbar-input::placeholder {
            color: var(--primary-dark);
            opacity: 0.5;
        }
        
        .toolbar-btn {
            width: 48px;
            height: 48px;
            background: rgba(35, 87, 137, 0.15);
            border: 1px solid rgba(35, 87, 137, 0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-blue);
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .toolbar-btn:hover {
            background: rgba(35, 87, 137, 0.25);
            transform: scale(1.1);
            box-shadow: 0 4px 16px rgba(35, 87, 137, 0.2);
        }
        
        .toolbar-btn:active {
            transform: scale(0.95);
        }
        
        /* Modal Overlay */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(8, 7, 5, 0.6);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .modal-overlay.active {
            display: flex;
            opacity: 1;
        }
        
        .modal-content {
            background: var(--glass-bg);
            backdrop-filter: blur(40px);
            -webkit-backdrop-filter: blur(40px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 24px 64px rgba(8, 7, 5, 0.3);
            transform: scale(0.9);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        .modal-overlay.active .modal-content {
            transform: scale(1);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(35, 87, 137, 0.1);
        }
        
        .modal-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--primary-blue);
        }
        
        .modal-close {
            width: 32px;
            height: 32px;
            background: rgba(35, 87, 137, 0.1);
            border: none;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-blue);
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .modal-close:hover {
            background: rgba(35, 87, 137, 0.2);
            transform: rotate(90deg);
        }
        
        /* Form Elements in Modal */
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--primary-blue);
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .form-input {
            width: 100%;
            background: rgba(255, 252, 249, 0.8);
            border: 1px solid rgba(35, 87, 137, 0.2);
            border-radius: 50px;
            padding: 12px 20px;
            font-size: 15px;
            color: var(--primary-dark);
            outline: none;
            transition: all 0.3s ease;
        }
        
        .form-input:focus {
            background: rgba(255, 252, 249, 1);
            border-color: var(--primary-blue);
            box-shadow: 0 0 0 3px rgba(35, 87, 137, 0.1);
        }
        
        .form-checkbox {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            cursor: pointer;
        }
        
        .form-checkbox input {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        /* Streamlit Element Overrides */
        .stTextInput input, .stNumberInput input {
            background: rgba(255, 252, 249, 0.8) !important;
            backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(35, 87, 137, 0.2) !important;
            border-radius: 50px !important;
            padding: 12px 20px !important;
            font-size: 15px !important;
            color: var(--primary-dark) !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput input:focus, .stNumberInput input:focus {
            background: rgba(255, 252, 249, 1) !important;
            border-color: var(--primary-blue) !important;
            box-shadow: 0 0 0 3px rgba(35, 87, 137, 0.1) !important;
        }
        
        .stButton button {
            background: rgba(35, 87, 137, 0.15) !important;
            backdrop-filter: blur(25px) !important;
            border: 1px solid rgba(35, 87, 137, 0.2) !important;
            color: var(--primary-blue) !important;
            border-radius: 50px !important;
            padding: 12px 28px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        }
        
        .stButton button:hover {
            background: rgba(35, 87, 137, 0.25) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Hide Streamlit default spacing */
        .element-container {
            margin: 0 !important;
        }
        
        /* Smooth Scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(35, 87, 137, 0.05);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(35, 87, 137, 0.3);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(35, 87, 137, 0.5);
        }
        
        /* Recommendation Badge */
        .rec-badge {
            display: inline-block;
            padding: 0.75rem 2rem;
            border-radius: 50px;
            font-size: 1.2rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            backdrop-filter: blur(25px);
            transition: all 0.3s ease;
        }
        
        .rec-badge.buy {
            background: rgba(16, 185, 129, 0.15);
            border: 2px solid rgba(16, 185, 129, 0.4);
            color: #059669;
        }
        
        .rec-badge.sell {
            background: rgba(239, 68, 68, 0.15);
            border: 2px solid rgba(239, 68, 68, 0.4);
            color: #DC2626;
        }
        
        .rec-badge.hold {
            background: rgba(251, 191, 36, 0.15);
            border: 2px solid rgba(251, 191, 36, 0.4);
            color: #D97706;
        }
        
        /* Alert/Info Cards */
        .info-card {
            background: rgba(35, 87, 137, 0.08);
            border-left: 4px solid var(--primary-blue);
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .warning-card {
            background: rgba(251, 191, 36, 0.08);
            border-left: 4px solid #FBBF24;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .success-card {
            background: rgba(16, 185, 129, 0.08);
            border-left: 4px solid #10B981;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Section Divider */
        .section-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(35, 87, 137, 0.2), transparent);
            margin: 3rem 0;
        }
        
        /* Back Button */
        .back-btn {
            position: fixed;
            top: 24px;
            left: 24px;
            width: 48px;
            height: 48px;
            background: var(--glass-bg);
            backdrop-filter: blur(40px);
            border: 1px solid var(--glass-border);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary-blue);
            font-size: 1.2rem;
            cursor: pointer;
            z-index: 999;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 8px 24px rgba(8, 7, 5, 0.1);
        }
        
        .back-btn:hover {
            transform: scale(1.1) translateX(-4px);
            box-shadow: 0 12px 32px rgba(8, 7, 5, 0.15);
        }
    </style>
    
    <script>
        // Show floating toolbar on scroll
        window.addEventListener('scroll', function() {
            const toolbar = document.querySelector('.floating-toolbar');
            if (toolbar) {
                if (window.scrollY > 400) {
                    toolbar.classList.add('visible');
                } else {
                    toolbar.classList.remove('visible');
                }
            }
        });
    </script>
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
            "purchase_price": 0.0,
            "quantity": 0
        }
    if 'show_settings_modal' not in st.session_state:
        st.session_state.show_settings_modal = False
    
    # Hero Section (Always visible, scrolls behind content)
    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">STOCKIFY</h1>
            <p class="hero-subtitle">Australian Stock Market Intelligence</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Main Content Feed
    if not st.session_state.show_analysis:
        render_dashboard_feed()
    else:
        render_analysis_page()
    
    # Floating Toolbar (shown after scrolling)
    render_floating_toolbar()
    
    # Settings Modal
    if st.session_state.show_settings_modal:
        render_settings_modal()


def render_dashboard_feed():
    """Render the main dashboard as a card-based news feed"""
    
    st.markdown('<div class="content-feed">', unsafe_allow_html=True)
    
    # Load market data
    with st.spinner("Loading market data..."):
        stock_data = load_market_overview()
        gainers, losers = get_top_movers(stock_data)
    
    # Create masonry grid layout
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    
    # Card 1: Top Gainers (Medium)
    st.markdown('''
        <div class="feed-card card-medium">
            <div class="card-header">
                <div class="card-icon">
                    <i class="bi bi-arrow-up-circle-fill"></i>
                </div>
                <div class="card-title">Top Gainers</div>
                <div class="card-badge">Today</div>
            </div>
    ''', unsafe_allow_html=True)
    
    for g in gainers:
        st.markdown(f'''
            <div class="stat-row">
                <span class="stat-label">{g['ticker']}</span>
                <span class="stat-value positive">+{g['change']}%</span>
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Card 2: Top Losers (Medium)
    st.markdown('''
        <div class="feed-card card-medium">
            <div class="card-header">
                <div class="card-icon">
                    <i class="bi bi-arrow-down-circle-fill"></i>
                </div>
                <div class="card-title">Top Losers</div>
                <div class="card-badge">Today</div>
            </div>
    ''', unsafe_allow_html=True)
    
    for l in losers:
        st.markdown(f'''
            <div class="stat-row">
                <span class="stat-label">{l['ticker']}</span>
                <span class="stat-value negative">{l['change']}%</span>
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Card 3: Market Summary Big Stat (Small)
    avg_change = sum([g['change'] for g in gainers[:3]]) / 3
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="big-stat">
                <div class="big-stat-value {'positive' if avg_change > 0 else 'negative'}">{avg_change:+.2f}%</div>
                <div class="big-stat-label">Market Average</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Card 4: Active Stocks Count (Small)
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="big-stat">
                <div class="big-stat-value">{len(stock_data)}</div>
                <div class="big-stat-label">Tracked Stocks</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close first row
    
    # Full-width chart cards
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    
    # Card 5: Price Trends Chart (Full Width)
    st.markdown('''
        <div class="feed-card card-full chart-card">
            <div class="card-header">
                <div class="card-icon">
                    <i class="bi bi-graph-up"></i>
                </div>
                <div class="card-title">6-Month Price Trends</div>
                <div class="card-badge">Historical</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    price_data = {k: v["history"]["Close"] for k, v in stock_data.items()}
    st.line_chart(price_data, height=350)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Card 6: Volume Chart (Full Width)
    st.markdown('''
        <div class="feed-card card-full chart-card">
            <div class="card-header">
                <div class="card-icon">
                    <i class="bi bi-bar-chart-fill"></i>
                </div>
                <div class="card-title">Trading Volume</div>
                <div class="card-badge">6 Months</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    volume_data = {k: v["history"]["Volume"] for k, v in stock_data.items()}
    st.area_chart(volume_data, height=300)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Individual stock performance cards
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    
    top_stocks = list(stock_data.keys())[:6]
    for ticker in top_stocks:
        data = stock_data[ticker]
        hist = data["history"]
        current_price = hist["Close"].iloc[-1]
        change_30d = calculate_trend(hist, 30)
        
        st.markdown(f'''
            <div class="feed-card card-small">
                <div class="card-header">
                    <div class="card-icon">
                        <i class="bi bi-graph-up-arrow"></i>
                    </div>
                    <div class="card-title">{ticker}</div>
                </div>
                <div class="big-stat">
                    <div class="big-stat-value">${current_price:.2f}</div>
                    <div class="big-stat-label {'positive' if change_30d > 0 else 'negative'}">{change_30d:+.1f}% (30d)</div>
                </div>
            </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)  # Close grid and content-feed


def render_analysis_page():
    """Render detailed stock analysis page"""
    
    ticker = st.session_state.selected_ticker
    
    # Back button
    st.markdown('''
        <div class="back-btn" onclick="window.location.reload()">
            <i class="bi bi-arrow-left"></i>
        </div>
    ''', unsafe_allow_html=True)
    
    if st.button("← Back", key="back_btn_streamlit"):
        st.session_state.show_analysis = False
        st.session_state.selected_ticker = None
        st.rerun()
    
    st.markdown('<div class="content-feed">', unsafe_allow_html=True)
    
    # Get stock info
    with st.spinner("Fetching stock data..."):
        stock_info = get_stock_info(ticker)
    
    if not stock_info:
        st.error("Could not fetch stock data. Please check the ticker symbol.")
        st.stop()
    
    # Stock Header Card (Full Width)
    st.markdown(f'''
        <div class="feed-card card-full">
            <div class="card-header">
                <div class="card-icon">
                    <i class="bi bi-building"></i>
                </div>
                <div>
                    <div style="font-size: 2rem; font-weight: 600; color: var(--primary-blue);">{stock_info['ticker'].replace('.AX', '')}</div>
                    <div style="font-size: 1.2rem; opacity: 0.7;">{stock_info['company_name']}</div>
                </div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Key stats in grid
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    
    # Price Card
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="big-stat">
                <div class="big-stat-value">${stock_info['current_price']}</div>
                <div class="big-stat-label">Current Price</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Sector Card
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="card-header">
                <div class="card-icon"><i class="bi bi-tag-fill"></i></div>
                <div class="card-title">Sector</div>
            </div>
            <div style="font-size: 1.1rem; font-weight: 500; text-align: center; padding: 1rem 0;">
                {stock_info['sector']}
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # P/E Ratio Card
    pe_ratio = stock_info['pe_ratio']
    pe_display = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="big-stat">
                <div class="big-stat-value">{pe_display}</div>
                <div class="big-stat-label">P/E Ratio</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Market Cap Card
    market_cap_b = stock_info['market_cap'] / 1e9 if stock_info['market_cap'] else 0
    st.markdown(f'''
        <div class="feed-card card-small">
            <div class="big-stat">
                <div class="big-stat-value">${market_cap_b:.2f}B</div>
                <div class="big-stat-label">Market Cap</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close stats grid
    
    # Performance Card
    change_7d = calculate_trend(stock_info['history'], 7)
    change_30d = calculate_trend(stock_info['history'], 30)
    volatility = calculate_volatility(stock_info['history'])
    
    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    
    st.markdown(f'''
        <div class="feed-card card-medium">
            <div class="card-header">
                <div class="card-icon"><i class="bi bi-activity"></i></div>
                <div class="card-title">Performance</div>
            </div>
            <div class="stat-row">
                <span class="stat-label">7-Day Change</span>
                <span class="stat-value {'positive' if change_7d > 0 else 'negative'}">{change_7d:+.2f}%</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">30-Day Change</span>
                <span class="stat-value {'positive' if change_30d > 0 else 'negative'}">{change_30d:+.2f}%</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Volatility</span>
                <span class="stat-value">{volatility}%</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    # 52-Week Range Card
    st.markdown(f'''
        <div class="feed-card card-medium">
            <div class="card-header">
                <div class="card-icon"><i class="bi bi-arrow-down-up"></i></div>
                <div class="card-title">52-Week Range</div>
            </div>
            <div class="stat-row">
                <span class="stat-label">High</span>
                <span class="stat-value">${stock_info['52w_high']:.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Low</span>
                <span class="stat-value">${stock_info['52w_low']:.2f}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Current Position</span>
                <span class="stat-value">${stock_info['current_price']}</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Price Chart (Full Width)
    st.markdown('''
        <div class="feed-card card-full chart-card">
            <div class="card-header">
                <div class="card-icon"><i class="bi bi-graph-up"></i></div>
                <div class="card-title">Price History (1 Year)</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.line_chart(stock_info['history']['Close'], height=350)
    
    # Fetch and analyze news
    st.markdown('''
        <div class="section-divider"></div>
        <h2 style="text-align: center; color: var(--primary-blue); font-size: 2rem; margin: 2rem 0;">AI Analysis</h2>
    ''', unsafe_allow_html=True)
    
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
                # Recommendation Card
                rec = analysis.get("recommendation", "HOLD").upper()
                rec_class = "buy" if "BUY" in rec else ("sell" if "SELL" in rec else "hold")
                
                st.markdown(f'''
                    <div class="feed-card card-full" style="text-align: center;">
                        <div class="rec-badge {rec_class}">
                            <i class="bi bi-{'check-circle' if 'BUY' in rec else ('x-circle' if 'SELL' in rec else 'dash-circle')}"></i>
                            {rec}
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Analysis Cards
                st.markdown('<div class="card-grid">', unsafe_allow_html=True)
                
                # Sentiment Card
                sentiment = analysis.get("sentiment", "Neutral")
                st.markdown(f'''
                    <div class="feed-card card-small">
                        <div class="card-header">
                            <div class="card-icon"><i class="bi bi-emoji-smile"></i></div>
                            <div class="card-title">Sentiment</div>
                        </div>
                        <div class="big-stat">
                            <div class="big-stat-value" style="font-size: 1.5rem;">{sentiment}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Valuation Card
                st.markdown(f'''
                    <div class="feed-card card-medium">
                        <div class="card-header">
                            <div class="card-icon"><i class="bi bi-scale"></i></div>
                            <div class="card-title">Valuation</div>
                        </div>
                        <p style="line-height: 1.6;">{analysis.get('valuation', 'N/A')}</p>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Price Justification Card
                st.markdown(f'''
                    <div class="feed-card card-medium">
                        <div class="card-header">
                            <div class="card-icon"><i class="bi bi-cash-stack"></i></div>
                            <div class="card-title">Price Justification</div>
                        </div>
                        <p style="line-height: 1.6;">{analysis.get('price_justification', 'N/A')}</p>
                    </div>
                ''', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Insights Card (Full Width)
                if analysis.get("insights"):
                    st.markdown('''
                        <div class="feed-card card-full">
                            <div class="card-header">
                                <div class="card-icon"><i class="bi bi-lightbulb-fill"></i></div>
                                <div class="card-title">Actionable Insights</div>
                            </div>
                    ''', unsafe_allow_html=True)
                    
                    for insight in analysis.get("insights", []):
                        st.markdown(f'<div class="info-card">{insight}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Headlines Card (Full Width)
                if analysis.get("headlines"):
                    st.markdown('''
                        <div class="feed-card card-full">
                            <div class="card-header">
                                <div class="card-icon"><i class="bi bi-newspaper"></i></div>
                                <div class="card-title">Major Headlines</div>
                            </div>
                    ''', unsafe_allow_html=True)
                    
                    for headline in analysis.get("headlines", []):
                        st.markdown(f'''
                            <div class="stat-row">
                                <span class="stat-label"><i class="bi bi-dot"></i> {headline}</span>
                            </div>
                        ''', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close content-feed


def render_floating_toolbar():
    """Render the floating toolbar with search and settings"""
    
    # Create columns for the toolbar
    col1, col2, col3 = st.columns([6, 1, 1])
    
    with col1:
        ticker_input = st.text_input(
            "Search Stock",
            placeholder="Enter ASX ticker (e.g., WOW, BHP)",
            label_visibility="collapsed",
            key="ticker_toolbar"
        )
    
    with col2:
        if st.button("🔍", key="search_btn", help="Analyze Stock"):
            if ticker_input:
                st.session_state.selected_ticker = format_ticker_for_australia(ticker_input)
                st.session_state.show_analysis = True
                st.rerun()
    
    with col3:
        if st.button("⚙️", key="settings_btn", help="Settings"):
            st.session_state.show_settings_modal = not st.session_state.show_settings_modal
            st.rerun()


def render_settings_modal():
    """Render settings modal dialog"""
    
    st.markdown('<div class="modal-overlay active" id="settingsModal">', unsafe_allow_html=True)
    st.markdown('''
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Stock Settings</div>
            </div>
    ''', unsafe_allow_html=True)
    
    owns_stock = st.checkbox(
        "I already own this stock",
        value=st.session_state.user_settings["owns_stock"],
        key="owns_stock_checkbox"
    )
    st.session_state.user_settings["owns_stock"] = owns_stock
    
    if owns_stock:
        purchase_price = st.number_input(
            "Purchase Price ($)",
            min_value=0.0,
            value=st.session_state.user_settings["purchase_price"],
            step=0.01,
            key="purchase_price_input"
        )
        st.session_state.user_settings["purchase_price"] = purchase_price
        
        quantity = st.number_input(
            "Quantity",
            min_value=0,
            value=st.session_state.user_settings["quantity"],
            step=1,
            key="quantity_input"
        )
        st.session_state.user_settings["quantity"] = quantity
    
    if st.button("Close", key="close_modal"):
        st.session_state.show_settings_modal = False
        st.rerun()
    
    st.markdown('</div></div>', unsafe_allow_html=True)



if __name__ == "__main__":
    main()
