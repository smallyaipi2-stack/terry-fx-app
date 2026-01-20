import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime

# 1. 網頁外觀設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式：自動適應深淺模式，並美化新聞卡片
st.markdown("""
    <style>
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    .news-container {
        max-height: 800px;
        overflow-y: auto;
        padding-right: 10px;
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
st.write(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 建立主頁面佈局：左側功能區(3) vs 右側新聞區(1) ---
col_main, col_news = st.columns([3, 1])

# --- 左側功能區 ---
with col_main:
    tab1, tab2 = st.tabs(["📊 匯率監控與換算", "🎙️ Podcast 數據監控"])
    
    # Tab 1: 匯率功能
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
                        if k in code: rates[v] = float(parts[12].strip())
                return rates
            except: return None

        rates_dict = get_bot_rates()
        if rates_dict:
            # 即時匯率
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
                amt = st.number_input("金額", min_value=0.0, value=100.0)
                f_curr = st.selectbox("從", list(rates_dict.keys()), index=1)
                t_curr = st.selectbox("換成", list(rates_dict.keys()), index=0)
                if st.button("計算", use_container_width=True):
                    res = (amt * rates_dict[f_curr]) / rates_dict[t_curr]
                    st.success(f"### {res:,.2f} {t_
