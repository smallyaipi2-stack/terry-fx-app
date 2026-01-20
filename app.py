import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime, timedelta

# 1. 網頁基本設定 [cite: 2026-01-10]
st.set_page_config(page_title="Terry戰情室", page_icon="📈", layout="wide")

# 修正深色模式顯示：使用系統變數 var(--...) 確保顏色自動適應 [cite: 2026-01-20]
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    .status-box, .comparison-box {
        padding: 12px;
        border-radius: 8px;
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        margin-bottom: 10px;
    }
    .time-label { font-size: 12px; color: gray; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料抓取邏輯 [cite: 2026-01-18]
@st.cache_data(ttl=600)
def fetch_all_data():
    # 匯率抓取
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
    except: pass

    # 標竿股價 (8家完美矩陣) [cite: 2026-01-16]
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

    # 產業新聞 [cite: 2026-01-18]
    news = []
    try:
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass

    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_all_data()

# 3. 介面呈現 [cite: 2025-12-17]
st.title("📈 Terry戰情室")
st.write(f"執行長您好，戰情數據同步時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

col_main, col_right = st.columns([3, 1])

# --- 左側欄位邏輯 ---
with col_main:
    # 第一層：即時匯率
    st.subheader("📊 即時匯率 (對台幣)")
    if rates_dict and len(rates_dict) > 1:
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
    
    st.divider()

    # 第二層：換匯跟歷史趨勢 [cite: 2026-01-20]
    c_left, c_right = st.columns([1, 1.2])
    with c_left:
        st.subheader("🔄 快速換算")
        amt = st.number_input("試算金額", min_value=0.0, value=100.0, key="calc_amt")
        f_c = st.selectbox("來源幣別", list(rates_dict.keys()), index=1, key="f_c")
        t_c = st.selectbox("目標幣別", list(rates_dict.keys()), index=0, key="t_c")
        if st.button("立即計算", use_container_width=True):
            res = (amt * rates_dict[f_c]) / rates_dict[t_c]
            st.success(f"### {res:,.2f} {t_c}")
    
    with c_right:
        st.subheader("📈 歷史趨勢")
        target_c = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="trend_c")
        range_p = st.radio("時間範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="range_p")
        s_map = {
            '美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', 
            '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'
        }
        hist_data = yf.download(s_map.get(target_c), period=range_p, progress=False)['Close']
        if not hist_data.empty: st.line_chart(hist_data)

    st.divider()

    # 第三層：進出口預警 [cite: 2026-01-10]
    with st.expander("🚀 海外佈局：進出口損益預警系統", expanded=True):
        t_im, t_ex = st.tabs(["📥 進口採購成本分析", "📤 外銷收益影響分析"])
        with t_im:
            ic1, ic2, ic3 = st.columns(3)
            with ic1: im_curr = st.selectbox("採購幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="im_c")
            with ic2: im_base = st.number_input("基準匯率", value=7.10, format="%.4f", key="im_b")
            with ic3: im_amt = st.number_input(f"採購金額 ({im_curr})", value=1000000, key="im_a")
            imp = im_amt * (rates_dict[im_curr] - im_base)
            if imp > 0: st.error(f"⚠️ 成本預計增加 {imp:,.0f} 元")
            elif imp < 0: st.success(f"✅ 成本預計節省 {abs(imp):,.0f} 元")
        
        with t_ex:
            ec1, ec2, ec3 = st.columns(3)
            with ec1: ex_curr = st.selectbox("收款幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="ex_c")
            with ec2: ex_base = st.number_input("結算基準", value=24.00, format="%.4f", key="ex_b")
            with ec3: ex_amt = st.number_input(f"預計收款 ({ex_curr})", value=500000, key="ex_a")
            exp_imp = ex_amt * (rates_dict[ex_curr] - ex_base)
            if exp_imp > 0: st.success(f"✅ 收益預計增加 {exp_imp:,.0f} 元")
            elif exp_imp < 0: st.error(f"⚠️ 收益預計縮水 {abs(exp_imp):,.0f} 元")

    st.divider()

    # 第四層：標竿股價 (4x2 完美矩陣) [cite: 2026-01-16]
    st.subheader("🏢 食品生技與零售標竿股價")
    if stocks_dict:
        keys = list(stocks_dict.keys())
        s1 = st.columns(4)
        for i in range(4):
            n = keys[i]
            p, c = stocks_dict[n]
            s1[i].metric(n, f"{p:.2f}", f"{c:+.2f}")
        s2 = st.columns(4)
        for i in range(4, 8):
            n = keys[i]
            p, c = stocks_dict[n]
            s2[i-4].metric(n, f"{p:.2f}", f"{c:+.2f}")

# --- 右側欄位邏輯 ---
with col_right:
    # 願景里程碑 [cite: 2026-01-10]
    st.subheader("🚀 願景里程碑")
    days_left = (datetime(2033, 1, 1) - datetime.now()).days
    st.markdown(f"""
    <div class="status-box">
        <b>2033 上市目標倒數</b><br>
        <span style="font-size: 22px; color: #00A650;">{days_left:,} 天</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # 營收達標看板 (手動修改版) [cite: 2026-01-20]
    st.subheader("🎯 營收達標看板 (目標 1.5 億)")
    revenue_input = st.number_input("目前營收金額 (TWD)", value=3800000, step=100000)
    date_input = st.text_input("數據統計截至日期", value="2026-01-20")
    
    try:
        curr_dt = datetime.strptime(date_input, "%Y-%m-%d")
        day_idx = curr_dt.timetuple().tm_yday
        is_leap = (curr_dt.year % 4 == 0 and curr_dt.year % 100 != 0) or (curr_dt.year % 400 == 0)
        expected_prog = day_idx / (366 if is_leap else 365)
    except: expected_prog = 0.0

    actual_prog = min(revenue_input / 150000000, 1.0)
    st.progress(actual_prog)
    
    status_color = '#00A650' if actual_prog >= expected_prog else '#d32f2f'
    st.markdown(f"""
    <div class="comparison-box" style="border-left: 5px solid {status_color};">
        <b>{date_input} 營收進度對比</b><br>
        實際達成: <span style="color: {status_color}; font-weight:bold;">{actual_prog:.2%}</span><br>
        時間進度: {expected_prog:.2%}
    </div>
    """, unsafe_allow_html=True)
    
    if actual_prog < expected_prog: st.caption("🔴 目前業績落後於時間進度")
    else: st.caption("🟢 目前業績領先時間進度")

    st.divider()
    
    # 海外市場狀態 [cite: 2026-01-20]
    st.subheader("🌍 海外市場狀態")
    now_tw = datetime.now()
    time_jp = now_tw + timedelta(hours=1)
    time_la = now_tw - timedelta(hours=-16 if (datetime(2026,3,8) <= now_tw <= datetime(2026,11,1)) else -16) 
    # 簡易修正洛杉磯時間邏輯 (洛杉磯 UTC-8，台北 UTC+8，時差 16 小時)
    time_la = now_tw - timedelta(hours=16) 

    def get_status(h): return "營運中" if 9 <= h <= 18 else "休息中"

    st.markdown(f"""
    <div style='margin-bottom: 8px;'>
        <div class='time-label'>台北 / 新加坡 / 吉隆坡</div>
        <b>{now_tw.strftime('%H:%M')}</b> <small>({get_status(now_tw.hour)})</small>
    </div>
    <div style='margin-bottom: 8px;'>
        <div class='time-label'>東京 (TYO)</div>
        <b>{time_jp.strftime('%H:%M')}</b> <small>({get_status(time_jp.hour)})</small>
    </div>
    <div style='margin-bottom: 8px;'>
        <div class='time-label'>洛杉磯 (LAX)</div>
        <b>{time_la.strftime('%H:%M')}</b> <small>({get_status(time_la.hour)})</small>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 產業商報 [cite: 2026-01-18]
    st.subheader("📰 產業商報")
    if news_list:
        for entry in news_list:
            clean_t = entry.title.split(" - ")[0]
            st.markdown(f"<div style='padding:4px 0; border-bottom:1px solid var(--border-color);'><a href='{entry.link}' target='_blank' style='text-decoration:none; font-size:13px; color:#2563eb;'>{clean_t}</a></div>", unsafe_allow_html=True)

st.divider()
# 多幣別對照矩陣
st.subheader("📋 多幣別對照矩陣")
if rates_dict:
    matrix_c = list(rates_dict.keys())
    m_data = [[round(rates_dict[r] / rates_dict[c], 4) for c in matrix_c] for r in matrix_c]
    st.dataframe(pd.DataFrame(m_data, index=matrix_c, columns=matrix_c), use_container_width=True)
