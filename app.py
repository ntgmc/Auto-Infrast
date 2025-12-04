import streamlit as st
import json
import os
from logic import WorkplaceOptimizer

# 设置页面配置
st.set_page_config(page_title="明日方舟基建排班优化器", layout="wide", page_icon="🏭")

# --- 状态初始化 ---
# 使用 session_state 来保存计算结果，防止点击下载按钮后结果消失
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
if 'results' not in st.session_state:
    st.session_state.results = {}

st.title("🏭 明日方舟基建排班优化器")

# ==========================================
# 1. 侧边栏：基础文件与干员数据
# ==========================================
st.sidebar.header("1. 数据导入")
base_efficiency_path = "efficiency.json"

# 检查环境
if not os.path.exists(base_efficiency_path):
    st.error("⚠️ 错误：未在仓库中找到 efficiency.json。")
    st.stop()

uploaded_ops = st.sidebar.file_uploader(
    "上传 operators.json (MAA导出)",
    type="json",
    help="请上传包含干员练度数据的 JSON 文件"
)

# ==========================================
# 2. 主界面：配置区域
# ==========================================
st.header("2. 基建参数配置")

col_base1, col_base2 = st.columns(2)

with col_base1:
    st.subheader("🏢 设施数量")
    n_trading = st.number_input("贸易站数量", min_value=0, max_value=5, value=2)
    n_manufacture = st.number_input("制造站数量", min_value=0, max_value=5, value=4)

with col_base2:
    st.subheader("📦 产物分配")
    # 贸易站产物
    st.markdown("**贸易站产物需求**")
    col_t1, col_t2 = st.columns(2)
    req_lmd = col_t1.number_input("龙门币 (LMD)", min_value=0, max_value=5, value=2)
    req_orundum = col_t2.number_input("合成玉 (Orundum)", min_value=0, max_value=5, value=0)

    # 校验贸易站数量
    if req_lmd + req_orundum != n_trading:
        st.warning(f"⚠️ 注意：贸易站产物总数 ({req_lmd + req_orundum}) 与 设施数量 ({n_trading}) 不一致！")

    # 制造站产物
    st.markdown("**制造站产物需求**")
    col_m1, col_m2, col_m3 = st.columns(3)
    req_gold = col_m1.number_input("赤金", min_value=0, max_value=5, value=2)
    req_shard = col_m2.number_input("源石碎片", min_value=0, max_value=5, value=0)
    req_record = col_m3.number_input("经验书", min_value=0, max_value=5, value=2)

    # 校验制造站数量
    if req_gold + req_shard + req_record != n_manufacture:
        st.warning(
            f"⚠️ 注意：制造站产物总数 ({req_gold + req_shard + req_record}) 与 设施数量 ({n_manufacture}) 不一致！")

st.divider()

# 高级设置 (折叠起来保持界面整洁)
with st.expander("⚙️ 高级设置 (菲亚梅塔 & 无人机)", expanded=True):
    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        st.markdown("**🔥 菲亚梅塔**")
        enable_fia = st.checkbox("启用菲亚梅塔自动充能", value=True)

    with col_adv2:
        st.markdown("**🚁 无人机加速**")
        enable_drone = st.checkbox("启用无人机加速", value=True)

        drone_targets = []
        if enable_drone:
            st.caption("请分别为3个班次选择加速目标：")
            # 所有的可选产物名称 (对应 logic.py 中的识别键)
            product_options = {
                "龙门币": "LMD",
                "合成玉": "Orundum",
                "赤金": "Pure Gold",
                "经验书": "Battle Record",
                "源石碎片": "Originium Shard"
            }
            # 为了方便用户，显示中文，传给后台英文
            option_keys = list(product_options.keys())

            d_col1, d_col2, d_col3 = st.columns(3)
            # 默认值设置：LMD, 赤金, LMD (对应索引 0, 2, 0)
            t1 = d_col1.selectbox("第1班 加速", option_keys, index=0)
            t2 = d_col2.selectbox("第2班 加速", option_keys, index=2)
            t3 = d_col3.selectbox("第3班 加速", option_keys, index=0)

            drone_targets = [product_options[t1], product_options[t2], product_options[t3]]
            drone_order = "pre"  # 默认 pre
        else:
            drone_targets = []
            drone_order = "pre"

# ==========================================
# 3. 核心逻辑执行区
# ==========================================

st.divider()
btn_col1, btn_col2 = st.columns([1, 2])

# 生成 Config 字典
current_config = {
    "product_requirements": {
        "trading_stations": {
            "LMD": req_lmd,
            "Orundum": req_orundum
        },
        "manufacturing_stations": {
            "Pure Gold": req_gold,
            "Originium Shard": req_shard,
            "Battle Record": req_record
        }
    },
    "trading_stations_count": n_trading,
    "manufacturing_stations_count": n_manufacture,
    "Fiammetta": {
        "enable": enable_fia
    },
    "drones": {
        "enable": enable_drone,
        "order": drone_order,
        "targets": drone_targets
    }
}

start_btn = btn_col1.button("🚀 开始计算排班", type="primary", use_container_width=True)

if start_btn:
    if not uploaded_ops:
        st.error("请先在左侧侧边栏上传 operators.json 文件！")
    else:
        with st.spinner("正在分析干员数据与计算最优解，请稍候..."):
            try:
                # 1. 保存临时干员文件
                with open("temp_operators.json", "wb") as f:
                    f.write(uploaded_ops.getbuffer())

                # 2. 保存临时配置文件 (从网页UI构建的字典直接写入)
                with open("temp_config.json", "w", encoding='utf-8') as f:
                    json.dump(current_config, f, ensure_ascii=False, indent=2)

                # 3. 运行优化器
                optimizer = WorkplaceOptimizer(
                    efficiency_file=base_efficiency_path,
                    operator_file="temp_operators.json",
                    config_file="temp_config.json"
                )

                # 执行计算
                curr_assign = optimizer.get_optimal_assignments(ignore_elite=False)
                pot_assign = optimizer.get_optimal_assignments(ignore_elite=True)
                upgrades = optimizer.calculate_upgrade_requirements(curr_assign, pot_assign)


                # 4. 准备下载数据 (JSON序列化)
                def clean_json(data):
                    return {k: v for k, v in data.items() if k != 'raw_results'}


                json_current = json.dumps(clean_json(curr_assign), ensure_ascii=False, indent=2)
                json_potential = json.dumps(clean_json(pot_assign), ensure_ascii=False, indent=2)

                # 准备 TXT 内容
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

                # 5. 将结果存入 session_state
                st.session_state.results = {
                    "current": json_current,
                    "potential": json_potential,
                    "txt": txt_content,
                    "efficiency": curr_assign['raw_results'][0].total_efficiency if curr_assign['raw_results'] else 0
                }
                st.session_state.calculated = True

                # 清理临时文件
                if os.path.exists("temp_operators.json"): os.remove("temp_operators.json")
                if os.path.exists("temp_config.json"): os.remove("temp_config.json")

            except Exception as e:
                st.error(f"运行出错: {e}")
                import traceback

                st.text(traceback.format_exc())


# 为了使用 datetime，需要在函数内或全局导入
def import_datetime():
    import datetime
    return datetime.datetime.now()


# ==========================================
# 4. 结果展示区 (根据 session_state 渲染)
# ==========================================

if st.session_state.calculated:
    res = st.session_state.results

    st.success("✅ 计算完成！")
    st.info(f"📊 当前方案首班效率参考: {res['efficiency']:.2f}")

    st.subheader("📥 结果下载")
    st.markdown("您可以同时下载以下所有文件：")

    # 使用列布局放置三个下载按钮
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

# 如果没有计算过，且有文件，显示提示
elif uploaded_ops:
    st.info("👆 请配置好上方参数，然后点击“开始计算排班”按钮。")