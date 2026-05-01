import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. 密碼檢查 ---
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

# --- 2. 資產與 4 月起購設定 ---
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

@st.cache_data(ttl=3600)
def get_prices():
    prices = {}
    for ticker in MY_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            prices[ticker] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            prices[ticker] = 200.0 if "0050" in ticker else 25.0
    return prices

prices = get_prices()

# --- 3. 計算 180 個月明細 ---
def calculate_full_detail(total_years):
    data = []
    for yr in range(2026, 2026 + total_years):
        for m in range(1, 13):
            mo_income = CASH_BASE * (INT_RATE / 12)
            for tk, info in MY_ASSETS.items():
                current_total_mo = (yr - 2026) * 12 + m
                start_total_mo = info["start_mo"]
                if current_total_mo >= start_total_mo:
                    passed = current_total_mo - start_total_mo
                    shares = info["base"] + (info["m"] * passed / prices[tk])
                    if m in STRICT_DPS.get(tk, {}):
                        mo_income += shares * STRICT_DPS[tk][m]
            data.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(mo_income)})
    return pd.DataFrame(data)

# --- 4. 網頁分段顯示 ---
st.title("📊 15 年資產入帳全明細")
st.write(f"數據基準：2026-05-01 | 已修正 00878/00919 於 4 月起購")

df_full = calculate_full_detail(15)

# 定義分段函數
def show_phase(start_yr, end_yr, title):
    st.subheader(title)
    phase_df = df_full[(df_full["年份"] >= start_yr) & (df_full["年份"] <= end_yr)]
    pivot_df = phase_df.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot_df.reindex([f"{i}月" for i in range(1, 13)]))

# 顯示 5 個階段，共 15 年
show_phase(2026, 2028, "📍 階段 1：2026 - 2028")
show_phase(2029, 2031, "📍 階段 2：2029 - 2031")
show_phase(2032, 2034, "📍 階段 3：2032 - 2034")
show_phase(2035, 2037, "📍 階段 4：2035 - 2037")
show_phase(2038, 2040, "📍 階段 5：2038 - 2040")
show_phase(2041, 2041, "📍 最終年：2041")

# 總結
total_cash = df_full["預估入帳"].sum()
st.success(f"💰 這 15 年(180個月)您預估累計領取：**{total_cash:,.0f}** 元")
