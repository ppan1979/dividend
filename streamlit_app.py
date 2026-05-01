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

# --- 2. 資產配置 (已修正 00878, 00919 於 4 月開始投入) ---
MY_ASSETS = {
    "0050.TW":  {"base": 15793, "m": 0,    "start_mo": 1}, 
    "00878.TW": {"base": 0,     "m": 5000, "start_mo": 4}, 
    "00919.TW": {"base": 0,     "m": 5000, "start_mo": 4}, 
    "2412.TW":  {"base": 1000,  "m": 0,    "start_mo": 1},
    "2892.TW":  {"base": 2000,  "m": 0,    "start_mo": 1},
}

CASH_BASE = 3000000  
INT_RATE = 0.0175    

STRICT_DPS = {
    "0050.TW":  {1: 1.0, 7: 3.0},
    "00878.TW": {2: 0.55, 5: 0.55, 8: 0.55, 11: 0.55},
    "00919.TW": {3: 0.72, 6: 0.72, 9: 0.72, 12: 0.72},
    "2412.TW":  {8: 4.7},
    "2892.TW":  {8: 1.5},
}

# --- 3. 抓取股價 ---
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

# --- 4. 計算 15 年邏輯 ---
def calculate_forecast(total_years):
    data = []
    for yr in range(2026, 2026 + total_years):
        for m in range(1, 13):
            mo_income = CASH_BASE * (INT_RATE / 12)
            for tk, info in MY_ASSETS.items():
                current_total_mo = (yr - 2026) * 12 + m
                start_total_mo = (2026 - 2026) * 12 + info["start_mo"]
                
                if current_total_mo >= start_total_mo:
                    passed = current_total_mo - start_total_mo
                    shares = info["base"] + (info["m"] * passed / prices[tk])
                    if m in STRICT_DPS.get(tk, {}):
                        mo_income += shares * STRICT_DPS[tk][m]
            
            data.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(mo_income)})
    return pd.DataFrame(data)

# --- 5. 網頁顯示 ---
st.title("📊 個人資產 15 年增長預估")
st.write(f"系統日期：2026-05-01 | 初始存款：300萬")

df_full = calculate_forecast(15)

# A. 詳細月份表 (前三年)
st.subheader("📍 階段 1：月份明細 (2026 - 2028)")
p1 = df_full[df_full["年份"] <= 2028].pivot(index="月份", columns="年份", values="預估入帳")
st.table(p1.reindex([f"{i}月" for i in range(1, 13)]))

# B. 15 年每年總計表
st.subheader("💰 15 年長線預估 (每年總計)")
annual_sum = df_full.groupby("年份")["預估入帳"].sum().reset_index()
annual_sum.columns = ["年份", "全年預估領取 (元)"]
st.dataframe(annual_sum, use_container_width=True)

# C. 總結分析
total_15 = annual_sum["全年預估領取 (元)"].sum()
st.success(f"🎊 預估未來 15 年 (2026-2041) 累計領取：**{total_15:,.0f}** 元")
