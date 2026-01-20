import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime

# 1. 網頁外觀設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式：智慧適應深淺模式，美化右側新聞欄位
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
    .news-source {
        font-size: 12px;
        color: gray;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 資料抓取邏輯 (移至頂層確保優先執行) ---
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
    except Exception as e:
        return None

# 預先取得匯率資料
rates_dict = get_bot_rates()

# --- 主畫面標題 ---
st.title("🌍 Terry的換匯小工具")
st.write(f"系統狀態：穩定運行 | 資料時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 建立佈局：左側功能區(3) vs 右側新聞區(1) ---
col_main, col_news = st.columns([3, 1])

# --- 左側主要功能區 ---
with col_main:
    if rates_dict:
        # 即時匯率看板
        st.subheader("📊 即時匯率看板 (對台幣)")
        display_items = [item for item in rates_dict.items() if item[0] != '台幣 (TWD)']
        cols = st.columns(len(display_items))
        for i, (name, rate) in enumerate(display_items):
            with cols[i]:
                st.metric(name, f"{rate:.4f} TWD")
        
        st.divider()
        
        # 換算與歷史圖表
        c_calc, c_chart = st.columns([1, 1.2])
        with c_calc:
            st.subheader("🔄 快速試算")
            amt = st.number_input("金額", min_value=0.0, value=100.0)
            f_curr = st.selectbox("來源幣別", list(rates_dict.keys()), index=1)
            t_curr = st.selectbox("目標幣別", list(rates_dict.keys()), index=0)
            
            if st.button("立即計算", use_container_width=True):
                res = (amt * rates_dict[f_curr]) / rates_dict[t_curr]
                st.success(f"### {res:,.2f} {t_curr}")
        
        with c_chart:
            st.subheader("📈 歷史趨勢")
            target = st.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
            range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
            
            def get_h(curr, p):
                s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
                symbol = s_map.get(curr)
                data = yf.download(symbol, period=p, progress=False)
                return data['Close'] if not data.empty else None
            
            h_data = get_h(target, range_p)
            if h_data is not None:
                st.line_chart(h_data)
    else:
        st.error("無法取得即時匯率資料，請確認網路連線。")

# --- 右側：強化版產業商情報告 ---
with col_news:
    st.header("📰 產業快訊")
    # 增加更多關鍵字，優化抓取內容
    search_keywords = "台灣+零售+餐飲+連鎖+我饗國際+元初豆坊+植物奶+食品科技"
    rss_url = f"https://news.google.com/rss/search?q={search_keywords}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        # 顯示最新 15 則新聞
        for entry in feed.entries[:15]:
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{entry.link}" target="_blank">{entry.title}</a><br>
                <div class="news-source">{entry.source.get('title', '新聞來源')} | {entry.published[:16]}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("暫無相關產業新聞。")
