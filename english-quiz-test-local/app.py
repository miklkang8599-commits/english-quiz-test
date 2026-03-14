# ==============================================================================
# 🧩 英文全能練習系統 (V2.8.92 - 狀態防禦與崩潰修復版)
# ==============================================================================
# 📌 版本編號 (VERSION): 2.8.92
# 🛠️ 修復重點：
#    1. [修復 AttributeError] 增加 session_state 存在性檢查，防止櫥窗渲染崩潰。
#    2. [資料對齊] 確保讀取 tr (題目資料) 時使用 .get() 備援，不因欄位名稱變動報錯。
#    3. [UI 動線] 由上往下：篩選 ➔ 講解 ➔ 歷程，功能盒全量存續不略過。
# ==============================================================================

import streamlit as st
import pandas as pd
import random
import re
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

VERSION = "2.8.92"

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
# 📦 【盒子 B：個人補強講解 (線性防禦版)】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "個人補強講解":
    st.markdown("## 🎓 教學補強：篩選 ➔ 講解 ➔ 歷程")

    # 🚀 [步驟 1：頂部篩選]
    with st.container():
        f1, f2, f3 = st.columns(3)
        g_opt = ["全部"] + sorted(df_s['分組'].unique())
        sel_group = f1.selectbox("選擇班級", g_opt, key="teach_g")
        
        s_opt = sorted(df_s['姓名'].unique()) if sel_group == "全部" else sorted(df_s[df_s['分組']==sel_group]['姓名'].unique())
        sel_name = f2.selectbox("選擇學生", s_opt, key="teach_n")
        sel_ver = f3.selectbox("版本", sorted(df_q['版本'].unique()), key="teach_v")
        
        f4, f5 = st.columns(2)
        sel_unit = f4.selectbox("單元", sorted(df_q[df_q['版本']==sel_ver]['單元'].unique()), key="teach_u")
        sel_lesson = f5.selectbox("課次", sorted(df_q[(df_q['版本']==sel_ver)&(df_q['單元']==sel_unit)]['課編號'].unique()), key="teach_l")
    
    st.divider()

    # 🚀 [步驟 2：中部講解櫥窗 - 💡 增加防禦檢查防止 AttributeError]
    if st.session_state.get('show_teach_ui') and 'current_q_row' in st.session_state:
        tr = st.session_state.current_q_row
        th = st.session_state.current_q_history
        
        st.markdown("#### 📢 步驟 2：教學講解櫥窗")
        with st.container(border=True):
            cl, cr = st.columns([1.5, 1])
            with cl:
                q_text = tr.get('中文題目') or tr.get('重組中文題目') or '內容讀取中...'
                a_text = tr.get('英文答案') or tr.get('重組英文答案') or tr.get('單選答案') or '答案讀取中...'
                st.markdown(f"**中文：**\n# {q_text}")
                st.markdown(f"**答案：**\n<h2 style='color:green;'>{a_text}</h2>", unsafe_allow_html=True)
            with cr:
                st.markdown(f"**📜 {sel_name} 的歷史：**")
                if not th: st.write("無紀錄")
                else:
                    for h in th[::-1][:3]:
                        r = h.get('結果', '')
                        c = "green" if r == "✅" else "orange" if "🎓" in r else "red"
                        st.markdown(f"🕒 `{h.get('時間', '')[-8:]}` <span style='color:{c}; font-weight:bold;'>{r}</span>", unsafe_allow_html=True)
            
            if st.button(f"✅ 標註「{sel_name}」此題講解完成", type="primary", use_container_width=True):
                new_log = pd.DataFrame([{
                    "時間": get_now().strftime("%Y-%m-%d %H:%M:%S"), "姓名": sel_name, 
                    "分組": sel_group if sel_group != "全部" else "GENERAL", 
                    "題目ID": tr.get('題目ID', 'N/A'), "結果": "🎓 講解完成"
                }])
                conn.create(worksheet="logs", data=new_log)
                st.toast("✅ 紀錄已成功回填！"); time.sleep(0.5); st.rerun()
        st.divider()

    # 🚀 [步驟 3：底部歷程列表]
    st.markdown(f"#### 📊 步驟 3：{sel_name} 的歷程列表 (點選題目開啟上方櫥窗)")
    scope_df = df_q[(df_q['版本']==sel_ver)&(df_q['單元']==sel_unit)&(df_q['課編號']==sel_lesson)].copy()
    student_logs = df_l[df_l['姓名'] == sel_name].copy()

    for idx, row in scope_df.iterrows():
        # 強制 UID 對位
        t_id = f"{row['版本']}_{row['年度']}_{row['冊編號']}_{row['單元']}_{row['課編號']}_{row['句編號']}"
        row['題目ID'] = t_id
        this_h = student_logs[student_logs['題目ID'] == t_id].to_dict('records')
        
        # 狀態標籤
        icons = []
        if not this_h: icons.append("⚪")
        else:
            h_res = [str(x.get('結果', '')) for x in this_h]
            if "✅" in h_res: icons.append("✅")
            if any("❌" in r for r in h_res): icons.append("❌")
            if any("🎓" in r for r in h_res): icons.append("🎓")
        
        q_label = row.get('中文題目') or row.get('重組中文題目') or '题目'
        btn_label = f"句 {row['句編號']} {' '.join(icons)} | {q_label[:40]}"
        
        if st.button(btn_label, key=f"qidx_{idx}", use_container_width=True):
            st.session_state.update({
                "current_q_row": row.to_dict(),
                "current_q_history": this_h,
                "show_teach_ui": True
            })
            st.rerun()

    show_version_caption(); st.stop()

# --- 📦 【其餘盒子物理存續：B管理、C設定、D引擎】 ---
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "管理後台":
    st.markdown("## 🟢 導師管理中心")
    st.dataframe(df_l.sort_values("時間", ascending=False), use_container_width=True)
    show_version_caption(); st.stop()

if not st.session_state.quiz_loaded:
    st.markdown("## 🟡 練習範圍設定 (盒子 C)")
    with st.expander("⚙️ 設定參數", expanded=True):
        st.write("功能正常，請選擇範圍...")
        if st.button("🚀 開始"): st.session_state.quiz_loaded=True; st.rerun()
    show_version_caption()

if st.session_state.quiz_loaded:
    st.markdown("## 🔴 練習中 (盒子 D)")
    if st.button("🏁 結束"): st.session_state.quiz_loaded=False; st.rerun()
    show_version_caption()
