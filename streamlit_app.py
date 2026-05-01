import streamlit as st
import pandas as pd
import yfinance as yf
import time

# --- 1. 密碼檢查 ---
def check_password():
    if "password_correct" not in st.session_state:
        def password_entered():
            if st.session_state["password"] == "1215":
                st.session_state["password_correct"] = True
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False
        st.sidebar.text_input("請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# --- 2. 核心資產設定 ---
DEFAULT_ASSETS = {
    "0050.TW":   {"name": "元大台灣50", "base": 15793, "m": 5000, "months": [1, 7]},
    "006208.TW": {"name": "富邦台50", "base": 4800,  "m": 5000, "months": [7, 11]},
    "2412.TW":   {"name": "中華電", "base": 2556,  "m": 5000, "months": [8]},
    "2892.TW":   {"name": "第一金", "base": 13464, "m": 5000, "months": [8]},
    "00878.TW":  {"name": "國泰永續高股息", "base": 200,   "m": 5000, "months": [2, 5, 8, 11]},
    "00919.TW":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000, "months": [3, 6, 9, 12]},
    "2002.TW":   {"name": "中鋼", "base": 5106,  "m": 0, "months": [8]},
    "2633.TW":   {"name": "台灣高鐵", "base": 1802,  "m": 0, "months": [8]},
}

# --- 3. 純網路抓取邏輯 ---
@st.cache_data(ttl=86400) # 緩存一天，避免頻繁請求被擋
def fetch_market_data():
    prices_map = {}
    dps_map = {}
    
    for tk, info in DEFAULT_ASSETS.items():
        try:
            ticker = yf.Ticker(tk)
            # 抓取價格
            prices_map[tk] = ticker.fast_info.get('last_price', 0.0)
            
            # 抓取配息紀錄
            divs = ticker.actions['Dividends']
            if not divs.empty:
                # 抓取過去一年的配息總和並平均
                last_year = divs[divs.index > (pd.Timestamp.now() - pd.DateOffset(years=1))]
                if not last_year.empty:
                    avg_val = last_year.sum() / len(info['months'])
                else:
                    avg_val = float(divs.iloc[-1])
                dps_map[tk] = {m: round(float(avg_val), 3) for m in info['months']}
            else:
                dps_map[tk] = {}
            
            # 稍微延遲請求，減少被 Yahoo 偵測的風險
            time.sleep(0.5) 
        except:
            prices_map[tk] = 0.0
            dps_map[tk] = {}
            
    return prices_map, dps_map

prices, STRICT_DPS = fetch_market_data()

# --- 4. 介面與顯示 (完全保留原始格式) ---
st.set_page_config(layout="wide")
st.title("明細 (純網路同步版)")

with st.expander("🔍 檢查網路即時抓取數值"):
    for tk, info in DEFAULT_ASSETS.items():
        dps_list = list(STRICT_DPS.get(tk, {}).values())
        d_val = dps_list[0] if dps_list else 0.0
        st.markdown(f"**{info['name']}**: ${prices[tk]:.2f} | 抓取配息: ${d_val}")

st.markdown("---")

# 參數編輯區
user_cash = st.number_input("💰 目前定存總額 (元):", value=3000000, step=10000)
edit_data = [{"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']} for tk, info in DEFAULT_ASSETS.items()]
df_config = st.data_editor(pd.DataFrame(edit_data), hide_index=True, use_container_width=True)

# 模擬計算
def run_simulation(years, cash, config_df):
    results = []
    cfg_map = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    shares_map = {tk: float(c["base"]) for tk, c in cfg_map.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            income = cash * (0.0175 / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    income += shares_map[tk] * dps_info[m]
            for tk, c in cfg_map.items():
                if prices[tk] > 0:
                    shares_map[tk] += c["m"] / prices[tk]
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = run_simulation(15, user_cash, df_config)

# 分階段顯示與年度總計
phases = [(2026,2028,"📍 第一階段"),(2029,2031,"📍 第二階段"),(2032,2034,"📍 第三階段"),(2035,2037,"📍 第四階段"),(2038,2041,"📍 最終階段")]
for start, end, title in phases:
    st.subheader(title)
    sub = df_final[(df_final["年份"] >= start) & (df_final["年份"] <= end)]
    st.table(sub.pivot(index="月份", columns="年份", values="預估金額").reindex([f"{i}月" for i in range(1, 13)]))
    st.dataframe(sub.groupby("年份")["預估金額"].sum().reset_index().rename(columns={"預估金額":"該年總入帳"}), hide_index=True, use_container_width=True)

st.success(f"🎊 15 年累計預估總領取：**{df_final['預估金額'].sum():,.0f}** 元")
