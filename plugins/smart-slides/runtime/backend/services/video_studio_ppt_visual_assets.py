"""Composable PPT-derived visual language for the MG director.

The catalog contains design grammar, not render templates. The MG director
combines the grammar around a shot's meaning; the HTML model only executes the
resulting contract.
"""

import json
from typing import Any, Dict


PPT_VISUAL_LANGUAGE: Dict[str, Dict[str, str]] = {
    "compositions": {
        "asymmetric_split": "不对称分屏，用两个完整的 HTML 视觉区域建立主次关系，不预留外部素材窗口。",
        "causal_spine": "一条占据中部的大型因果脊柱串联少量不等距节点，结果端成为视觉峰值。",
        "editorial_timeline": "时间轴进入画面中部，转折节点远大于普通年份，不做底部细线年表。",
        "directional_route": "地图、资金或迁移路径作为宽阔主轨迹穿越画面，地点只做少量锚点。",
        "comparison_stage": "同一对象的两种状态形成明确冲突，可用切割、擦除、翻页或比例差表达。",
        "depth_reveal": "用前后景、剖面、水位或遮罩揭示表象下的隐藏结构。",
        "hero_metric": "一个核心数字与一个语义图形共同成为主体，证据围绕而不组成 KPI 面板。",
        "evidence_orbit": "核心判断位于视觉重心，少量证据沿不完整轨道或弧线形成张力。",
        "document_focus": "档案、条款或截图局部成为大号证据面，批注只强调一个决定性细节。",
        "layered_cascade": "层叠色场、台阶或连续坠落结构表达积累、升级、崩塌或传导。",
        "radial_convergence": "多个来源向一个核心汇聚或从核心外溢，方向性强且只保留一个中心。",
        "typographic_monument": "关键词、数字或短结论成为巨型排版主体，图形负责补充语义而非装饰。",
    },
    "hero_devices": {
        "semantic_icon_cluster": "2-4 个可辨认的大号 SVG 语义图标组成一个关系主体，不排列成图标菜单。",
        "oversized_number": "核心数字占据强视觉面积，并与趋势、比例或对象轮廓发生关系。",
        "symbolic_silhouette": "人物、国家、机构、工厂、芯片等轮廓承载抽象关系。",
        "wide_flow_band": "有宽度、有方向、有色场的带状路径承载流动或传导，不使用发丝线。",
        "cropped_evidence": "放大的档案、地图、票据或图表局部作为证据主体。",
        "before_after_object": "同一对象的前后状态共用坐标或轮廓，突出真正变化的位置。",
        "scale_contrast": "通过极端大小、距离或占比差异表达权力、成本、规模或失衡。",
        "stacked_layers": "少量大块层叠面表达地层、债务、供应链或结构累积。",
        "kinetic_wordmark": "一个短词或结论通过切割、挤压、展开等方式成为视觉对象。",
        "focus_frame": "大型取景框、扫描窗或聚焦圈锁定 HTML 内部绘制的关键证据对象。",
    },
    "materials": {
        "editorial_color_field": "高对比实体色场与硬边裁切，像纪录片包装而不是网页卡片。",
        "archival_paper": "克制的纸张、印刷、打字与档案磨损质感。",
        "ink_wash": "水墨扩散、干湿边缘或遮罩显影，只辅助主结构。",
        "cinematic_gradient": "有明确光源方向的电影渐变，不使用无意义渐变球。",
        "satellite_scan": "卫星纹理、扫描带和地理坐标质感，用于地图或环境证据。",
        "technical_blueprint": "工程线稿、剖面和测量标记，仅作为大型主体的辅助层。",
        "film_grain": "低强度胶片颗粒、曝光或闸门感，适合历史和人物证据。",
        "luminous_data": "克制的数据辉光和能量边缘，用于科技、资本或网络流动。",
    },
    "motion_rhythms": {
        "directional_build_lock": "先建立方向，再沿同一方向推进主体，最后锁定结论。",
        "mask_reveal_focus": "大遮罩揭示主体，随后焦点框停在决定性证据上。",
        "scale_punch_settle": "主体快速建立尺度冲击，短暂回弹后稳定，辅助信息再进入。",
        "progressive_cascade": "节点或层级按因果顺序连续推进，终点获得最大视觉权重。",
        "split_transform": "一个统一画面被切开并转化成两种状态，最终差异处停住。",
        "route_trace_arrival": "主路径从起点持续生长，到达终点后再出现短结论。",
        "evidence_accumulation": "证据逐一进入并围绕核心收敛，不同时出现一堆标签。",
        "hold_then_disrupt": "先用稳定构图建立认知，再由一次明显断裂、坠落或反转完成叙事。",
    },
}


_RECIPE_KEYS = {
    "composition_id": "compositions",
    "hero_device_id": "hero_devices",
    "material_id": "materials",
    "motion_id": "motion_rhythms",
}


def ppt_visual_language_catalog_prompt() -> str:
    """Expose the full grammar to the MG director, not to the HTML model."""
    return "\n".join(
        [
            "PPT 提炼视觉语法库（这是视觉语法库，不是 PPT 模板库）：",
            json.dumps(PPT_VISUAL_LANGUAGE, ensure_ascii=False),
            "使用规则：",
            "- 从 composition、hero_device、material、motion 四个维度各选一个 id，围绕当前分镜语义重新组合；不得照抄任何单页 PPT、固定版式、示例颜色或模块数量。",
            "- PPT 资产只提供构图原则、视觉层级和动效语言；主视觉隐喻、具体形状、比例、路径和文案必须根据当前内容原创。",
            "- composition_id 决定空间骨架，hero_device_id 决定第一眼主体，两者不能互相替代。",
            "- material_id 只决定美术质感，motion_id 只决定时间节奏。HTML 必须独立完成构图，不得依赖 B-roll 或其他外部画面。",
            "- 在 visual_recipe.originality_note 中说明这次如何针对内容做原创转译，不能只复述所选 id。",
        ]
    )


def ppt_visual_contract_art_direction(visual_recipe: Any) -> str:
    """Render the MG director's exact selection without making a new choice."""
    recipe = visual_recipe if isinstance(visual_recipe, dict) else {}
    lines = [
        "MG_VISUAL_RECIPE_CONTRACT",
        "这是 MG 导演已经完成的视觉决策。HTML 层只执行，不得重新选配方，也不是复刻 PPT 页面。",
    ]
    for contract_key, catalog_key in _RECIPE_KEYS.items():
        selected_id = str(recipe.get(contract_key) or "").strip()
        direction = PPT_VISUAL_LANGUAGE[catalog_key].get(selected_id)
        if not selected_id or not direction:
            lines.append(f"- {contract_key}: missing")
            continue
        lines.append(f"- {contract_key}: {selected_id} | {direction}")
    originality_note = str(recipe.get("originality_note") or "").strip()
    lines.append(f"- originality_note: {originality_note or 'missing'}")
    lines.extend(
        [
            "- 允许改变几何形状、裁切边界、节奏细节和色彩，但不得改变导演确定的叙事结构与视觉重心。",
            "- 禁止调用其他视觉语法作为第二主结构；禁止把该合同降级成卡片、dashboard 或小标签阵列。",
        ]
    )
    return "\n".join(lines)
