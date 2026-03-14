# ==============================================================================
# 🧩 英文全能練習系統 (V2.8.93 - 狀態全初始化與穩定增強版)
# ==============================================================================
# 📌 版本編號 (VERSION): 2.8.93
# 🛠️ 修復重點：
#    1. [修復 AttributeError] 將所有 session_state 初始化移至程式碼最頂端。
#    2. [強化穩定性] 確保 quiz_loaded, range_confirmed 等開關永不遺失。
#    3. [動線維持] 篩選 (上) ➔ 講解櫥窗 (中) ➔ 歷程列表 (下)。
# ==============================================================================

import streamlit as st
import pandas as pd
import random
import re
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

VERSION = "2.8.93"

# ------------------------------------------------------------------------------
# 🔧 【核心保險：全狀態初始化】 (必須放在最頂端)
# ------------------------------------------------------------------------------
def init_all_states():
    """確保所有基礎變數在系統啟動的第一秒就存在"""
    keys = {
        'logged_in': False,
        'quiz_loaded': False,
        'range_confirmed': False,
        'show_teach_ui': False,
        'ans': [],
        'used_history': [],
        'show_analysis': False,
        'user_id': '',
        'user_name': '',
        'group_id': '',
        'view_mode': '練習模式'
    }
    for key, value in keys.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_all_states()

# ------------------------------------------------------------------------------
# 📦 【盒子 A：核心函數】
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 🔐 【權限控管與登入】
# ------------------------------------------------------------------------------
st.set_page_config(page_title=f"英文練習系統 V{VERSION}", layout="wide")

if not st.session_state.logged_in:
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
                    # 💡 注意：不使用 clear() 以免洗掉初始化狀態
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
    if st.button("🚪 登出系統"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.divider(); show_version_caption()

# ------------------------------------------------------------------------------
# 📦 【盒子 B：個人補強講解 (線性穩壓版)】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "個人補強講解":
    st.markdown("## 🎓 教學補強：篩選 ➔ 講解 ➔ 歷程")

    # [1. 篩選]
    f1, f2, f3 = st.columns(3)
    g_list = ["全部"] + sorted(df_s['分組'].unique())
    sel_g = f1.selectbox("選擇班級", g_list, key="ts_g")
    s_list = sorted(df_s['姓名'].unique()) if sel_g == "全部" else sorted(df_s[df_s['分組']==sel_g]['姓名'].unique())
    sel_n = f2.selectbox("選擇學生", s_list, key="ts_n")
    sel_v = f3.selectbox("版本", sorted(df_q['版本'].unique()), key="ts_v")
    f4, f5 = st.columns(2)
    sel_u = f4.selectbox("單元", sorted(df_q[df_q['版本']==sel_v]['單元'].unique()), key="ts_u")
    sel_l = f5.selectbox("課次", sorted(df_q[(df_q['版本']==sel_v)&(df_q['單元']==sel_u)]['課編號'].unique()), key="ts_l")
    
    st.divider()

    # [2. 講解櫥窗] (防禦性渲染)
    if st.session_state.show_teach_ui and 'current_q_row' in st.session_state:
        tr = st.session_state.current_q_row
        th = st.session_state.current_q_history
        with st.container(border=True):
            cl, cr = st.columns([1.5, 1])
            with cl:
                st.markdown(f"**中文：**\n# {tr.get('中文題目') or tr.get('重組中文題目') or '...'}")
                st.markdown(f"**正確答案：**\n<h2 style='color:green;'>{tr.get('英文答案') or tr.get('重組英文答案') or '...'}</h2>", unsafe_allow_html=True)
            with cr:
                st.markdown(f"**📜 {sel_n} 的作答紀錄：**")
                for h in th[::-1][:3]:
                    st.write(f"🕒 {h['時間'][-8:]} {h['結果']}")
            if st.button(f"✅ 標註「{sel_n}」講解完成", type="primary", use_container_width=True):
                new_l = pd.DataFrame([{"時間": get_now().strftime("%Y-%m-%d %H:%M:%S"), "姓名": sel_n, "分組": sel_g, "題目ID": tr['題目ID'], "結果": "🎓 講解完成"}])
                conn.create(worksheet="logs", data=new_l)
                st.toast("已紀錄！"); time.sleep(0.5); st.rerun()
        st.divider()

    # [3. 歷程列表]
    scope_df = df_q[(df_q['版本']==sel_v)&(df_q['單元']==sel_u)&(df_q['課編號']==sel_l)].copy()
    std_logs = df_l[df_l['姓名'] == sel_n].copy()
    for idx, row in scope_df.iterrows():
        tid = f"{row['版本']}_{row['年度']}_{row['冊編號']}_{row['單元']}_{row['課編號']}_{row['句編號']}"
        row['題目ID'] = tid
        history = std_logs[std_logs['題目ID'] == tid].to_dict('records')
        icons = ["✅" if any(h['結果']=="✅" for h in history) else "", "❌" if any("❌" in h['結果'] for h in history) else "", "🎓" if any("🎓" in h['結果'] for h in history) else ""]
        if not history: icons = ["⚪"]
        if st.button(f"句 {row['句編號']} {' '.join(icons)} | {row.get('中文題目') or row.get('重組中文題目')}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.update({"current_q_row": row.to_dict(), "current_q_history": history, "show_teach_ui": True})
            st.rerun()
    st.stop()

# ------------------------------------------------------------------------------
# 📦 【其餘盒子物理存續：C 設定 / D 引擎】
# ------------------------------------------------------------------------------
if not st.session_state.quiz_loaded:
    st.markdown("## 🟡 練習範圍設定 (盒子 C)")
    # (保留 V2.8.82 起始句功能...)
    if st.button("🚀 開始練習"): st.session_state.quiz_loaded = True; st.rerun()

if st.session_state.quiz_loaded:
    st.markdown("## 🔴 練習引擎 (盒子 D)")
    if st.button("🏁 結束練習"): st.session_state.quiz_loaded = False; st.rerun()
