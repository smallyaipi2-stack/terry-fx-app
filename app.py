import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
import altair as alt
import os
from datetime import datetime, timedelta

# 1. 網頁基本設定
st.set_page_config(page_title="Terry戰情室", page_icon="📈", layout="wide")

# 定義常數與路徑
DATA_FILE = "revenue_persistence.csv"
TARGET_TOTAL = 140000000

# 2. 記憶功能函數
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            return df
        except: pass
    return pd.DataFrame({
        "月份": [f"{i:02d}月" for i in range(1, 13)],
        "業績目標 (TWD)": [round(TARGET_TOTAL/12, 0)] * 12,
        "實際營收 (TWD)": [0] * 12
    })

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ 數據已成功存入記憶體！")

# 初始化數據
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
def fetch_external_info():
    rates = {'台幣 (TWD)': 1.0}
    try:
        r = requests.get("https://rate.bot.com.tw/xrt/flcsv/0/day", timeout=10)
        r.encoding = 'utf-8-sig'
        for line in r.text.split('\n'):
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            t_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'}
            for k, v in t_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except: pass

    stocks = {}
    s_targets = {'1216.TW': '統一', '1201.TW': '味全', '1210.TW': '大成', '1231.TW': '聯華食', '1227.TW': '佳格', '1707.TW': '葡萄王', '2912.TW': '統一超', '5903.TWO': '全家'}
    try:
        for sym, name in s_targets.items():
            tk = yf.Ticker(sym); info = tk.history(period='2d')
            if len(info) >= 2:
                p, c = info['Close'].iloc[-1], info['Close'].iloc[-1] - info['Close'].iloc[-2]
                stocks[name] = (p, c)
    except: pass

    news = []
    try:
        q = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        news = feed.entries[:7]
    except: pass
    return rates, stocks, news

rates_dict, stocks_dict, news_list = fetch_external_info()

# 3. 介面呈現
st.title("📈 Terry戰情室")
tab1, tab2 = st.tabs(["📊 戰情看板", "📅 年度業績規劃"])

# --- Tab 1: 戰情看板 ---
with tab1:
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.subheader("📊 即時匯率 (對台幣)")
        if rates_dict:
            it = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
            cs = st.columns(len(it))
            for i, (n, r) in enumerate(it): cs[i].metric(n, f"{r:.4f}")
        
        st.divider()
        cl, cr = st.columns([1, 1.2])
        with cl:
            st.subheader("🔄 快速換算")
            a_fx = st.number_input("試算金額", min_value=0.0, value=100.0, key="fxa")
            f_fx = st.selectbox("從", list(rates_dict.keys()), index=1, key="fxf")
            t_fx = st.selectbox("到", list(rates_dict.keys()), index=0, key="fxt")
            if st.button("立即計算", use_container_width=True):
                st.success(f"### {(a_fx * rates_dict[f_fx]) / rates_dict[t_fx]:,.2f} {t_fx}")
        with cr:
            st.subheader("📈 歷史趨勢")
            hc = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], key="hc")
            hp = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, key="hp")
            sm = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(sm.get(hc), period=hp, progress=False)['Close']
            if not hist.empty: st.line_chart(hist)
        
        st.divider()
        with st.expander("🚀 海外佈局：進出口損益預警系統", expanded=True):
            t_im, t_ex = st.tabs(["📥 進口採購成本分析", "📤 外銷收益影響分析"])
            with t_im:
                c1, c2, c3 = st.columns(3)
                curr_i = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=4, key="imc")
                base_i = c2.number_input("基準匯率", value=7.10, format="%.4f", key="imb")
                amt_i = c3.number_input("金額", value=1000000, key="ima")
                imp_i = amt_i * (rates_dict[curr_i] - base_i)
                if imp_i > 0: st.error(f"⚠️ 支出預計增加 {imp_i:,.0f} 元")
                elif imp_i < 0: st.success(f"✅ 支出預計節省 {abs(imp_i):,.0f} 元")
            with t_ex:
                c1, c2, c3 = st.columns(3)
                curr_e = c1.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'], index=6, key="exc")
                base_e = c2.number_input("預算匯率", value=24.00, format="%.4f", key="exb")
                amt_e = c3.number_input("收匯金額", value=500000, key="exa")
                imp_e = amt_e * (rates_dict[curr_e] - base_e)
                if imp_e > 0: st.success(f"✅ 收益預計增加 {imp_e:,.0f} 元")
                elif imp_e < 0: st.error(f"⚠️ 收益預計縮水 {abs(imp_e):,.0f} 元")
        
        st.divider()
        st.subheader("🏢 食品生技與零售標竿股價")
        if stocks_dict:
            k_list = list(stocks_dict.keys())
            s_row1 = st.columns(4)
            for i in range(4):
                nk = k_list[i]; pk, ck = stocks_dict[nk]
                s_row1[i].metric(nk, f"{pk:,.2f}", f"{ck:+,.2f}")
            s_row2 = st.columns(4)
            for i in range(4, 8):
                nk = k_list[i]; pk, ck = stocks_dict[nk]
                s_row2[i-4].metric(nk, f"{pk:,.2f}", f"{ck:+,.2f}")
        
        st.divider()
        st.subheader("📋 多幣別對照矩陣")
        if rates_dict:
            m_c = list(rates_dict.keys()); m_d = [[round(rates_dict[r] / rates_dict[c], 4) for c in m_c] for r in m_c]
            st.dataframe(pd.DataFrame(m_d, index=m_c, columns=m_c), use_container_width=True)

    with col_r:
        st.subheader("🚀 願景里程碑")
        days_l = (datetime(2033, 1, 1) - datetime.now()).days
        st.markdown(f"<div class='status-box'><b>2033 上市目標倒數</b><br><span style='font-size:22px; color:#00A650;'>{days_l:,} 天</span></div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🎯 營收達成率 (目標 1.4 億)")
        st.metric("目前累計營收 (TWD)", f"{total_actual_revenue:,.0f}")
        
        dt_now = datetime.now(); dy_idx = dt_now.timetuple().tm_yday
        is_l = (dt_now.year % 4 == 0 and dt_now.year % 100 != 0) or (dt_now.year % 400 == 0)
        exp_p = dy_idx / (366 if is_l else 365)
        act_p = min(total_actual_revenue / TARGET_TOTAL, 1.0)
        st.progress(act_p)
        s_color = '#00A650' if act_p >= exp_p else '#d32f2f'
        st.markdown(f"<div class='comparison-box' style='border-left:5px solid {s_color};'>實際達成: <b>{act_p:.2%}</b><br>時間進度: {exp_p:.2%}</div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🌍 全球時間")
        nt = datetime.now(); tj = nt + timedelta(hours=1); tl = nt - timedelta(hours=16)
        def gs(h): return "營運中" if 9 <= h <= 18 else "休息中"
        st.markdown(f"<small>台北/星馬: {nt.strftime('%H:%M')} ({gs(nt.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>東京: {tj.strftime('%H:%M')} ({gs(tj.hour)})</small>", unsafe_allow_html=True)
        st.markdown(f"<small>洛杉磯: {tl.strftime('%H:%M')} ({gs(tl.hour)})</small>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📰 產業商報")
        for ne in news_list: st.markdown(f"<div style='font-size:13px; margin-bottom:5px;'><a href='{ne.link}' target='_blank'>{ne.title.split(' - ')[0]}</a></div>", unsafe_allow_html=True)

# --- Tab 2: 年度業績規劃 (千分位與小數點優化) ---
with tab2:
    st.header("📅 年度業績與達成率追蹤")
    st.write("請輸入各月數據。系統會即時計算達成率，修改後請點擊儲存。")
    
    c_edit, c_save = st.columns([3, 1])
    
    with c_edit:
        # 表格編輯區：使用 "%,d" 實現千分位分隔
        edited_df = st.data_editor(
            st.session_state.revenue_data, 
            use_container_width=True, 
            hide_index=True, 
            height=475,
            column_config={
                "業績目標 (TWD)": st.column_config.NumberColumn(format="%,d"),
                "實際營收 (TWD)": st.column_config.NumberColumn(format="%,d")
            }
        )
        
        # 即時計算達成率 (四捨五入至小數點後兩位)
        edited_df["達成率 (%)"] = (edited_df["實際營收 (TWD)"] / edited_df["業績目標 (TWD)"] * 100).round(2).fillna(0)
        st.session_state.revenue_data = edited_df

    with c_save:
        if st.button("💾 儲存並同步數據", use_container_width=True):
            save_data(edited_df)
            st.rerun()
        st.divider()
        sum_actual = edited_df["實際營收 (TWD)"].sum()
        st.metric("年度總實績", f"{sum_actual:,.0f}")
        st.metric("年度總達成率", f"{(sum_actual/TARGET_TOTAL):.2%}")

    st.divider()
    
    # 圖表呈現
    c_chart1, c_chart2 = st.columns([2.5, 1])
    with c_chart1:
        st.subheader("📊 每月業績對比 (左實績 vs 右目標)")
        c_long = edited_df.melt(id_vars=["月份"], value_vars=["實際營收 (TWD)", "業績目標 (TWD)"], var_name="類型", value_name="金額")
        chart = alt.Chart(c_long).mark_bar().encode(
            x=alt.X('月份:N'),
            y=alt.Y('金額:Q', axis=alt.Axis(format=',.0f')),
            color=alt.Color('類型:N', scale=alt.Scale(domain=['實際營收 (TWD)', '業績目標 (TWD)'], range=['#F58518', '#4C78A8'])),
            xOffset='類型:N',
            tooltip=['月份', '類型', alt.Tooltip('金額', format=',.0f')]
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

    with c_chart2:
        st.subheader("🎯 目標達成分析")
        # 顯示包含小數點後兩位的達成率表格
        disp_df = edited_df[["月份", "達成率 (%)"]].copy()
        disp_df["達成率 (%)"] = disp_df["達成率 (%)"].map('{:,.2f}%'.format)
        st.table(disp_df)
