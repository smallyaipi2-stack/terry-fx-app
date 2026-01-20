import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定 [cite: 2025-08-10]
st.set_page_config(page_title="Terry的換匯小工具", page_icon="📈", layout="wide")

# CSS 樣式：美化指標與區塊佈局
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

# 2. 資料抓取邏輯 (快取設定 10 分鐘)
@st.cache_data(ttl=600)
def fetch_all_data():
    # --- 匯率部分 --- [cite: 2025-08-11]
    rates = {'台幣 (TWD)': 1.0}
    try:
        r = requests.get("https://rate.bot.com.tw/xrt/flcsv/0/day", timeout=10)
        r.encoding = 'utf-8-sig'
        for line in r.text.split('\n'):
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            # 支援幣別 [cite: 2026-01-10]
            target_map = {
                'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 
                'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'
            }
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except: pass

    # --- 標竿股價部分 --- [cite: 2026-01-16]
    stocks = {}
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
                p, c = info['Close'].iloc[-1], info['Close'].iloc[-1] - info['Close'].iloc[-2]
                stocks[name] = (p, c)
    except: pass

    # --- 新聞部分 --- [cite: 2026-01-18]
    news = []
    try:
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        encoded_query = urllib.parse.quote(query)
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass

    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現 [cite: 2025-12-17]
st.title("📈 Terry的換匯小工具 (海外戰情室版)")
st.write(f"執行長您好，目前系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_news = st.columns([3, 1])

with col_main:
    # --- 第一層：即時匯率 (對台幣) ---
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    st.divider()

    # --- 第二層：換匯跟歷史趨勢 --- [cite: 2025-08-10]
    c_left, c_right = st.columns([1, 1.2])
    with c_left:
        st.subheader("🔄 快速換算")
        amt = st.number_input("試算金額", min_value=0.0, value=100.0, key="calc_amt")
        f_c = st.selectbox("從", list(rates_dict.keys()), index=1, key="f_c")
        t_c = st.selectbox("到", list(rates_dict.keys()), index=0, key="t_c")
        if st.button("立即計算", use_container_width=True):
            res = (amt * rates_dict[f_c]) / rates_dict[t_c]
            st.success(f"### {res:,.2f} {t_c}")
    
    with c_right:
        st.subheader("📈 歷史趨勢")
        target_c = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="trend_c")
        range_p = st.radio("時間範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="range_p")
        s_map = {
            '美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', 
            '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', 
            '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', 
            '新幣 (SGD)': 'SGDTWD=X'
        }
        hist_data = yf.download(s_map.get(target_c), period=range_p, progress=False)['Close']
        if not hist_data.empty:
            st.line_chart(hist_data)

    st.divider()

    # --- 第三層：進出口預警 --- [cite: 2026-01-10]
    with st.expander("🚀 海外佈局：進出口損益預警系統", expanded=True):
        tab_import, tab_export = st.tabs(["📥 進口採購成本分析", "📤 外銷收益影響分析"])
        
        with tab_import:
            st.write("針對海外佈局，計算匯率波動對採購成本的影響。")
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                im_curr = st.selectbox("採購幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="im_curr")
            with ic2:
                im_base = st.number_input("基準匯率 (TWD)", value=7.10, step=0.01, format="%.4f", key="im_base")
            with ic3:
                im_amt = st.number_input(f"採購金額 ({im_curr})", value=1000000, step=10000, key="im_amt")
            
            im_impact = im_amt * (rates_dict[im_curr] - im_base)
            if im_impact > 0:
                st.error(f"⚠️ **成本增加**：台幣支出預計將增加 **{im_impact:,.0f}** 元。")
            elif im_impact < 0:
                st.success(f"✅ **成本節省**：台幣支出預計將節省 **{abs(im_impact):,.0f}** 元。")
            else:
                st.info("匯率與基準持平。")

        with tab_export:
            st.write("針對海外佈局，計算匯率波動對外銷收益的影響。")
            ex1, ex2, ex3 = st.columns(3)
            with ex1:
                ex_curr = st.selectbox("收款幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="ex_curr")
            with ex2:
                ex_base = st.number_input("基準匯率 (TWD)", value=24.00, step=0.01, format="%.4f", key="ex_base")
            with ex3:
                ex_amt = st.number_input(f"收匯金額 ({ex_curr})", value=500000, step=10000, key="ex_amt")
            
            ex_impact = ex_amt * (rates_dict[ex_curr] - ex_base)
            if ex_impact > 0:
                st.success(f"✅ **外銷紅利**：換算台幣收益將增加 **{ex_impact:,.0f}** 元。")
            elif ex_impact < 0:
                st.error(f"⚠️ **收益縮減**：台幣收益預計將縮水 **{abs(ex_impact):,.0f}** 元。")
            else:
                st.info("匯率與基準持平。")

    st.divider()

    # --- 第四層：食品生技與零售標竿股價 (4x2 完美矩陣) --- [cite: 2026-01-10, 2026-01-16]
    st.subheader("🏢 食品生技與零售標竿股價")
    if stocks_dict:
        keys = list(stocks_dict.keys())
        s_cols1 = st.columns(4)
        for i in range(min(4, len(keys))):
            name = keys[i]
            p, c = stocks_dict[name]
            s_cols1[i].metric(name, f"{p:.2f}", f"{c:+.2f}")
            
        s_cols2 = st.columns(4)
        for i in range(4, min(8, len(keys))):
            name = keys[i]
            p, c = stocks_dict[name]
            s_cols2[i-4].metric(name, f"{p:.2f}", f"{c:+.2f}")

with col_news:
    # --- 右側：產業新聞欄位 --- [cite: 2026-01-18]
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
# --- 最下方：多幣別對照矩陣 --- [cite: 2026-01-10]
st.subheader("📋 多幣別對照矩陣 (Cross Rates)")
if rates_dict:
    matrix_currencies = list(rates_dict.keys())
    matrix_data = [[round(rates_dict[row] / rates_dict[col], 4) for col in matrix_currencies] for row in matrix_currencies]
    st.dataframe(pd.DataFrame(matrix_data, index=matrix_currencies, columns=matrix_currencies), use_container_width=True)
