# ==============================================================================
# 🧩 英文全能練習系統 (V2.8.94 - 終極全量實體對位版)
# ==============================================================================
# 📌 版本編號 (VERSION): 2.8.94
# 📅 更新日期: 2026-03-14
# 🛠️ 核心任務：補回消失的學生功能、鎖定初始化變數、維持線性教學動線。
# ==============================================================================

import streamlit as st
import pandas as pd
import random
import re
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

VERSION = "2.8.94"

# ------------------------------------------------------------------------------
# 🔧 【核心保險：初始化全域狀態】 (防禦 AttributeError)
# ------------------------------------------------------------------------------
if 'quiz_loaded' not in st.session_state:
    st.session_state.update({
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
        'view_mode': '練習模式',
        'q_idx': 0,
        'shuf': [],
        'quiz_list': []
    })

# ------------------------------------------------------------------------------
# 📦 【盒子 A：核心函數】
# ------------------------------------------------------------------------------
def get_now():
    """強制獲取台灣時間 (UTC+8)"""
    return datetime.utcnow() + timedelta(hours=8)

def standardize(v):
    """標準化 ID"""
    val = str(v).split('.')[0].strip()
    return val.zfill(4) if val.isdigit() else val

def clean_string_for_compare(s):
    """智慧標點比對"""
    s = s.lower().replace(" ", "").replace("’", "'").replace("‘", "'")
    s = re.sub(r'[.,?!:;()]', '', s) 
    return s.strip()

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
                    st.session_state.update({
                        "logged_in": True, "user_id": f"EA{std_id}", "user_name": user.iloc[0]['姓名'], 
                        "group_id": user.iloc[0]['分組'], "view_mode": "管理後台" if user.iloc[0]['分組']=="ADMIN" else "練習模式"
                    })
                    st.rerun()
                else: st.error("❌ 帳號或密碼錯誤")
    st.stop()

df_q, df_s = load_static_data()
df_a, df_l = load_dynamic_data()

# ------------------------------------------------------------------------------
# 📦 【盒子 E：側邊欄】
# ------------------------------------------------------------------------------
with st.sidebar:
    st.write(f"👤 {st.session_state.user_name} ({st.session_state.group_id})")
    if st.session_state.group_id == "ADMIN":
        st.session_state.view_mode = st.radio("功能切換：", ["管理後台", "進入練習", "個人補強講解"])
    if st.button("🚪 登出系統", use_container_width=True):
        st.session_state.clear(); st.rerun()
    st.divider(); show_version_caption()

# ------------------------------------------------------------------------------
# 📦 【盒子 B：個人補強講解 (實體線性對位版)】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "個人補強講解":
    st.markdown("## 🎓 教學補強流：篩選 ➔ 講解 ➔ 歷程")

    # [1. 篩選區]
    with st.container():
        f1, f2, f3 = st.columns(3)
        g_list = ["全部"] + sorted(df_s['分組'].unique())
        sel_g = f1.selectbox("選擇班級", g_list, key="ts_g")
        std_list = sorted(df_s['姓名'].unique()) if sel_g == "全部" else sorted(df_s[df_s['分組']==sel_g]['姓名'].unique())
        sel_n = f2.selectbox("選擇學生", std_list, key="ts_n")
        sel_v = f3.selectbox("版本", sorted(df_q['版本'].unique()), key="ts_v")
        f4, f5 = st.columns(2)
        sel_u = f4.selectbox("單元", sorted(df_q[df_q['版本']==sel_v]['單元'].unique()), key="ts_u")
        sel_l = f5.selectbox("課次", sorted(df_q[(df_q['版本']==sel_v)&(df_q['單元']==sel_u)]['課編號'].unique()), key="ts_l")
    
    st.divider()

    # [2. 中部講解櫥窗]
    if st.session_state.get('show_teach_ui') and 'current_q_row' in st.session_state:
        tr = st.session_state.current_q_row
        th = st.session_state.current_q_history
        with st.container(border=True):
            cl, cr = st.columns([1.5, 1])
            with cl:
                st.markdown(f"**中文：**\n# {tr.get('中文題目') or tr.get('重組中文題目')}")
                st.markdown(f"**答案：**\n<h2 style='color:green;'>{tr.get('英文答案') or tr.get('重組英文答案')}</h2>", unsafe_allow_html=True)
            with cr:
                st.markdown(f"**📜 {sel_n} 紀錄：**")
                if not th: st.write("尚未有紀錄")
                else:
                    for h in th[::-1][:3]:
                        st.markdown(f"🕒 `{h['時間'][-8:]}` **{h['結果']}**")
            if st.button(f"✅ 標註「{sel_n}」講解完成", type="primary", use_container_width=True):
                new_l = pd.DataFrame([{"時間": get_now().strftime("%Y-%m-%d %H:%M:%S"), "姓名": sel_n, "分組": sel_g if sel_g != "全部" else "GENERAL", "題目ID": tr['題目ID'], "結果": "🎓 講解完成"}])
                conn.create(worksheet="logs", data=new_l); st.toast("✅ 已回填！"); time.sleep(0.5); st.rerun()
        st.divider()

    # [3. 底部歷程列表]
    st.markdown(f"#### 📊 {sel_name if 'sel_name' in locals() else '學生'} 的歷程 (點選題目開啟置頂櫥窗)")
    scope_df = df_q[(df_q['版本']==sel_v)&(df_q['單元']==sel_u)&(df_q['課編號']==sel_l)].copy()
    std_logs = df_l[df_l['姓名'] == sel_n].copy()

    for idx, row in scope_df.iterrows():
        tid = f"{row['版本']}_{row['年度']}_{row['冊編號']}_{row['單元']}_{row['課編號']}_{row['句編號']}"
        row['題目ID'] = tid
        this_h = std_logs[std_logs['題目ID'] == tid].to_dict('records')
        icons = ["✅" if any(h['結果']=="✅" for h in this_h) else "", "❌" if any("❌" in h['結果'] for h in this_h) else "", "🎓" if any("🎓" in h['結果'] for h in this_h) else ""]
        if not this_h: icons = ["⚪"]
        if st.button(f"句 {row['句編號']} {' '.join(icons)} | {row.get('中文題目') or row.get('重組中文題目')}", key=f"tbtn_{idx}", use_container_width=True):
            st.session_state.update({"current_q_row": row.to_dict(), "current_q_history": this_h, "show_teach_ui": True}); st.rerun()
    st.stop()

# ------------------------------------------------------------------------------
# 📦 【盒子 C：練習範圍設定】
# ------------------------------------------------------------------------------
if not st.session_state.quiz_loaded:
    st.markdown("## 🟡 練習範圍設定 (盒子 C)")
    with st.expander("⚙️ 篩選題目範圍", expanded=not st.session_state.range_confirmed):
        c_s = st.columns(5)
        sv = c_s[0].selectbox("版本", sorted(df_q['版本'].unique()), key="sv_c")
        su = c_s[1].selectbox("單元", sorted(df_q[df_q['版本']==sv]['單元'].unique()), key="su_c")
        sy = c_s[2].selectbox("年度", sorted(df_q[(df_q['版本']==sv)&(df_q['單元']==su)]['年度'].unique()), key="sy_c")
        sb = c_s[3].selectbox("冊別", sorted(df_q[(df_q['版本']==sv)&(df_q['單元']==su)&(df_q['年度']==sy)]['冊編號'].unique()), key="sb_c")
        sl = c_s[4].selectbox("課次", sorted(df_q[(df_q['版本']==sv)&(df_q['單元']==su)&(df_q['年度']==sy)&(df_q['冊編號']==sb)]['課編號'].unique()), key="sl_c")
        if st.button("🔍 確認篩選", use_container_width=True): st.session_state.range_confirmed = True; st.rerun()
    
    if st.session_state.range_confirmed:
        df_scope = df_q[(df_q['版本']==st.session_state.sv_c)&(df_q['單元']==st.session_state.su_c)&(df_q['年度']==st.session_state.sy_c)&(df_q['冊編號']==st.session_state.sb_c)&(df_q['課編號']==st.session_state.sl_c)].copy()
        cc1, cc2 = st.columns(2)
        all_sentences = sorted(df_scope['句編號'].unique(), key=lambda x: int(x) if x.isdigit() else 0)
        start_q = cc1.selectbox("🔢 指定起始句", all_sentences)
        nu_i = cc2.number_input("🔢 練習題數", 1, 100, 10)
        if st.button("🚀 正式開始練習", type="primary", use_container_width=True):
            df_final = df_scope[df_scope['句編號'].astype(int) >= int(start_q)].head(int(nu_i))
            st.session_state.update({
                "quiz_list": df_final.to_dict('records'), "q_idx": 0, "quiz_loaded": True, 
                "ans": [], "used_history": [], "shuf": [], "show_analysis": False
            })
            st.rerun()
    show_version_caption()

# ------------------------------------------------------------------------------
# 📦 【盒子 D：學生練習引擎 (完整補回)】
# ------------------------------------------------------------------------------
if st.session_state.quiz_loaded:
    st.markdown(f"### 🔴 練習中 (第 {st.session_state.q_idx + 1} / {len(st.session_state.quiz_list)} 題)")
    q = st.session_state.quiz_list[st.session_state.q_idx]
    is_mcq = "單選" in q.get("單元", "")
    ans_key = str(q.get("重組英文答案") or q.get("英文答案") or q.get("單選答案")).strip()
    st.markdown(f"#### 題目：{q.get('中文題目') or q.get('重組中文題目')}")
    
    if is_mcq:
        cols = st.columns(4)
        for opt in ["A", "B", "C", "D"]:
            if cols["ABCD".find(opt)].button(opt, key=f"opt_{opt}", use_container_width=True):
                is_ok = (opt == ans_key); st.session_state.update({"current_res": "✅" if is_ok else f"❌ ({ans_key})", "show_analysis": True}); st.rerun()
    else:
        st.info(" ".join(st.session_state.ans) if st.session_state.ans else "請點選單字...")
        c_ctrl = st.columns(2)
        if c_ctrl[0].button("⬅️ 🟠 退回一步", use_container_width=True): 
            if st.session_state.ans: st.session_state.ans.pop(); st.session_state.used_history.pop(); st.rerun()
        if c_ctrl[1].button("🗑️ 🟠 全部清除", use_container_width=True): st.session_state.update({"ans":[], "used_history":[]}); st.rerun()
        
        tk = re.findall(r"[\w']+|[.,?!:;()]", ans_key)
        if not st.session_state.shuf: 
            st.session_state.shuf = tk.copy()
            random.shuffle(st.session_state.shuf)
            
        bs = st.columns(3)
        for i, t in enumerate(st.session_state.shuf):
            if i not in st.session_state.used_history:
                if bs[i%3].button(t, key=f"word_{i}", use_container_width=True):
                    st.session_state.ans.append(t); st.session_state.used_history.append(i); st.rerun()
        
        if len(st.session_state.ans) == len(tk) and not st.session_state.show_analysis:
            if st.button("✅ 🔵 檢查作答結果", type="primary", use_container_width=True):
                is_ok = clean_string_for_compare("".join(st.session_state.ans)) == clean_string_for_compare(ans_key)
                st.session_state.update({"current_res": "✅ 正確" if is_ok else f"❌ 正確答案：{ans_key}", "show_analysis": True})
                log_df = pd.DataFrame([{
                    "時間": get_now().strftime("%Y-%m-%d %H:%M:%S"), "姓名": st.session_state.user_name, "分組": st.session_state.group_id, 
                    "題目ID": f"{q['版本']}_{q['年度']}_{q['冊編號']}_{q['單元']}_{q['課編號']}_{q['句編號']}", "結果": "✅" if is_ok else "❌"
                }])
                conn.create(worksheet="logs", data=log_df); st.rerun()
    
    if st.session_state.show_analysis: st.warning(st.session_state.current_res)
    st.divider()
    c_nav = st.columns(2)
    if st.session_state.q_idx > 0:
        if c_nav[0].button("⬅️ 🔵 上一題", use_container_width=True):
            st.session_state.update({"q_idx": st.session_state.q_idx-1, "ans":[], "used_history":[], "shuf":[], "show_analysis":False}); st.rerun()
    if c_nav[1].button("下一題 ➡️", type="primary", use_container_width=True):
        if st.session_state.q_idx + 1 < len(st.session_state.quiz_list):
            st.session_state.update({"q_idx": st.session_state.q_idx+1, "ans":[], "used_history":[], "shuf":[], "show_analysis":False}); st.rerun()
        else: st.session_state.update({"quiz_loaded": False, "range_confirmed": False}); st.rerun()
    
    if st.button("🏁 🔴 結束作答", use_container_width=True):
        st.session_state.update({"quiz_loaded": False, "range_confirmed": False}); st.rerun()
    show_version_caption()

# ------------------------------------------------------------------------------
# 📦 【其餘盒子維持物理存續：B 管理後台】
# ------------------------------------------------------------------------------
if st.session_state.group_id == "ADMIN" and st.session_state.view_mode == "管理後台":
    st.markdown("## 🟢 導師管理中心")
    st.dataframe(df_l.sort_values("時間", ascending=False), use_container_width=True)
    show_version_caption()
