import streamlit as st
import pandas as pd
import random
import io

if 'initialized' not in st.session_state:
    df = pd.read_excel("3種回答_3.xlsx")

    # 隨機打亂
    problem_indices = list(range(len(df)))
    random.shuffle(problem_indices)

    st.session_state.df = df
    st.session_state.problem_indices = problem_indices
    st.session_state.current_pointer = 0
    st.session_state.results = []
    st.session_state.current_clicks = []  # 格式改為: [{"model": m, "text": t, "rank": r}]
    st.session_state.current_shuffled_ans = None
    st.session_state.next_rank_to_assign = 1  # 下一個要分配的名次（1, 2, 或 3）
    st.session_state.initialized = True

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
            st.success(
                f"第 {clicked_ans['rank']} 名 ➔ [{clicked_ans['model'] if False else '盲測文本'}] {clicked_ans['text'][:30]}...")

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
            # 使用橫向欄位，左邊放答案按鈕，右邊放並列按鈕
            c_btn, c_tie = st.columns([4, 1])

            with c_btn:
                # 正常點擊，分配下一個名次
                if st.button(f"選項 {idx + 1}：\n\n{choice['text']}", key=f"btn_{pointer}_{choice['model']}",
                             use_container_width=True):
                    current_rank = st.session_state.next_rank_to_assign
                    st.session_state.current_clicks.append({
                        "model": choice["model"],
                        "text": choice["text"],
                        "rank": current_rank
                    })
                    # 正常點擊後，下一個名次往下加 1
                    st.session_state.next_rank_to_assign += 1
                    st.rerun()

            with c_tie:
                # 只有當藥師已經點了至少一個答案時，才允許剩下的答案選擇「與前項並列」
                if num_clicks > 0:
                    if st.button("與前項並列", key=f"tie_{pointer}_{choice['model']}", use_container_width=True):
                        # 並列名次 = 上一次分出去的名次
                        last_assigned_rank = st.session_state.current_clicks[-1]["rank"]
                        st.session_state.current_clicks.append({
                            "model": choice["model"],
                            "text": choice["text"],
                            "rank": last_assigned_rank
                        })
                        # 因為是並列，所以下一個名次不需要加 1（例如：1、2、2，下一個就是 3）
                        # 但如果是 1、1，下一個名次要變成 2
                        unique_ranks = len(set(c['rank'] for c in st.session_state.current_clicks))
                        st.session_state.next_rank_to_assign = unique_ranks + 1
                        st.rerun()

    # 如果已經點滿 3 個答案，自動整理數據並儲存，然後跳題
    if len(st.session_state.current_clicks) == 3:
        clicks = st.session_state.current_clicks

        # 為了方便你後台統計，我們直接根據模型名稱找出各自獲得的名次
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

        # 重置狀態，進入下一題
        st.session_state.current_clicks = []
        st.session_state.current_shuffled_ans = None
        st.session_state.next_rank_to_assign = 1
        st.session_state.current_pointer += 1
        st.rerun()

else:
    # 藥師做完題目後看到的乾淨畫面
    st.success("所有測試已完成，辛苦藥師了！")

    # 檢查網址列參數，只有當網址最後帶有 ?admin=true 時才渲染後台下載按鈕
    if st.query_params.get("admin") == "true":
        st.markdown("---")
        st.markdown("### 管理員後台數據下載")

        result_df = pd.DataFrame(st.session_state.results)
        st.dataframe(result_df)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False, sheet_name='盲測結果')

        st.download_button(
            label="點我下載盲測結果 Excel 報表",
            data=buffer.getvalue(),
            file_name="盲測實驗結果.xlsx",
            mime="application/vnd.ms-excel"
        )
