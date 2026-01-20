import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. 網頁外觀與標題設定 (已修改標題)
st.set_page_config(page_title="Terry的換匯小工具", page_icon="🌍", layout="wide")

# 2. CSS 樣式修正 (關鍵修正)
# 改用 Streamlit 的 CSS 變數 (var(--...))，讓顏色能自動適應深/淺模式
st.markdown("""
    <style>
    /* 移除強制背景色，改用變數讓系統自動適應 */
    .stMetric {
        background-color: var(--secondary-background-color); /* 自動切換深淺背景 */
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color); /* 加入邊框增加層次感 */
    }
    /* 調整標題顏色，讓它在深色模式下也能自動變亮 */
    h1, h2, h3 {
        color: var(--text-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 主標題 (已修改)
st.title("🌍 Terry的換匯小工具")
st.write(f"資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 數據來源：台灣銀行 & Yahoo Finance")

# 3. 抓取台銀即時資料 (邏輯不變)
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
                    try:
                        val = parts[12].strip()
                        rates[v] = float(val) if val else None
                    except: rates[v] = None
        return rates
    except: return None

# 4. 抓取歷史資料 (邏輯不變)
def get_history(currency_name, period):
    symbol_map = {
        '美金 (USD)': 'USDTWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X',
        '韓元 (KRW)': 'KRWTWD=X', '馬幣 (MYR)': 'MYRTWD=X', '泰銖 (THB)': 'THBTWD=X', '新幣 (SGD)': 'SGDTWD=X'
    }
    symbol = symbol_map.get(currency_name)
    data = yf.download(symbol, period=period, interval='1d', progress=False)
    return data['Close'] if not data.empty else None

rates_dict = get_bot_rates()

if rates_dict:
    # --- 區塊一：即期匯率看板 ---
    display_items = [item for item in rates_dict.items() if item[0] != '台幣 (TWD)']
    cols = st.columns(len(display_items))
    for i, (name, rate) in enumerate(display_items):
        with cols[i]:
            if rate:
                st.metric(name, f"{rate:.4f} TWD")
            else:
                st.metric(name, "查無資料")

    st.divider()

    # --- 區塊二：換算與趨勢 ---
    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.subheader("🔄 跨幣別快速換算")
        amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
        from_curr = st.selectbox("從", options=list(rates_dict.keys()), index=1)
        to_curr = st.selectbox("換成", options=list(rates_dict.keys()), index=0)
        
        if st.button("執行計算", use_container_width=True):
            if rates_dict[from_curr] and rates_dict[to_curr]:
                res = (amt * rates_dict[from_curr]) / rates_dict[to_curr]
                st.success(f"### {res:,.2f} {to_curr}")
                st.caption(f"匯率基準：1 {from_curr} ≈ {(rates_dict[from_curr]/rates_dict[to_curr]):.4f} {to_curr}")
            else:
                st.error("計算失敗，部分匯率資料缺失。")

    with col_right:
        st.subheader("📈 歷史趨勢分析")
        target_curr = st.selectbox("選擇幣別", options=[n for n in rates_dict.keys() if n != '台幣 (TWD)'])
        time_range = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
        hist_data = get_history(target_curr, time_range)
        if hist_data is not None:
            # 讓圖表顏色也自動適應，淺色用藍，深色用淺藍
            st.line_chart(hist_data) 
        else:
            st.info("資料載入中，請稍後再試。")

    st.divider()

    # --- 區塊三：多幣別對照矩陣 ---
    st.subheader("📋 多幣別對照矩陣 (Cross Rates)")
    st.write("顯示「1單位左側貨幣」可兌換多少「上方貨幣」。")
    
    matrix_currencies = [n for n in rates_dict.keys()]
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

else:
    st.error("無法連線至銀行端，請稍後再試。")
