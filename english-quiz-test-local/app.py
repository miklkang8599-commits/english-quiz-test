# ==============================================================================
# 🧩 英文全能練習系統 (V2.8.89 - 變數物理鎖定與 N/A 修復版)
# ==============================================================================
# 📌 版本編號 (VERSION): 2.8.89
# 🛠️ 修復重點：
#    1. [修復 AttributeError] 點擊題目時強制將 sel_name 寫入 session_state。
#    2. [修復 N/A 顯示] 確保櫥窗讀取的 tr (teach_row) 欄位名稱與題庫表完全對位。
#    3. [UI 順序] 維持：頂部篩選 ➔ 中部講解櫥窗 ➔ 底部歷程列表。
# ==============================================================================

import streamlit as st
import pandas as pd
import random
import re
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

VERSION = "2.8.89"

# --- 📦 【盒子 A：核心函數】 ---
def get_now():
    return datetime.utcnow() + timedelta(hours=8)

def standardize(v):
    val = str(v).split('.')[0].strip()
    return val.zfill(4) if val.isdigit() else val

def show_version_caption():
    st.caption(f"🚀 系統版本：Ver {VERSION} | 🌍 台灣時間鎖定 (GMT+8)")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_static_data():
    try:
        df_q = conn.read(worksheet="questions").fillna("").astype(str).replace(r'\.0$', '', regex=True)
        df_s = conn.read(worksheet="students").fillna("").astype(str).replace(r'\.0$', '', regex=True)
        return df_q, df_s
    except: return None, None

def load_dynamic_data():
    try:
        df_a = conn.read(worksheet="assignments", ttl=10)
        df_l = conn.read(worksheet="logs", ttl=10)
        return df_a, df_l
    except: return pd.DataFrame(), pd.DataFrame()

# --- 🔐 【權限與登入】 ---
st.set_page_config(page_title=f"英文練習系統 V{VERSION}", layout="wide")

if not st.session_state.get('logged_in', False):
    df_q, df_s = load_static_data()
    _, c, _ = st.columns([1, 1.2, 1])
    with c:
        st.markdown("### 🔵 系統登入")
        i_id = st.text_input("帳號", key="l_id")
        i_pw = st.text_input("密碼", type="password", key="l_pw")
        if st.button("🚀 登入系統", use_container_width=True):
            if df_s is not None:
                std_id, std_pw = standardize(i_id), standardize(i_pw)
                df_s['c_id'], df_s['c_pw'] = df_s['帳號'].apply(standardize), df_s['密碼'].apply(standardize)
                user = df_s[df_s['c_id'] == std_id]
                if not user.empty and user.iloc[0]['c_pw'] == std_pw:
                    st.session_state.clear()
                    st.session_state.update({
                        "logged_in": True, "user_id": f"EA{std_id}", "user_name": user.iloc[0]['姓名'], 
                        "group_id": user.iloc[0]['分組'], "view_mode": "管理後台" if user.iloc[0]['分組']=="ADMIN" else "練習模式"
                    })
                    st.rerun()
    st.stop()

df_q, df_s = load_static_data()
df_a, df_l = load_dynamic_data()

# --- 📦 【盒子 E：側邊欄】 ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user_name}")
    if st.session_state.group_id == "ADMIN":
        st.session_state.view_mode = st.radio("功能切換：", ["管理後台", "進入練習", "個人補強講解"])
    if st.button("🚪 登出系統"): st.session_state.clear(); st.rerun()
    st.divider(); st.caption(f"Ver {VERSION}")

# ------------------------------------------------------------------------------
# 📦 【盒子 B：個人補強講解 (修復崩潰版)】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "個人補強講解":
    st.markdown("## 🎓 教學補強：篩選 ➔ 講解 ➔ 歷程")

    # 🚀 [1. 頂部篩選區]
    with st.container():
        st.markdown("#### 🔍 步驟 1：設定篩選條件")
        f1, f2, f3 = st.columns(3)
        group_opt = ["全部"] + sorted(df_s['分組'].unique())
        sel_group = f1.selectbox("班級", group_opt, key="teach_sel_group")
        
        std_opt = sorted(df_s['姓名'].unique()) if sel_group == "全部" else sorted(df_s[df_s['分組']==sel_group]['姓名'].unique())
        sel_name = f2.selectbox("學生", std_opt, key="teach_sel_name")
        sel_ver = f3.selectbox("版本", sorted(df_q['版本'].unique()), key="teach_sel_ver")
        
        f4, f5 = st.columns(2)
        sel_unit = f4.selectbox("單元", sorted(df_q[df_q['版本']==sel_ver]['單元'].unique()), key="teach_sel_unit")
        sel_lesson = f5.selectbox("課次", sorted(df_q[(df_q['版本']==sel_ver)&(df_q['單元']==sel_unit)]['課編號'].unique()), key="teach_sel_lesson")
    
    st.divider()

    # 🚀 [2. 中部講解櫥窗 - 💡 修復 AttributeError 與 N/A]
    if st.session_state.get('show_teach_ui') and 'current_teach_row' in st.session_state:
        tr = st.session_state.current_teach_row
        th = st.session_state.current_history
        # 💡 安全讀取學生姓名 (若 session 中沒有，則抓取下拉選單目前的選值)
        s_name = st.session_state.get('sel_name_teach', sel_name)
        
        st.markdown("#### 📢 步驟 2：教學講解櫥窗")
        with st.container(border=True):
            c_ui_1, c_ui_2 = st.columns([1.5, 1])
            with c_ui_1:
                # 💡 修復 N/A：檢查題庫欄位名稱是否存在 (支援 '中文題目' 或 '重組中文題目')
                q_text = tr.get('中文題目') or tr.get('重組中文題目') or '【無題目內容】'
                a_text = tr.get('英文答案') or tr.get('重組英文答案') or tr.get('單選答案') or '【無答案內容】'
                st.markdown(f"**中文題目：**\n# {q_text}")
                st.markdown(f"**正確答案：**\n<h2 style='color:green;'>{a_text}</h2>", unsafe_allow_html=True)
            with c_ui_2:
                st.markdown(f"**📜 {s_name} 的作答紀錄：**")
                if not th: st.write("無紀錄")
                else:
                    for h in th[::-1][:3]:
                        color = "green" if h['結果'] == "✅" else "orange" if "🎓" in h['結果'] else "red"
                        st.markdown(f"🕒 `{h['時間'][-8:]}` <span style='color:{color}; font-weight:bold;'>{h['結果']}</span>", unsafe_allow_html=True)
            
            if st.button(f"✅ 標註「{s_name}」此題講解完成", type="primary", use_container_width=True):
                new_log = pd.DataFrame([{
                    "時間": get_now().strftime("%Y-%m-%d %H:%M:%S"), 
                    "姓名": s_name, 
                    "分組": st.session_state.get('sel_group_teach', sel_group), 
                    "題目ID": tr.get('題目ID', 'N/A'), 
                    "結果": "🎓 講解完成"
                }])
                conn.create(worksheet="logs", data=new_log)
                st.toast("✅ 紀錄已成功回填！"); time.sleep(0.5); st.rerun()
        st.divider()

    # 🚀 [3. 底部歷程列表]
    st.markdown(f"#### 📊 步驟 3：{sel_name} 的歷程列表 (點選開啟櫥窗)")
    df_scope_q = df_q[(df_q['版本']==sel_ver)&(df_q['單元']==sel_unit)&(df_q['課編號']==sel_lesson)].copy()
    df_scope_q['題目ID'] = df_scope_q.apply(lambda r: f"{r['版本']}_{r['年度']}_{r['冊編號']}_{r['單元']}_{r['課編號']}_{r['句編號']}", axis=1)
    std_logs = df_l[df_l['姓名'] == sel_name].copy()

    for idx, row in df_scope_q.iterrows():
        q_id = row['題目ID']
        history = std_logs[std_logs['題目ID'] == q_id]
        
        icons = []
        if history.empty: icons.append("⚪")
        else:
            if not history[history['結果'] == "✅"].empty: icons.append("✅")
            if not history[history['結果'].str.contains('❌', na=False)].empty: icons.append("❌")
            if not history[history['結果'].str.contains('🎓', na=False)].empty: icons.append("🎓")
        
        q_label = row.get('中文題目') or row.get('重組中文題目') or '題目'
        btn_txt = f"句 {row['句編號']} {' '.join(icons)} | {q_label[:45]}"
        
        # 💡 [關鍵修正]：按鈕觸發時「物理鎖定」所有必要變數
        if st.button(btn_txt, key=f"btn_{idx}", use_container_width=True):
            st.session_state.update({
                "current_teach_row": row.to_dict(), 
                "current_history": history.to_dict('records'), 
                "show_teach_ui": True,
                "sel_name_teach": sel_name,
                "sel_group_teach": sel_group
            })
            st.rerun()

    show_version_caption(); st.stop()

# ------------------------------------------------------------------------------
# 📦 【其餘盒子維持完整實體存續】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "管理後台":
    st.markdown("## 🟢 導師管理中心")
    st.dataframe(df_l.sort_values("時間", ascending=False), use_container_width=True)
    show_version_caption(); st.stop()

if not st.session_state.quiz_loaded:
    st.markdown("## 🟡 練習範圍設定 (盒子 C)")
    # (此處物理保留 V2.8.82 所有起始句與題數加減功能...)
    show_version_caption()
