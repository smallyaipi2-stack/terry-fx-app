import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
import altair as alt
import os
from datetime import datetime, timedelta

# 1. 網頁基本設定 [cite: 2025-08-10]
st.set_page_config(page_title="Terry戰情室", page_icon="📈", layout="wide")

# 定義常數與路徑
DATA_FILE = "revenue_persistence.csv"
TARGET_TOTAL = 140000000

# 2. 記憶功能函數
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            df["月份"] = df["月份"].apply(lambda x: f"{int(str(x).replace('月','')):02d}月")
            return df
        except: pass
    return pd.DataFrame({
        "月份": [f"{i:02d}月" for i in range(1, 13)],
        "業績目標 (TWD)": [round(TARGET_TOTAL/12, 0)] * 12,
        "實際營收 (TWD)": [0] * 12
    })

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ 數據已存入記憶體！")

# 初始化資料
if 'revenue_data' not in st.session_state:
    st.session_state.revenue_data = load_data()

total_actual_revenue = st.session_state.revenue_data["實際營收 (TWD)"].sum()

# CSS 樣式修正
st.markdown("""
    <style>
    .stMetric { background-color: var(--secondary-background-color); padding: 10px; border-radius: 10px; border: 1px solid var(--border-color); }
    .status-box, .comparison-box { padding: 12px; border-radius: 8px; background-color: var(--secondary-background-color); border: 1px solid var(--border-color); margin-bottom: 10px; }
    .time-label { font-size: 12px; color: gray; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

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

with tab_dashboard:
    col_main, col_right = st.columns([3, 1])
    with col_main:
        st.subheader("📊 即時匯率 (對台幣)")
        if rates_dict:
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
            if st.button("立即計算", use_container_width=True):
                res = (amt * rates_dict[fc]) / rates_dict[tc]
                st.success(f"### {res:,.2f} {tc}")
        
        with cr:
            st.subheader("📈 歷史趨勢")
            h_c = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="h_c")
            h_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="h_p")
            sm = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(sm.get(h_c), period=h_p, progress=False)['Close']
            if not hist.empty: st.line_chart(hist)

        st.divider()
        with st.expander("🚀 海外佈局：進出口預警系統", expanded=True):
            ti, te = st.tabs(["📥 進口採購成本分析", "📤 外銷收益影響分析"])
            with ti:
                c1, c2, c3 = st.columns(3)
                curr_im = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="im_c")
                base_im = c2.number_input("基準匯率", value=7.10, format="%.4f", key="im_b")
                amt_im = c3.number_input("金額", value=1000000, key="im_a")
                imp_im = amt_im * (rates_dict[curr_im] - base_im)
                if imp_im > 0: st.error(f"⚠️ 支出預計增加 {imp_im:,.0f} 元")
                elif imp_im < 0: st.success(f"✅ 支出預計節省 {abs(imp_im):,.0f} 元")
            with te:
                c1, c2, c3 = st.columns(3)
                curr_ex = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="ex_c")
                base_ex = c2.number_input("預算匯率", value=24.00, format="%.4f", key="ex_b")
                amt_ex = c3.number_input("收匯金額", value=500000, key="ex_a")
                imp_ex = amt_ex * (rates_dict[curr_ex] - base_ex)
                if imp_ex > 0: st.success(f"✅ 收益預計增加 {imp_ex:,.0f} 元")
                elif imp_ex < 0: st.error(f"⚠️ 收益預計縮水 {abs(imp_ex):,.0f} 元")

        st.divider()
        st.subheader("🏢 食品生技與零售標竿股價")
        if stocks_dict:
            ks = list(stocks_dict.keys())
            s1 = st.columns(4)
            for i in range(4):
                n = ks[i]; p, c = stocks_dict[n]
                s1[i].metric(n, f"{p:,.2f}", f"{c:+,.2f}")
            s2 = st.columns(4)
            for i in range(4, 8):
                n = ks[i]; p, c = stocks_dict[n]
                s2[i-4].metric(n, f"{p:,.2f}", f"{c:+,.2f}")
        
        st.divider()
        st.subheader("📋 多幣別對照矩陣")
        if rates_dict:
            mc = list(rates_dict.keys())
            md = [[round(rates_dict[r] / rates_dict[c], 4) for c in mc] for r in mc]
            st.dataframe(pd.DataFrame(md, index=mc, columns=mc), use_container_width=True)

    with col_right:
        st.subheader("🚀 願景里程碑")
        dl = (datetime(2033, 1, 1) - datetime.now()).days
        st.markdown(f"<div class='status-box'><b>2033 上市倒數</b><br><span style='font-size:22px; color:#00A650;'>{dl:,} 天</span></div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🎯 營收達標看板 (目標 1.4 億)")
        st.metric("目前累計營收 (TWD)", f"{total_actual_revenue:,.0f}")
        # 時間進度計算
        curr_dt = datetime.now(); day_idx = curr_dt.timetuple().tm_yday
        is_leap = (curr_dt.year % 4 == 0 and curr_dt.year % 100 != 0) or (curr_dt.year % 400 == 0)
        expected_prog = day_idx / (366 if is_leap else 365)
        actual_prog = min(total_actual_revenue / TARGET_TOTAL, 1.0)
        st.progress(actual_prog)
        sc = '#00A650' if actual_prog >= expected_prog else '#d32f2f'
        st.markdown(f"<div class='comparison-box' style='border-left:5px solid {sc};'>實際達成: <b>{actual_prog:.2%}</b><br>時間進度: {expected_prog:.2%}</div>", unsafe_allow_html=True)

        st.divider()
        st.subheader("🌍 全球時間")
        nt = datetime.now(); tj = nt + timedelta(hours=1); tl = nt - timedelta(hours=16)
        def gs(h): return "營運中" if 9 <= h <= 18 else "休息中"
        st.markdown(f"<small>台北/星馬: {nt.strftime('%H:%M')} ({gs(nt.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>東京: {tj.strftime('%H:%M')} ({gs(tj.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>洛杉磯: {tl.strftime('%H:%M')} ({gs(tl.hour)})</small>", unsafe_allow_html=True)
        st.divider()
        st.subheader("📰 產業商報")
        for e in news_list: st.markdown(f"<div style='font-size:13px; margin-bottom:5px;'><a href='{e.link}' target='_blank'>{e.title.split(' - ')[0]}</a></div>", unsafe_allow_html=True)

with tab_revenue:
    st.header("📅 年度業績規劃與追蹤")
    st.write("輸入數據後請務必點擊『儲存目前業績數據』。")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        # 使用 column_config 設定表格數字格式 [cite: 2026-01-20]
        edited_df = st.data_editor(
            st.session_state.revenue_data, 
            use_container_width=True, 
            hide_index=True, 
            height=475,
            column_config={
                "業績目標 (TWD)": st.column_config.NumberColumn(format="%d"),
                "實際營收 (TWD)": st.column_config.NumberColumn(format="%d")
            }
        )
    
    with col_t2:
        if st.button("💾 儲存目前業績數據", use_container_width=True):
            save_data(edited_df)
            st.session_state.revenue_data = edited_df
            st.rerun()
        st.divider()
        total_a = edited_df["實際營收 (TWD)"].sum()
        st.metric("年度總實績", f"{total_a:,.0f}")
        st.metric("年度總達成率", f"{(total_a/TARGET_TOTAL):.2%}")

    st.divider()
    edited_df["達成率 (%)"] = (edited_df["實際營收 (TWD)"] / edited_df["業績目標 (TWD)"] * 100).round(2).fillna(0)
    c_c1, c_c2 = st.columns([2.5, 1])
    with c_c1:
        chart_data = edited_df.melt(id_vars=["月份"], value_vars=["實際營收 (TWD)", "業績目標 (TWD)"], var_name="類型", value_name="金額")
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('月份:N'),
            y=alt.Y('金額:Q', axis=alt.Axis(format=',.0f', title='金額 (TWD)')),
            color=alt.Color('類型:N', scale=alt.Scale(domain=['實際營收 (TWD)', '業績目標 (TWD)'], range=['#F58518', '#4C78A8'])),
            xOffset='類型:N',
            tooltip=['月份', '類型', alt.Tooltip('金額', format=',.0f')]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)
    with c_c2:
        disp_df = edited_df[["月份", "達成率 (%)"]].copy()
        disp_df["達成率 (%)"] = disp_df["達成率 (%)"].map('{:.2f}%'.format)
        st.table(disp_df)
