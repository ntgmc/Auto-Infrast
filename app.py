import streamlit as st
import json
import os
import shutil
from logic import WorkplaceOptimizer  # 从 logic.py 导入你的类

# 页面配置
st.set_page_config(page_title="明日方舟基建排班优化器", layout="wide")

st.title("🏭 明日方舟基建排班优化器")
st.markdown("""
上传您的 `operators.json` (干员数据) 和 `config.json` (配置)，系统将为您计算最优排班方案。
""")

# --- 侧边栏：文件上传 ---
st.sidebar.header("1. 上传文件")

# 这里假设 efficiency.json 已经包含在仓库中，作为基础数据
# 如果你想让用户自己上传 efficiency.json，也可以加一个 uploader
base_efficiency_path = "efficiency.json"
if not os.path.exists(base_efficiency_path):
    st.error("错误：仓库中缺少 efficiency.json 文件，无法运行。")
    st.stop()

uploaded_ops = st.sidebar.file_uploader("上传 operators.json", type="json")
uploaded_conf = st.sidebar.file_uploader("上传 config.json", type="json")

# --- 主逻辑 ---

if uploaded_ops and uploaded_conf:
    st.success("文件上传成功！点击下方按钮开始计算。")

    if st.button("🚀 开始计算排班", type="primary"):
        with st.spinner("正在分析干员数据与计算最优解，请稍候..."):
            try:
                # 1. 将上传的文件保存为临时文件，以便 WorkplaceOptimizer 读取
                # Streamlit 的上传文件是内存对象，我们需要写入磁盘
                with open("temp_operators.json", "wb") as f:
                    f.write(uploaded_ops.getbuffer())

                with open("temp_config.json", "wb") as f:
                    f.write(uploaded_conf.getbuffer())

                # 2. 初始化优化器
                # 注意：efficiency.json 使用仓库自带的
                optimizer = WorkplaceOptimizer(
                    efficiency_file=base_efficiency_path,
                    operator_file="temp_operators.json",
                    config_file="temp_config.json"
                )

                # 3. 执行核心逻辑 (直接调用你原本写好的方法)
                current_assignments = optimizer.get_optimal_assignments(ignore_elite=False)
                potential_assignments = optimizer.get_optimal_assignments(ignore_elite=True)
                upgrade_list = optimizer.calculate_upgrade_requirements(current_assignments, potential_assignments)


                # 4. 生成文件内容 (不直接存盘，而是转为 JSON 字符串供下载)
                def clean_for_json(data):
                    # 移除不可序列化的 raw_results
                    return {k: v for k, v in data.items() if k != 'raw_results'}


                json_current = json.dumps(clean_for_json(current_assignments), ensure_ascii=False, indent=2)
                json_potential = json.dumps(clean_for_json(potential_assignments), ensure_ascii=False, indent=2)

                # 生成 TXT 建议内容
                # 这里我们需要稍微魔改一下 save_suggestions_to_txt 或者直接重写一段生成文本的逻辑
                # 为了方便，我们直接手动生成字符串
                txt_content = "=== 练度提升建议报告 ===\n\n"
                if not upgrade_list:
                    txt_content += "无需提升练度。\n"
                else:
                    for item in upgrade_list:
                        gain_val = item['gain']
                        gain_str = f"{gain_val * 100:.1f}%" if gain_val < 0.9 else f"{gain_val:.1f}%"
                        if item.get('type') == 'bundle':
                            names = "+".join([op['name'] for op in item['ops']])
                            txt_content += f"[组合] {names} | 收益: {gain_str}\n"
                            for op in item['ops']:
                                txt_content += f"  - {op['name']}: 精{op['current']} -> 精{op['target']}\n"
                        else:
                            txt_content += f"[单人] {item['name']} | 收益: {gain_str}\n"
                            txt_content += f"  - 精{item['current']} -> 精{item['target']}\n"
                        txt_content += "-" * 30 + "\n"

                # 5. 显示结果概览
                st.subheader("📊 计算完成")
                st.info(f"当前方案效率: {current_assignments['raw_results'][0].total_efficiency:.2f} (仅示例第一班)")

                # 6. 提供下载按钮
                st.subheader("📥 下载结果")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.download_button(
                        label="下载当前方案 (JSON)",
                        data=json_current,
                        file_name="current_assignments.json",
                        mime="application/json"
                    )

                with col2:
                    st.download_button(
                        label="下载潜在方案 (JSON)",
                        data=json_potential,
                        file_name="potential_assignments.json",
                        mime="application/json"
                    )

                with col3:
                    st.download_button(
                        label="下载提升建议 (TXT)",
                        data=txt_content,
                        file_name="upgrade_suggestions.txt",
                        mime="text/plain"
                    )

                # 清理临时文件
                if os.path.exists("temp_operators.json"): os.remove("temp_operators.json")
                if os.path.exists("temp_config.json"): os.remove("temp_config.json")

            except Exception as e:
                st.error(f"运行出错: {e}")
                # 打印详细错误方便调试
                import traceback

                st.text(traceback.format_exc())

else:
    st.info("👈 请先在左侧侧边栏上传必要的数据文件。")