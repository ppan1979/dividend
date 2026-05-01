import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. 密碼檢查 (1215) ---
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
    "0050.TW":  {"name": "元大台灣50", "base": 15793, "m": 0,    "start_mo": 1}, 
    "00878.TW": {"name": "國泰永續高股息", "base": 0,     "m": 5000, "start_mo": 4}, 
    "00919.TW": {"name": "群益台灣精選高息", "base": 0,     "m": 5000, "start_mo": 4}, 
    "2412.TW":  {"name": "中華電", "base": 1000,  "m": 0,    "start_mo": 1},
    "2892.TW":  {"name": "第一金", "base": 2000,  "m": 0,    "start_mo": 1},
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

# --- 3. 股價抓取 ---
@st.cache_data(ttl=3600)
def get_prices():
    prices = {}
    for ticker in MY_ASSETS.keys():
        try:
            # 查詢當下股價
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            prices[ticker] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            prices[ticker] = 200.0 if "0050" in ticker else 25.0
    return prices

prices = get_prices()

st.title("📊 15 年資產入帳全明細 (修正版)")

# 顯示當前股價看板
st.subheader("📈 當前市場行情 (預估基準)")
price_cols = st.columns(len(MY_ASSETS))
for i, (ticker, info) in enumerate(MY_ASSETS.items()):
    price_cols[i].metric(info["name"], f"${prices[ticker]}", ticker)

if st.button("🔄 重新整理即時股價"):
    st.cache_data.clear()
    st.rerun()

st.markdown("---")

# --- 4. 計算 180 個月明細 (加入動態成長邏輯) ---
def calculate_full_detail(total_years):
    data = []
    annual_price_growth = 1.03 # 假設股價年增 3%
    
    for yr in range(2026, 2026 + total_years):
        year_idx = yr - 2026
        for m in range(1, 13):
            # 銀行存款利息
            mo_income = CASH_BASE * (INT_RATE / 12)
            
            for tk, info in MY_ASSETS.items():
                current_total_mo = year_idx * 12 + m
                start_total_mo = info["start_mo"]
                
                if current_total_mo >= start_total_mo:
                    # 計算到當月為止累積的股數
                    # 定期定額部分會隨年份增加而買入較貴的股價
                    passed_months = current_total_mo - start_total_mo
                    adj_price = prices[tk] * (annual_price_growth ** year_idx)
                    shares = info["base"] + (info["m"] * passed_months / adj_price)
                    
                    if m in STRICT_DPS.get(tk, {}):
                        mo_income += shares * STRICT_DPS[tk][m]
            
            data.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(mo_income)})
    return pd.DataFrame(data)

df_full = calculate_full_detail(15)

# --- 5. 分段顯示 ---
def show_phase(start_yr, end_yr, title):
    st.subheader(title)
    phase_df = df_full[(df_full["年份"] >= start_yr) & (df_full["年份"] <= end_yr)]
    pivot_df = phase_df.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot_df.reindex([f"{i}月" for i in range(1, 13)]))
    
    # 年度總結
    annual_summary = phase_df.groupby("年份")["預估入帳"].sum().reset_index()
    annual_summary.columns = ["年份", "年度總領取金額 (元)"]
    st.dataframe(annual_summary, hide_index=True, use_container_width=True)

show_phase(2026, 2028, "📍 2026 - 2028 (4月起購修正)")
show_phase(2029, 2031, "📍 2029 - 2031")
show_phase(2032, 2034, "📍 2032 - 2034")
show_phase(2035, 2037, "📍 2035 - 2037")
show_phase(2038, 2040, "📍 2038 - 2040")
show_phase(2041, 2041, "📍 2041")

total_cash = df_full["預估入帳"].sum()
st.success(f"💰 15 年累計領取預估：**{total_cash:,.0f}** 元")
