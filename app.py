import streamlit as st
import json
import os
import datetime
from logic import WorkplaceOptimizer

# ==========================================
# 0. 全局配置与样式优化
# ==========================================
st.set_page_config(
    page_title="罗德岛基建排班向导",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS 以提升专业感
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    h1 {font-family: 'Helvetica Neue', sans-serif; font-weight: 700;}
    .stButton>button {border-radius: 8px; font-weight: bold;}
    .stDownloadButton>button {width: 100%; border-radius: 6px;}
    /* 隐藏 Streamlit 默认菜单，看起来更像独立 App */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


def get_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 状态初始化
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
if 'results' not in st.session_state:
    st.session_state.results = {}

# ==========================================
# 1. 侧边栏：数据源 (Source of Truth)
# ==========================================
with st.sidebar:
    st.image("https://web.hycdn.cn/arknights/official/assets/images/brand.png", width=100)  # 只是个示例Logo，可换
    st.title("基建排班向导")
    st.markdown("---")

    st.subheader("📂 数据导入")
    base_efficiency_path = "efficiency.json"

    if not os.path.exists(base_efficiency_path):
        st.error("⚠️ 系统文件缺失: efficiency.json")
        st.stop()

    # 使用 Tab 切换导入方式，更简洁
    import_tab1, import_tab2 = st.tabs(["📋 剪贴板 (推荐)", "📁 文件上传"])

    with import_tab1:
        pasted_ops = st.text_area(
            "粘贴 MAA 导出的 JSON",
            height=300,
            help="在 MAA '小工具' -> '干员识别' -> 识别后点击 '复制到剪贴板'，然后在此处 Ctrl+V粘贴",
            placeholder='[\n  {\n    "id": "char_002_amiya",\n    "name": "阿米娅",\n    ...\n  }\n]'
        )
        if pasted_ops:
            st.success("已检测到文本数据")

    with import_tab2:
        uploaded_ops = st.file_uploader("上传 operators.json", type="json")

    st.markdown("---")
    st.caption(f"v1.3.0 | Author: 一只摆烂的42")

# ==========================================
# 2. 主界面：分步配置向导
# ==========================================

st.markdown("## 🏭 罗德岛基建排班控制台")
st.markdown("根据您的干员练度与基建布局，生成理论最高效率的排班方案。")

# --- 板块 1: 基建布局 (Layout) ---
with st.container(border=True):
    st.subheader("1. 基建布局设定")

    # 使用列布局 + Radio 模拟预设按钮
    l_col1, l_col2 = st.columns([1, 2])

    with l_col1:
        layout_preset = st.radio(
            "⚡ 快速预设 (3发电站)",
            ["3-3-3 (搓玉推荐)", "2-4-3 (均衡)", "1-5-3 (极限制造)", "自定义"],
            index=0,
            horizontal=False
        )

    with l_col2:
        # 根据预设自动填充，或者允许自定义
        if layout_preset == "3-3-3 (搓玉推荐)":
            def_t, def_m = 3, 3
            disabled = True
        elif layout_preset == "2-4-3 (均衡)":
            def_t, def_m = 2, 4
            disabled = True
        elif layout_preset == "1-5-3 (极限制造)":
            def_t, def_m = 1, 5
            disabled = True
        else:
            def_t, def_m = 2, 4
            disabled = False

        c1, c2 = st.columns(2)
        n_trading = c1.number_input("贸易站", 1, 5, def_t, disabled=disabled)
        n_manufacture = c2.number_input("制造站", 1, 5, def_m, disabled=disabled)

        # 实时计算发电站并校验
        n_power = 9 - n_trading - n_manufacture
        if n_power != 3:
            st.warning(f"当前为 {n_power} 发电站布局。算法目前仅针对 3 发电站优化，其他布局可能导致不可预知的排班结果。",
                       icon="⚠️")
        else:
            st.caption(f"当前布局: {n_trading}贸易 - {n_manufacture}制造 - {n_power}发电")

# --- 板块 2: 产物策略 (Strategy) ---
with st.container(border=True):
    st.subheader("2. 产物策略分配")

    col_prod1, col_prod2 = st.columns(2)

    # 贸易站策略：使用 Slider 直观展示比例
    with col_prod1:
        st.markdown("#### 💰 贸易站订单")
        if n_trading > 0:
            # 滑块逻辑：总数固定，分配LMD，剩下的给合成玉
            req_lmd = st.slider("龙门币 (LMD) 占比", 0, n_trading, n_trading, help="剩下的将分配给合成玉")
            req_orundum = n_trading - req_lmd

            st.info(f"分配: {req_lmd} 龙门币 + {req_orundum} 合成玉")
        else:
            req_lmd, req_orundum = 0, 0
            st.write("无贸易站")

    # 制造站策略
    with col_prod2:
        st.markdown("#### 📦 制造站产线")
        # 制造站通常比较复杂，保持 Number Input 但优化布局
        m1, m2, m3 = st.columns(3)
        req_gold = m1.number_input("赤金", 0, n_manufacture, min(2, n_manufacture))
        req_record = m2.number_input("经验书", 0, n_manufacture, min(2, n_manufacture))
        req_shard = m3.number_input("源石碎片", 0, n_manufacture, 0)

        current_m_total = req_gold + req_record + req_shard
        if current_m_total != n_manufacture:
            st.error(f"分配错误: 已分配 {current_m_total} / {n_manufacture} 间设施", icon="🚫")
        else:
            st.success(f"产线分配完成", icon="✅")

# --- 板块 3: 自动化科技 (Advanced) ---
with st.expander("⚙️ 高级设置 (菲亚梅塔 / 无人机)", expanded=False):
    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        st.markdown("##### 🔥 菲亚梅塔体系")
        enable_fia = st.toggle("启用自动充能", value=True, help="自动识别排班中收益最高的干员进行心情恢复")
        if enable_fia:
            st.warning(
                "⚠️ **重要提示**：\n\n"
                "菲亚梅塔体系需要**严格保证换班时间**（通常为 12小时 或 8小时一换）。\n"
                "建议配合 **MAA 定时任务** 或闹钟使用。\n\n"
                "🚫 **如果无法保证准时换班，充能对象极易心情耗尽（红脸），反而降低效率，此时请关闭此选项。**",
                icon="⚠️"
            )

    with col_adv2:
        st.markdown("##### 🚁 无人机加速")
        enable_drone = st.toggle("启用无人机加速", value=True)

        drone_targets = []
        if enable_drone:
            # 紧凑型选择器
            product_map = {"龙门币": "LMD", "赤金": "Pure Gold", "经验书": "Battle Record", "合成玉": "Orundum"}
            rev_map = {v: k for k, v in product_map.items()}

            dc1, dc2, dc3 = st.columns(3)
            # 默认方案
            t1 = dc1.selectbox("班次 1", list(product_map.keys()), index=0)  # LMD
            t2 = dc2.selectbox("班次 2", list(product_map.keys()), index=1)  # Gold
            t3 = dc3.selectbox("班次 3", list(product_map.keys()), index=0)  # LMD
            drone_targets = [product_map[t1], product_map[t2], product_map[t3]]

        drone_order = "pre"

# ==========================================
# 3. 核心执行与状态反馈
# ==========================================
st.markdown("---")
col_action, col_blank = st.columns([1, 2])

# 构建 Config
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

# 校验逻辑
is_config_valid = (current_m_total == n_manufacture) and ((req_lmd + req_orundum) == n_trading)
is_data_ready = (pasted_ops is not None and pasted_ops.strip() != "") or (uploaded_ops is not None)

if col_action.button("🚀 生成排班方案", type="primary", use_container_width=True,
                     disabled=not (is_config_valid and is_data_ready)):

    # 准备数据源
    operators_bytes = None
    if uploaded_ops:
        operators_bytes = uploaded_ops.getvalue()
    elif pasted_ops:
        try:
            json.loads(pasted_ops)  # 简单校验
            operators_bytes = pasted_ops.encode('utf-8')
        except:
            st.toast("❌ 粘贴的 JSON 格式无效", icon="🚫")
            st.stop()

    # 使用 st.status 提供高级反馈
    with st.status("正在进行神经模拟...", expanded=True) as status:
        try:
            st.write("📥 读取干员练度数据...")
            with open("temp_ops.json", "wb") as f:
                f.write(operators_bytes)

            st.write("⚙️ 解析基建配置...")
            with open("temp_conf.json", "w", encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False)

            st.write("🧠 运行优化算法 (WorkplaceOptimizer)...")
            optimizer = WorkplaceOptimizer("efficiency.json", "temp_ops.json", "temp_conf.json")

            st.write("📊 计算当前练度最优解...")
            curr = optimizer.get_optimal_assignments(ignore_elite=False)

            st.write("🔮 计算理论极限最优解...")
            pot = optimizer.get_optimal_assignments(ignore_elite=True)

            st.write("📈 分析练度提升路径...")
            upgrades = optimizer.calculate_upgrade_requirements(curr, pot)


            # 结果处理
            def clean(d):
                return {k: v for k, v in d.items() if k != 'raw_results'}


            # 生成 TXT
            txt = "=== 罗德岛基建练度提升建议 ===\n"
            txt += f"生成时间: {get_timestamp()}\n{'=' * 40}\n\n"
            if not upgrades:
                txt += "✅ 完美！您的队伍已达到当前配置的理论极限效率。\n"
            else:
                for item in upgrades:
                    g = item['gain']
                    g_str = f"{g * 100:.1f}%" if g < 0.9 else f"{g:.1f}%"
                    if item.get('type') == 'bundle':
                        names = "+".join([o['name'] for o in item['ops']])
                        txt += f"[组合] {names}\n   收益: {item['rooms']} 效率 +{g_str}\n"
                        for o in item['ops']: txt += f"   - {o['name']}: 精{o['current']} -> 精{o['target']}\n"
                    else:
                        txt += f"[单人] {item['name']}\n   收益: {item['rooms']} 效率 +{g_str}\n"
                        txt += f"   - 当前: 精{item['current']} -> 目标: 精{item['target']}\n"
                    txt += "-" * 30 + "\n"

            st.session_state.results = {
                "curr": json.dumps(clean(curr), ensure_ascii=False, indent=2),
                "pot": json.dumps(clean(pot), ensure_ascii=False, indent=2),
                "txt": txt,
                "eff": curr['raw_results'][0].total_efficiency if curr['raw_results'] else 0
            }
            st.session_state.calculated = True

            # 清理
            if os.path.exists("temp_ops.json"): os.remove("temp_ops.json")
            if os.path.exists("temp_conf.json"): os.remove("temp_conf.json")

            status.update(label="✅ 计算完成！", state="complete", expanded=False)

        except Exception as e:
            status.update(label="❌ 计算失败", state="error")
            st.error(f"错误详情: {str(e)}")
            import traceback

            st.code(traceback.format_exc())

# ==========================================
# 4. 结果仪表盘
# ==========================================
if st.session_state.calculated:
    res = st.session_state.results

    st.markdown("### 📊 分析报告")

    # 关键指标展示
    m1, m2, m3 = st.columns(3)
    m1.metric("首班总效率", f"{res['eff']:.2f}%", delta="当前练度")
    m2.metric("排班方案", "3班轮换", help="固定为3班倒模式")
    m3.metric("基建类型", f"{n_trading}{n_manufacture}{9 - n_trading - n_manufacture}")

    st.markdown("#### 📥 方案下载")

    # 下载区使用卡片式布局
    d1, d2, d3 = st.columns(3)

    with d1:
        with st.container(border=True):
            st.markdown("**📄 当前方案**")
            st.caption("基于您现有的干员练度")
            st.download_button("下载 JSON", res['curr'], "current.json", "application/json", use_container_width=True)

    with d2:
        with st.container(border=True):
            st.markdown("**🔮 极限方案**")
            st.caption("忽略练度限制的理论最优")
            st.download_button("下载 JSON", res['pot'], "potential.json", "application/json", use_container_width=True)

    with d3:
        with st.container(border=True):
            st.markdown("**📈 提升建议**")
            st.caption("性价比最高的练度提升路径")
            st.download_button("下载 报告", res['txt'], "suggestions.txt", "text/plain", use_container_width=True)

    # 底部指南
    st.info("""
    **💡 如何使用导出的 JSON？**
    1. **自动化**: `基建换班` -> 启用 `自定义排班` -> 选择文件。
    2. **可视化**: 前往 [一图流工具](https://ark.yituliu.cn/tools/scheduleV2) 导入文件预览排班详情。
    """)