import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="📈", layout="wide")

# CSS 樣式修正
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料抓取邏輯
@st.cache_data(ttl=600)
def fetch_all_data():
    rates = {'台幣 (TWD)': 1.0}
    try:
        r = requests.get("https://rate.bot.com.tw/xrt/flcsv/0/day", timeout=10)
        r.encoding = 'utf-8-sig'
        for line in r.text.split('\n'):
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            # 支援幣別
            target_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'}
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except: pass

    stocks = {}
    # 產業標竿監控名單，包含執行長指定的佳格與葡萄王
    stock_targets = {
        '1216.TW': '統一', '1201.TW': '味全', '1210.TW': '大成', 
        '1231.TW': '聯華食', '1227.TW': '佳格', '1707.TW': '葡萄王', 
        '2912.TW': '統一超', '5903.TWO': '全家'
    }
    try:
        for symbol, name in stock_targets.items():
            ticker = yf.Ticker(symbol)
            info = ticker.history(period='2d')
            if len(info) >= 2:
                p, prev = info['Close'].iloc[-1], info['Close'].iloc[-2]
                stocks[name] = (p, p - prev)
    except: pass

    news = []
    try:
        # 鎖定食力、經濟日報、數位時代
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass

    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("📈 Terry的換匯小工具 (海外戰情室版)")
st.write(f"執行長您好，今日系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_news = st.columns([3, 1])

with col_main:
    # 第一層：即時匯率 (對台幣)
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    st.divider()

    # 第二層：換匯跟歷史趨勢 (排序提前)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("🔄 快速換算")
        amt = st.number_input("金額", min_value=0.0, value=100.0, key="calc_amt")
        f_c = st.selectbox("從", list(rates_dict.keys()), index=1, key="f_c")
        t_c = st.selectbox("到", list(rates_dict.keys()), index=0, key="t_c")
        if st.button("計算結果", use_container_width=True):
            res = (amt * rates_dict[f_c]) / rates_dict[t_c]
            st.success(f"### {res:,.2f} {t_c}")
    
    with c2:
        st.subheader("📈 歷史趨勢")
        target = st.selectbox("趨勢幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="trend_c")
        range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="range_p")
        s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '
