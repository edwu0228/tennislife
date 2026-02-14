import streamlit as st
import json
import os
from datetime import datetime, date
import pandas as pd

# ==========================================
# 1. 永久儲存與工具邏輯
# ==========================================
DB_FILE = 'tennis_data.json'

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return None
    return None

def save_data():
    data_to_save = {
        "calendar_data": st.session_state.calendar_data,
        "courts": st.session_state.courts,
        "booked_data": st.session_state.booked_data
    }
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)

def get_date_with_weekday(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    return f"{date_str} ({weekdays[d.weekday()]})"

# ==========================================
# 2. 初始化 Session State
# ==========================================
if 'initialized' not in st.session_state:
    saved_info = load_data()
    if saved_info:
        st.session_state.calendar_data = saved_info.get("calendar_data", [])
        st.session_state.courts = saved_info.get("courts", ["第一場地", "第二場地"])
        st.session_state.booked_data = saved_info.get("booked_data", [])
    else:
        st.session_state.calendar_data = []
        st.session_state.courts = ["第一場地", "第二場地"]
        st.session_state.booked_data = []
    st.session_state.initialized = True

# ==========================================
# 3. 介面設定
# ==========================================
st.set_page_config(page_title="網球預約系統 V8", layout="wide")

# --- 🖼️ Banner 區塊 ---
BANNER_PATH = "banner.jpg" 
if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_container_width=True)
else:
    st.image("https://images.unsplash.com/photo-1595435064219-510ccbdbd239?auto=format&fit=crop&q=80&w=2000", 
             caption="歡迎來到網球中心", use_container_width=True)

# --- 🏠 回到首頁功能 (橫跨身分) ---
col_title, col_home = st.columns([5, 1])
with col_title:
    st.title("🎾 專業網球預約中心")
with col_home:
    st.write("") # 調整間距
    if st.button("🏠 回到首頁", use_container_width=True):
        # 清除所有選取狀態
        if 'active_slot' in st.session_state:
            del st.session_state.active_slot
        st.rerun()

role = st.sidebar.radio("切換身分", ["一般使用者", "管理員登入"])

# ==========================================
# 4. 管理者介面
# ==========================================
if role == "管理員登入":
    st.header("⚙️ 管理員後台設定")
    password = st.sidebar.text_input("輸入管理員密碼", type="password")
    if password == "1234":
        tab1, tab2, tab3 = st.tabs(["🏗️ 場地管理", "📅 開放課程管理", "📝 學生預約清單"])
        
        with tab1:
            st.subheader("管理場地清單")
            new_court_input = st.text_input("輸入新場地名稱")
            if st.button("➕ 新增場地"):
                if new_court_input and new_court_input not in st.session_state.courts:
                    st.session_state.courts.append(new_court_input); save_data(); st.rerun()
            for index, court_name in enumerate(st.session_state.courts):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"📍 **{court_name}**")
                with c2:
                    with st.popover("編輯"):
                        edit_name = st.text_input("修改名稱", value=court_name, key=f"e_{index}")
                        if st.button("確認", key=f"eb_{index}"):
                            st.session_state.courts[index] = edit_name; save_data(); st.rerun()
                if c3.button("🗑️", key=f"d_{index}"):
                    st.session_state.courts.pop(index); save_data(); st.rerun()

        with tab2:
            st.subheader("設定開放預約時段")
            ca1, ca2, ca3 = st.columns(3) # 改名避免與前台衝突
            with ca1: admin_date = st.date_input("選擇日期", date.today())
            with ca2: admin_court = st.selectbox("選擇場地", st.session_state.courts)
            with ca3: admin_time = st.selectbox("選擇時段", [f"{h:02d}:00" for h in range(8, 22)])
            admin_note = st.text_area("課程備註 (教練、內容等)")
            if st.button("✅ 確認開放", use_container_width=True):
                new_slot = {"date": str(admin_date), "court": admin_court, "time": admin_time, "note": admin_note}
                st.session_state.calendar_data.append(new_slot); save_data(); st.toast("課程已同步！")
            
            st.write("---")
            st.subheader("📋 目前已開放的所有課程 (可手動刪除)")
            if st.session_state.calendar_data:
                for idx, slot in enumerate(st.session_state.calendar_data):
                    col_info, col_del = st.columns([5, 1])
                    with col_info:
                        date_display = get_date_with_weekday(slot['date'])
                        st.write(f"📅 **{date_display}** | ⏰ {slot['time']} | 🏟️ {slot['court']} | 📝 {slot.get('note','')}")
                    with col_del:
                        if st.button("❌ 刪除", key=f"del_slot_{idx}"):
                            st.session_state.calendar_data.pop(idx); save_data(); st.rerun()
            else: st.info("目前沒有開放時段。")

        with tab3:
            st.subheader("👥 學生預約清單")
            if st.session_state.booked_data:
                df_booked = pd.DataFrame(st.session_state.booked_data).rename(columns={"date":"日期","court":"場地","time":"時間","user_name":"學生","user_phone":"電話","user_note":"學生備註"})
                st.dataframe(df_booked, use_container_width=True)
            else: st.info("目前尚無預約。")
    else: st.info("請輸入密碼進入後台")

# ==========================================
# 5. 一般使用者介面
# ==========================================
else:
    st.header("📅 預約網球課程")

    available_dates = sorted(list(set([s['date'] for s in st.session_state.calendar_data])))
    
    if available_dates:
        st.write("### 1. 選擇日期")
        date_options = {get_date_with_weekday(d): d for d in available_dates}
        
        # 這裡加一個 index 確保回到首頁時能重置
        selected_display = st.radio(
            "請點選日期查看當天課程：",
            options=list(date_options.keys()),
            horizontal=True,
            key="date_radio"
        )
        selected_date_str = date_options[selected_display]

        st.write(f"### 2. {selected_display} 課程詳情")
        today_slots = [s for s in st.session_state.calendar_data if s['date'] == selected_date_str]
        
        for s in today_slots:
            is_booked = any(b['date'] == s['date'] and b['court'] == s['court'] and b['time'] == s['time'] for b in st.session_state.booked_data)
            
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    status_tag = "🔴 [已約滿]" if is_booked else "🟢 [可預約]"
                    st.markdown(f"#### {status_tag} {s['time']} - {s['court']}")
                    st.write(f"**💡 課程說明：** {s.get('note', '無備註')}")
                with col_btn:
                    if not is_booked:
                        if st.button("立即預約", key=f"book_{s['date']}_{s['court']}_{s['time']}", use_container_width=True):
                            st.session_state.active_slot = s; st.toast(f"已選取 {s['time']}")
                    else:
                        st.button("已約滿", disabled=True, key=f"full_{s['date']}_{s['court']}_{s['time']}", use_container_width=True)

        # 預約表單區
        if 'active_slot' in st.session_state:
            s = st.session_state.active_slot
            # 只有當選取的時段日期與上方 radio 一致才顯示
            if s['date'] == selected_date_str:
                st.write("---")
                st.write(f"### 3. 填寫預約資訊：{s['court']} ({s['time']})")
                with st.form("booking_form"):
                    c1, c2 = st.columns(2)
                    u_name = c1.text_input("學生姓名 *")
                    u_phone = c2.text_input("聯絡電話 *")
                    u_note = st.text_area("預約備註")
                    
                    form_col1, form_col2 = st.columns(2)
                    with form_col1:
                        if st.form_submit_button("🚀 確認提交預約單", use_container_width=True):
                            if u_name and u_phone:
                                new_booking = {"date": s['date'], "court": s['court'], "time": s['time'], "user_name": u_name, "user_phone": u_phone, "user_note": u_note}
                                st.session_state.booked_data.append(new_booking); save_data(); st.balloons(); del st.session_state.active_slot; st.rerun()
                            else: st.error("請填寫姓名與電話")
                    with form_col2:
                        # 在表單內加一個取消按鈕
                        if st.form_submit_button("❌ 取消填寫", use_container_width=True):
                            del st.session_state.active_slot
                            st.rerun()
    else:
        st.info("🎾 目前沒有開放課程。")

    if st.session_state.booked_data:
        with st.expander("📝 我的預約明細紀錄"):
            for b in st.session_state.booked_data:
                st.write(f"✅ {get_date_with_weekday(b['date'])} | {b['court']} | {b['time']} (人：{b['user_name']})")
