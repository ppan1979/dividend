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

# --- 2. 初始設定與配息月份 ---
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

INT_RATE = 0.0175    

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

# --- 3. 介面配置 ---
st.set_page_config(layout="wide", page_title="投資組合 Dashboard")
st.title("📈 股票投資資產 Dashboard")

# 頂部控制列
col_cash, col_btn = st.columns([3, 1])
with col_cash:
    user_cash = st.number_input("💰 當前定存總額 (元):", value=3000000, step=10000)
with col_btn:
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
            prices[ticker] = 0.0
    return prices

prices = get_prices()

# --- 5. 整合型 Dashboard 表格 (可編輯區) ---
st.subheader("📋 即時行情與參數設定")

# 建立可動態異動的配置字典
updated_assets = {}

# 顯示標題列
h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 1.5, 1.5, 2, 2])
h_col1.markdown("**標題名稱 (代碼)**")
h_col2.markdown("**即時股價**")
h_col3.markdown("**除息月份**")
h_col4.markdown("**初始股數 (可改)**")
h_col5.markdown("**每月定額 (可改)**")

for tk, info in DEFAULT_ASSETS.items():
    c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 2, 2])
    
    # 名稱與代碼整合
    c1.write(f"{info['name']} ({tk})")
    
    # 即時股價
    c2.write(f"${prices[tk]}")
    
    # 除息月份 (移除「月」字)
    mo_list = sorted(list(STRICT_DPS.get(tk, {}).keys()))
    c3.write(", ".join(map(str, mo_list)))
    
    # 可編輯的初始股數
    new_base = c4.number_input(f"股數_{tk}", value=int(info['base']), label_visibility="collapsed", key=f"b_{tk}")
    
    # 可編輯的定期定額
    new_m = c5.number_input(f"定額_{tk}", value=int(info['m']), label_visibility="collapsed", key=f"m_{tk}")
    
    updated_assets[tk] = {
        "name": info["name"],
        "base": new_base,
        "m": new_m,
        "start_mo": info["start_mo"]
    }

st.markdown("---")

# --- 6. 計算預估邏輯 ---
def calculate_projection(years, cash, assets_cfg):
    rows = []
    for yr in range(2026, 2026 + years):
        for m in range(1, 13):
            # 銀行利息
            income = cash * (INT_RATE / 12)
            for tk, info in assets_cfg.items():
                curr_mo = (yr - 2026) * 12 + m
                if curr_mo >= info["start_mo"]:
                    price = prices[tk] if prices[tk] > 0 else 100.0
                    passed = curr_mo - info["start_mo"]
                    # 總持股 = 初始股數 + (每月定額 * 經過月數 / 股價)
                    total_shares = info["base"] + (info["m"] * passed / price)
                    if m in STRICT_DPS.get(tk, {}):
                        income += total_shares * STRICT_DPS[tk][m]
            rows.append({"年份": yr, "月份": f"{m}月", "預估金額": round(income)})
    return pd.DataFrame(rows)

df = calculate_projection(15, user_cash, updated_assets)

# --- 7. 顯示 15 年現金流明細 ---
def render_table(s_yr, e_yr, title):
    st.subheader(title)
    sub_df = df[(df["年份"] >= s_yr) & (df["年份"] <= e_yr)]
    pivot = sub_df.pivot(index="月份", columns="年份", values="預估金額")
    st.table(pivot.reindex([f"{i}月" for i in range(1, 13)]))
    
    # 年度加總
    annual = sub_df.groupby("年份")["預估金額"].sum().reset_index()
    annual.columns = ["年份", "該年總入帳"]
    st.dataframe(annual, hide_index=True, use_container_width=True)

# 渲染各階段
ranges = [(2026, 2028), (2029, 2031), (2032, 2034), (2035, 2037), (2038, 2040), (2041, 2041)]
for s, e in ranges:
    render_table(s, e, f"📍 {s} - {e} 預估明細")

st.success(f"🎊 15 年累計預估總領取：**{df['預估金額'].sum():,.0f}** 元")
