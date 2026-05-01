import streamlit as st
import pandas as pd
import requests

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

# --- 2. 修正後的 2026 配息單價 (根據網路搜尋結果) ---
STRICT_DPS = {
    "0050.TW":   {1: 1.0, 7: 0.36},    # 修正：1月配1元，7月預估0.36元
    "006208.TW": {7: 0.989, 11: 3.44}, # 修正：7月0.989元，11月參考去年底
    "2412.TW":   {8: 4.7},             # 中華電維持預估
    "2892.TW":   {8: 1.5},             # 第一金維持預估
    "00878.TW":  {2: 0.42, 5: 0.42, 8: 0.42, 11: 0.42}, # 修正：2月配0.42
    "00919.TW":  {3: 0.72, 6: 0.72, 9: 0.72, 12: 0.72},
    "2002.TW":   {8: 0.3},
    "2633.TW":   {8: 1.0},
}

DEFAULT_ASSETS = {
    "0050.TW":   {"name": "元大台灣50", "base": 15793, "m": 5000},
    "006208.TW": {"name": "富邦台50", "base": 4800,  "m": 5000},
    "2412.TW":   {"name": "中華電", "base": 2556,  "m": 5000},
    "2892.TW":   {"name": "第一金", "base": 13464, "m": 5000},
    "00878.TW":  {"name": "國泰永續高股息", "base": 200,   "m": 5000},
    "00919.TW":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000},
    "2002.TW":   {"name": "中鋼", "base": 5106,  "m": 0},
    "2633.TW":   {"name": "台灣高鐵", "base": 1802,  "m": 0},
}

# --- 3. 即時股價與 Dashboard ---
st.set_page_config(layout="wide")
st.title("📈 資產即時預估 Dashboard (2026修正版)")

@st.cache_data(ttl=3600)
def get_prices():
    p = {}
    for tk in DEFAULT_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            p[tk] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            p[tk] = 100.0
    return p

prices = get_prices()

# 看板區
st.subheader("📊 即時市場看板")
tickers = list(DEFAULT_ASSETS.keys())
for i in range(0, len(tickers), 4):
    cols = st.columns(4)
    for j, tk in enumerate(tickers[i:i+4]):
        with cols[j]:
            info = DEFAULT_ASSETS[tk]
            mos = sorted(list(STRICT_DPS.get(tk, {}).keys()))
            st.metric(label=f"{info['name']} ({tk})", value=f"${prices[tk]}")
            st.caption(f"配息月: {', '.join(map(str, mos))} (單價依2026公告)")

st.markdown("---")

# --- 4. 參數異動區 ---
st.subheader("⚙️ 投資參數自定義")
col_input, col_action = st.columns([3, 1])
with col_input:
    user_cash = st.number_input("💰 目前定存總額 (元):", value=3000000, step=10000)
with col_action:
    st.write(" ")
    if st.button("🔄 重新跑 15 年模擬計算"):
        st.cache_data.clear()
        st.rerun()

edit_data = []
for tk, info in DEFAULT_ASSETS.items():
    edit_data.append({"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']})

df_config = st.data_editor(pd.DataFrame(edit_data), hide_index=True, use_container_width=True)

# --- 5. 精確計算引擎 ---
def run_simulation(years, cash, config_df):
    results = []
    cfg_map = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    # 初始化股數
    shares_map = {tk: float(c["base"]) for tk, c in cfg_map.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # 先算月收入 (定存息 + 股息)
            income = cash * (0.0175 / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    # 使用「月底買入前」的持股算配息
                    income += shares_map[tk] * dps_info[m]
            
            # 月底定期定額買入股數 (下個月才能領息)
            for tk, c in cfg_map.items():
                shares_map[tk] += c["m"] / prices[tk]
                
            results.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(income)})
    return pd.DataFrame(results)

df_result = run_simulation(15, user_cash, df_config)

# --- 6. 15 年明細表格 ---
st.markdown("---")
phases = [(2026, 2028), (2029, 2031), (2032, 2034), (2035, 2037), (2038, 2040), (2041, 2041)]
for s, e in phases:
    st.subheader(f"📍 {s} - {e} 現金流預估")
    sub = df_result[(df_result["年份"] >= s) & (df_result["年份"] <= e)]
    pivot = sub.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))

st.success(f"🎊 15 年累計現金流總額預估：**{df_result['預估入帳'].sum():,.0f}** 元")
