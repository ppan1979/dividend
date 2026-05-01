import streamlit as st
import pandas as pd
import requests

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

# --- 2. 核心配息數據 (2026 最新公告/預估) ---
STRICT_DPS = {
    "0050.TW":   {1: 1.0, 7: 0.36},
    "006208.TW": {7: 0.989, 11: 3.44},
    "2412.TW":   {8: 4.7},
    "2892.TW":   {8: 1.5},
    "00878.TW":  {2: 0.42, 5: 0.42, 8: 0.42, 11: 0.42},
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

# --- 3. 頁面配置與股價抓取 ---
st.set_page_config(layout="wide")
st.title("明細 (修正 006208 月份)")

@st.cache_data(ttl=3600)
def get_prices():
    p = {}
    for tk in DEFAULT_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            p[tk] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            p[tk] = 0.0
    return p

prices = get_prices()

# --- 4. 依照圖1修改的看板區 ---
with st.expander("🔍 點擊檢查各標的當前價格與配息設定"):
    for tk, info in DEFAULT_ASSETS.items():
        mos = sorted(list(STRICT_DPS.get(tk, {}).keys()))
        st.markdown(f"**{info['name']}**: ${prices[tk]} | 配息月份: {mos}")

st.markdown("---")

# --- 5. 參數編輯與控制區 ---
col_cash, col_btn = st.columns([3, 1])
with col_cash:
    user_cash = st.number_input("💰 目前定存總額 (元):", value=3000000, step=10000)
with col_btn:
    st.write(" ")
    if st.button("🔄 執行計算"):
        st.cache_data.clear()
        st.rerun()

edit_data = []
for tk, info in DEFAULT_ASSETS.items():
    edit_data.append({"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']})

df_config = st.data_editor(pd.DataFrame(edit_data), hide_index=True, use_container_width=True)

# --- 6. 模擬計算邏輯 ---
def run_simulation(years, cash, config_df):
    results = []
    cfg_map = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    shares_map = {tk: float(c["base"]) for tk, c in cfg_map.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # 1. 計算當月利息與股息
            income = cash * (0.0175 / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    income += shares_map[tk] * dps_info[m]
            
            # 2. 月底買入定期定額
            for tk, c in cfg_map.items():
                if prices[tk] > 0:
                    shares_map[tk] += c["m"] / prices[tk]
                
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = run_simulation(15, user_cash, df_config)

# --- 7. 明細顯示 (含年度總計) ---
phases = [
    (2026, 2028, "📍 第一階段明細"),
    (2029, 2031, "📍 第二階段明細"),
    (2032, 2034, "📍 第三階段明細"),
    (2035, 2037, "📍 第四階段明細"),
    (2038, 2040, "📍 第五階段明細"),
    (2041, 2041, "📍 最終階段明細")
]

for start_y, end_y, title in phases:
    st.subheader(title)
    sub = df_final[(df_final["年份"] >= start_y) & (df_final["年份"] <= end_y)]
    
    # 顯示月明細表格
    pivot = sub.pivot(index="月份", columns="年份", values="預估金額")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    # 重新加回年度總計表格
    ann_sum = sub.groupby("年份")["預估金額"].sum().reset_index()
    ann_sum.columns = ["年份", "該年總入帳預估"]
    st.dataframe(ann_sum, hide_index=True, use_container_width=True)

st.success(f"🎊 15 年累計預估總領取：**{df_final['預估金額'].sum():,.0f}** 元")
