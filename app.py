import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime, timedelta

# 1. 網頁基本設定 [cite: 2025-08-10]
st.set_page_config(page_title="Terry戰情室", page_icon="📈", layout="wide")

# CSS 樣式：美化深/淺模式下的顯示
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

# 建立兩大分頁 [cite: 2026-01-20]
tab_dashboard, tab_revenue = st.tabs(["📊 戰情看板", "📅 年度業績規劃"])

# --- 分頁一：主要戰情看板 ---
with tab_dashboard:
    col_main, col_right = st.columns([3, 1])
    
    with col_main:
        # 匯率區
        st.subheader("匯率即時監控")
        if rates_dict:
            cols = st.columns(len(rates_dict)-1)
            items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
            for i, (name, rate) in enumerate(items):
                cols[i].metric(name, f"{rate:.4f}")
        
        st.divider()
        
        # 趨勢與計算
        c_l, c_r = st.columns([1, 1.2])
        with c_l:
            st.subheader("🔄 快速換算")
            amt = st.number_input("試算金額", min_value=0.0, value=100.0, key="fx_amt")
            f_c = st.selectbox("從", list(rates_dict.keys()), index=1, key="fx_f")
            t_c = st.selectbox("到", list(rates_dict.keys()), index=0, key="fx_t")
            if st.button("計算", use_container_width=True):
                st.success(f"### {(amt * rates_dict[f_c]) / rates_dict[t_c]:,.2f} {t_c}")
        
        with c_r:
            st.subheader("📈 歷史趨勢")
            tc = st.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="h_c")
            rp = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="h_p")
            sm = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(sm.get(tc), period=rp, progress=False)['Close']
            if not hist.empty: st.line_chart(hist)

        st.divider()
        
        # 預警系統
        with st.expander("🚀 海外佈局：進出口損益預警", expanded=True):
            ti, te = st.tabs(["進口採購", "外銷收益"])
            with ti:
                ic1, ic2, ic3 = st.columns(3)
                curr = ic1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="i_c")
                base = ic2.number_input("基準匯率", value=7.10, format="%.4f", key="i_b")
                a = ic3.number_input("金額", value=1000000, key="i_a")
                imp = a * (rates_dict[curr] - base)
                if imp > 0: st.error(f"⚠️ 支出預計增加 {imp:,.0f} 元")
                elif imp < 0: st.success(f"✅ 支出預計節省 {abs(imp):,.0f} 元")
            with te:
                ec1, ec2, ec3 = st.columns(3)
                curr_e = ec1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="e_c")
                base_e = ec2.number_input("預算匯率", value=24.00, format="%.4f", key="e_b")
                a_e = ec3.number_input("收款金額", value=500000, key="e_a")
                imp_e = a_e * (rates_dict[curr_e] - base_e)
                if imp_e > 0: st.success(f"✅ 收益預計增加 {imp_e:,.0f} 元")
                elif imp_e < 0: st.error(f"⚠️ 收益預計縮水 {abs(imp_e):,.0f} 元")

        st.divider()
        
        # 股價矩陣
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
        # 願景里程碑 [cite: 2026-01-10]
        st.subheader("🚀 願景里程碑")
        dl = (datetime(2033, 1, 1) - datetime.now()).days
        st.markdown(f"<div class='status-box'><b>2033 上市倒數</b><br><span style='font-size:22px; color:#00A650;'>{dl:,} 天</span></div>", unsafe_allow_html=True)
        
        st.divider()
        
        # 海外時鐘 [cite: 2026-01-20]
        st.subheader("🌍 全球時間")
        nt = datetime.now()
        tj = nt + timedelta(hours=1)
        tl = nt - timedelta(hours=16)
        def gs(h): return "營運中" if 9 <= h <= 18 else "休息中"
        st.markdown(f"<small>台北/星馬: {nt.strftime('%H:%M')} ({gs(nt.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>東京: {tj.strftime('%H:%M')} ({gs(tj.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>洛杉磯: {tl.strftime('%H:%M')} ({gs(tl.hour)})</small>", unsafe_allow_html=True)
        
        st.divider()
        
        # 產業新聞 [cite: 2026-01-18]
        st.subheader("📰 產業商報")
        for e in news_list:
            st.markdown(f"<div style='font-size:13px; margin-bottom:5px;'><a href='{e.link}' target='_blank'>{e.title.split(' - ')[0]}</a></div>", unsafe_allow_html=True)

# --- 分頁二：年度業績規劃 (新功能) --- [cite: 2026-01-20]
with tab_revenue:
    st.header("📅 年度業績與達成率追蹤")
    st.write("請在下方表格輸入各月目標與實績，系統將自動計算達成率並生成圖表。")
    
    # 建立初始資料表格
    if 'revenue_data' not in st.session_state:
        st.session_state.revenue_data = pd.DataFrame({
            "月份": [f"{i}月" for i in range(1, 13)],
            "業績目標 (TWD)": [12500000] * 12, # 預設平分 1.5 億 [cite: 2026-01-10]
            "實際營收 (TWD)": [0] * 12
        })
        # 填入目前的實績數據
        st.session_state.revenue_data.at[0, "實際營收 (TWD)"] = 3800000 # 1月目前概算 [cite: 2026-01-20]

    # 可編輯表格
    edited_df = st.data_editor(st.session_state.revenue_data, use_container_width=True, hide_index=True)
    st.session_state.revenue_data = edited_df
    
    # 計算達成率
    edited_df["達成率 (%)"] = (edited_df["實際營收 (TWD)"] / edited_df["業績目標 (TWD)"] * 100).round(2)
    
    st.divider()
    
    # 圖表呈現區
    c_chart1, c_chart2 = st.columns([2, 1])
    
    with c_chart1:
        st.subheader("📊 每月業績對比圖 (目標 vs 實績)")
        chart_data = edited_df.melt(id_vars="月份", value_vars=["業績目標 (TWD)", "實際營收 (TWD)"], var_name="類別", value_name="金額")
        # 使用 Streamlit 內建直條圖
        st.bar_chart(edited_df.set_index("月份")[["業績目標 (TWD)", "實際營收 (TWD)"]])
        st.caption("💡 藍色代表目標，橘色代表實績。您可以透過此圖觀察大小月的起伏。")

    with c_chart2:
        st.subheader("🎯 各月達成率分析")
        st.table(edited_df[["月份", "達成率 (%)"]])

st.divider()
# 矩陣放置於最下方
st.subheader("📋 多幣別對照矩陣")
if rates_dict:
    mc = list(rates_dict.keys())
    md = [[round(rates_dict[r] / rates_dict[c], 4) for c in mc] for r in mc]
    st.dataframe(pd.DataFrame(md, index=mc, columns=mc), use_container_width=True)
