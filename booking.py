import streamlit as st
import pandas as pd
import os
from streamlit_calendar import calendar as st_calendar

# --- 1. 檔案與基本設定 ---
BOOKING_FILE = "bookings.csv"
CONFIG_FILE = "config.csv"
PRICE_FILE = "price_info.txt"  # 新增：儲存費用介紹的檔案
BANNER_IMAGE = "banner.jpg" 
ADMIN_PASSWORD = "1234"

def load_data(file, columns):
    if os.path.exists(file):
        try:
            return pd.read_csv(file)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# 新增：讀取與儲存文字資訊的函式
def load_text(file, default_text="請在後台設定費用介紹內容"):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return f.read()
    return default_text

def save_text(text, file):
    with open(file, "w", encoding="utf-8") as f:
        f.write(text)

# --- 2. 顯示網頁橫幅 ---
try:
    if os.path.exists(BANNER_IMAGE):
        st.image(BANNER_IMAGE, use_container_width=True)
    else:
        st.image("https://images.unsplash.com/photo-1595435064214-08df12859444?q=80&w=1000", use_container_width=True)
except:
    pass

# --- 3. 載入所有資料 ---
df_bookings = load_data(BOOKING_FILE, ["姓名", "日期", "地點", "時段", "備註"])
df_config = load_data(CONFIG_FILE, ["日期", "地點", "時段", "備註"])
price_content = load_text(PRICE_FILE)

# --- 4. 側邊欄導覽 ---
st.sidebar.title("🎾 球場預約管理系統")
mode = st.sidebar.radio("請選擇模式：", ["我要預約", "費用介紹", "管理者後台"])

# --- 5. 【我要預約】模式 ---
if mode == "我要預約":
    st.title("📅 球場預約月曆與填單")
    # (月曆與表單邏輯保持不變...)
    if not df_config.empty:
        calendar_events = []
        loc_map = {"社子風箏球場": "社子", "內湖美堤球場": "內湖", "萬華雙園球場": "萬華"}
        for _, row in df_config.iterrows():
            is_booked = ((df_bookings['日期'] == row['日期']) & (df_bookings['地點'] == row['地點']) & (df_bookings['時段'] == row['時段'])).any()
            color = "#FF4B4B" if is_booked else "#28a745"
            status_icon = "🈵" if is_booked else "✅"
            short_loc = loc_map.get(row['地點'], row['地點'][:2])
            note_text = f"\n[{row['備註']}]" if pd.notna(row['備註']) and str(row['備註']).strip() != "" else ""
            calendar_events.append({
                "title": f"{short_loc}{status_icon}{note_text}",
                "start": f"{row['日期']}T{str(row['時段']).split(' - ')[0]}:00",
                "end": f"{row['日期']}T{str(row['時段']).split(' - ')[1]}:00",
                "color": color,
            })
        calendar_options = {
            "initialView": "timeGridWeek",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
            "slotMinTime": "06:00:00", "slotMaxTime": "23:00:00", "allDaySlot": False, "height": 700,
            "eventTimeFormat": {"hour": "numeric", "minute": "2-digit", "meridiem": False, "hour12": False}
        }
        st_calendar(events=calendar_events, options=calendar_options)
    
    st.divider()
    # (表單部分省略，同原程式碼...)
    st.subheader("✍️ 填寫預約單")
    if df_config.empty:
        st.info("目前尚無開放時段，請聯繫管理員。")
    else:
        available_dates = sorted(df_config["日期"].unique())
        selected_date = st.selectbox("1. 選擇預約日期", available_dates)
        locs = df_config[df_config["日期"] == selected_date]["地點"].unique()
        selected_location = st.selectbox("2. 選擇球場地點", locs)
        all_slots = df_config[(df_config["日期"] == selected_date) & (df_config["地點"] == selected_location)]["時段"].tolist()
        already_booked = df_bookings[(df_bookings["日期"] == selected_date) & (df_bookings["地點"] == selected_location)]["時段"].tolist()
        final_times = [t for t in all_slots if t not in already_booked]
        if final_times:
            current_admin_note = df_config[(df_config["日期"] == selected_date) & (df_config["地點"] == selected_location) & (df_config["時段"] == all_slots[0])]["備註"].values[0]
            if pd.notna(current_admin_note) and str(current_admin_note).strip() != "":
                st.info(f"💡 管理者提醒：{current_admin_note}")
            name = st.text_input("3. 預約人姓名")
            note = st.text_area("4. 特別備註 (選填)")
            time = st.selectbox("5. 選擇預約時段", final_times)
            if st.button("確認提交預約"):
                if name:
                    new_b = pd.DataFrame([[name, str(selected_date), selected_location, time, note]], columns=["姓名", "日期", "地點", "時段", "備註"])
                    df_bookings = pd.concat([df_bookings, new_b], ignore_index=True)
                    save_data(df_bookings, BOOKING_FILE)
                    st.success("✅ 預約成功！")
                    st.rerun()

# --- 6. 【費用介紹】模式 ---
elif mode == "費用介紹":
    st.title("💰 費用與收費標準")
    # 直接顯示後台設定的內容 (支援 Markdown 語法)
    st.markdown(price_content)

# --- 7. 【管理者後台】模式 ---
else:
    st.title("🔐 管理者後台")
    pwd = st.sidebar.text_input("請輸入管理員密碼：", type="password")
    
    if pwd == ADMIN_PASSWORD:
        tab1, tab2, tab3 = st.tabs(["⚙️ 時段設定", "📊 預約管理", "💵 費用資訊修改"])
        
        with tab1:
            st.subheader("新增開放時段")
            LOCATION_LIST = ["社子風箏球場", "內湖美堤球場", "萬華雙園球場"]
            TIME_LIST = [f"{str(h).zfill(2)}:00 - {str(h+1).zfill(2)}:00" for h in range(6, 23)]
            c_date = st.date_input("選擇日期")
            c_loc = st.selectbox("選擇球場", LOCATION_LIST)
            c_time = st.selectbox("選擇時段", TIME_LIST)
            c_note = st.text_input("時段備註 (選填)")
            if st.button("確認開放此時段"):
                new_c = pd.DataFrame([[str(c_date), c_loc, c_time, c_note]], columns=["日期", "地點", "時段", "備註"])
                df_config = pd.concat([df_config, new_c], ignore_index=True).drop_duplicates()
                save_data(df_config, CONFIG_FILE)
                st.success("已更新班表！")
                st.rerun()
            st.divider()
            st.subheader("🗑️ 管理/移除現有時段")
            if not df_config.empty:
                config_delete_options = {f"{row['日期']} | {row['地點']} | {row['時段']} ({row['備註']})": i for i, row in df_config.iterrows()}
                selected_configs = st.multiselect("請勾選欲關閉的時段：", options=list(config_delete_options.keys()))
                if selected_configs:
                    if st.button("🗑️ 移除選取時段"):
                        df_config = df_config.drop([config_delete_options[label] for label in selected_configs])
                        save_data(df_config, CONFIG_FILE)
                        st.rerun()
                st.dataframe(df_config, use_container_width=True)

        with tab2:
            st.subheader("📋 預約紀錄管理")
            # (原本的預約刪除邏輯...)
            if not df_bookings.empty:
                delete_options = {f"{i}: {row['姓名']} | {row['日期']} | {row['地點']}": i for i, row in df_bookings.iterrows()}
                selected_labels = st.multiselect("勾選刪除預約：", options=list(delete_options.keys()))
                if selected_labels and st.button("🔥 確認刪除"):
                    df_bookings = df_bookings.drop([delete_options[label] for label in selected_labels])
                    save_data(df_bookings, BOOKING_FILE)
                    st.rerun()
                st.dataframe(df_bookings, use_container_width=True)

        with tab3:
            st.subheader("📝 編輯費用介紹內容")
            st.info("支援 Markdown 格式（可用 # 代表標題、* 代表清單）")
            # 使用 text_area 讓管理者編輯費用資訊
            new_price_info = st.text_area("請輸入費用介紹文字：", value=price_content, height=400)
            if st.button("💾 儲存費用資訊"):
                save_text(new_price_info, PRICE_FILE)
                st.success("費用資訊已更新！")
                st.rerun()