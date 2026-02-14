import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import os

# ==========================================
# 1. 建立 Google Sheets 連線
# ==========================================
# 正式上線後，請在 Streamlit Secrets 設定 connections.gsheets.spreadsheet 網址
conn = st.connection("gsheets", type=GSheetsConnection)

def get_date_with_weekday(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    return f"{date_str} ({weekdays[d.weekday()]})"

# ==========================================
# 2. 介面與 Banner
# ==========================================
st.set_page_config(page_title="網球雲端預約中心", layout="wide")

BANNER_PATH = "banner.jpg" 
if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_container_width=True)
else:
    st.image("https://images.unsplash.com/photo-1595435064219-510ccbdbd239?auto=format&fit=crop&q=80&w=2000", use_container_width=True)

# 橫跨身分的首頁按鈕
if st.button("🏠 回到首頁 / 重新整理資料"):
    if 'active_slot' in st.session_state: del st.session_state.active_slot
    st.rerun()

st.title("🎾 專業網球雲端預約系統")
role = st.sidebar.radio("切換身分", ["一般使用者", "管理員登入"])

# ==========================================
# 3. 核心資料處理 (從雲端讀取)
# ==========================================
@st.cache_data(ttl=5) # 快取 5 秒，確保資料即時性
def fetch_data(sheet_name):
    # 使用你提供的語法讀取特定分頁
    return conn.read(worksheet=sheet_name)

# 讀取目前所有資料
try:
    df_courts = fetch_data("courts")
    df_calendar = fetch_data("calendar")
    df_bookings = fetch_data("bookings")
except Exception as e:
    st.error("連線失敗，請檢查 Google Sheets 權限或 Secrets 設定。")
    st.stop()

# ==========================================
# 4. 管理者介面
# ==========================================
if role == "管理員登入":
    password = st.sidebar.text_input("輸入管理員密碼", type="password")
    if password == "1234":
        t1, t2, t3 = st.tabs(["🏗️ 場地管理", "📅 開放課程", "📝 預約名單"])
        
        with t1:
            st.subheader("管理場地")
            new_c = st.text_input("新場地名稱")
            if st.button("➕ 新增"):
                new_row = pd.DataFrame([{"court_name": new_c}])
                updated = pd.concat([df_courts, new_row], ignore_index=True)
                conn.update(worksheet="courts", data=updated)
                st.success("已更新雲端！"); st.rerun()
            st.dataframe(df_courts, use_container_width=True)

        with t2:
            st.subheader("開放課程時段")
            c1, c2, c3 = st.columns(3)
            with c1: admin_date = st.date_input("選擇日期", date.today())
            with c2: admin_court = st.selectbox("選擇場地", df_courts["court_name"].tolist())
            with c3: admin_time = st.selectbox("選擇時段", [f"{h:02d}:00" for h in range(8, 22)])
            admin_note = st.text_area("課程備註")
            
            if st.button("✅ 確認開放時段"):
                new_slot = pd.DataFrame([{"date": str(admin_date), "court": admin_court, "time": admin_time, "note": admin_note}])
                updated_cal = pd.concat([df_calendar, new_slot], ignore_index=True)
                conn.update(worksheet="calendar", data=updated_cal)
                st.toast("已同步至雲端！"); st.rerun()
            
            st.write("---")
            st.dataframe(df_calendar, use_container_width=True)
            if st.button("🧨 清空所有時段"):
                conn.update(worksheet="calendar", data=pd.DataFrame(columns=df_calendar.columns))
                st.rerun()

        with t3:
            st.subheader("📝 學生預約清單")
            st.dataframe(df_bookings, use_container_width=True)
    else:
        st.info("請輸入正確密碼")

# ==========================================
# 5. 一般使用者介面
# ==========================================
else:
    if not df_calendar.empty:
        available_dates = sorted(df_calendar['date'].unique().tolist())
        date_options = {get_date_with_weekday(d): d for d in available_dates}
        selected_display = st.radio("1. 選擇日期：", options=list(date_options.keys()), horizontal=True)
        selected_date_str = date_options[selected_display]

        st.write(f"### 2. {selected_display} 課程列表")
        today_slots = df_calendar[df_calendar['date'] == selected_date_str]

        for _, s in today_slots.iterrows():
            # 檢查是否已被預約
            is_booked = not df_bookings[(df_bookings['date'] == s['date']) & 
                                        (df_bookings['court'] == s['court']) & 
                                        (df_bookings['time'] == s['time'])].empty
            
            with st.container(border=True):
                col_i, col_b = st.columns([4, 1])
                with col_i:
                    st.markdown(f"#### {'🔴 [已滿]' if is_booked else '🟢 [可預約]'} {s['time']} - {s['court']}")
                    st.write(f"💡 **備註：** {s['note']}")
                with col_b:
                    if not is_booked:
                        if st.button("立即預約", key=f"bk_{s.name}"):
                            st.session_state.active_slot = s
                
        if 'active_slot' in st.session_state:
            slot = st.session_state.active_slot
            st.write("---")
            st.subheader(f"✍️ 填寫預約：{slot['date']} {slot['time']}")
            with st.form("bk_form"):
                u_name = st.text_input("學生姓名 *")
                u_phone = st.text_input("聯絡電話 *")
                u_note = st.text_area("預約備註 (選填)")
                if st.form_submit_button("🚀 確定提交"):
                    if u_name and u_phone:
                        new_bk = pd.DataFrame([{"date": slot['date'], "court": slot['court'], "time": slot['time'], 
                                               "user_name": u_name, "user_phone": u_phone, "user_note": u_note}])
                        updated_bks = pd.concat([df_bookings, new_bk], ignore_index=True)
                        conn.update(worksheet="bookings", data=updated_bks)
                        st.balloons(); del st.session_state.active_slot; st.rerun()
                    else:
                        st.error("請完整填寫姓名與電話")
    else:
        st.info("🎾 目前尚無開放課程。")
