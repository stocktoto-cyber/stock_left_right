import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# 1. 頁面設定與 CSS
# ==========================================
st.set_page_config(page_title="方舟 v17.3 全球通", layout="wide")

style_css = """
<style>
    .ark-container { max-width: 100%; margin: 0 auto; font-family: 'Microsoft JhengHei', sans-serif; }
    .ark-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
    .ark-card { background: white; border-radius: 12px; padding: 15px; border: 1px solid #ddd; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between; }
    
    .card-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px;}
    
    .ticker-box { display: flex; align-items: baseline; gap: 8px; }
    .ticker { font-size: 1.6em; font-weight: 900; color: #333; }
    .stock-name { font-size: 1.0em; font-weight: bold; color: #7f8c8d; }
    
    .price { font-size: 1.6em; font-weight: bold; color: #2980b9; }
    
    .price-twd-hint {
        font-size: 0.9em;
        color: #95a5a6;
        display: block;
        text-align: right;
        margin-top: 5px;
        font-weight: bold;
    }
    
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; background: #fdfefe; padding: 12px; border-radius: 8px; }
    .data-item-box { display: flex; flex-direction: column; align-items: center; border-right: 1px solid #eee; padding: 8px 0; border-bottom: 1px solid #eee;}
    
    .data-item-box:nth-child(4), .data-item-box:nth-child(8) { border-right: none; }
    .data-item-box:nth-child(n+5) { border-bottom: none; }
    
    .data-lbl { font-size: 0.9em; color: #95a5a6; margin-bottom: 4px; text-align: center; font-weight: bold;}
    .data-num { font-size: 1.3em; font-weight: 900; color: #2c3e50; text-align: center; }
    
    .tags-row { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap;}
    .tag { padding: 5px 8px; border-radius: 6px; font-size: 1.0em; font-weight: bold; }
    
    .reason-box { text-align: right; margin-bottom: 8px; }
    .reason-text { font-size: 1.25em; font-weight: bold; }
    
    .action-box { background: #f4f6f7; border-radius: 8px; padding: 10px; text-align: center; }
    .money { font-size: 2.2em; font-weight: 900; color: #27ae60; line-height: 1.1; }
    .label { font-size: 0.95em; color: #7f8c8d; font-weight: bold; }
    
    .sell-box { background: #fadbd8; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
</style>
"""
st.markdown(style_css, unsafe_allow_html=True)

# ==========================================
# 2. 核心運算
# ==========================================

STOCK_MAP = {
    # === 台股 ===
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息",
    "00919": "群益台灣精選高息", "00929": "復華台灣科技優息", "00713": "元大台灣高息低波",
    "006208": "富邦台50", "00675L": "富邦臺灣加權正2", "00631L": "元大台灣50正2",
    "00679B": "元大美債20年", "00680L": "元大美債20正2", "00881": "國泰台灣5G+",
    "00632R": "元大台灣50反1", "00663L": "國泰20年美債正2",
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2303": "聯電",
    "2308": "台達電", "2881": "富邦金", "2882": "國泰金", "2603": "長榮",
    # === 美股 ===
    "VOO": "標普500 ETF", "VTI": "整體股市 ETF", "VT": "全球股市 ETF",
    "QQQ": "那斯達克100", "SOXX": "半導體 ETF", "TLT": "20年美債",
    "TQQQ": "那斯達克三倍", "SOXL": "半導體三倍", "SCHD": "美國高股息",
    "AAPL": "蘋果", "MSFT": "微軟", "NVDA": "輝達", "GOOG": "谷歌",
    "AMZN": "亞馬遜", "META": "臉書", "TSLA": "特斯拉", "AMD": "超微",
    "TSM": "台積電ADR", "COIN": "Coinbase", "PLTR": "Palantir"
}

def get_stock_name(ticker):
    return STOCK_MAP.get(ticker.upper(), "")

def get_symbol_and_currency(ticker):
    ticker = ticker.strip().upper()
    if ticker.endswith('.TW') or ticker.endswith('.TWO'):
        return ticker, 'TWD'
    # 修正判斷邏輯：只要開頭是數字，一律視為台股
    if len(ticker) > 0 and ticker[0].isdigit():
        return ticker + '.TW', 'TWD'
    return ticker, 'USD'

@st.cache_data(ttl=3600)
def get_usdtwd_rate():
    try:
        rate_df = yf.Ticker("USDTWD=X").history(period="1d")
        if not rate_df.empty:
            return rate_df['Close'].iloc[-1]
    except: pass
    return 32.5

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_kd(df, n=9):
    low_min = df['Low'].rolling(window=n).min()
    high_max = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    k = [50]
    d = [50]
    rsv_list = rsv.tolist()
    for i in range(1, len(rsv_list)):
        k_val = (2/3) * k[-1] + (1/3) * rsv_list[i]
        d_val = (2/3) * d[-1] + (1/3) * k_val
        k.append(k_val)
        d.append(d_val)
    return k, d

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return histogram

def calculate_bollinger_b(df, window=20):
    ma = df['Close'].rolling(window=window).mean()
    std = df['Close'].rolling(window=window).std()
    upper = ma + (2 * std)
    lower = ma - (2 * std)
    pct_b = (df['Close'] - lower) / (upper - lower) * 100
    return pct_b

def get_strategy(allocated_budget, days_divisor, bias, trend, is_val, profit, strategy_mode, sell_signal):
    if sell_signal:
        return -999, "📉破線賣", "#c0392b"
    if allocated_budget <= 0: return 0, "無預算", "#bdc3c7"
    
    base = allocated_budget / days_divisor
    amt, reason, color = 0, "", "#95a5a6"
    
    if bias > 12: return 0, "🔥過熱(停)", "#e74c3c"
    
    if profit is not None and profit < -5:
        if bias < 0: return round(base * 3.0/100)*100, "📉大補倉", "#27ae60"
        else: return round(base * 2.0/100)*100, "📉降成本", "#2ecc71"
        
    if strategy_mode == 'trend':
        if bias < -15: amt, reason, color = base * 2.5, "✨黃金坑", "#d35400"
        elif "短多" in trend:
            if bias < 5: amt, reason, color = base * 1.0, "🚀順勢買", "#2980b9"
            else: amt, reason, color = base * 0.5, "⚠️追高買", "#f39c12"
        elif "短空" in trend: amt, reason, color = 0, "🛑趨勢空", "#95a5a6"
        else: amt, reason, color = 0, "👀觀望", "#95a5a6"
    else:
        if bias < -10: amt, reason, color = base * 2.5, "✨微笑買", "#27ae60"
        elif is_val:
            if "短空" in trend: amt, reason, color = base * 1.2, "💎撿便宜", "#1abc9c"
            else: amt, reason, color = base * 1.0, "☁️存價值", "#16a085"
        elif bias < 0: amt, reason, color = base * 0.8, "📉低檔佈", "#a2d9ce"
        else: amt, reason, color = base * 0.5, "☕小額存", "#95a5a6"
        
    final_amt = round(amt/100)*100
    if final_amt == 0 and amt > 100: reason = "額度過小"
    return final_amt, reason, color

def check_trend(df):
    if len(df) < 25: return "資料不足"
    df['MA20'] = df['Close'].rolling(window=20).mean()
    now = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2]
    ma20 = df['MA20'].iloc[-1]
    ma20_prev = df['MA20'].iloc[-2]
    if now > ma20 and prev > ma20_prev: return "🚀短多"
    elif now < ma20 and prev < ma20_prev: return "☠️短空"
    else: return "⚠️轉折"

def run_analysis_v17(rows, total_budget, mode_days, strat_mode):
    cards = []
    # 過濾空行
    valid_rows = [r for r in rows if r['代號'] and str(r['代號']).strip() != ""]
    stock_count = len(valid_rows)
    if stock_count == 0: return [], 32.5
    
    usd_rate = get_usdtwd_rate()
    budget_per_stock = total_budget / stock_count
    
    for row in valid_rows:
        tk = str(row['代號']).strip().upper()
        sym, currency = get_symbol_and_currency(tk)
        
        try:
            div = float(row['股利']) if row['股利'] else 0
            eps = float(row['EPS']) if row['EPS'] else 0
            cost = float(row['成本']) if row['成本'] else 0
        except: continue
        
        try:
            stk = yf.Ticker(sym)
            df = stk.history(period="3mo")
            if df.empty and tk[0].isdigit() and not tk.endswith('.TWO'):
                stk = yf.Ticker(tk+'.TWO')
                df = stk.history(period="3mo")
            if df.empty: continue
            
            price = df['Close'].iloc[-1]
            
            if currency == 'USD':
                price_display = f"US$ {price:.1f}"
                price_twd_approx = price * usd_rate
            else:
                price_display = f"{price:.0f}"
                price_twd_approx = price
                
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            ma10 = df['MA10'].iloc[-1] if
