import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="📈", layout="wide")

# CSS 樣式：美化指標與矩陣
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    .news-card {
        padding: 8px;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料抓取邏輯
@st.cache_data(ttl=600)
def fetch_all_data():
    # --- 匯率部分 ---
    rates = {'台幣 (TWD)': 1.0}
    try:
        r = requests.get("https://rate.bot.com.tw/xrt/flcsv/0/day", timeout=10)
        r.encoding = 'utf-8-sig'
        for line in r.text.split('\n'):
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            target_map = {
                'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 
                'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'
            }
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except:
        pass

    # --- 標竿股價部分 (補足第 8 家：葡萄王 1707.TW) ---
    stocks = {}
    stock_targets = {
        '1216.TW': '統一',
        '1201.TW': '味全',
        '1210.TW': '大成',
        '1231.TW': '聯華食',
        '1227.TW': '佳格',
        '1707.TW': '葡萄王',  # 新增
        '2912.TW': '統一超',
        '5903.TWO': '全家'
    }
    try:
        for symbol, name in stock_targets.items():
            ticker = yf.Ticker(symbol)
            info = ticker.history(period='2d')
            if len(info) >= 2:
                price = info['Close'].iloc[-1]
                prev_price = info['Close'].iloc[-2]
                change = price - prev_price
                stocks[name] = (price, change)
    except:
        pass

    # --- 新聞部分 ---
    news_entries = []
    try:
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        kw = urllib.parse.quote(query) 
        rss_url = f"https://news.google.com/rss/search?q={kw}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        news_entries = feed.entries[:7]
    except:
        pass

    return rates, stocks, news_entries

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("📈 Terry的換匯小工具 (產業戰情室版)")
st.write(f"執行長您好，今日系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_news = st.columns([3, 1])

with col_main:
    # 匯率看板
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    # 產業標竿股價 (完美的 4x2 矩陣)
    st.subheader("🏢 食品生技與零售標竿股價")
    if stocks_dict:
        keys = list(stocks_dict.keys())
        # 第一排 4 家
        s_cols1 = st.columns(4)
        for i in range(4):
            name = keys[i]
            price, change = stocks_dict[name]
            s_cols1[i].metric(name, f"{price:.2f}", f"{change:+.2f}")
            
        # 第二排 4 家
        s_cols2 = st.columns(4)
        for i in range(4, 8):
            name = keys[i]
            price, change = stocks_dict[name]
            s_cols2[i-4].metric(name, f"{price:.2f}", f"{change:+.2f}")
    
    st.divider()
    
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.write("🔄 **快速試算**")
        amt = st.number_input("試算金額", min_value=0.0, value=100.0)
        f_curr = st.selectbox("從", list(rates_dict.keys()), index=1)
        t_curr = st.selectbox("到", list(rates_dict.keys()), index=0)
        if st.button("立即計算", use_container_width=True):
            res = (amt * rates_dict[f_curr]) / rates_dict[t_curr]
            st.success(f"### {res:,.2f} {t_curr}")
    
    with c2:
        st.write("📈 **趨勢分析**")
        target = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
        range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
        s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
        hist = yf.download(s_map.get(target), period=range_p, progress=False)['Close']
        st.line_chart(hist)

with col_news:
    st.subheader("📰 產業商報")
    if news_list:
        for entry in news_list:
            clean_title = entry.title.split(" - ")[0]
            st.markdown(f"""
            <div class="news-card">
                <a href="{entry.link}" target="_blank" style="text-decoration:none; font-size:14px; font-weight:bold; color:#2563eb;">{clean_title}</a><br>
                <small style="color:gray;">{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)

st.divider()
st.subheader("📋 多幣別對照矩陣")
if rates_dict:
    matrix_currencies = list(rates_dict.keys())
    matrix_data = []
    for row_curr in matrix_currencies:
        row_values = [round(rates_dict[row_curr] / rates_dict[col_curr], 4) for col_curr in matrix_currencies]
        matrix_data.append(row_values)
    st.dataframe(pd.DataFrame(matrix_data, index=matrix_currencies, columns=matrix_currencies), use_container_width=True)
