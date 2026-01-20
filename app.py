import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime

# 1. 網頁外觀設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式：智慧適應深淺模式，並美化新聞與卡片佈局
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    .news-card {
        padding: 12px;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 12px;
    }
    .news-title {
        font-size: 15px;
        font-weight: bold;
        text-decoration: none;
        color: #2563eb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 主標題 ---
st.title("🌍 Terry的換匯小工具")
st.write(f"系統狀態：正常運行 | 最後同步：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 建立佈局：左側功能區(3) vs 右側新聞區(1) ---
col_main, col_news = st.columns([3, 1])

# --- 左側主要功能區 ---
with col_main:
    tab1, tab2 = st.tabs(["📊 匯率監控與換算", "🎙️ Podcast 數據監控"])
    
    # --- Tab 1: 匯率分析 ---
    with tab1:
        @st.cache_data(ttl=600)
        def get_bot_rates():
            url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
            try:
                response = requests.get(url, timeout=10)
                response.encoding = 'utf-8-sig'
                lines = response.text.split('\n')
                rates = {'台幣 (TWD)': 1.0}
                target_map = {
                    'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 
                    'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'
                }
                for line in lines:
                    parts = line.split(',')
                    if len(parts) < 13: continue
                    code = parts[0].strip()
                    for k, v in target_map.items():
                        if k in code:
                            rates[v] = float(parts[12].strip())
                return rates
            except: return None

        rates_dict = get_bot_rates()
        if rates_dict:
            st.subheader("📊 即時匯率看板")
            display_items = [item for item in rates_dict.items() if item[0] != '台幣 (TWD)']
            cols = st.columns(len(display_items))
            for i, (name, rate) in enumerate(display_items):
                with cols[i]:
                    st.metric(name, f"{rate:.4f} TWD")
            
            st.divider()
            
            c_calc, c_chart = st.columns([1, 1.2])
            with c_calc:
                st.subheader("🔄 快速換算")
                amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
                f_curr = st.selectbox("來源幣別", list(rates_dict.keys()), index=1)
                t_curr = st.selectbox("目標幣別", list(rates_dict.keys()), index=0)
                
                # 執行計算按鈕
                if st.button("立即計算", use_container_width=True):
                    res = (amt * rates_dict[f_curr]) / rates_dict[t_curr]
                    st.success(f"### {res:,.2f} {t_curr}")
            
            with c_chart:
                st.subheader("📈 歷史趨勢")
                target = st.selectbox("分析幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
                range_p = st.radio("時間範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
                
                def get_h(curr, p):
                    s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
                    symbol = s_map.get(curr)
                    data = yf.download(symbol, period=p, progress=False)
                    return data['Close'] if not data.empty else None
                
                hist_data = get_h(target, range_p)
                if hist_data is not None:
                    st.line_chart(hist_data)

    # --- Tab 2: Podcast 監控 (員工編號001) ---
    with tab2:
        st.header("🎙️ 節目監控：員工編號001")
        p_cols = st.columns(4)
        p_cols[0].metric("不重複收聽數", "15,240", "+12%")
        p_cols[1].metric("每集平均下載", "1,250", "+5%")
        p_cols[2].metric("Apple Podcast 評分", "4.9", "⭐️")
        p_cols[3].metric("Spotify 追蹤數", "2,480", "+85")
        
        st.divider()
        st.subheader("📢 集數摘要分析")
        eps = [
            {"標題": "NO.001 鼓勵去創業的人，都下地獄吧！", "日期": "2025-12-01", "下載": "2,450"},
            {"標題": "NO.002 執行長的 2033 上市藍圖規劃", "日期": "2025-12-15", "下載": "1,820"},
            {"標題": "NO.003 從 0 到 1：元初豆坊的創業實相", "日期": "2026-01-05", "下載": "1,540"}
        ]
        st.table(eps)

# --- 右側：產業商情報告 ---
with col_news:
    st.header("📰 產業商報")
    st.caption("零售、餐飲與我饗國際動態")
    
    # 抓取 Google News RSS
    rss_url = "https://news.google.com/rss/search?q=台灣+零售+餐飲+我饗國際+元初豆坊&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        # 顯示最新 12 則
        for entry in feed.entries[:12]:
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{entry.link}" target="_blank">{entry.title}</a><br>
                <small style='color: gray;'>{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("目前無相關產業報導。")
