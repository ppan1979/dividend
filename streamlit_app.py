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

# --- 2. 核心數據鎖定 ---
STRICT_DPS = {
    "0050.TW":   {1: 1.0, 7: 3.0},
    "006208.TW": {7: 2.2, 11: 0.8}, 
    "2412.TW":   {8: 4.7},
    "2892.TW":   {8: 1.5},
    "00878.TW":  {2: 0.55, 5: 0.55, 8: 0.55, 11: 0.55},
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

# --- 3. 頁面配置與股價 ---
st.set_page_config(layout="wide")
st.title("📊 股票資產即時 Dashboard")

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

# --- 4. 即時看板 (Dashboard) ---
st.subheader("📈 市場即時行情")
ks = list(DEFAULT_ASSETS.keys())
for i in range(0, len(ks), 4):
    cols = st.columns(4)
    for j, tk in enumerate(ks[i:i+4]):
        with cols[j]:
            info = DEFAULT_ASSETS[tk]
            mos = sorted(list(STRICT_DPS.get(tk, {}).keys()))
            st.metric(label=f"{info['name']} ({tk})", value=f"${prices[tk]}")
            st.caption(f"除息月份: {', '.join(map(str, mos))}")

st.markdown("---")

# --- 5. 參數異動區 ---
st.subheader("⚙️ 資產參數與定存設定")
c_cash, c_btn = st.columns([3, 1])
with c_cash:
    user_cash = st.number_input("💰 當前定存總額 (元):", value=3000000, step=10000)
with c_btn:
    st.write(" ")
    if st.button("🔄 執行計算 (一鍵更新)"):
        st.cache_data.clear()
        st.rerun()

edit_list = []
for tk, info in DEFAULT_ASSETS.items():
    edit_list.append({"代碼": tk, "名稱": info['name'], "初始股數": info['base'], "每月定額": info['m']})

edited_df = st.data_editor(pd.DataFrame(edit_list), hide_index=True, use_container_width=True)

# --- 6. 核心計算引擎 (精確修復版) ---
def run_calculation(years, cash_base, config_df):
    results = []
    # 建立配置地圖
    cfg = {row["代碼"]: {"base": row["初始股數"], "m": row["每月定額"]} for _, row in config_df.iterrows()}
    
    # 追蹤每檔股票當前的累積股數
    current_shares = {tk: float(c["base"]) for tk, c in cfg.items()}
    
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # A. 計算銀行月利息 (以當前定存額計)
            monthly_income = cash_base * (0.0175 / 12)
            
            # B. 檢查本月是否有配息 (配息是根據「本月買入前」的累積股數)
            for tk, dps_info in STRICT_DPS.items():
                if m in dps_info:
                    monthly_income += current_shares[tk] * dps_info[m]
            
            # C. 每月月底進行定期定額買入 (增加股數，供下個月配息使用)
            for tk, c in cfg.items():
                if c["m"] > 0:
                    new_bought = c["m"] / prices[tk]
                    current_shares[tk] += new_bought
            
            results.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(monthly_income)})
    return pd.DataFrame(results)

df_final = run_calculation(15, user_cash, edited_df)

# --- 7. 顯示明細 ---
st.markdown("---")
phases = [(2026, 2028), (2029, 2031), (2032, 2034), (2035, 2037), (2038, 2040), (2041, 2041)]
for s, e in phases:
    st.subheader(f"📍 {s} - {e} 預估明細")
    sub = df_final[(df_final["年份"] >= s) & (df_final["年份"] <= e)]
    pivot = sub.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    ann = sub.groupby("年份")["預估入帳"].sum().reset_index()
    ann.columns = ["年份", "年度總入帳"]
    st.dataframe(ann, hide_index=True, use_container_width=True)

st.success(f"🎊 15 年累計預估領取：**{df_final['預估入帳'].sum():,.0f}** 元")
