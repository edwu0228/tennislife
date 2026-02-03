import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_calendar import calendar as st_calendar

# --- 1. 基本設定 ---
st.set_page_config(page_title="球場預約系統", layout="wide")
ADMIN_PASSWORD = "1234"
BANNER_IMAGE = "https://images.unsplash.com/photo-1595435064214-08df12859444?q=80&w=1000"

# --- 2. 建立 Google Sheets 連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name, columns):
    try:
        # ttl=0 代表不使用暫存，每次都抓最新資料
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear() # 強制清除所有讀取快取

# --- 3. 載入資料 ---
df_bookings = load_data("bookings", ["姓名", "日期", "地點", "時段", "備註"])
df_config = load_data("config", ["日期", "地點", "時段", "備註"])
df_price = load_data("price", ["內容"])

# 處理費用文字
if not df_price.empty:
    price_content = str(df_price.iloc[0, 0])
else:
    price_content = "請至後台設定費用內容"

# --- 4. 橫幅與導覽 ---
st.image(BANNER_IMAGE, use_container_width=True)
st.sidebar.title("🎾 球場預約管理系統")
mode = st.sidebar.radio("請選擇模式：", ["我要預約", "費用介紹", "管理者後台"])

# --- 5. 【我要預約】模式 ---
if mode == "我要預約":
    st.title("📅 球場預約月曆")
    
    if not df_config.empty:
        calendar_events = []
        loc_map = {"社子風箏球場": "社子", "內湖美堤球場": "內湖", "萬華雙園球場": "萬華"}
        
        for _, row in df_config.iterrows():
            is_booked = ((df_bookings['日期'].astype(str) == str(row['日期'])) & 
                         (df_bookings['地點'] == row['地點']) & 
                         (df_bookings['時段'] == row['時段'])).any()
            
            color = "#FF4B4B" if is_booked else "#28a745"
            status_icon = "🈵" if is_booked else "✅"
            short_loc = loc_map.get(row['地點'], row['地點'][:2])
            note_text = f"\n[{row['備註']}]" if pd.notna(row['備註']) and str(row['備註']).strip() != "" else ""
            
            # 取得時段開始與結束
            try:
                start_t = str(row['時段']).split(" - ")[0]
                end_t = str(row['時段']).split(" - ")[1]
            except:
                start_t, end_t = "06:00", "07:00"

            calendar_events.append({
                "title": f"{short_loc}{status_icon}{note_text}",
                "start": f"{row['日期']}T{start_t}:00",
                "end": f"{row['日期']}T{end_t}:00",
                "color": color,
            })

        st_calendar(events=calendar_events, options={
            "initialView": "timeGridWeek",
            "slotMinTime": "06:00:00", "slotMaxTime": "23:00:00",
            "allDaySlot": False, "height": 600
        })

    st.divider()
    st.subheader("✍️ 填寫預約單")
    if df_config.empty:
        st.info("目前尚無開放時段。")
    else:
        # 表單邏輯 (簡化版)
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_date = st.selectbox("日期", sorted(df_config["日期"].unique()))
        with c2:
            sel_loc = st.selectbox("地點", df_config[df_config["日期"] == sel_date]["地點"].unique())
        with c3:
            all_s = df_config[(df_config["日期"] == sel_date) & (df_config["地點"] == sel_loc)]["時段"].tolist()
            booked_s = df_bookings[(df_bookings["日期"].astype(str) == str(sel_date)) & (df_bookings["地點"] == sel_loc)]["時段"].tolist()
            final_s = [s for s in all_s if s not in booked_s]
            sel_time = st.selectbox("時段", final_s if final_s else ["已客滿"])

        name = st.text_input("預約人姓名")
        user_note = st.text_area("給教練的備註")
        
        if st.button("提交預約") and name and sel_time != "已客滿":
            new_data = pd.DataFrame([[name, str(sel_date), sel_loc, sel_time, user_note]], columns=df_bookings.columns)
            df_bookings = pd.concat([df_bookings, new_data], ignore_index=True)
            save_data(df_bookings, "bookings")
            st.success("預約成功！")
            st.rerun()

# --- 6. 【費用介紹】模式 ---
elif mode == "費用介紹":
    st.title("💰 費用與收費標準")
    st.markdown(price_content)

# --- 7. 【管理者後台】模式 ---
else:
    st.title("🔐 管理者後台")
    pwd = st.sidebar.text_input("請輸入管理員密碼：", type="password")
    
    if pwd == ADMIN_PASSWORD:
        t1, t2, t3 = st.tabs(["⚙️ 時段設定", "📊 預約管理", "💵 費用資訊修改"])
        
        with t1:
            st.subheader("新增時段")
            date_input = st.date_input("選擇日期")
            loc_input = st.selectbox("球場", ["社子風箏球場", "內湖美堤球場", "萬華雙園球場"])
            time_input = st.selectbox("時段", [f"{str(h).zfill(2)}:00 - {str(h+1).zfill(2)}:00" for h in range(6, 23)])
            note_input = st.text_input("備註 (例如: 團體課)")
            if st.button("確認新增"):
                new_c = pd.DataFrame([[str(date_input), loc_input, time_input, note_input]], columns=df_config.columns)
                df_config = pd.concat([df_config, new_c], ignore_index=True).drop_duplicates()
                save_data(df_config, "config")
                st.rerun()

        with t2:
            st.subheader("刪除預約")
            if not df_bookings.empty:
                sel_del = st.multiselect("選取要刪除的項目", df_bookings.index.map(lambda i: f"{i}: {df_bookings.loc[i, '姓名']}"))
                if sel_del and st.button("確認刪除"):
                    idx = [int(s.split(":")[0]) for s in sel_del]
                    df_bookings = df_bookings.drop(idx)
                    save_data(df_bookings, "bookings")
                    st.rerun()
                st.dataframe(df_bookings)

        with t3:
            st.subheader("編輯費用介紹")
            new_price = st.text_area("請輸入 Markdown 格式內容", value=price_content, height=300)
            if st.button("儲存費用資訊"):
                df_p = pd.DataFrame([[new_price]], columns=["內容"])
                save_data(df_p, "price")
                st.success("儲存成功！")
                st.rerun()
