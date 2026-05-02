import streamlit as st
import pandas as pd
import yfinance as yf
import time

# --- 1. 密碼檢查 (1215) ---
if "password_correct" not in st.session_state:
    def password_entered():
        if st.session_state["password"] == "1215":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
    st.sidebar.text_input("請輸入訪問密碼", type="password", on_change=password_entered, key="password")
    st.stop()

# --- 2. 核心資產設定 (嚴格保留您的月份) ---
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

# --- 3. 透明診斷抓取邏輯 ---
@st.cache_data(ttl=600) # 縮短緩存至 10 分鐘，方便您測試
def fetch_with_diagnostic():
    prices_map, dps_map, logs = {}, {}, []
    for tk in DEFAULT_ASSETS.keys():
        try:
            ticker = yf.Ticker(tk)
            # 測試抓取價格
            p = ticker.fast_info.get('last_price')
            if p is None or p <= 0:
                logs.append(f"❌ {tk}: 抓不到價格 (可能被擋 IP)")
                prices_map[tk] = 0.0
            else:
                prices_map[tk] = p
            
            # 測試抓取配息
            divs = ticker.actions['Dividends']
            if divs.empty:
                logs.append(f"❓ {tk}: 價格正常，但配息表回傳為空 (Yahoo 暫時無資料)")
                dps_map[tk] = {}
            else:
                last_yr = divs[divs.index > (pd.Timestamp.now() - pd.DateOffset(years=1))]
                avg_v = last_year.sum() / len(DEFAULT_ASSETS[tk]['months']) if not last_year.empty else float(divs.iloc[-1])
                dps_map[tk] = {m: round(float(avg_v), 3) for m in DEFAULT_ASSETS[tk]['months']}
                logs.append(f"✅ {tk}: 抓取成功 (單次約 ${round(float(avg_v), 2)})")
        except Exception as e:
            logs.append(f"🚨 {tk}: 發生連線錯誤 -> {str(e)}")
            prices_map[tk] = 0.0
            dps_map[tk] = {}
    return prices_map, dps_map, logs

prices, STRICT_DPS, debug_logs = fetch_with_diagnostic()

# --- 4. 介面配置 ---
st.set_page_config(layout="wide")
st.title("數據透明診斷明細表")

# --- 💡 診斷中心 (這裡可以看真相) ---
with st.expander("🛠 網路抓取診斷中心 (點開看為什麼資料沒出來)"):
    for log in debug_logs:
        st.write(log)

st.markdown("---")

# --- 5. 參數編輯與計算 (其餘邏輯完全不動) ---
user_cash = st.number_input("💰 目前定存總額 (元):", value=3000000)
edit_data = [{"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']} for tk, info in DEFAULT_ASSETS.items()]
df_config = st.data_editor(pd.DataFrame(edit_data), hide_index=True, use_container_width=True)

def run_simulation(years, cash, config_df):
    results = []
    cfg_map = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    shares_map = {tk: float(c["base"]) for tk, c in cfg_map.items()}
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            income = cash * (0.0175 / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info: income += shares_map[tk] * dps_info[m]
            for tk, c in cfg_map.items():
                if prices[tk] > 0: shares_map[tk] += c["m"] / prices[tk]
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = run_simulation(15, user_cash, df_config)

# --- 6. 顯示表格 ---
for start, end, title in [(2026,2028,"📍 第一階段"),(2029,2031,"📍 第二階段"),(2032,2034,"📍 第三階段"),(2035,2037,"📍 第四階段"),(2038,2041,"📍 最終階段")]:
    st.subheader(title)
    sub = df_final[(df_final["年份"] >= start) & (df_final["年份"] <= end)]
    st.table(sub.pivot(index="月份", columns="年份", values="預估金額").reindex([f"{i}月" for i in range(1, 13)]))

st.success(f"🎊 15 年累計預估總領取：**{df_final['預估金額'].sum():,.0f}** 元")
