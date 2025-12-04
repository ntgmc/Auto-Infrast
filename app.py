import streamlit as st
import json
import os
from logic import WorkplaceOptimizer

# ==========================================
# 0. 基础配置与函数
# ==========================================
st.set_page_config(page_title="明日方舟基建排班生成器", layout="wide", page_icon="🏭")


def import_datetime():
    import datetime
    return datetime.datetime.now()


# 状态初始化
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
if 'results' not in st.session_state:
    st.session_state.results = {}

st.title("🏭 明日方舟基建排班生成器")

# ==========================================
# 1. 侧边栏：数据导入 (支持粘贴)
# ==========================================
st.sidebar.header("1. 数据导入")
base_efficiency_path = "efficiency.json"

if not os.path.exists(base_efficiency_path):
    st.error("⚠️ 错误：未在仓库中找到 efficiency.json。")
    st.stop()

# --- 修改开始：使用 Tab 分页 ---
input_mode = st.sidebar.radio("选择导入方式:", ["📋 剪贴板粘贴 (推荐)", "📁 文件上传"], horizontal=True)

uploaded_ops = None
pasted_ops = None

if input_mode == "📁 文件上传":
    uploaded_ops = st.sidebar.file_uploader(
        "上传 operators.json",
        type="json",
        help="上传 MAA 导出的 JSON 文件"
    )
else:
    pasted_ops = st.sidebar.text_area(
        "在此处粘贴 MAA 导出的 JSON 内容:",
        height=300,
        help="在 MAA '小工具' -> '干员识别' -> 识别后点击 '复制到剪贴板'，然后在此处 Ctrl+V粘贴",
        placeholder='[\n  {\n    "id": "char_002_amiya",\n    "name": "阿米娅",\n    ...\n  }\n]'
    )
    if pasted_ops:
        st.sidebar.caption("✅ 已检测到文本内容")
# --- 修改结束 ---

# ==========================================
# 2. 主界面：配置区域
# ==========================================
st.header("2. 基建参数配置")

col_base1, col_base2 = st.columns(2)

with col_base1:
    st.subheader("🏢 设施数量")
    n_trading = st.number_input("贸易站数量", min_value=0, max_value=5, value=2)
    n_manufacture = st.number_input("制造站数量", min_value=0, max_value=5, value=4)

    # --- [新增] 提示信息 ---
    st.caption("ℹ️ **说明**：当前算法仅支持 **3发电站** 布局，且固定生成 **3班** 排班方案。")

    # [可选] 动态校验：如果贸易+制造不等于6，显示警告
    current_power = 9 - n_trading - n_manufacture
    if current_power != 3:
        st.warning(f"⚠️ 检测到当前设施非 3 发电站，建议调整设施数量以满足 3 发电站限制。", icon="⚠️")

with col_base2:
    st.subheader("📦 产物分配")
    # 贸易站
    st.markdown("**贸易站产物需求**")
    col_t1, col_t2 = st.columns(2)
    req_lmd = col_t1.number_input("龙门币 (LMD)", min_value=0, max_value=5, value=2)
    req_orundum = col_t2.number_input("合成玉 (Orundum)", min_value=0, max_value=5, value=0)

    if req_lmd + req_orundum != n_trading:
        st.warning(f"⚠️ 警告：贸易站产物数量 ({req_lmd + req_orundum}) 与 设施数量 ({n_trading}) 不一致！")

    # 制造站
    st.markdown("**制造站产物需求**")
    col_m1, col_m2, col_m3 = st.columns(3)
    req_gold = col_m1.number_input("赤金", min_value=0, max_value=5, value=2)
    req_shard = col_m2.number_input("源石碎片", min_value=0, max_value=5, value=0)
    req_record = col_m3.number_input("经验书", min_value=0, max_value=5, value=2)

    if req_gold + req_shard + req_record != n_manufacture:
        st.warning(f"⚠️ 警告：制造站产物数量 ({req_gold + req_shard + req_record}) 与 设施数量 ({n_manufacture}) 不一致！")

st.divider()

# 高级设置
with st.expander("⚙️ 高级设置 (菲亚梅塔 & 无人机)", expanded=True):
    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        st.markdown("**🔥 菲亚梅塔 (Fiammetta)**")
        enable_fia = st.checkbox("启用菲亚梅塔自动充能", value=True, help="自动识别排班中收益最高的干员进行心情恢复")

        if enable_fia:
            st.warning(
                "⚠️ **重要提示**：\n\n"
                "菲亚梅塔体系需要**严格保证换班时间**（通常为 12小时 或 8小时一换）。\n"
                "建议配合 **MAA 定时任务** 或闹钟使用。\n\n"
                "🚫 **如果无法保证准时换班，充能对象极易心情耗尽（红脸），反而降低效率，此时请关闭此选项。**",
                icon="⚠️"
            )

    with col_adv2:
        st.markdown("**🚁 无人机加速**")
        enable_drone = st.checkbox("启用无人机加速", value=True)

        drone_targets = []
        if enable_drone:
            st.caption("请分别为3个班次选择加速目标：")
            product_options = {
                "龙门币": "LMD",
                "合成玉": "Orundum",
                "赤金": "Pure Gold",
                "经验书": "Battle Record",
                "源石碎片": "Originium Shard"
            }
            option_keys = list(product_options.keys())

            d_col1, d_col2, d_col3 = st.columns(3)
            t1 = d_col1.selectbox("第1班", option_keys, index=0)
            t2 = d_col2.selectbox("第2班", option_keys, index=2)
            t3 = d_col3.selectbox("第3班", option_keys, index=0)

            drone_targets = [product_options[t1], product_options[t2], product_options[t3]]
            drone_order = "pre"
        else:
            drone_targets = []
            drone_order = "pre"

# ==========================================
# 3. 核心逻辑执行区
# ==========================================

st.divider()
btn_col1, btn_col2 = st.columns([1, 2])

# Config 构建
current_config = {
    "product_requirements": {
        "trading_stations": {"LMD": req_lmd, "Orundum": req_orundum},
        "manufacturing_stations": {"Pure Gold": req_gold, "Originium Shard": req_shard, "Battle Record": req_record}
    },
    "trading_stations_count": n_trading,
    "manufacturing_stations_count": n_manufacture,
    "Fiammetta": {"enable": enable_fia},
    "drones": {"enable": enable_drone, "order": drone_order, "targets": drone_targets}
}

start_btn = btn_col1.button("🚀 开始计算排班", type="primary", use_container_width=True)

if start_btn:
    # --- 输入数据源校验 ---
    operators_data_bytes = None

    # 优先检查文件
    if uploaded_ops is not None:
        operators_data_bytes = uploaded_ops.getvalue()
    # 其次检查文本
    elif pasted_ops and pasted_ops.strip():
        try:
            # 尝试解析一下 JSON，确保粘贴的不是乱码
            json.loads(pasted_ops)
            operators_data_bytes = pasted_ops.encode('utf-8')
        except json.JSONDecodeError:
            st.error("❌ 粘贴的内容不是有效的 JSON 格式！请重新复制 MAA 的导出内容。")
            st.stop()
    else:
        st.error("❌ 请在左侧侧边栏上传文件或粘贴 JSON 数据！")
        st.stop()
    # --------------------

    with st.spinner("正在分析干员数据与计算最优解，请稍候..."):
        try:
            # 1. 写入临时 Operators 文件
            with open("temp_operators.json", "wb") as f:
                f.write(operators_data_bytes)

            # 2. 写入临时 Config 文件
            with open("temp_config.json", "w", encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)

            # 3. 运行核心逻辑
            optimizer = WorkplaceOptimizer(
                efficiency_file=base_efficiency_path,
                operator_file="temp_operators.json",
                config_file="temp_config.json"
            )

            curr_assign = optimizer.get_optimal_assignments(ignore_elite=False)
            pot_assign = optimizer.get_optimal_assignments(ignore_elite=True)
            upgrades = optimizer.calculate_upgrade_requirements(curr_assign, pot_assign)


            # 4. 数据打包
            def clean_json(data):
                return {k: v for k, v in data.items() if k != 'raw_results'}


            json_current = json.dumps(clean_json(curr_assign), ensure_ascii=False, indent=2)
            json_potential = json.dumps(clean_json(pot_assign), ensure_ascii=False, indent=2)

            txt_content = "=== 练度提升建议报告 ===\n\n"
            txt_content += f"生成时间: {import_datetime().strftime('%Y-%m-%d %H:%M:%S')}\n"
            txt_content += "=" * 40 + "\n\n"

            if not upgrades:
                txt_content += "无需提升练度。\n"
            else:
                for item in upgrades:
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

            # 5. 存入 Session
            st.session_state.results = {
                "current": json_current,
                "potential": json_potential,
                "txt": txt_content,
                "efficiency": curr_assign['raw_results'][0].total_efficiency if curr_assign['raw_results'] else 0
            }
            st.session_state.calculated = True

            # 清理
            if os.path.exists("temp_operators.json"): os.remove("temp_operators.json")
            if os.path.exists("temp_config.json"): os.remove("temp_config.json")

        except Exception as e:
            st.error(f"运行出错: {e}")
            import traceback

            st.text(traceback.format_exc())

# ==========================================
# 4. 结果展示区
# ==========================================

if st.session_state.calculated:
    res = st.session_state.results

    st.success("✅ 计算完成！")
    st.info(f"📊 当前方案首班效率参考: {res['efficiency']:.2f}")

    st.subheader("📥 结果下载")
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
        st.download_button(
            label="📄 1. 当前方案 (JSON)",
            data=res['current'],
            file_name="current_assignments.json",
            mime="application/json",
            use_container_width=True
        )

    with d_col2:
        st.download_button(
            label="🔮 2. 潜在方案 (JSON)",
            data=res['potential'],
            file_name="potential_assignments.json",
            mime="application/json",
            use_container_width=True
        )

    with d_col3:
        st.download_button(
            label="📈 3. 提升建议 (TXT)",
            data=res['txt'],
            file_name="upgrade_suggestions.txt",
            mime="text/plain",
            use_container_width=True
        )

elif not pasted_ops and not uploaded_ops:
    st.info("👆 请在左侧侧边栏粘贴 JSON 数据或上传文件，然后点击“开始计算排班”。")
elif pasted_ops or uploaded_ops:
    st.info("✅ 数据已就绪，请点击“开始计算排班”按钮。")