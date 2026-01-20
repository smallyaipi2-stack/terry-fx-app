import streamlit as st
import requests

# 網頁外觀與標題
st.set_page_config(page_title="我饗國際匯率工具", page_icon="💰")
st.title("💰 執行長專屬：即時匯率換算器")
st.write("資料來源：台灣銀行牌告匯率")

# 抓取台銀資料的邏輯
def get_bot_rates():
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    response = requests.get(url, timeout=10)
    response.encoding = 'utf-8-sig'
    lines = response.text.split('\n')
    
    rates = {}
    for line in lines:
        parts = line.split(',')
        if len(parts) < 13: continue
        currency = parts[0].strip()
        # 抓取即期賣出匯率 (index 12)
        if 'USD' in currency: rates['USD'] = float(parts[12].strip())
        if 'JPY' in currency: rates['JPY'] = float(parts[12].strip())
    return rates

try:
    current_rates = get_bot_rates()
    
    # 顯示匯率儀表板
    col1, col2 = st.columns(2)
    with col1:
        st.metric("美金即期賣出", f"{current_rates['USD']} TWD")
    with col2:
        st.metric("日圓即期賣出", f"{current_rates['JPY']} TWD")

    st.divider()

    # 換算介面
    amount = st.number_input("請輸入金額", min_value=0.0, value=100.0)
    option = st.selectbox("請選擇換算方式", 
                        ["美金 ➔ 台幣", "日圓 ➔ 台幣", "台幣 ➔ 美金"])

    if st.button("立即換算"):
        if option == "美金 ➔ 台幣":
            res = amount * current_rates['USD']
            st.success(f"換算結果：{res:,.2f} 台幣")
        elif option == "日圓 ➔ 台幣":
            res = amount * current_rates['JPY']
            st.success(f"換算結果：{res:,.2f} 台幣")
        else:
            res = amount / current_rates['USD']
            st.success(f"換算結果：{res:,.2f} 美金")

except Exception as e:
    st.error(f"目前無法從台銀抓取資料，請稍後再試。")
