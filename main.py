import streamlit as st
import pandas as pd
import random
import io
import requests
import base64
import datetime  # 引入時間模組，用來生成不重複的檔名

if 'initialized' not in st.session_state:
    df = pd.read_excel("3種回答_3.xlsx")

    # 隨機打亂
    problem_indices = list(range(len(df)))
    random.shuffle(problem_indices)

    st.session_state.df = df
    st.session_state.problem_indices = problem_indices
    st.session_state.current_pointer = 0
    st.session_state.results = []
    st.session_state.current_clicks = []  # 格式為: [{"model": m, "text": t, "rank": r}]
    st.session_state.current_shuffled_ans = None
    st.session_state.next_rank_to_assign = 1  # 下一個要分配的名次（1, 2, 或 3）
    st.session_state.initialized = True
    st.session_state.uploaded_to_github = False  # 防止重複觸發上傳


df = st.session_state.df
pointer = st.session_state.current_pointer
total_questions = len(st.session_state.problem_indices)

st.title("藥物教育問答")
st.write("請藥師閱讀問題與三個答案後，依序由好到差點選。若遇到答案相同或難分好壞，可使用「與前項並列」功能。")
st.markdown("---")

# 檢查是否所有題目都做完了
if pointer < total_questions:
    current_row_idx = st.session_state.problem_indices[pointer]
    row = df.iloc[current_row_idx]

    # 顯示進度與題目
    st.subheader(f"進度：{pointer + 1} / {total_questions}")
    st.info(f"問題：{row['問題']}")

    # 鎖定當前這一題的答案隨機順序
    if st.session_state.current_shuffled_ans is None:
        raw_choices = [
            {"model": "不抓", "text": row["不抓"]},
            {"model": "仿單", "text": row["仿單"]},
            {"model": "仿單+lexidrug", "text": row["仿單+lexidrug"]}
        ]
        random.shuffle(raw_choices)
        st.session_state.current_shuffled_ans = raw_choices

    choices = st.session_state.current_shuffled_ans

    # 顯示目前藥師已經排定的名次進度
    num_clicks = len(st.session_state.current_clicks)
    if num_clicks > 0:
        st.markdown("### 目前排定名次：")
        for clicked_ans in st.session_state.current_clicks:
            st.success(f"第 {clicked_ans['rank']} 名 ➔ [{clicked_ans['model'] if False else '盲測文本'}]")
            st.text(clicked_ans['text'])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("重填本題（順序點錯時點此）", key=f"reset_{pointer}"):
                st.session_state.current_clicks = []
                st.session_state.next_rank_to_assign = 1
                st.rerun()

        st.markdown("---")

    # 決定下一步的操作提示
    if num_clicks == 0:
        st.write("#### 請點選「第一名（最好）」的答案：")
    elif num_clicks == 1:
        st.write("#### 請選擇下一個答案的名次：")
    elif num_clicks == 2:
        st.write("#### 請選擇最後一個答案的名次：")

    # 渲染選項按鈕與並列按鈕
    for idx, choice in enumerate(choices):
        is_already_clicked = any(c['model'] == choice['model'] for c in st.session_state.current_clicks)

        if not is_already_clicked:
            c_btn, c_tie = st.columns([4, 1])

            with c_btn:
                button_text = f"選項 {idx + 1}：\n\n{choice['text']}"
                st.markdown("""
                    <style>
                    div.stButton > button p {
                        white-space: pre-line !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                if st.button(button_text, key=f"btn_{pointer}_{choice['model']}", use_container_width=True):
                    current_rank = st.session_state.next_rank_to_assign
                    st.session_state.current_clicks.append({
                        "model": choice["model"],
                        "text": choice["text"],
                        "rank": current_rank
                    })
                    st.session_state.next_rank_to_assign += 1
                    st.rerun()

            with c_tie:
                if num_clicks > 0:
                    st.write("") 
                    if st.button("與前項並列", key=f"tie_{pointer}_{choice['model']}", use_container_width=True):
                        last_assigned_rank = st.session_state.current_clicks[-1]["rank"]
                        st.session_state.current_clicks.append({
                            "model": choice["model"],
                            "text": choice["text"],
                            "rank": last_assigned_rank
                        })
                        unique_ranks = len(set(c['rank'] for c in st.session_state.current_clicks))
                        st.session_state.next_rank_to_assign = unique_ranks + 1
                        st.rerun()

    if len(st.session_state.current_clicks) == 3:
        clicks = st.session_state.current_clicks
        rank_dict = {c["model"]: c["rank"] for c in clicks}
        text_dict = {c["model"]: c["text"] for c in clicks}

        st.session_state.results.append({
            "問題ID(原始Row)": current_row_idx + 2,
            "問題內容": row["問題"],
            "不抓_名次": rank_dict["不抓"],
            "仿單_名次": rank_dict["仿單"],
            "仿單+lexidrug_名次": rank_dict["仿單+lexidrug"],
            "不抓_答案": text_dict["不抓"],
            "仿單_答案": text_dict["仿單"],
            "仿單+lexidrug_答案": text_dict["仿單+lexidrug"]
        })

        st.session_state.current_clicks = []
        st.session_state.current_shuffled_ans = None
        st.session_state.next_rank_to_assign = 1
        st.session_state.current_pointer += 1
        st.rerun()

else:
    st.success("所有測試已完成，辛苦藥師了！")
    
    if not st.session_state.uploaded_to_github:
        with st.spinner("系統正在安全儲存盲測數據，請稍候..."):
            try:
                result_df = pd.DataFrame(st.session_state.results)
                
                # 將 Excel 寫入記憶體 buffer
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    result_df.to_excel(writer, index=False, sheet_name='盲測結果')
                excel_data = buffer.getvalue()
                
                # ------ 💡 修改核心：生成唯一檔名與詳細的 Commit 訊息 ------
                # 獲取當前時間字串 (例如: 20260707_154530)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # 產生 4 位數隨機值防撞
                rand_id = random.randint(1000, 9999)
                
                # 新的檔名格式：盲測結果_時間_隨機數.xlsx
                FILE_PATH = f"盲測結果_{timestamp}_{rand_id}.xlsx" 
                
                REPO = "chiulimei/med-qa-blind-test"
                TOKEN = st.secrets["GITHUB_TOKEN"]
                
                url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
                headers = {
                    "Authorization": f"token {TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                # 因為每個檔名都是全新且唯一的，所以不再需要去 GET 檢查有沒有舊的 sha
                
                # 準備上傳的 Payload (Commit 訊息也加入時間與資料筆數，讓歷史紀錄一目了然)
                payload = {
                    "message": f"Auto-save {len(result_df)} blind test results at {timestamp}",
                    "content": base64.b64encode(excel_data).decode("utf-8"),
                    "branch": "main"
                }
                # ------------------------------------------------------------
                    
                # 發送 PUT 請求給 GitHub 自動創建新檔案
                put_res = requests.put(url, headers=headers, json=payload)
                
                if put_res.status_code in [200, 201]:
                    st.session_state.uploaded_to_github = True
                    st.toast("盲測數據已成功自動備份至 GitHub 儲存庫！", icon="💾")
                else:
                    st.error(f"自動儲存失敗，請聯繫工程師。錯誤代碼: {put_res.status_code}")
            except Exception as e:
                st.error(f"儲存過程中發生未預期錯誤: {e}")
