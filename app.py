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
    .cost-box {
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #2563eb;
        background-color: var(--secondary-background-color);
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
            target_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'}
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except: pass

    stocks = {}
    stock_targets = {'1216.TW': '統一', '1201.TW': '味全', '1210.TW': '大成', '1231.TW': '聯華食', '1227.TW': '佳格', '1707.TW': '葡萄王', '2912.TW': '統一超', '5903.TWO': '全家'}
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
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass

    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("📈 Terry的換匯小工具 (決策升級版)")
st.write(f"執行長您好，今日系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_news = st.columns([3, 1])

with col_main:
    # 第一層：匯率看板
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    st.divider()

    # 第二層：採購成本變動試算 (本次新增)
    with st.expander("🚀 海外採購成本與損益預警系統", expanded=True):
        st.write("針對馬來西亞或新加坡佈局，計算匯率波動對採購成本的影響。")
        c1, c2, c3 = st.columns(3)
        with c1:
            target_curr = st.selectbox("選擇採購幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4) # 預設馬幣
        with c2:
            base_rate = st.number_input("設定預算基準匯率 (TWD)", value=7.10, step=0.01, format="%.4f")
        with c3:
            total_amount = st.number_input(f"預計採購金額 ({target_curr})", value=1000000, step=10000)

        # 計算
        current_rate = rates_dict[target_curr]
        rate_diff = current_rate - base_rate
        impact = total_amount * rate_diff

        if impact > 0:
            st.error(f"⚠️ **成本預警**：當前匯率 ({current_rate:.4f}) 高於基準。若維持原採購量，台幣支出將**增加 {impact:,.0f} 元**。")
        elif impact < 0:
            st.success(f"✅ **成本紅利**：當前匯率 ({current_rate:.4f}) 低於基準。若維持原採購量，台幣支出將**節省 {abs(impact):,.0f} 元**。")
        else:
            st.info(f"當前匯率與基準持平。")

    st.divider()

    # 第三層：股價看板
    st.subheader("🏢 產業標竿企業股價")
    if stocks_dict:
        keys = list(stocks_dict.keys())
        s_cols1 = st.columns(4)
        for i in range(4):
            name = keys[i]
            p, c = stocks_dict[name]
            s_cols1[i].metric(name, f"{p:.2f}", f"{c:+.2f}")
        s_cols2 = st.columns(4)
        for i in range(4, 8):
            name = keys[i]
            p, c = stocks_dict[name]
            s_cols2[i-4].metric(name, f"{p:.2f}", f"{c:+.2f}")

    st.divider()
    
    # 第四層：換算與圖表
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.write("🔄 **快速換算**")
        amt = st.number_input("金額", min_value=0.0, value=100.0, key="calc_amt")
        f_c = st.selectbox("從", list(rates_dict.keys()), index=1, key="f_c")
        t_c = st.selectbox("到", list(rates_dict.keys()), index=0, key="t_c")
        if st.button("計算結果", use_container_width=True):
            res = (amt * rates_dict[f_c]) / rates_dict[t_c]
            st.success(f"### {res:,.2f} {t_c}")
    
    with c2:
        st.write("📈 **歷史分析**")
        target = st.selectbox("趨勢幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="trend_c")
        range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="range_p")
        s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
        hist = yf.download(s_map.get(target), period=range_p, progress=False)['Close']
        st.line_chart(hist)

with col_news:
    st.subheader("📰 產業商報")
    if news_list:
        for entry in news_list:
            clean_title = entry.title.split(" - ")[0]
            st.markdown(f"""
            <div style='padding:8px; border-bottom:1px solid var(--border-color); margin-bottom:5px;'>
                <a href='{entry.link}' target='_blank' style='text-decoration:none; font-size:14px; font-weight:bold; color:#2563eb;'>{clean_title}</a><br>
                <small style='color:gray;'>{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)

st.divider()
st.subheader("📋 多幣別對照矩陣")
if rates_dict:
    matrix_currencies = list(rates_dict.keys())
    matrix_data = [[round(rates_dict[row] / rates_dict[col], 4) for col in matrix_currencies] for row in matrix_currencies]
    st.dataframe(pd.DataFrame(matrix_data, index=matrix_currencies, columns=matrix_currencies), use_container_width=True)
