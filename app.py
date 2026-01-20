import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# 2. 抓取匯率與新聞資料 (簡化邏輯)
@st.cache_data(ttl=600)
def fetch_all_data():
    # --- 匯率部分 ---
    rates = {'台幣 (TWD)': 1.0}
    try:
        r = requests.get("https://rate.bot.com.tw/xrt/flcsv/0/day", timeout=10)
        r.encoding = 'utf-8-sig'
        for line in r.text.split('\n'):
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            # 目標幣別清單
            target_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'}
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except:
        pass

    # --- 新聞部分 (簡化關鍵字) ---
    news_entries = []
    try:
        # 只抓取最核心的關鍵字，並確保編碼正確
        kw = urllib.parse.quote("元初豆坊 植物奶") 
        rss_url = f"https://news.google.com/rss/search?q={kw}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        news_entries = feed.entries[:10] # 顯示前 10 則
    except:
        pass

    return rates, news_entries

rates_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("🌍 Terry的換匯小工具")
st.write(f"執行長您好，目前系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 分成左右兩欄：[匯率工具 : 產業新聞] = 3 : 1
col_left, col_right = st.columns([3, 1])

with col_left:
    st.subheader("📊 匯率看板與試算")
    if rates_dict and len(rates_dict) > 1:
        # 看板顯示
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
        
        st.divider()
        
        # 換算區與圖表區
        c_l, c_r = st.columns([1, 1.2])
        with c_l:
            amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
            f_c = st.selectbox("來源幣別", list(rates_dict.keys()), index=1)
            t_c = st.selectbox("目標幣別", list(rates_dict.keys()), index=0)
            if st.button("立即試算", use_container_width=True):
                res = (amt * rates_dict[f_c]) / rates_dict[t_c]
                st.success(f"### {res:,.2f} {t_c}")
        
        with c_r:
            target = st.selectbox("查看趨勢", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
            range_p = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
            # Yahoo Finance 代碼對照
            s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(s_map.get(target), period=range_p, progress=False)['Close']
            st.line_chart(hist)
    else:
        st.error("匯率資料讀取中，請稍候。")

with col_right:
    st.subheader("📰 產業快訊")
    if news_list:
        for entry in news_list:
            st.markdown(f"""
            <div style='padding: 8px; border-bottom: 1px solid #ddd; margin-bottom: 5px;'>
                <a href='{entry.link}' target='_blank' style='text-decoration: none; font-size: 14px; font-weight: bold; color: #2563eb;'>{entry.title}</a><br>
                <small style='color: gray;'>{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("目前無相關新聞或正在加載中...")
        if st.button("強制刷新新聞區"):
            st.cache_data.clear()
            st.rerun()
