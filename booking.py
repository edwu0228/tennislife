import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os

# ==========================================
# 1. 介面與基本設定
# ==========================================
st.set_page_config(page_title="網球雲端預約中心", layout="wide")

# Banner 區塊
BANNER_PATH = "banner.jpg" 
if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_container_width=True)
else:
    st.image("https://images.unsplash.com/photo-1595435064219-510ccbdbd239?auto=format&fit=crop&q=80&w=2000", use_container_width=True)

# 標題與刷新按鈕
col_t, col_r = st.columns([5, 1])
with col_t:
    st.title("🎾 專業網球雲端預約系統")
with col_r:
    if st.button("🔄 刷新頁面 / 回首頁", use_container_width=True):
        st.cache_data.clear()
        if 'active_slot' in st.session_state: del st.session_state.active_slot
        st.rerun()

# ==========================================
# 2. 資料連線邏輯 (核心除錯區)
# ==========================================
def get_date_with_weekday(date_str):
    try:
        date_str = str(date_str).split(" ")[0]
        d = datetime.strptime(date_str, '%Y-%m-%d')
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        return f"{date_str} ({weekdays[d.weekday()]})"
    except:
        return date_str

# 初始化連線
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_all_data():
    # ttl=0 確保每次都抓最新，不被快取干擾
    df_c = conn.read(worksheet="courts", ttl=0).dropna(how="all")
    df_cal = conn.read(worksheet="calendar", ttl=0).dropna(how="all")
    df_b = conn.read(worksheet="bookings", ttl=0).dropna(how="all")
    return df_c, df_cal, df_b

# --- 替換後的除錯啟動區區 ---
try:
    df_courts, df_calendar, df_bookings = fetch_all_data()
except Exception as e:
    st.error(f"⚠️ 偵測到具體錯誤：{str(e)}")
    st.info("💡 檢查清單：\n1. Google 試算表是否已開啟「知道連結的人即可編輯」？\n2. Secrets 中的網址是否正確？\n3. 分頁名稱是否為 courts, calendar, bookings？")
    st.stop()
# --------------------------

# ==========================================
# 3. 身分切換
# ==========================================
role = st.sidebar.radio("切換身分", ["一般使用者", "管理員登入"])

# ==========================================
# 4. 管理者介面
# ==========================================
if role == "管理員登入":
    password = st.sidebar.text_input("輸入管理員密碼", type="password")
    if password == "1234":
        t1, t2, t3 = st.tabs(["🏗️ 場地管理", "📅 開放課程", "📝 預約名單"])
        
        with t1:
            st.subheader("場地清單")
            new_c = st.text_input("新增場地名稱")
            if st.button("➕ 確定新增"):
                if new_c:
                    new_row = pd.DataFrame([{"court_name": new_c}])
                    updated = pd.concat([df_courts, new_row], ignore_index=True)
                    conn.update(worksheet="courts", data=updated)
                    st.success("場地已更新！"); st.rerun()
            st.table(df_courts)

        with t2:
            st.subheader("開放課程時段")
            c1, c2, c3 = st.columns(3)
            with c1: admin_date = st.date_input("選擇日期", date.today())
            with c2: 
                clist = df_courts['court_name'].tolist() if not df_courts.empty else []
                admin_court = st.selectbox("選擇場地", clist)
            with c3: admin_time = st.selectbox("選擇時段", [f"{h:02d}:00" for h in range(8, 22)])
            admin_note = st.text_area("課程備註")
            
            if st.button("✅ 確認開放時段", use_container_width=True):
                new_slot = pd.DataFrame([{"date": str(admin_date), "court": admin_court, "time": admin_time, "note": admin_note}])
                updated_cal = pd.concat([df_calendar, new_slot], ignore_index=True)
                conn.update(worksheet="calendar", data=updated_cal)
                st.success("已同步至雲端課表！"); st.rerun()
            
            st.write("---")
            st.dataframe(df_calendar, use_container_width=True)
            if st.button("🧨 清空所有開放時段"):
                conn.update(worksheet="calendar", data=pd.DataFrame(columns=["date", "court", "time", "note"]))
                st.rerun()

        with t3:
            st.subheader("👥 學生預約清單")
            st.dataframe(df_bookings, use_container_width=True)
    else:
        st.info("請輸入密碼進入管理系統")

# ==========================================
# 5. 一般使用者介面
# ==========================================
else:
    st.header("📅 預約網球課程")
    
    if not df_calendar.empty:
        df_calendar['date'] = df_calendar['date'].astype(str)
