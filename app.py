import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime

# 1. 網頁外觀設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式修正：讓介面在深/淺模式下都美觀，並自訂側邊欄風格
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
        padding: 10px;
        border-bottom: 1px solid #ddd;
        margin-bottom: 10px;
    }
    .news-title {
        font-size: 14px;
        font-weight: bold;
        text-decoration: none;
        color: #2563eb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄：零售與餐飲產業新聞爬蟲 ---
with st.sidebar:
    st.header("📰 產業商情報告")
    st.write("零售與餐飲最新動態")
    
    # 使用 Google News RSS 抓取相關新聞
    news_url = "https://news.google.com/rss/search?q=台灣+零售+餐飲+產業&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(news_url)
    
    if feed.entries:
        for entry in feed.entries[:8]: # 顯示前 8 條新聞
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{entry.link}" target="_blank">{entry.title}</a><br>
                <small style='color: gray;'>{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("暫無即時新聞。")

# --- 主畫面標題 ---
st.title("🌍 Terry的換匯小工具")

# --- 功能分頁設定 ---
tab1, tab2 = st.tabs(["📊 匯率監控與換算", "🎙️ Podcast 數據監控"])

# --- Tab 1: 匯率功能 (保留原本功能) ---
with tab1:
    # 抓取台銀資料邏輯
    @st.cache_data(ttl=600)
    def get_bot_rates():
        url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
        try:
            response = requests.get(url, timeout=10)
            response.encoding = 'utf-8-sig'
            lines = response.text.split('\n')
            rates = {'台幣 (TWD)': 1.0}
            target_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'}
            for line in lines:
                parts = line.split(',')
                if len(parts) < 13: continue
                code = parts[0].strip()
                for k, v in target_map.items():
                    if k in code: rates[v] = float(parts[12].strip())
            return rates
        except: return None

    rates_dict = get_bot_rates()
    if rates_dict:
        # 匯率看板
        display_items = [item for item in rates_dict.items() if item[0] != '台幣 (TWD)']
        cols = st.columns(len(display_items))
        for i, (name, rate) in enumerate(display_items):
            with cols[i]:
                st.metric(name, f"{rate:.4f} TWD")
        
        st.divider()
        
        col_calc, col_chart = st.columns([1, 1.5])
        with col_calc:
            st.subheader("🔄 跨幣別快速換算")
            amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
            from_curr = st.selectbox("從", options=list(rates_dict.keys()), index=1)
            to_curr = st.selectbox("換成", options=list(rates_dict.keys()), index=0)
            if st.button("執行計算", use_container_width=True):
                res = (amt * rates_dict[from_curr]) / rates_dict[to_curr]
                st.success(f"### {res:,.2f} {to_curr}")
        
        with col_chart:
            st.subheader("📈 歷史趨勢分析")
            target_curr = st.selectbox("選擇幣別", options=[n for n in rates_dict.keys() if n != '台幣 (TWD)'])
            time_range = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
            # 歷史資料抓取 (略，使用原邏輯)
            def get_history(c_name, p):
                s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
                data = yf.download(s_map.get(c_name), period=p, interval='1d', progress=False)
                return data['Close'] if not data.empty else None
            st.line_chart(get_history(target_curr, time_range))

# --- Tab 2: Podcast 數據監控 (新功能) ---
with tab2:
    st.header("🎙️ 節目數據監控：員工編號001")
    
    # 頂部數據指標 (此處可根據您的後台數據手動更新，或未來串接 API)
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    p_col1.metric("累積不重複收聽數", "15,240", "+12%")
    p_col2.metric("每集平均下載", "1,250", "+5%")
    p_col3.metric("Apple Podcast 評分", "4.9", "⭐️")
    p_col4.metric("Spotify 追蹤人數", "2,480", "+85")

    st.divider()

    # 內容分析區
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.subheader("📢 最新集數狀態")
        # 這裡展示您最新的節目資訊
        episodes = [
            {"title": "NO.001 鼓勵去創業的人，都下地獄吧！", "date": "2025-12-01", "downloads": "2,450"},
            {"title": "NO.002 執行長的 2033 上市藍圖規劃", "date": "2025-12-15", "downloads": "1,820"},
            {"title": "NO.003 從 0 到 1：元初豆坊的創業實相", "date": "2026-01-05", "downloads": "1,540"}
        ]
        st.table(episodes)
        
    with c2:
        st.subheader("🎯 聽眾來源分佈")
        # 簡單的模擬圖表
        source_data = pd.DataFrame({
            "來源": ["Spotify", "Apple", "KKBOX", "其他"],
            "比例": [45, 35, 15, 5]
        })
        st.bar_chart(source_data.set_index("來源"))

    st.info("💡 Erica 的小提醒：執行長，目前的數據是根據您的營運目標設定的模擬格式。如果您有 Spotify for Podcasters 的專屬 API 權限，未來我們可以直接將真實數據同步過來！")
