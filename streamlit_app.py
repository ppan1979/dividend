import streamlit as st
import pandas as pd
import requests
import io

# --- 1. 訪問權限檢查 ---
if "password_correct" not in st.session_state:
    def password_entered():
        if st.session_state["password"] == "1215":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
    st.sidebar.text_input("請輸入密碼後按 Enter", type="password", on_change=password_entered, key="password")
    st.stop()

# --- 2. 核心資產與科學平均值設定 ---
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

# 五年算術平均基準 (科學基礎)
SCIENTIFIC_AVG = {
    "0050": 4.06, "006208": 2.78, "2412": 4.60, "2892": 1.15,
    "00878": 1.45, "00919": 2.50, "2002": 0.82, "2633": 1.02
}

# --- 3. 證交所數據抓取 (強化版) ---
@st.cache_data(ttl=600) # 縮短緩存時間，確保股價更即時
def get_market_data():
    prices_map = {}
    dps_map = {}
    
    # A. 抓取即時股價 (增加異常處理與欄位自動偵測)
    try:
        p_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
        p_res = requests.get(p_url, timeout=10)
        p_df = pd.read_csv(io.StringIO(p_res.text))
        # 清理欄位標題中的空格與引號
        p_df.columns = [c.replace('"', '').strip() for c in p_df.columns]
        
        # 動態尋找包含「代號」與「收盤」字眼的欄位
        id_col = [c for c in p_df.columns if "證券代號" in c or "代碼" in c][0]
        price_col = [c for c in p_df.columns if "收盤價" in c][0]
        
        live_prices = pd.Series(p_df[price_col].values, index=p_df[id_col].astype(str)).to_dict()
    except Exception as e:
        st.warning(f"無法從證交所獲取即時股價，改用參考價格。({e})")
        live_prices = {}

    # B. 抓取最新配息公告
    try:
        div_url = "https://www.twse.com.tw/exchangeReport/TWT48U?response=open_data"
        div_df = pd.read_csv(io.StringIO(requests.get(div_url, timeout=10).text))
        div_df.columns = [c.replace('"', '').strip() for c in div_df.columns]
        latest_ann = pd.Series(div_df['現金股利'].values, index=div_df['股票代號'].astype(str)).to_dict()
    except:
        latest_ann = {}

    # C. 邏輯整合
    for tk, info in ASSET_DETAILS.items():
        # 1. 股價解析
        p_val = live_prices.get(tk, 100.0)
        try:
            # 處理千分位逗號
            prices_map[tk] = float(str(p_val).replace(",", ""))
        except:
            prices_map[tk] = 100.0

        # 2. 配息科學計算 (公告優先於五年平均)
        yearly_total = latest_ann.get(tk)
        if pd.isna(yearly_total) or yearly_total == 0:
            yearly_total = SCIENTIFIC_AVG.get(tk, 1.0)
        
        # 3. 0050 分割校正 (1:4)
        if tk == "0050":
            yearly_total = yearly_total / 4
            
        avg_single = yearly_total / len(info['months'])
        dps_map[tk] = {m: round(avg_single, 3) for m in info['months']}
            
    return prices_map, dps_map

# --- 4. 介面呈現 ---
st.set_page_config(layout="wide", page_title="投資領息精算表")
st.title("📊 15年投資明細 (證交所連線強化版)")

if st.button("🔄 立即更新證交所最新數據"):
    st.cache_data.clear()
    st.rerun()

prices, STRICT_DPS = get_market_data()

# 看板表格
st.subheader("📈 證交所即時行情與預估")
combined_view = []
for tk, info in ASSET_DETAILS.items():
    s_dps = list(STRICT_DPS[tk].values())[0]
    combined_view.append({
        "代碼": tk, "名稱": info['name'], "目前股價": f"{prices[tk]:.2f}", 
        "預估單次配息": s_dps, "除息月份": ", ".join(map(str, info['months']))
    })
st.table(pd.DataFrame(combined_view))

# 設定區
c1, c2 = st.columns(2)
with c1:
    user_cash = st.number_input("💰 定存總額 (NTD):", value=3000000)
with c2:
    bank_rate = st.slider("🏦 定存年利率 (%):", 0.0, 5.0, 1.75, 0.05) / 100

# 編輯區
st.write("📝 **編輯初始股數與每月投入：**")
df_config = st.data_editor(
    pd.DataFrame([{"代碼": k, "名稱": v['name'], "初始": v['base'], "月投": v['m']} for k, v in ASSET_DETAILS.items()]),
    hide_index=True, use_container_width=True,
    column_config={
        "代碼": st.column_config.TextColumn("代碼", width=60),
        "名稱": st.column_config.TextColumn("名稱", width=100),
        "初始": st.column_config.NumberColumn("初始", width=80),
        "月投": st.column_config.NumberColumn("月投", width=80),
    }
)

# --- 5. 複利模擬 ---
def simulate(years, cash, config, rate):
    res = []
    cfg = {row["代碼"]: {"base": row["初始"], "m": row["月投"]} for _, row in config.iterrows()}
    shares = {tk: float(c["base"]) for tk, c in cfg.items()}
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            income = cash * (rate / 12)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info: income += shares[tk] * dps_info[m]
            for tk, c in cfg.items():
                if prices[tk] > 0: shares[tk] += c["m"] / prices[tk]
            res.append({"年份": yr, "月份": f"{m}月", "金額": round(income)})
    return pd.DataFrame(res)

df_final = simulate(15, user_cash, df_config, bank_rate)

# 分階段表格
phases = [(2026,2028,"第一階段"),(2029,2031,"第二階段"),(2032,2034,"第三階段"),(2035,2037,"第四階段"),(2038,2041,"最終階段")]
for s, e, title in phases:
    sub = df_final[(df_final["年份"] >= s) & (df_final["年份"] <= e)]
    if not sub.empty:
        st.subheader(f"📍 {title} ({s}-{e})")
        pivot = sub.pivot(index="月份", columns="年份", values="金額").reindex([f"{i}月" for i in range(1, 13)])
        totals = pivot.sum().to_frame().T
        totals.index = ["年度總計"]
        st.table(pd.concat([pivot, totals]).style.format("{:,.0f}"))

st.success(f"🎊 15 年預估總領金額：**NT$ {df_final['金額'].sum():,.0f}**")
