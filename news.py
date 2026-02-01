from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import trafilatura
import yfinance as yf
from ddgs import DDGS
import time
from urllib.parse import urlparse
import os

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIGURATION
# ============================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Add your API key here or set environment variable
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

# ============================================
# UTILITY FUNCTIONS
# ============================================

def is_blocked_domain(url):
    """Check if URL is from a blocked domain"""
    domain = urlparse(url).netloc.lower()
    return any(bad in domain for bad in BLOCKED_DOMAINS)


def search_news_articles(ticker, max_results=50):
    """
    Search for news articles about the stock
    Returns list of URLs
    """
    links = []
    try:
        with DDGS() as ddgs:
            search_query = f"{ticker} ASX Australian stock market"
            for r in ddgs.news(search_query, max_results=max_results):
                url = r.get("url")
                if url and url not in links:
                    links.append(url)
        return links
    except Exception as e:
        print(f"Error searching news: {e}")
        return []


def crawl_single_article(url):
    """
    Crawl a single article and extract text
    Returns text content or None
    """
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

    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return None


def get_stock_price_data(ticker):
    """
    Get current stock price for ASX ticker
    Returns (price, full_ticker) or (None, None)
    """
    try:
        # Add .AX suffix for ASX stocks
        if not ticker.endswith('.AX'):
            full_ticker = f"{ticker}.AX"
        else:
            full_ticker = ticker

        stock = yf.Ticker(full_ticker)
        hist = stock.history(period="1d")

        if hist.empty:
            return None, None

        price = round(float(hist["Close"].iloc[-1]), 2)
        return price, full_ticker

    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None, None


def analyze_with_ai(news_text, price, ticker, purchase_price=None):
    """
    Analyze stock news with AI and provide recommendations
    Returns analysis text
    """
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY not configured. Please add your API key."

    # Build the prompt based on whether user owns the stock
    if purchase_price:
        gain_loss = price - purchase_price
        gain_loss_pct = ((price - purchase_price) / purchase_price) * 100

        prompt = f"""You are an expert Australian financial analyst specializing in ASX stocks.

Stock: {ticker}
Current Price: ${price:.2f} AUD
Your Purchase Price: ${purchase_price:.2f} AUD
Current Gain/Loss: ${gain_loss:.2f} AUD ({gain_loss_pct:+.2f}%)

Recent News Articles:
{news_text[:4000]}

Tasks:
1. Sentiment Analysis: (Positive / Negative / Neutral)
2. News Impact: Does the recent news justify the current price level?
3. Investment Recommendation: Based on your purchase price of ${purchase_price:.2f} and the current news:
   - Should you BUY MORE shares at current price?
   - Should you HOLD your position?
   - Should you SELL to lock in gains/cut losses?
4. Rationale: Provide 3-4 key points supporting your recommendation
5. Risk Assessment: What are the main risks to consider?

Respond in clear, structured format suitable for Australian investors."""
    else:
        prompt = f"""You are an expert Australian financial analyst specializing in ASX stocks.

Stock: {ticker}
Current Price: ${price:.2f} AUD

Recent News Articles:
{news_text[:4000]}

Tasks:
1. Sentiment Analysis: (Positive / Negative / Neutral)
2. News Impact: Does the recent news justify the current price level?
3. Investment Outlook: Should potential investors consider this stock now?
4. Key Insights: Provide 3-4 actionable insights for Australian investors
5. Risk Assessment: What are the main risks to consider?

Respond in clear, structured format suitable for Australian investors."""

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
            return f"Error: Invalid API response - {data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error calling Groq API: {str(e)}"


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/')
def serve_frontend():
    """Serve the HTML frontend"""
    return send_from_directory('.', 'index.html')


@app.route('/api/stock-price', methods=['POST'])
def api_get_stock_price():
    """
    Endpoint to get stock price
    POST body: { "ticker": "CBA" }
    Returns: { "ticker": "CBA.AX", "price": 123.45 }
    """
    data = request.json
    ticker = data.get('ticker', '').strip().upper()

    if not ticker:
        return jsonify({'error': 'Ticker required'}), 400

    price, full_ticker = get_stock_price_data(ticker)

    if price is None:
        return jsonify({'error': 'Could not fetch stock data. Please check the ticker symbol.'}), 404

    return jsonify({
        'ticker': full_ticker,
        'price': price,
        'success': True
    })


@app.route('/api/search-news', methods=['POST'])
def api_search_news():
    """
    Endpoint to search news articles
    POST body: { "ticker": "CBA", "max_results": 50 }
    Returns: { "links": [...], "count": 10 }
    """
    data = request.json
    ticker = data.get('ticker', '').strip().upper()
    max_results = data.get('max_results', 50)

    if not ticker:
        return jsonify({'error': 'Ticker required'}), 400

    links = search_news_articles(ticker, max_results)

    return jsonify({
        'links': links,
        'count': len(links),
        'success': True
    })


@app.route('/api/crawl-article', methods=['POST'])
def api_crawl_article():
    """
    Endpoint to crawl a single article
    POST body: { "url": "https://..." }
    Returns: { "success": true, "text": "...", "length": 1234 }
    """
    data = request.json
    url = data.get('url', '')

    if not url:
        return jsonify({'error': 'URL required'}), 400

    if is_blocked_domain(url):
        return jsonify({
            'error': 'Domain blocked (paywall)',
            'success': False
        }), 403

    text = crawl_single_article(url)

    if text:
        return jsonify({
            'success': True,
            'text': text,
            'length': len(text)
        })
    else:
        return jsonify({
            'error': 'Could not extract text from article',
            'success': False
        }), 400


@app.route('/api/crawl-articles', methods=['POST'])
def api_crawl_articles():
    """
    Endpoint to crawl multiple articles at once
    POST body: { "urls": ["url1", "url2", ...], "max_articles": 10 }
    Returns: { "articles": [...], "success_count": 5, "statuses": [...] }
    """
    data = request.json
    urls = data.get('urls', [])
    max_articles = data.get('max_articles', 10)

    if not urls:
        return jsonify({'error': 'URLs required'}), 400

    articles = []
    statuses = []

    for i, url in enumerate(urls[:max_articles]):
        if len(articles) >= max_articles:
            break

        text = crawl_single_article(url)

        if text:
            articles.append(text)
            statuses.append({
                'index': i + 1,
                'url': url,
                'success': True,
                'length': len(text)
            })
        else:
            statuses.append({
                'index': i + 1,
                'url': url,
                'success': False,
                'error': 'Could not extract text'
            })

        # Small delay to avoid overwhelming servers
        time.sleep(0.5)

    return jsonify({
        'articles': articles,
        'success_count': len(articles),
        'total_attempted': len(statuses),
        'statuses': statuses,
        'success': True
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    Endpoint to get AI analysis
    POST body: { 
        "news_text": "combined article text",
        "price": 123.45,
        "ticker": "CBA",
        "purchase_price": 100.00  # optional
    }
    Returns: { "analysis": "...", "success": true }
    """
    data = request.json
    news_text = data.get('news_text', '')
    price = data.get('price', 0)
    ticker = data.get('ticker', '')
    purchase_price = data.get('purchase_price')

    if not all([news_text, price, ticker]):
        return jsonify({'error': 'Missing required fields (news_text, price, ticker)'}), 400

    analysis = analyze_with_ai(news_text, price, ticker, purchase_price)

    return jsonify({
        'analysis': analysis,
        'success': True
    })


@app.route('/api/full-analysis', methods=['POST'])
def api_full_analysis():
    """
    Complete end-to-end analysis endpoint
    POST body: { 
        "ticker": "CBA",
        "purchase_price": 100.00,  # optional
        "max_articles": 10
    }
    Returns complete analysis with all data
    """
    data = request.json
    ticker = data.get('ticker', '').strip().upper()
    purchase_price = data.get('purchase_price')
    max_articles = data.get('max_articles', 10)

    if not ticker:
        return jsonify({'error': 'Ticker required'}), 400

    result = {
        'ticker': ticker,
        'success': False
    }

    # Step 1: Get stock price
    price, full_ticker = get_stock_price_data(ticker)
    if price is None:
        result['error'] = 'Could not fetch stock price'
        return jsonify(result), 404

    result['price'] = price
    result['full_ticker'] = full_ticker

    # Step 2: Search news
    news_links = search_news_articles(ticker, max_results=50)
    if not news_links:
        result['error'] = 'No news articles found'
        return jsonify(result), 404

    result['news_links'] = news_links
    result['news_count'] = len(news_links)

    # Step 3: Crawl articles
    articles = []
    crawl_statuses = []

    for i, url in enumerate(news_links[:max_articles]):
        if len(articles) >= max_articles:
            break

        text = crawl_single_article(url)

        if text:
            articles.append(text)
            crawl_statuses.append({
                'index': i + 1,
                'url': url,
                'success': True,
                'length': len(text)
            })
        else:
            crawl_statuses.append({
                'index': i + 1,
                'url': url,
                'success': False
            })

        time.sleep(0.5)

    if not articles:
        result['error'] = 'Could not extract content from any articles'
        result['crawl_statuses'] = crawl_statuses
        return jsonify(result), 400

    result['articles_extracted'] = len(articles)
    result['crawl_statuses'] = crawl_statuses

    # Step 4: AI Analysis
    combined_text = "\n\n".join(articles)
    analysis = analyze_with_ai(combined_text, price, ticker, purchase_price)

    result['analysis'] = analysis
    result['success'] = True

    # Add position data if purchase price provided
    if purchase_price:
        gain_loss = price - purchase_price
        gain_loss_pct = ((price - purchase_price) / purchase_price) * 100
        result['position'] = {
            'purchase_price': purchase_price,
            'gain_loss': round(gain_loss, 2),
            'gain_loss_pct': round(gain_loss_pct, 2)
        }

    return jsonify(result)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'groq_api_configured': bool(GROQ_API_KEY)
    })


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("ASX Stock Intelligence Backend Server")
    print("=" * 60)
    print(f"GROQ API Key configured: {bool(GROQ_API_KEY)}")
    print(f"Server starting on http://localhost:5000")
    print("=" * 60)
    
    if not GROQ_API_KEY:
        print("⚠️  WARNING: GROQ_API_KEY not set!")
        print("   Set it as environment variable or edit the code")
        print("=" * 60)
    
    app.run(debug=True, port=5000, host='0.0.0.0')
