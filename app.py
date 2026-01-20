import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

# 1. 網頁外觀視覺優化 (自定義商務藍綠配色)
st.set_page_config(page_title="我饗國際：全球財務決策系統", page_icon="🌍", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h1, h2, h3 { color: #1e3a8a; } /* 深藍色標題 */
    </style>
    """, unsafe_allow_html=True)

st.title("🌍 我饗國際：執行長專屬全球財務監控系統")
st.write(f"資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 數據來源：台灣銀行 & Yahoo Finance")

# 2. 抓取台銀即時資料
@st.cache_data(ttl=600)
def get_bot_rates():
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8-sig'
        lines = response.text.split('\n')
        rates = {'台幣 (TWD)': 1.0}
        # 加入新幣 (SGD)
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

# 3. 抓取歷史資料
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
            st.metric(name, f"{rate:.4f} TWD")

    st.divider()

    # --- 區塊二：換算與趨勢 ---
    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.subheader("🔄 跨幣別快速換算")
        amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
        from_curr = st.selectbox("從", options=list(rates_dict.keys()), index=1)
        to_curr = st.selectbox("換成", options=list(rates_dict.keys()), index=0)
        
        if st.button("執行計算", use_container_width=True):
            res = (amt * rates_dict[from_curr]) / rates_dict[to_curr]
            st.success(f"### {res:,.2f} {to_curr}")

    with col_right:
        st.subheader("📈 歷史趨勢分析")
        target_curr = st.selectbox("選擇幣別", options=[n for n in rates_dict.keys() if n != '台幣 (TWD)'])
        time_range = st.radio("範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True)
        hist_data = get_history(target_curr, time_range)
        if hist_data is not None:
            st.line_chart(hist_data, color="#2563eb") # 使用商務藍

    st.divider()

    # --- 區塊三：多幣別對照矩陣 (本次新增) ---
    st.subheader("📋 多幣別對照矩陣 (Cross Rates)")
    st.write("這張表顯示「1單位左側貨幣」可兌換多少「上方貨幣」。適用於觀察非台幣間的換算（如馬幣換新幣）。")
    
    # 建立矩陣數據
    matrix_currencies = [n for n in rates_dict.keys()]
    matrix_data = []
    for row_curr in matrix_currencies:
        row_values = []
        for col_curr in matrix_currencies:
            # 計算公式：(1 * 來源對台幣匯率) / 目標對台幣匯率
            val = rates_dict[row_curr] / rates_dict[col_curr]
            row_values.append(round(val, 4))
        matrix_data.append(row_values)
    
    df_matrix = pd.DataFrame(matrix_data, index=matrix_currencies, columns=matrix_currencies)
    st.table(df_matrix) # 使用靜態表格更易於閱讀

else:
    st.error("無法取得資料，請稍後再試。")
