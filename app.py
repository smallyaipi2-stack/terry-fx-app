import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
from datetime import datetime

# 1. 網頁外觀與標題設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式：美化深/淺模式下的新聞與卡片
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
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 8px;
    }
    .news-title {
        font-size: 14px;
        font-weight: bold;
        text-decoration: none;
        color: #2563eb;
    }
    .news-meta {
        font-size: 11px;
        color: gray;
    }
    </style>
    """, unsafe_allow_html=True)

# --- A. 資料抓取區 (確保在介面渲染前完成) ---
@st.cache_data(ttl=600)
def fetch_data():
    # 抓取匯率
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
    
    # 抓取新聞 (使用精簡後的搜尋字串)
    news_entries = []
    # 關鍵字：零售, 餐飲, 植物奶, 我饗國際
    query = "零售+餐飲+植物奶+我饗國際"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        feed = feedparser.parse(rss_url)
        news_entries = feed.entries[:15]
    except: pass
    
    return rates, news_entries

rates_dict, news_list = fetch_data()

# --- B. 介面渲染區 ---
st.title("🌍 Terry的換匯小工具")
st.write(f"最後同步：{datetime.now().strftime('%H:%M:%S')}")

# 分成左右兩欄
col_left, col_right = st.columns([3, 1])

with col_left:
    if rates_dict and len(rates_dict) > 1:
        st.subheader("📊 即時匯率與試算")
        # 看板
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
        
        st.divider()
        
        # 換算與圖表
        c1, c2 = st.columns([1, 1.2])
        with c1:
            amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
            f_c = st.selectbox("從", list(rates_dict.keys()), index=1)
            t_c = st.selectbox("到", list(rates_dict.keys()), index=0)
            if st.button("立即計算", use_container_width=True):
                res = (amt * rates_dict[f_c]) / rates_dict[t_c]
                st.success(f"### {res:,.2f} {t_c}")
        
        with c2:
            target = st.selectbox("趨勢分析", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
            range_p = st.radio("跨度", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
            s_map = {'美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'}
            hist = yf.download(s_map.get(target), period=range_p, progress=False)['Close']
            st.line_chart(hist)
    else:
        st.error("匯率資料載入失敗。")

with col_right:
    st.subheader("📰 產業快訊")
    if news_list:
        for entry in news_list:
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{entry.link}" target="_blank">{entry.title}</a><br>
                <div class="news-meta">{entry.published[:16]}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔄 正在嘗試重新獲取新聞...")
        # 若快取導致空白，強制重新整理可解決
        if st.button("手動刷新新聞"):
            st.cache_data.clear()
            st.rerun()
