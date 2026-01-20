import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime, timedelta

# 1. 網頁基本設定
st.set_page_config(page_title="Terry戰情室", page_icon="📈", layout="wide")

# CSS 樣式：自動適應深淺模式，並美化表格與指標
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
                p, c = info['Close'].iloc[-1], info['Close'].iloc[-1] - info['Close'].iloc[-2]
                stocks[name] = (p, c)
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
st.title("📈 Terry戰情室")

tab_dashboard, tab_revenue = st.tabs(["📊 戰情看板", "📅 年度業績規劃"])

# --- 分頁一：主要戰情看板 ---
with tab_dashboard:
    col_main, col_right = st.columns([3, 1])
    with col_main:
        st.subheader("📊 即時匯率 (對台幣)")
        if rates_dict and len(rates_dict) > 1:
            items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
            cols = st.columns(len(items))
            for i, (name, rate) in enumerate(items):
                cols[i].metric(name, f"{rate:.4f}")
        st.divider()
        cl, cr = st.columns([1, 1.2])
        with cl:
            st.subheader("🔄 快速換算")
            amt = st.number_input("試算金額", min_value=0.0, value=100.0, key="fx_a")
            fc = st.selectbox("從", list(rates_dict.keys()), index=1, key="fx_f")
            tc = st.selectbox("到", list(rates_dict.keys()), index=0, key="fx_t")
            if st.button("計算", use_container_width=True):
                st.success(f"### {(amt * rates_dict[fc]) / rates_dict[tc]:,.2f} {tc}")
        with cr:
            st.subheader("📈 歷史趨勢")
            h_c = st.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="h_c")
            h_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="h_p")
            sm = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(sm.get(h_c), period=h_p, progress=False)['Close']
            if not hist.empty: st.line_chart(hist)
        st.divider()
        with st.expander("🚀 海外佈局預警", expanded=True):
            ti, te = st.tabs(["📥 進口採購", "📤 外銷收益"])
            with ti:
                c1, c2, c3 = st.columns(3)
                ic = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="im_c")
                ib = c2.number_input("基準", value=7.10, format="%.4f", key="im_b")
                ia = c3.number_input("金額", value=1000000, key="im_a")
                imp = ia * (rates_dict[ic] - ib)
                if imp > 0: st.error(f"⚠️ 成本增加 {imp:,.0f} 元")
                elif imp < 0: st.success(f"✅ 成本節省 {abs(imp):,.0f} 元")
            with te:
                c1, c2, c3 = st.columns(3)
                ec = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="ex_c")
                eb = c2.number_input("基準", value=24.00, format="%.4f", key="ex_b")
                ea = c3.number_input("收款", value=500000, key="ex_a")
                ex_imp = ea * (rates_dict[ec] - eb)
                if ex_imp > 0: st.success(f"✅ 收益增加 {ex_imp:,.0f} 元")
                elif ex_imp < 0: st.error(f"⚠️ 收益縮水 {abs(ex_imp):,.0f} 元")
        st.divider()
        st.subheader("🏢 食品與零售標竿股價")
        if stocks_dict:
            ks = list(stocks_dict.keys())
            s1 = st.columns(4)
            for i in range(4):
                n = ks[i]
                p, c = stocks_dict[n]
                s1[i].metric(n, f"{p:.2f}", f"{c:+.2f}")
            s2 = st.columns(4)
            for i in range(4, 8):
                n = ks[i]
                p, c = stocks_dict[n]
                s2[i-4].metric(n, f"{p:.2f}", f"{c:+.2f}")

    with col_right:
        st.subheader("🚀 願景里程碑")
        dl = (datetime(2033, 1, 1) - datetime.now()).days
        st.markdown(f"<div class='status-box'><b>2033 上市倒數</b><br><span style='font-size:22px; color:#00A650;'>{dl:,} 天</span></div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("🌍 全球時間")
        nt = datetime.now()
        tj = nt + timedelta(hours=1)
        tl = nt - timedelta(hours=16)
        def gs(h): return "營運中" if 9 <= h <= 18 else "休息中"
        st.markdown(f"<small>台北/星馬: {nt.strftime('%H:%M')} ({gs(nt.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>東京: {tj.strftime('%H:%M')} ({gs(tj.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>洛杉磯: {tl.strftime('%H:%M')} ({gs(tl.hour)})</small>", unsafe_allow_html=True)
        st.divider()
        st.subheader("📰 產業商報")
        for e in news_list:
            st.markdown(f"<div style='font-size:13px; margin-bottom:5px;'><a href='{e.link}' target='_blank'>{e.title.split(' - ')[0]}</a></div>", unsafe_allow_html=True)

# --- 分頁二：年度業績規劃 (優化版) ---
with tab_revenue:
    st.header("📅 2026 年度業績規劃與追蹤")
    st.write("請輸入各月目標與實績（單月目標預設以年度 1.4 億平均計算）。")
    
    # 建立數據結構 (使用 01, 02 確保排序正確)
    if 'revenue_data' not in st.session_state:
        target_total = 140000000
        st.session_state.revenue_data = pd.DataFrame({
            "月份": [f"{i:02d}月" for i in range(1, 13)],
            "業績目標 (TWD)": [round(target_total/12, 0)] * 12,
            "實際營收 (TWD)": [0] * 12
        })
        st.session_state.revenue_data.at[0, "實際營收 (TWD)"] = 3800000

    # 顯示編輯表格 (固定高度確保不出現內部捲軸)
    edited_df = st.data_editor(
        st.session_state.revenue_data, 
        use_container_width=True, 
        hide_index=True,
        height=475, # 12列+標頭的理想高度
        num_rows="fixed"
    )
    
    # 即時計算達成率
    edited_df["達成率 (%)"] = (edited_df["實際營收 (TWD)"] / edited_df["業績目標 (TWD)"] * 100).round(2).fillna(0)
    st.session_state.revenue_data = edited_df

    st.divider()
    
    # 圖表呈現
    c_c1, c_c2 = st.columns([2, 1])
    with c_c1:
        st.subheader("📊 每月業績對比 (目標 vs 實績)")
        # 準備圖表數據
        chart_plot = edited_df.copy().set_index("月份")[["業績目標 (TWD)", "實際營收 (TWD)"]]
        st.bar_chart(chart_plot)
        st.caption("💡 藍色：目標業績 | 橘色：目前達成。月份已依序排列。")

    with c_c2:
        st.subheader("🎯 目標達成分析")
        st.table(edited_df[["月份", "達成率 (%)"]])
        total_actual = edited_df["實際營收 (TWD)"].sum()
        st.metric("年度累計營收", f"{total_actual:,.0f}", f"{(total_actual/140000000):.2%}")

st.divider()
st.subheader("📋 多幣別對照矩陣")
if rates_dict:
    mc = list(rates_dict.keys())
    md = [[round(rates_dict[r] / rates_dict[c], 4) for c in mc] for r in mc]
    st.dataframe(pd.DataFrame(md, index=mc, columns=mc), use_container_width=True)
