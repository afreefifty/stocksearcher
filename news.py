import streamlit as st
import requests
import trafilatura
import yfinance as yf
from ddgs import DDGS
import os
import time
from urllib.parse import urlparse

# ---------------- CONFIG ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

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
    "afr.com",  # Australian Financial Review (paywall)
    "smh.com.au",  # Sydney Morning Herald (paywall)
    "theage.com.au",  # The Age (paywall)
)

# ---------------- HELPERS ----------------
def search_news(query, max_results=50):
    """Search for news articles with Australian focus"""
    links = []
    with DDGS() as ddgs:
        # Add Australian market context to search
        search_query = f"{query} ASX Australian stock market"
        for r in ddgs.news(search_query, max_results=max_results):
            url = r.get("url")
            if url and url not in links:
                links.append(url)
    return links


def is_blocked_domain(url):
    domain = urlparse(url).netloc.lower()
    return any(bad in domain for bad in BLOCKED_DOMAINS)


def crawl_article(url):
    try:
        if is_blocked_domain(url):
            return None

        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

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


def get_stock_price(ticker):
    """Get stock price for Australian stocks"""
    try:
        # For ASX stocks, yfinance requires .AX suffix
        if not ticker.endswith('.AX'):
            ticker = f"{ticker}.AX"
        
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if data.empty:
            return None, ticker
        return round(float(data["Close"].iloc[-1]), 2), ticker
    except Exception:
        return None, ticker


def analyze_with_groq(news_text, current_price, ticker, purchase_price=None):
    """Analyze stock with optional purchase price for buy/hold/sell recommendation"""
    
    if purchase_price:
        gain_loss = current_price - purchase_price
        gain_loss_pct = ((current_price - purchase_price) / purchase_price) * 100
        
        prompt = f"""
You are an expert Australian financial analyst specializing in ASX stocks.

Stock: {ticker}
Current Price: ${current_price} AUD
Your Purchase Price: ${purchase_price} AUD
Current Gain/Loss: ${gain_loss:.2f} AUD ({gain_loss_pct:+.2f}%)

Recent News Articles:
{news_text[:4000]}

Tasks:
1. Sentiment Analysis: (Positive / Negative / Neutral)
2. News Impact: Does the recent news justify the current price level?
3. Investment Recommendation: Based on your purchase price of ${purchase_price} and the current news:
   - Should you BUY MORE shares at current price?
   - Should you HOLD your position?
   - Should you SELL to lock in gains/cut losses?
4. Rationale: Provide 3-4 key points supporting your recommendation
5. Risk Assessment: What are the main risks to consider?

Respond in clear, structured format suitable for Australian investors.
"""
    else:
        prompt = f"""
You are an expert Australian financial analyst specializing in ASX stocks.

Stock: {ticker}
Current Price: ${current_price} AUD

Recent News Articles:
{news_text[:4000]}

Tasks:
1. Sentiment Analysis: (Positive / Negative / Neutral)
2. News Impact: Does the recent news justify the current price level?
3. Investment Outlook: Should potential investors consider this stock now?
4. Key Insights: Provide 3-4 actionable insights for Australian investors
5. Risk Assessment: What are the main risks to consider?

Respond in clear, structured format suitable for Australian investors.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )

        data = response.json()

        if "choices" not in data:
            return (
                "⚠️ Groq API did not return a valid completion.\n\n"
                f"Response:\n{data}"
            )

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"⚠️ Groq API call failed: {str(e)}"


# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="ASX Stock Analyzer", layout="wide")

st.title("📈 Australian Stock Market Analyzer")
st.caption("ASX-focused analysis • News intelligence • Investment recommendations")

# Input section
col1, col2 = st.columns([2, 1])

with col1:
    ticker = st.text_input(
        "Enter ASX Stock Ticker (e.g. CBA, BHP, CSL, WBC)",
        placeholder="CBA"
    )

with col2:
    own_stock = st.checkbox("I own this stock")

purchase_price = None
if own_stock:
    purchase_price = st.number_input(
        "Enter your purchase price (AUD)",
        min_value=0.01,
        step=0.01,
        format="%.2f",
        help="Enter the price you bought the stock at to get personalized buy/hold/sell recommendations"
    )

if st.button("Analyze") and ticker:
    ticker = ticker.strip().upper()

    # ---- PRICE ----
    with st.spinner("Fetching live ASX stock price..."):
        price, full_ticker = get_stock_price(ticker)

    if not price:
        st.error("❌ Could not fetch stock price. Check ticker symbol (ASX stocks only).")
        st.stop()

    st.success(f"💰 Current Price: ${price} AUD")
    
    if purchase_price:
        gain_loss = price - purchase_price
        gain_loss_pct = ((price - purchase_price) / purchase_price) * 100
        
        if gain_loss >= 0:
            st.info(f"📊 Your Position: **Gain of ${gain_loss:.2f} ({gain_loss_pct:+.2f}%)**")
        else:
            st.warning(f"📊 Your Position: **Loss of ${abs(gain_loss):.2f} ({gain_loss_pct:.2f}%)**")

    # ---- SEARCH ----
    with st.spinner("Searching Australian financial news..."):
        links = search_news(ticker)

    if not links:
        st.error("❌ No news links found.")
        st.stop()

    st.subheader("📰 Discovered News Links")
    for l in links[:15]:
        st.markdown(f"- {l}")

    # ---- ADAPTIVE CRAWLING (10 articles) ----
    st.subheader("📄 Crawled Articles")

    successful_articles = []
    attempted = 0

    for link in links:
        if len(successful_articles) >= 10:  # Changed from 5 to 10
            break

        attempted += 1
        with st.spinner(f"Extracting article {attempted}..."):
            text = crawl_article(link)

        if text:
            successful_articles.append(text)
            st.success(f"✅ Article {attempted}: Successfully extracted ({len(text)} chars)")
        else:
            st.warning(f"❌ Article {attempted}: Blocked or failed to extract")

        time.sleep(0.8)

    if not successful_articles:
        st.error("❌ Could not extract content from any source.")
        st.stop()

    st.info(f"📚 Successfully extracted **{len(successful_articles)}** articles for analysis")
    
    combined_text = "\n\n".join(successful_articles)

    # ---- LLM ----
    if not GROQ_API_KEY:
        st.error("❌ GROQ_API_KEY not set. Please set your API key in environment variables.")
        st.stop()

    st.subheader("🧠 AI Analysis")
    with st.spinner("Analyzing news sentiment and generating recommendations..."):
        result = analyze_with_groq(combined_text, price, ticker, purchase_price)

    st.markdown("### 🧠 Expert Analysis")
    st.markdown(result)


# ---------------- ASX TOP STOCKS DASHBOARD ----------------
st.divider()
st.subheader("📊 ASX Market Snapshot: Top Australian Stocks")

# Top ASX stocks by market cap
TOP_ASX_STOCKS = ["CBA.AX", "BHP.AX", "CSL.AX", "NAB.AX", "WBC.AX", 
                  "ANZ.AX", "WES.AX", "MQG.AX", "FMG.AX", "RIO.AX"]

@st.cache_data(ttl=900)
def load_stock_history(tickers):
    data = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="6mo")
            if not hist.empty:
                data[t] = hist
        except:
            continue
    return data

stock_data = load_stock_history(TOP_ASX_STOCKS)

if stock_data:
    c1, c2 = st.columns(2)

    # 1️⃣ Line chart – Price trends
    with c1:
        st.markdown("**1. Price Trends (6 months)**")
        st.line_chart({k.replace('.AX', ''): v["Close"] for k, v in stock_data.items()})

    # 2️⃣ Area chart – Volume
    with c2:
        st.markdown("**2. Trading Volume (6 months)**")
        st.area_chart({k.replace('.AX', ''): v["Volume"] for k, v in stock_data.items()})

    # 3️⃣ Bar chart – Latest Close
    st.markdown("**3. Latest Closing Prices (AUD)**")
    latest_prices = {
        k.replace('.AX', ''): float(v["Close"].iloc[-1]) for k, v in stock_data.items()
    }
    st.bar_chart(latest_prices)

    # 4️⃣ Bar chart – % Change (7d)
    st.markdown("**4. 7-Day % Change**")
    pct_change = {
        k.replace('.AX', ''): round(((v["Close"].iloc[-1] / v["Close"].iloc[-7]) - 1) * 100, 2)
        for k, v in stock_data.items() if len(v) >= 7
    }
    st.bar_chart(pct_change)

    # 5️⃣ Line chart – Big 4 Banks
    st.markdown("**5. Big 4 Banks Comparison (CBA, NAB, WBC, ANZ)**")
    banks = {}
    for ticker in ["CBA.AX", "NAB.AX", "WBC.AX", "ANZ.AX"]:
        if ticker in stock_data:
            banks[ticker.replace('.AX', '')] = stock_data[ticker]["Close"]
    if banks:
        st.line_chart(banks)

    # 6️⃣ Area chart – BHP momentum
    st.markdown("**6. BHP Momentum (Close Price)**")
    if "BHP.AX" in stock_data:
        st.area_chart(stock_data["BHP.AX"]["Close"])

    # 7️⃣ Line chart – Mining stocks volatility
    st.markdown("**7. Mining Stocks Volatility (BHP, RIO, FMG)**")
    mining = {}
    for ticker in ["BHP.AX", "RIO.AX", "FMG.AX"]:
        if ticker in stock_data:
            mining[ticker.replace('.AX', '')] = stock_data[ticker]["High"] - stock_data[ticker]["Low"]
    if mining:
        st.line_chart(mining)

    # 8️⃣ Bar chart – Average Volume
    st.markdown("**8. Average Daily Volume**")
    avg_volume = {
        k.replace('.AX', ''): int(v["Volume"].mean()) for k, v in stock_data.items()
    }
    st.bar_chart(avg_volume)

    # 9️⃣ Line chart – CSL growth
    st.markdown("**9. CSL Growth Curve**")
    if "CSL.AX" in stock_data:
        st.line_chart(stock_data["CSL.AX"]["Close"])

    # 🔟 Line chart – Financial Services
    st.markdown("**10. Financial Services Performance (MQG vs WES)**")
    finance = {}
    for ticker in ["MQG.AX", "WES.AX"]:
        if ticker in stock_data:
            finance[ticker.replace('.AX', '')] = stock_data[ticker]["Close"]
    if finance:
        st.line_chart(finance)
else:
    st.warning("Unable to load ASX market data. Please check your internet connection.")

st.divider()
st.caption("💡 Tip: Enable 'I own this stock' and enter your purchase price for personalized buy/hold/sell recommendations")
