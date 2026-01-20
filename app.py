import streamlit as st
import requests

# 網頁外觀設定
st.set_page_config(page_title="我饗國際匯率換算系統", page_icon="💰", layout="wide")
st.title("💰 執行長專屬：全方位即時匯率換算器")
st.write("資料來源：台灣銀行牌告匯率 (即期賣出價)")

# 抓取台銀資料的邏輯
@st.cache_data(ttl=600) # 每10分鐘自動更新一次
def get_all_bot_rates():
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8-sig'
        lines = response.text.split('\n')
        
        # 建立匯率字典，預設台幣對台幣是 1
        rates = {'台幣 (TWD)': 1.0}
        
        # 定義我們要抓取的幣別與其顯示名稱
        target_map = {
            'USD': '美金 (USD)',
            'JPY': '日圓 (JPY)',
            'EUR': '歐元 (EUR)',
            'KRW': '韓元 (KRW)',
            'CNY': '人民幣 (CNY)'
        }
        
        for line in lines:
            parts = line.split(',')
            if len(parts) < 13: continue
            
            currency_code = parts[0].strip()
            # 遍歷目標幣別，只要台銀的代碼出現在其中，就抓取即期賣出價 (index 12)
            for code, full_name in target_map.items():
                if code in currency_code:
                    try:
                        rates[full_name] = float(parts[12].strip())
                    except:
                        rates[full_name] = None
        return rates
    except Exception as e:
        st.error(f"連線異常：{e}")
        return None

rates_dict = get_all_bot_rates()

if rates_dict:
    # 1. 匯率儀表板：橫向顯示所有幣別
    st.subheader("📊 即時匯率看板")
    cols = st.columns(len(rates_dict) - 1)
    for i, (name, rate) in enumerate(list(rates_dict.items())[1:]): # 跳過台幣
        with cols[i]:
            st.metric(name, f"{rate} TWD")

    st.divider()

    # 2. 換算互動區
    st.subheader("🔄 匯率試算")
    
    col_input, col_from, col_arrow, col_to = st.columns([2, 2, 1, 2])
    
    with col_input:
        amount = st.number_input("輸入金額", min_value=0.0, value=100.0, step=1.0)
        
    with col_from:
        from_currency = st.selectbox("從", options=list(rates_dict.keys()), index=1)
        
    with col_arrow:
        st.markdown("<h2 style='text-align: center;'>➔</h2>", unsafe_allow_html=True)
        
    with col_to:
        to_currency = st.selectbox("換成", options=list(rates_dict.keys()), index=0)

    # 換算邏輯：以台幣作為中繼站
    # 邏輯：(金額 * 來源幣別對台幣匯率) / 目標幣別對台幣匯率
    if st.button("執行換算", use_container_width=True):
        from_rate = rates_dict[from_currency]
        to_rate = rates_dict[to_currency]
        
        if from_rate and to_rate:
            # 計算結果
            result = (amount * from_rate) / to_rate
            
            # 顯示結果
            st.success(f"### 換算結果：{result:,.2f} {to_currency}")
            
            # 補充資訊
            st.info(f"計算邏輯：使用台銀即期賣出價進行轉換。")
        else:
            st.error("抱歉，目前該幣別資料有誤，無法換算。")

else:
    st.error("無法取得即時資料，請確認網路連線或稍後再試。")
