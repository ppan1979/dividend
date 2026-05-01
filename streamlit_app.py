import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. 基礎設定與密碼檢查 ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "1215":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.sidebar.text_input("請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.sidebar.text_input("請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        st.sidebar.error("密碼錯誤")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. 資產配置與起始月份修正 ---
# base: 初始股數, m: 每月投入金額, start_mo: 開始計算月份
MY_ASSETS = {
    "0050.TW":  {"base": 15793, "m": 0,    "start_mo": 1}, 
    "00878.TW": {"base": 0,     "m": 5000, "start_mo": 4}, # 4月才開始買
    "00919.TW": {"base": 0,     "m": 5000, "start_mo": 4}, # 4月才開始買
    "2412.TW":  {"base": 1000,  "m": 0,    "start_mo": 1},
    "2892.TW":  {"base": 2000,  "m": 0,    "start_mo": 1},
}

CASH_BASE = 3000000  # 300萬存款
INT_RATE = 0.0175    # 銀行年利率 1.75%

# 配息預估 (元/每股)
STRICT_DPS = {
    "0050.TW":  {1: 1.0, 7: 3.0},
    "00878.TW": {2: 0.55, 5: 0.55, 8: 0.55, 11: 0.55},
    "00919.TW": {3: 0.72, 6: 0.72, 9: 0.72, 12: 0.72},
    "2412.TW":  {8: 4.7},
    "2892.TW":  {8: 1.5},
}

# --- 3. 抓取即時股價 ---
@st.cache_data(ttl=3600)
def get_prices():
    prices = {}
    for ticker in MY_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = resp.json()
            prices[ticker] = data['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            prices[ticker] = 200.0 if "0050" in ticker else 25.0
    return prices

prices = get_prices()

# --- 4. 計算核心邏輯 ---
def calculate_forecast(years):
    data = []
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            mo_income = CASH_BASE * (INT_RATE / 12)
            for tk, info in MY_ASSETS.items():
                # 只有月份大於等於起始月份才計算
                current_total_mo = (yr - 2026) * 12 + m
                start_total_mo = (2026 - 2026) * 12 + info["start_mo"]
                
                if current_total_mo >= start_total_mo:
                    # 計算當下累積股數
                    passed = current_total_mo - start_total_mo
                    shares = info["base"] + (info["m"] * passed / prices[tk])
                    # 檢查當月是否配息
                    if m in STRICT_DPS.get(tk, {}):
                        mo_income += shares * STRICT_DPS[tk][m]
            
            data.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(mo_income)})
    return pd.DataFrame(data)

# --- 5. 網頁顯示 ---
st.title("📊 個人資產 15 年增長預估")
st.write(f"系統日期：{datetime.now().strftime('%Y-%m-%d')} | 初始存款：300萬")

df_full = calculate_forecast(15)

# 顯示 2026 - 2028
st.subheader("📍 階段 1：2026 - 2028 年 (修正 4 月起購版)")
p1 = df_full[df_full["年份"] <= 2028].pivot(index="月份", columns="年份", values="預估入帳")
st.table(p1.reindex([f"{i}月" for i in range(1, 13)]))

st.info("💡 說明：00878 與 00919 已設定為 2026 年 4 月起才開始投入，1-3 月僅計算 0050 配息與銀行利息。")
