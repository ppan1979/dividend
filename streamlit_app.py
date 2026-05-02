import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- 1. 訪問權限檢查 ---
if "password_correct" not in st.session_state:
    def password_entered():
        if st.session_state["password"] == "1215":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
    st.sidebar.text_input("請輸入密碼後按 Enter", type="password", on_change=password_entered, key="password")
    st.stop()

# --- 2. 核心資產與精確除息月份設定 ---
ASSET_DETAILS = {
    "0050":   {"name": "元大台灣50", "base": 15793, "m": 5000, "months": [1, 7], "ticker": "0050.TW"},
    "006208": {"name": "富邦台50", "base": 4800,  "m": 5000, "months": [7, 11], "ticker": "006208.TW"},
    "2412":   {"name": "中華電",   "base": 2556,  "m": 5000, "months": [8], "ticker": "2412.TW"},
    "2892":   {"name": "第一金",   "base": 13464, "m": 5000, "months": [8], "ticker": "2892.TW"},
    "00878":  {"name": "國泰永續高股息", "base": 200,   "m": 5000, "months": [2, 5, 8, 11], "ticker": "00878.TW"},
    "00919":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000, "months": [3, 6, 9, 12], "ticker": "00919.TW"},
    "2002":   {"name": "中鋼",     "base": 5106,  "m": 0,    "months": [8], "ticker": "2002.TW"},
    "2633":   {"name": "台灣高鐵", "base": 1802,  "m": 0,    "months": [8], "ticker": "2633.TW"},
}

# --- 3. 即時股價與歷史股息精算 ---
@st.cache_data(ttl=3600)
def get_market_data():
    prices_map = {}
    dps_map = {}
    
    h_0050 = [(3.05, True), (2.6, True), (3.4, True), (3.0, True), (1.0, False)]
    calib_0050 = [val/4 if split else val for val, split in h_0050]
    avg_0050 = sum(calib_0050) / len(calib_0050)
    
    others = {
        "006208": [1.2, 1.6, 2.1, 1.8, 1.4],
        "2412": [4.6, 4.3, 4.2, 4.7, 4.8],
        "2892": [1.1, 1.2, 1.0, 1.3, 1.2],
        "00878": [0.4, 0.4, 0.35, 0.45, 0.55],
        "00919": [0.55, 0.55, 0.6, 0.7, 0.72],
        "2002": [0.3, 2.8, 1.0, 0.5, 0.35],
        "2633": [1.2, 1.1, 1.0, 1.2, 1.1]
    }

    for tk, info in ASSET_DETAILS.items():
        try:
            ticker = yf.Ticker(info["ticker"])
            current_price = ticker.fast_info['last_price']
            prices_map[tk] = round(current_price, 2)
        except:
            prices_map[tk] = 50.0 if tk == "0050" else 150.0
        
        val = avg_0050 if tk == "0050" else sum(others[tk])/5
        dps_map[tk] = {m: round(val, 3) for m in info['months']}
            
    return prices_map, dps_map, avg_0050

# --- 4. 介面呈現 ---
st.set_page_config(layout="wide", page_title="投資領息精算表")
st.title("📊 15年投資明細 (優化行動端尺寸)")

if st.button("🔄 立即更新即時數據"):
    st.cache_data.clear()
    st.toast("即時報價已更新！")

prices, STRICT_DPS, final_avg_0050 = get_market_data()

# 頂部整合看板
st.subheader("📈 資產基準與除息資訊")
combined_data = []
for tk, info in ASSET_DETAILS.items():
    sample_dps = list(STRICT_DPS[tk].values())[0]
    combined_data.append({
        "代碼": tk,
        "名稱": info['name'],
        "即時股價": prices[tk],
        "預估股息": sample_dps,
        "除息月份": ", ".join([str(m) for m in info['months']])
    })
st.table(pd.DataFrame(combined_data))

st.info(f"⚖️ **精算備註：** 0050 已完成分割校正，預估單次配息為 **${round(final_avg_0050, 2)}**。")

# 定存設定區
col1, col2 = st.columns(2)
with col1:
    user_cash = st.number_input("💰 目前定存總額 (NTD):", value=3000000)
with col2:
    bank_rate = st.slider("🏦 預估定存年利率 (%):", 0.0, 5.0, 1.75, 0.05) / 100

# --- 修正後的編輯表格：固定欄位寬度，不左右滑動 ---
st.write("📝 **編輯初始股數與每月投入：**")
df_config_input = pd.DataFrame([
    {"代碼": k, "名稱": v['name'], "初始股數": v['base'], "每月投入": v['m']} 
    for k, v in ASSET_DETAILS.items()
])

df_config = st.data_editor(
    df_config_input,
    hide_index=True,
    use_container_width=True,
    column_config={
        "代碼": st.column_config.TextColumn("代碼", width=65),
        "名稱": st.column_config.TextColumn("名稱", width=120), # 適中寬度
        "初始股數": st.column_config.NumberColumn("初始", width=70),
        "每月投入": st.column_config.NumberColumn("月投", width=70),
    }
)

# --- 5. 複利模擬邏輯 ---
def simulate_wealth(years, cash, config, rate):
    results = []
    cfg = {row["代碼"]: {"base": row["初始股數"], "m": row["每月投入"]} for _, row in config.iterrows()}
    shares = {tk: float(c["base"]) for tk, c in cfg.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            income = cash * (rate / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    income += shares[tk] * dps_info[m]
            for tk, c in cfg.items():
                if prices[tk] > 0:
                    shares[tk] += c["m"] / prices[tk]
            
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = simulate_wealth(15, user_cash, df_config, bank_rate)

# --- 6. 分階段顯示結果 ---
phases = [(2026,2028,"第一階段"),(2029,2031,"第二階段"),(2032,2034,"第三階段"),(2035,2037,"第四階段"),(2038,2041,"最終階段")]

for s, e, title in phases:
    sub = df_final[(df_final["年份"] >= s) & (df_final["年份"] <= e)]
    if not sub.empty:
        st.subheader(f"📍 {title} ({s}-{e})")
        pivot = sub.pivot(index="月份", columns="年份", values="預估金額").reindex([f"{i}月" for i in range(1, 13)])
        
        totals = pivot.sum().to_frame().T
        totals.index = ["年度總計"]
        final_display = pd.concat([pivot, totals])
        
        st.table(final_display.style.format("{:,.0f}").apply(
            lambda x: ['background-color: #f0f2f6; font-weight: bold; color: #1f77b4' if x.name == '年度總計' else '' for _ in x], axis=1)
        )

st.success(f"🎊 預估 15 年總領取金額：**NT$ {df_final['預估金額'].sum():,.0f}**")
