from copy import deepcopy
from typing import Any, Dict, List


MG_TEMPLATE_IDS = [
    "metric_spine",
    "evidence_dashboard",
    "radial_focus",
    "split_verdict",
    "timeline_ridge",
    "causal_cascade",
    "feedback_loop",
    "route_arc",
    "system_orbit",
    "risk_gauge",
    "quote_document",
    "process_ladder",
    "funnel_filter",
    "matrix_scan",
    "impact_ripple",
    "map_grid",
    "stack_layers",
    "decision_fork",
    "source_strip",
    "signal_wall",
]


_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "metric_spine": {
        "name": "指标脊柱",
        "visual_system": "metric",
        "scene_fit": ["核心指标", "强数据开场", "对比前后"],
        "modules": ["hero_metric", "supporting_bars", "micro_timeline"],
        "layout": "left_metric_right_evidence",
    },
    "evidence_dashboard": {
        "name": "证据仪表盘",
        "visual_system": "comparison",
        "scene_fit": ["多证据并列", "事实核验", "趋势摘要"],
        "modules": ["evidence_tiles", "status_chip", "source_footer"],
        "layout": "dashboard_grid",
    },
    "radial_focus": {
        "name": "径向聚焦",
        "visual_system": "causal",
        "scene_fit": ["中心概念拆解", "因素围绕", "结构解释"],
        "modules": ["center_claim", "radial_nodes", "pulse_ring"],
        "layout": "center_orbit",
    },
    "split_verdict": {
        "name": "双栏判定",
        "visual_system": "comparison",
        "scene_fit": ["观点对照", "利弊比较", "结论裁决"],
        "modules": ["left_case", "right_case", "verdict_lock"],
        "layout": "split_panel",
    },
    "timeline_ridge": {
        "name": "时间山脊",
        "visual_system": "timeline",
        "scene_fit": ["历史推进", "阶段变化", "长期周期"],
        "modules": ["ridge_line", "stage_markers", "turning_point"],
        "layout": "horizontal_timeline",
    },
    "causal_cascade": {
        "name": "因果瀑布",
        "visual_system": "causal",
        "scene_fit": ["链式传导", "机制解释", "多步后果"],
        "modules": ["cause_steps", "connector_arrows", "effect_plate"],
        "layout": "diagonal_flow",
    },
    "feedback_loop": {
        "name": "反馈回路",
        "visual_system": "causal",
        "scene_fit": ["循环机制", "正反馈", "负反馈"],
        "modules": ["loop_nodes", "return_arrow", "cycle_label"],
        "layout": "loop_diagram",
    },
    "route_arc": {
        "name": "路径弧线",
        "visual_system": "route",
        "scene_fit": ["地点迁移", "流向变化", "路径推进"],
        "modules": ["route_curve", "pin_labels", "destination_lock"],
        "layout": "map_arc",
    },
    "system_orbit": {
        "name": "系统轨道",
        "visual_system": "causal",
        "scene_fit": ["系统组成", "角色关系", "结构网络"],
        "modules": ["system_core", "orbit_roles", "relationship_lines"],
        "layout": "orbit_network",
    },
    "risk_gauge": {
        "name": "风险仪表",
        "visual_system": "metric",
        "scene_fit": ["风险判断", "程度变化", "阈值提醒"],
        "modules": ["gauge_meter", "threshold_ticks", "risk_reason"],
        "layout": "gauge_panel",
    },
    "quote_document": {
        "name": "文档引述",
        "visual_system": "comparison",
        "scene_fit": ["引用原文", "政策条款", "资料解释"],
        "modules": ["document_sheet", "quote_highlight", "annotation"],
        "layout": "document_overlay",
    },
    "process_ladder": {
        "name": "流程阶梯",
        "visual_system": "timeline",
        "scene_fit": ["操作流程", "阶段递进", "生产步骤"],
        "modules": ["ladder_steps", "progress_badge", "final_step"],
        "layout": "vertical_steps",
    },
    "funnel_filter": {
        "name": "漏斗筛选",
        "visual_system": "causal",
        "scene_fit": ["筛选逻辑", "层层过滤", "转化漏斗"],
        "modules": ["funnel_layers", "drop_count", "result_slot"],
        "layout": "center_funnel",
    },
    "matrix_scan": {
        "name": "矩阵扫描",
        "visual_system": "comparison",
        "scene_fit": ["二维分类", "象限判断", "多对象比较"],
        "modules": ["matrix_axes", "quadrant_cells", "scan_line"],
        "layout": "two_axis_matrix",
    },
    "impact_ripple": {
        "name": "影响涟漪",
        "visual_system": "causal",
        "scene_fit": ["影响扩散", "外溢效应", "层级传播"],
        "modules": ["ripple_core", "impact_rings", "outer_effects"],
        "layout": "concentric_rings",
    },
    "map_grid": {
        "name": "地图网格",
        "visual_system": "route",
        "scene_fit": ["区域分布", "城市网络", "地点热区"],
        "modules": ["grid_map", "area_cells", "route_marks"],
        "layout": "map_grid",
    },
    "stack_layers": {
        "name": "堆叠层级",
        "visual_system": "comparison",
        "scene_fit": ["层级结构", "成本构成", "系统分层"],
        "modules": ["stack_cards", "depth_shadow", "layer_labels"],
        "layout": "stacked_planes",
    },
    "decision_fork": {
        "name": "决策分叉",
        "visual_system": "comparison",
        "scene_fit": ["选择路径", "策略分歧", "结果比较"],
        "modules": ["fork_paths", "choice_nodes", "outcome_lock"],
        "layout": "fork_diagram",
    },
    "source_strip": {
        "name": "来源条带",
        "visual_system": "timeline",
        "scene_fit": ["资料来源", "证据链", "时间顺序引用"],
        "modules": ["source_cards", "strip_rail", "citation_badge"],
        "layout": "horizontal_strip",
    },
    "signal_wall": {
        "name": "信号墙",
        "visual_system": "metric",
        "scene_fit": ["多个信号", "异常提示", "趋势集合"],
        "modules": ["signal_tiles", "alert_marker", "trend_lock"],
        "layout": "signal_grid",
    },
}


def _blueprint(template_id: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": "mg_template_blueprint_v1",
        "id": template_id,
        "name": str(raw["name"]),
        "visual_system": str(raw["visual_system"]),
        "scene_fit": list(raw["scene_fit"]),
        "modules": list(raw["modules"]),
        "layout": str(raw["layout"]),
        "mutation_policy": "copy_into_project_instance",
    }


def get_mg_template(template_id: str) -> Dict[str, Any]:
    if template_id not in _BLUEPRINTS:
        raise KeyError(f"Unknown MG template: {template_id}")
    return deepcopy(_blueprint(template_id, _BLUEPRINTS[template_id]))


def list_mg_templates() -> List[Dict[str, Any]]:
    return [get_mg_template(template_id) for template_id in MG_TEMPLATE_IDS]
