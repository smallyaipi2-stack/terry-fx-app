import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 網頁外觀設定
st.set_page_config(page_title="我饗國際匯率決策系統", page_icon="📈", layout="wide")
st.title("📈 執行長專屬：全方位匯率監控與換算系統")
st.write("即時資料：台灣銀行牌告匯率 | 歷史趨勢：Yahoo Finance")

# 1. 抓取台銀即時資料
@st.cache_data(ttl=600)
def get_bot_rates():
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8-sig'
        lines = response.text.split('\n')
        rates = {'台幣 (TWD)': 1.0}
        target_map = {'USD': '美金 (USD)', 'JPY': '日圓 (JPY)', 'EUR': '歐元 (EUR)', 'KRW': '韓元 (KRW)', 'CNY': '人民幣 (CNY)'}
        for line in lines:
            parts = line.split(',')
            if len(parts) < 13: continue
            code = parts[0].strip()
            for k, v in target_map.items():
                if k in code: rates[v] = float(parts[12].strip())
        return rates
    except: return None

# 2. 抓取歷史資料的函式
def get_history(currency_name, period):
    # 轉換幣別代碼為 Yahoo Finance 格式
    mapping = {'美金 (USD)': 'TWD=X', '日圓 (JPY)': 'JPYTWD=X', '歐元 (EUR)': 'EURTWD=X', '韓元 (KRW)': 'KRWTWD=X', 'CNY': 'CNYTWD=X'}
    # 備註：美金比較特別，Yahoo通常是 USD對台幣，所以我們用 TWD=X 倒推或直接用對應代碼
    symbol_map = {
        '美金 (USD)': 'USDTWD=X',
        '日圓 (JPY)': 'JPYTWD=X',
        '歐元 (EUR)': 'EURTWD=X',
        '韓元 (KRW)': 'KRWTWD=X',
        '人民幣 (CNY)': 'CNYTWD=X'
    }
    symbol = symbol_map.get(currency_name)
    data = yf.download(symbol, period=period, interval='1d')
    return data['Close']

rates_dict = get_bot_rates()

if rates_dict:
    # 頂部儀表板
    st.subheader("📊 即時匯率看板")
    cols = st.columns(len(rates_dict) - 1)
    for i, (name, rate) in enumerate(list(rates_dict.items())[1:]):
        with cols[i]:
            st.metric(name, f"{rate} TWD")

    st.divider()

    # 中間：換算與圖表並列
    col_left, col_right = st.columns([1, 1.5])

    with col_left:
        st.subheader("🔄 快速換算")
        amt = st.number_input("輸入金額", min_value=0.0, value=100.0)
        from_curr = st.selectbox("從", options=list(rates_dict.keys()), index=1)
        to_curr = st.selectbox("換成", options=list(rates_dict.keys()), index=0)
        
        if st.button("執行換算", use_container_width=True):
            res = (amt * rates_dict[from_curr]) / rates_dict[to_curr]
            st.success(f"結果：{res:,.2f} {to_curr}")

    with col_right:
        st.subheader("📈 歷史趨勢分析")
        target_curr = st.selectbox("選擇要分析的幣別", options=list(rates_dict.keys())[1:])
        time_range = st.radio("時間範圍", ["1mo", "3mo", "6mo", "1y"], horizontal=True, index=0)
        
        try:
            hist_data = get_history(target_curr, time_range)
            st.line_chart(hist_data)
            st.caption(f"註：以上顯示為 {target_curr} 對台幣之歷史走勢 (來源: Yahoo Finance)")
        except:
            st.warning("暫時無法取得歷史圖表，請稍後再試。")

else:
    st.error("系統暫時無法讀取資料。")
