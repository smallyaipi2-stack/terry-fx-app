import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="📈", layout="wide")

# CSS 樣式修正：美化指標與進度條
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    .status-box {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #00A650;
        background-color: var(--secondary-background-color);
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料抓取邏輯 (快取 10 分鐘)
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
    stock_targets = {
        '1216.TW': '統一', '1201.TW': '味全', '1210.TW': '大成', '1231.TW': '聯華食',
        '1227.TW': '佳格', '1707.TW': '葡萄王', '2912.TW': '統一超', '5903.TWO': '全家'
    }
    try:
        for symbol, name in stock_targets.items():
            ticker = yf.Ticker(symbol)
            info = ticker.history(period='2d')
            if len(info) >= 2:
                p, c = info['Close'].iloc[-1], info['Close'].iloc[-1] - info['Close'].iloc[-2]
                stocks[name] = (p, c)
    except: pass

    news = []
    try:
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        encoded_query = urllib.parse.quote(query)
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass

    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("📈 Terry的換匯小工具 (海外戰情室版)")
st.write(f"執行長您好，資料同步時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_right = st.columns([3, 1])

with col_main:
    # 第一層：即時匯率
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    st.divider()

    # 第二層：換匯跟歷史趨勢
    c_left, c_right = st.columns([1, 1.2])
    with c_left:
        st.subheader("🔄 快速換算")
        amt = st.number_input("金額", min_value=0.0, value=100.0, key="calc_amt")
        f_c = st.selectbox("從", list(rates_dict.keys()), index=1, key="f_c")
        t_c = st.selectbox("到", list(rates_dict.keys()), index=0, key="t_c")
        if st.button("執行計算", use_container_width=True):
            res = (amt * rates_dict[f_c]) / rates_dict[t_c]
            st.success(f"### {res:,.2f} {t_c}")
    
    with c_right:
        st.subheader("📈 歷史趨勢")
        target_c = st.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="trend_c")
        range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="range_p")
        s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
        hist = yf.download(s_map.get(target_c), period=range_p, progress=False)['Close']
        if not hist.empty: st.line_chart(hist)

    st.divider()

    # 第三層：進出口預警
    with st.expander("🚀 海外佈局：損益預警系統", expanded=True):
        t_im, t_ex = st.tabs(["📥 進口採購成本", "📤 外銷收益影響"])
        with t_im:
            st.write("計算匯率波動對海外採購成本的影響。")
            ic1, ic2, ic3 = st.columns(3)
            with ic1: im_curr = st.selectbox("採購幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4)
            with ic2: im_base = st.number_input("基準匯率", value=7.10, format="%.4f")
            with ic3: im_amt = st.number_input(f"採購金額 ({im_curr})", value=1000000)
            imp = im_amt * (rates_dict[im_curr] - im_base)
            if imp > 0: st.error(f"⚠️ 成本預計增加 {imp:,.0f} 元")
            elif imp < 0: st.success(f"✅ 成本預計節省 {abs(imp):,.0f} 元")
        
        with t_ex:
            st.write("計算匯率波動對外銷收款收益的影響。")
            ec1, ec2, ec3 = st.columns(3)
            with ec1: ex_curr = st.selectbox("收款幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6)
            with ec2: ex_base = st.number_input("預算匯率", value=24.00, format="%.4f")
            with ec3: ex_amt = st.number_input(f"預計收款 ({ex_curr})", value=500000)
            exp_imp = ex_amt * (rates_dict[ex_curr] - ex_base)
            if exp_imp > 0: st.success(f"✅ 收益預計增加 {exp_imp:,.0f} 元")
            elif exp_imp < 0: st.error(f"⚠️ 收益預計縮水 {abs(exp_imp):,.0f} 元")

    st.divider()

    # 第四層：標竿股價
    st.subheader("🏢 食品與零售標竿股價")
    if stocks_dict:
        keys = list(stocks_dict.keys())
        s1 = st.columns(4)
        for i in range(min(4, len(keys))):
            name = keys[i]
            p, c = stocks_dict[name]
            s1[i].metric(name, f"{p:.2f}", f"{c:+.2f}")
        s2 = st.columns(4)
        for i in range(4, min(8, len(keys))):
            name = keys[i]
            p, c = stocks_dict[name]
            s2[i-4].metric(name, f"{p:.2f}", f"{c:+.2f}")

# --- 右側欄位修正：填補空白並加入戰略指標 ---
with col_right:
    st.subheader("📰 產業商報")
    if news_list:
        for entry in news_list:
            clean_t = entry.title.split(" - ")[0]
            st.markdown(f"<div style='padding:5px; border-bottom:1px solid var(--border-color);'><a href='{entry.link}' target='_blank' style='text-decoration:none; font-size:13px; font-weight:bold; color:#2563eb;'>{clean_t}</a></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # 新增：執行長戰略看板
    st.subheader("🚀 執行長戰略指標")
    
    # 1. 2033 上市倒數
    target_date = datetime(2033, 1, 1)
    days_left = (target_date - datetime.now()).days
    st.markdown(f"""
    <div class="status-box">
        <b>2033 上市目標倒數</b><br>
        <span style="font-size: 20px; color: #00A650;">{days_left:,} 天</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. 2026 營收目標進度 (1.5 億)
    st.write("🎯 **2026 營收達標進度 (目標 1.5 億)**")
    current_revenue = 45000000  # 此處為模擬數據，執行長未來可串接財務報表
    revenue_target = 150000000
    progress = min(current_revenue / revenue_target, 1.0)
    st.progress(progress)
    st.caption(f"目前進度: {progress:.1%} (已達成 {current_revenue/1000000:.1f}M / 150M)")
    
    # 3. 海外市場狀態
    st.write("🌍 **市場營運狀態**")
    t_kl = datetime.now().strftime("%H:%M")
    st.caption(f"台北 / 吉隆坡 / 新加坡：{t_kl} (營運中)")

st.divider()
# 多幣別對照矩陣
st.subheader("📋 多幣別對照矩陣 (Cross Rates)")
if rates_dict:
    matrix_c = list(rates_dict.keys())
    matrix_data = [[round(rates_dict[row] / rates_dict[col], 4) for col in matrix_c] for row in matrix_c]
    st.dataframe(pd.DataFrame(matrix_data, index=matrix_c, columns=matrix_c), use_container_width=True)
