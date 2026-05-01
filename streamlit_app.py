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

# --- 2. 資產與配息設定 ---
MY_ASSETS = {
    "0050.TW":   {"name": "元大台灣50", "base": 15793, "m": 5000, "start_mo": 1},
    "006208.TW": {"name": "富邦台50", "base": 4800,  "m": 5000, "start_mo": 1},
    "2412.TW":   {"name": "中華電", "base": 2556,  "m": 5000, "start_mo": 1},
    "2892.TW":   {"name": "第一金", "base": 13464, "m": 5000, "start_mo": 1},
    "00878.TW":  {"name": "國泰永續高股息", "base": 200,   "m": 5000, "start_mo": 4},
    "00919.TW":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000, "start_mo": 4},
    "2002.TW":   {"name": "中鋼", "base": 5106,  "m": 0,    "start_mo": 1},
    "2633.TW":   {"name": "台灣高鐵", "base": 1802,  "m": 0,    "start_mo": 1},
}

INT_RATE = 0.0175    

STRICT_DPS = {
    "0050.TW":   {1: 1.0, 7: 3.0},
    "006208.TW": {7: 2.2, 11: 0.8}, # 正確月份：7/11月
    "2412.TW":   {8: 4.7},
    "2892.TW":   {8: 1.5},
    "00878.TW":  {2: 0.55, 5: 0.55, 8: 0.55, 11: 0.55},
    "00919.TW":  {3: 0.72, 6: 0.72, 9: 0.72, 12: 0.72},
    "2002.TW":   {8: 0.3},
    "2633.TW":   {8: 1.0},
}

# --- 3. 頂部輸入區與一鍵更新 ---
st.title("📊 資產 15 年增長預估系統")

col_input, col_btn = st.columns([3, 1])
with col_input:
    # 預設為 300 萬，讓使用者可以自由輸入
    user_cash = st.number_input("請輸入當前定存總額 (元):", value=3000000, step=10000)

with col_btn:
    st.write(" ") # 對齊用
    if st.button("🔄 一鍵更新表格"):
        st.cache_data.clear()
        st.success("數據已重新計算！")

# --- 4. 股價抓取 ---
@st.cache_data(ttl=3600)
def get_prices():
    prices = {}
    for ticker in MY_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            prices[ticker] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            prices[ticker] = 200.0 if "0050" in ticker else 30.0
    return prices

prices = get_prices()

# --- 5. 計算邏輯 ---
def calculate_full_detail(total_years, cash_base):
    data = []
    for yr in range(2026, 2026 + total_years):
        for m in range(1, 13):
            # 根據使用者輸入的金額計算每月利息
            mo_income = cash_base * (INT_RATE / 12)
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

df_full = calculate_full_detail(15, user_cash)

# --- 6. 顯示結果 ---
def show_phase(s, e, title):
    st.subheader(title)
    phase_df = df_full[(df_full["年份"] >= s) & (df_full["年份"] <= e)]
    pivot = phase_df.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    ann_sum = phase_df.groupby("年份")["預估入帳"].sum().reset_index()
    ann_sum.columns = ["年份", "年度總預估收入"]
    st.dataframe(ann_sum, hide_index=True, use_container_width=True)

show_phase(2026, 2028, "📍 2026 - 2028 明細")
show_phase(2029, 2031, "📍 2029 - 2031 明細")
show_phase(2032, 2034, "📍 2032 - 2034 明細")
show_phase(2035, 2037, "📍 2035 - 2037 明細")
show_phase(2038, 2040, "📍 2038 - 2040 明細")
show_phase(2041, 2041, "📍 最終年")

st.success(f"💰 15 年累計現金流總計：**{df_full['預估入帳'].sum():,.0f}** 元")
