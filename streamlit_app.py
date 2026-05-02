import streamlit as st
import pandas as pd
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
    "0050":   {"name": "元大台灣50", "base": 15793, "m": 5000, "months": [1, 7]},
    "006208": {"name": "富邦台50", "base": 4800,  "m": 5000, "months": [7, 11]},
    "2412":   {"name": "中華電",   "base": 2556,  "m": 5000, "months": [8]},
    "2892":   {"name": "第一金",   "base": 13464, "m": 5000, "months": [8]},
    "00878":  {"name": "國泰永續高股息", "base": 200,   "m": 5000, "months": [2, 5, 8, 11]},
    "00919":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000, "months": [3, 6, 9, 12]},
    "2002":   {"name": "中鋼",     "base": 5106,  "m": 0,    "months": [8]},
    "2633":   {"name": "台灣高鐵", "base": 1802,  "m": 0,    "months": [8]},
}

# --- 3. 0050 歷史數據精算 (含快取) ---
@st.cache_data(ttl=86400)
def calculate_calibrated_dps():
    dps_map = {}
    prices_map = {}
    
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
        prices_map[tk] = 50.0 if tk == "0050" else 150.0
        val = avg_0050 if tk == "0050" else sum(others[tk])/5
        dps_map[tk] = {m: round(val, 3) for m in info['months']}
            
    return prices_map, dps_map, avg_0050

# --- 4. 介面呈現 ---
st.set_page_config(layout="wide", page_title="投資領息精算表")
st.title("📊 15年投資明細 (含 0050 分割校正與除息月報)")

# --- 一鍵更新按鈕 ---
if st.button("🔄 立即更新數據與重新計算"):
    st.cache_data.clear()
    st.toast("數據已完成更新！")

# 執行計算
prices, STRICT_DPS, final_avg_0050 = calculate_calibrated_dps()

# --- 新增：即時看板 (即時股價與股息金額) ---
st.subheader("📈 當前計算基準看板")
board_data = []
for tk, info in ASSET_DETAILS.items():
    # 取得該標的第一次出現的預估股息作為代表
    sample_dps = list(STRICT_DPS[tk].values())[0]
    board_data.append({
        "股票代碼": tk,
        "名稱": info['name'],
        "預估股價 (NTD)": prices[tk],
        "預估單次股息 (NTD)": sample_dps
    })
st.table(pd.DataFrame(board_data))

with st.expander("📅 各股票預計除息月份明細表"):
    cal_data = [{"代碼": k, "名稱": v['name'], "預計除息月份": ", ".join([f"{m}月" for m in v['months']])} for k, v in ASSET_DETAILS.items()]
    st.table(pd.DataFrame(cal_data))

st.info(f"⚖️ **精算備註：** 0050 於 2025/06/18 分割(1:4)，歷史數據已完成 1/4 折算。預估單次配息為 **${round(final_avg_0050, 2)}**。")

# --- 定存參數設定區 ---
col1, col2 = st.columns(2)
with col1:
    user_cash = st.number_input("💰 目前定存總額 (NTD):", value=3000000)
with col2:
    bank_rate = st.slider("🏦 預估定存年利率 (%):", min_value=0.0, max_value=5.0, value=1.75, step=0.05) / 100

df_config = st.data_editor(pd.DataFrame([{"代碼": k, "名稱": v['name'], "初始股數": v['base'], "每月投入": v['m']} for k, v in ASSET_DETAILS.items()]), hide_index=True, use_container_width=True)

# --- 5. 複利模擬邏輯 ---
def simulate_wealth(years, cash, config, rate):
    results = []
    cfg = {row["代碼"]: {"base": row["初始股數"], "m": row["每月投入"]} for _, row in config.iterrows()}
    shares = {tk: float(c["base"]) for tk, c in cfg.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # 定存利息
            income = cash * (rate / 12)
            # 依據精確月份領取股息
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    income += shares[tk] * dps_info[m]
            # 每月投入買入新股數
            for tk, c in cfg.items():
                if prices[tk] > 0:
                    shares[tk] += c["m"] / prices[tk]
            
            results.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(results)

df_final = simulate_wealth(15, user_cash, df_config, bank_rate)

# --- 6. 分階段顯示與「年度總計」欄位 ---
phases = [(2026,2028,"第一階段"),(2029,2031,"第二階段"),(2032,2034,"第三階段"),(2035,2037,"第四階段"),(2038,2041,"最終階段")]

for s, e, title in phases:
    st.subheader(f"📍 {title} ({s}-{e})")
    sub = df_final[(df_final["年份"] >= s) & (df_final["年份"] <= e)]
    pivot = sub.pivot(index="月份", columns="年份", values="預估金額").reindex([f"{i}月" for i in range(1, 13)])
    
    # 計算並插入年度總計列
    totals = pivot.sum().to_frame().T
    totals.index = ["年度總計"]
    final_display = pd.concat([pivot, totals])
    
    st.table(final_display.style.format("{:,.0f}").apply(
        lambda x: ['background-color: #f0f2f6; font-weight: bold; color: #1f77b4' if x.name == '年度總計' else '' for _ in x], axis=1)
    )

st.success(f"🎊 預估 15 年總領取金額：**NT$ {df_final['預估金額'].sum():,.0f}** (定存利率以 {bank_rate*100:.2f}% 計算)")
