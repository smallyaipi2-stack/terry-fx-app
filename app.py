import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import feedparser
import urllib.parse
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# CSS 樣式修正：美化看板與矩陣表格
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
        padding: 8px;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 5px;
    }
    .news-title {
        font-size: 14px;
        font-weight: bold;
        text-decoration: none;
        color: #2563eb;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料抓取邏輯
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
            target_map = {
                'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 
                'KRW': '韓元 (KRW)', 'MYR': '馬幣 (MYR)', 'THB': '泰銖 (THB)', 'SGD': '新幣 (SGD)'
            }
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
    except:
        pass

    # --- 新聞部分 (鎖定食力、經濟、數位時代) ---
    news_entries = []
    try:
        # 鎖定站點：食力 (foodnext.net)、經濟日報 (money.udn.com)、數位時代 (bnext.com.tw)
        query = "site:foodnext.net OR site:money.udn.com OR site:bnext.com.tw"
        kw = urllib.parse.quote(query) 
        rss_url = f"https://news.google.com/rss/search?q={kw}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        news_entries = feed.entries[:7] # 維持 7 則
    except:
        pass

    return rates, news_entries

rates_dict, news_list = fetch_all_data()

# 3. 介面呈現
st.title("🌍 Terry的換匯小工具")
st.write(f"執行長您好，系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 分成左右兩欄：[功能區 : 新聞區] = 3 : 1
col_main, col_news = st.columns([3, 1])

with col_main:
    st.subheader("📊 即時匯率看板")
    if rates_dict and len(rates_dict) > 1:
        # 儀表板
        items = [i for i in rates_dict.items() if i[0] != '台幣 (TWD)']
        cols = st.columns(len(items))
        for i, (name, rate) in enumerate(items):
            cols[i].metric(name, f"{rate:.4f}")
        
        st.divider()
        
        # 換算與圖表
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.write("🔄 **快速試算**")
            amt = st.number_input("金額", min_value=0.0, value=100.0)
            f_curr = st.selectbox("從", list(rates_dict.keys()), index=1)
            t_curr = st.selectbox("到", list(rates_dict.keys()), index=0)
            if st.button("立即試算", use_container_width=True):
                res = (amt * rates_dict[f_curr]) / rates_dict[t_curr]
                st.success(f"### {res:,.2f} {t_curr}")
        
        with c2:
            st.write("📈 **歷史分析**")
            target = st.selectbox("幣別", [n for n in rates_dict.keys() if n != '台幣 (TWD)'])
            range_p = st.radio("跨度", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
            s_map = {
                '美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', 
                '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'
            }
            hist = yf.download(s_map.get(target), period=range_p, progress=False)['Close']
            st.line_chart(hist)
    else:
        st.error("匯率資料載入中...")

with col_news:
    st.subheader("📰 產業商報")
    st.caption("食力 / 經濟 / 數位時代")
    if news_list:
        for entry in news_list:
            clean_title = entry.title.split(" - ")[0]
            st.markdown(f"""
            <div class="news-card">
                <a class="news-title" href="{entry.link}" target="_blank">{clean_title}</a><br>
                <small style='color: gray;'>{entry.published[:16]}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("載入中...")

# 4. 最下方的多幣別對照矩陣 (找回來了！)
st.divider()
st.subheader("📋 多幣別對照矩陣 (Cross Rates)")
st.write("顯示「1單位左側貨幣」可兌換多少「上方貨幣」。適用於觀察非台幣間的換算（如馬幣換新幣）。")

if rates_dict:
    matrix_currencies = list(rates_dict.keys())
    matrix_data = []
    for row_curr in matrix_currencies:
        row_values = []
        for col_curr in matrix_currencies:
            if rates_dict[row_curr] and rates_dict[col_curr]:
                val = rates_dict[row_curr] / rates_dict[col_curr]
                row_values.append(round(val, 4))
            else:
                row_values.append("-")
        matrix_data.append(row_values)
    
    df_matrix = pd.DataFrame(matrix_data, index=matrix_currencies, columns=matrix_currencies)
    st.dataframe(df_matrix, use_container_width=True)
