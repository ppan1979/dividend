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

# --- 2. 核心數據與配息設定 (嚴格鎖定) ---
# 確保 006208 只有 7, 11 月配息，0050 為 1, 7 月
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
    "0050.TW":   {"name": "元大台灣50", "base": 15793, "m": 5000, "start_mo": 1},
    "006208.TW": {"name": "富邦台50", "base": 4800,  "m": 5000, "start_mo": 1},
    "2412.TW":   {"name": "中華電", "base": 2556,  "m": 5000, "start_mo": 1},
    "2892.TW":   {"name": "第一金", "base": 13464, "m": 5000, "start_mo": 1},
    "00878.TW":  {"name": "國泰永續高股息", "base": 200,   "m": 5000, "start_mo": 4},
    "00919.TW":  {"name": "群益台灣精選高息", "base": 210,   "m": 5000, "start_mo": 4},
    "2002.TW":   {"name": "中鋼", "base": 5106,  "m": 0,    "start_mo": 1},
    "2633.TW":   {"name": "台灣高鐵", "base": 1802,  "m": 0,    "start_mo": 1},
}

# --- 3. 頁面配置 ---
st.set_page_config(layout="wide")
st.title("📊 股票資產即時 Dashboard")

# 控制列
col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    user_cash = st.number_input("💰 定存總額設定:", value=3000000, step=10000)
with col_top2:
    st.write(" ")
    if st.button("🔄 一鍵更新所有數據"):
        st.cache_data.clear()
        st.rerun()

# --- 4. 股價抓取 ---
@st.cache_data(ttl=3600)
def get_prices():
    prices = {}
    for ticker in DEFAULT_ASSETS.keys():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            prices[ticker] = resp.json()['chart']['result'][0]['meta']['regularMarketPrice']
        except:
            prices[ticker] = 100.0 # 備用價格
    return prices

prices = get_prices()

# --- 5. 即時看板區 (Dashboard 橫向顯示) ---
st.subheader("📈 市場即時行情看板")
rows = [list(DEFAULT_ASSETS.keys())[i:i+4] for i in range(0, len(DEFAULT_ASSETS), 4)]
for row in rows:
    cols = st.columns(4)
    for i, tk in enumerate(row):
        with cols[i]:
            info = DEFAULT_ASSETS[tk]
            mo_list = sorted(list(STRICT_DPS.get(tk, {}).keys()))
            st.metric(label=f"{info['name']} ({tk})", value=f"${prices[tk]}")
            st.caption(f"除息月份: {', '.join(map(str, mo_list))}")

st.markdown("---")

# --- 6. 參數編輯區 (表格形式) ---
st.subheader("⚙️ 資產參數微調")
edit_df = []
for tk, info in DEFAULT_ASSETS.items():
    edit_df.append({
        "標的": f"{info['name']} ({tk})",
        "代碼": tk,
        "初始股數": info['base'],
        "每月定額": info['m']
    })

# 使用實驗性 data_editor 讓表格可直接修改
edited_data = st.data_editor(pd.DataFrame(edit_df), hide_index=True, use_container_width=True)

# 將修改後的數據轉回字典供計算使用
updated_assets = {}
for _, row in edited_data.iterrows():
    tk = row["代碼"]
    updated_assets[tk] = {
        "base": row["初始股數"],
        "m": row["每月定額"],
        "start_mo": DEFAULT_ASSETS[tk]["start_mo"]
    }

# --- 7. 計算與顯示 15 年明細 ---
def calculate_fixed(years, cash, config):
    data = []
    int_rate = 0.0175
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            income = cash * (int_rate / 12)
            for tk, info in config.items():
                curr_total_mo = (yr - 2026) * 12 + m
                if curr_total_mo >= info["start_mo"]:
                    price = prices[tk]
                    passed = curr_total_mo - info["start_mo"]
                    # 重新校正股數累積邏輯
                    shares = info["base"] + (info["m"] * passed / price)
                    if m in STRICT_DPS.get(tk, {}):
                        income += shares * STRICT_DPS[tk][m]
            data.append({"年份": yr, "月份": f"{m}月", "預估入帳": round(income)})
    return pd.DataFrame(data)

df_full = calculate_fixed(15, user_cash, updated_assets)

# 分段顯示表格
ranges = [(2026, 2028), (2029, 2031), (2032, 2034), (2035, 2037), (2038, 2040), (2041, 2041)]
for s, e in ranges:
    st.subheader(f"📍 {s} - {e} 預估明細")
    sub = df_full[(df_full["年份"] >= s) & (df_full["年份"] <= e)]
    pivot = sub.pivot(index="月份", columns="年份", values="預估入帳")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    ann_sum = sub.groupby("年份")["預估入帳"].sum().reset_index()
    ann_sum.columns = ["年份", "該年總領取預估"]
    st.dataframe(ann_sum, hide_index=True, use_container_width=True)

st.success(f"🎊 15 年累計預估總額：**{df_full['預估入帳'].sum():,.0f}** 元")
