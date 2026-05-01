import streamlit as st
import pandas as pd
import yfinance as yf
import time

# --- 1. 密碼檢查 (1215) ---
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

# --- 2. 核心資產設定 (嚴格保留除息月份) ---
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

# --- 3. 純網路抓取邏輯 (平均過去一年) ---
@st.cache_data(ttl=86400)
def fetch_market_data():
    prices_map = {}
    dps_map = {}
    for tk, info in DEFAULT_ASSETS.items():
        try:
            ticker = yf.Ticker(tk)
            prices_map[tk] = ticker.fast_info.get('last_price', 0.0)
            divs = ticker.actions['Dividends']
            if not divs.empty:
                last_year = divs[divs.index > (pd.Timestamp.now() - pd.DateOffset(years=1))]
                if not last_year.empty:
                    # 抓過去一年總和，除以你設定的配息次數
                    avg_val = last_year.sum() / len(info['months'])
                else:
                    avg_val = float(divs.iloc[-1])
                dps_map[tk] = {m: round(float(avg_val), 3) for m in info['months']}
            else:
                dps_map[tk] = {}
            time.sleep(0.5) 
        except:
            prices_map[tk] = 0.0
            dps_map[tk] = {}
    return prices_map, dps_map

prices, STRICT_DPS = fetch_market_data()

# --- 4. 介面配置 ---
st.set_page_config(layout="wide")
st.title("明細 (修正配息月份與網路同步)")

with st.expander("🔍 點擊檢查各標的當前價格與配息月份"):
    for tk, info in DEFAULT_ASSETS.items():
        mos = sorted(info['months'])
        d_val = list(STRICT_DPS.get(tk, {0:0}).values())[0] if STRICT_DPS.get(tk) else 0.0
        st.markdown(f"**{info['name']}**: ${prices[tk]:.2f} | 預估單次配息: ${d_val} | 配息月份: {mos}")

st.markdown("---")

# --- 5. 控制區與編輯區 ---
col_cash, col_btn = st.columns([3, 1])
with col_cash:
    user_cash = st.number_input("💰 目前定存總額 (元):", value=3000000, step=10000)
with col_btn:
    st.write(" ")
    if st.button("🔄 重新整理網路數據"):
        st.cache_data.clear()
        st.rerun()

edit_data = [{"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']} for tk, info in DEFAULT_ASSETS.items()]
df_config = st.data_editor(pd.DataFrame(edit_data), hide_index=True, use_container_width=True)

# --- 6. 模擬計算邏輯 ---
def run_simulation(years, cash, config_df):
    results = []
    cfg_map = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    shares_map = {tk: float(c["base"]) for tk, c in cfg_map.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # 利息
            income = cash * (0.0175 / 12)
            # 股息 (嚴格對應月份)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    income += shares_map[tk] * dps_info[m]
            
            # 定額買入
            for tk, c in cfg_map.items():
                if prices[tk] > 0:
                    shares_map[tk] += c["m"] / prices[tk]
            
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = run_simulation(15, user_cash, df_config)

# --- 7. 分階段顯示 ---
phases = [(2026,2028,"📍 第一階段明細"),(2029,2031,"📍 第二階段明細"),(2032,2034,"📍 第三階段明細"),(2035,2037,"📍 第四階段明細"),(2038,2041,"📍 最終階段明細")]
for start, end, title in phases:
    st.subheader(title)
    sub = df_final[(df_final["年份"] >= start) & (df_final["年份"] <= end)]
    pivot = sub.pivot(index="月份", columns="年份", values="預估金額")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    ann_sum = sub.groupby("年份")["預估金額"].sum().reset_index()
    ann_sum.columns = ["年份", "該年總入帳預估"]
    st.dataframe(ann_sum, hide_index=True, use_container_width=True)

st.success(f"🎊 15 年累計預估總領取：**{df_final['預估金額'].sum():,.0f}** 元")
