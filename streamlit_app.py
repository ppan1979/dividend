import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="15年全標的資產成長預估", layout="wide")

# --- 2. 密碼保護 (修改密碼為 1215) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    
    # 使用 sidebar 讓畫面更乾淨
    pwd = st.sidebar.text_input("🔑 請輸入訪問密碼", type="password")
    if st.sidebar.button("登入"):
        if pwd == "1215": # 密碼已更新為 1215
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.sidebar.error("密碼錯誤，請重新輸入")
    return False

if check_password():
    # --- 3. 全標的即時行情抓取函數 ---
    @st.cache_data(ttl=600) # 快取 10 分鐘，點擊按鈕可強制更新
    def get_all_prices(assets_dict):
        prices = {}
        for ticker in assets_dict.keys():
            try:
                symbol = ticker.split('.')[0]
                url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{symbol}.tw"
                res = requests.get(url, timeout=5).json()
                p = res['msgArray'][0]['z']
                # 若盤中無成交價則取昨收價
                prices[ticker] = float(p) if p != '-' else float(res['msgArray'][0]['y'])
            except:
                # 備援價格 (以 2026/05 目前行情為準)
                fallback = {"0050.TW": 54.5, "006208.TW": 116.5, "2412.TW": 127.0, "2892.TW": 29.5}
                prices[ticker] = fallback.get(ticker, 100.0)
        return prices

    # --- 4. 核心數據配置 (依據歷史紀錄與分割後股數) ---
    STRICT_DPS = {
        "0050.TW":   {1: 1.0, 7: 0.75},           
        "006208.TW": {7: 0.9, 11: 1.8},           
        "2412.TW":   {7: 4.75},                   
        "2892.TW":   {8: 1.05},                   
        "00878.TW":  {2: 0.55, 5: 0.55, 8: 0.55, 11: 0.55},
        "00919.TW":  {3: 0.72, 6: 0.72, 9: 0.72, 12: 0.72},
        "2002.TW":   {8: 0.35}, "2633.TW": {8: 0.50}
    }

    # 您目前的資產狀態 (0050 為分割後股數 15,793)
    MY_ASSETS = {
        "0050.TW":   {"base": 15793, "m": 5000},  
        "006208.TW": {"base": 4800,  "m": 5000},
        "2412.TW":   {"base": 2556,  "m": 5000},
        "2892.TW":   {"base": 13464, "m": 5000},
        "00878.TW":  {"base": 200,   "m": 5000},
        "00919.TW":  {"base": 210,   "m": 5000},
        "2002.TW":   {"base": 5106,  "m": 0},
        "2633.TW":   {"base": 1802,  "m": 0}
    }

    st.title("📈 15年全標的資產複利模型 (網頁版)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"最後同步時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with col2:
        if st.button("🔄 一鍵更新所有股票行情"):
            st.cache_data.clear()
            st.rerun()

    # 執行全標的行情抓取
    prices = get_all_prices(MY_ASSETS)
    bank_interest = (3000000 * 0.0175) / 12 # 300萬銀行利息

    # --- 5. 生成 5 個階段的 3 年對照表 ---
    phases = [range(2026, 2029), range(2029, 2032), range(2032, 2035), range(2035, 2038), range(2038, 2041)]

    for i, yr_range in enumerate(phases, 1):
        st.markdown(f"#### 📍 階段 {i}：{yr_range[0]} - {yr_range[-1]} 年")
        data = []
        yr_totals = {yr: 0 for yr in yr_range}

        for m in range(1, 13):
            row = {"月份": f"{m}月"}
            for yr in yr_range:
                monthly_income = bank_interest
                for tkr, info in MY_ASSETS.items():
                    p = prices[tkr]
                    # 計算累積股數 (2025/1 起算)
                    passed_months = (yr - 2025) * 12 + m
                    total_shares = info['base'] + (info['m'] * passed_months / p)
                    if m in STRICT_DPS.get(tkr, {}):
                        monthly_income += total_shares * STRICT_DPS[tkr][m]
                
                income_val = int(monthly_income)
                row[f"{yr}年"] = f"{income_val:,}"
                yr_totals[yr] += income_val
            data.append(row)

        df = pd.DataFrame(data)
        # 年度總計列
        footer = {"月份": "**年度總計**"}
        for yr in yr_range:
            footer[f"{yr}年"] = f"**{yr_totals[yr]:,}**"
        
        df = pd.concat([df, pd.DataFrame([footer])], ignore_index=True)
        st.table(df) # 產出精簡格式表格
