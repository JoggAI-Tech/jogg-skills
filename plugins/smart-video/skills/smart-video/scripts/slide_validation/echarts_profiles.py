"""Closed, data-driven profiles for supported declarative ECharts options."""

from __future__ import annotations

import re
from typing import Any

from .contracts import *

GL_SERIES = {
    "globe", "bar3D", "scatter3D", "surface", "map3D", "lines3D",
    "line3D", "scatterGL", "linesGL", "flowGL", "graphGL",
}
STANDARD_SERIES = {
    "line", "bar", "pie", "scatter", "effectScatter", "radar", "tree",
    "treemap", "sunburst", "graph", "sankey", "funnel", "gauge",
    "pictorialBar", "themeRiver", "boxplot", "candlestick", "heatmap",
    "map", "lines", "parallel",
}
SERIES_DATA_SURFACES = {
    "line": {"data"},
    "bar": {"data"},
    "pie": {"data"},
    "scatter": {"data"},
    "effectScatter": {"data"},
    "radar": {"data"},
    "tree": {"data"},
    "treemap": {"data"},
    "sunburst": {"data"},
    "graph": {"data", "nodes", "links", "edges", "categories"},
    "sankey": {"data", "nodes", "links", "edges"},
    "funnel": {"data"},
    "gauge": {"data"},
    "pictorialBar": {"data"},
    "themeRiver": {"data"},
    "boxplot": {"data"},
    "candlestick": {"data"},
    "heatmap": {"data"},
    "map": {"data"},
    "lines": {"data"},
    "parallel": {"data"},
}
DATASET_SERIES = {
    "line", "bar", "pie", "scatter", "effectScatter", "radar", "funnel",
    "pictorialBar", "themeRiver", "boxplot", "candlestick", "heatmap", "map",
    "parallel",
}
INTERACTION_ONLY_ENCODE_CHANNELS = {"tooltip"}
STATIC_ENCODE_CHANNELS = {
    "line": {"cartesian2d": {"x", "y"}, "polar": {"radius", "angle"}},
    "bar": {"cartesian2d": {"x", "y"}, "polar": {"radius", "angle"}},
    "pie": {"none": {"itemName", "value"}},
    "scatter": {
        "cartesian2d": {"x", "y"},
        "polar": {"radius", "angle"},
        "geo": {"lng", "lat"},
        "calendar": {"time", "value"},
    },
    "effectScatter": {
        "cartesian2d": {"x", "y"},
        "polar": {"radius", "angle"},
        "geo": {"lng", "lat"},
        "calendar": {"time", "value"},
    },
    "radar": {"radar": {"itemName", "value"}},
    "funnel": {"none": {"itemName", "value"}},
    "pictorialBar": {"cartesian2d": {"x", "y"}},
    "themeRiver": {"singleAxis": {"single", "value", "itemName"}},
    "boxplot": {"cartesian2d": {"x", "y"}},
    "candlestick": {"cartesian2d": {"x", "y"}},
    "heatmap": {
        "cartesian2d": {"x", "y", "value"},
        "geo": {"lng", "lat", "value"},
        "calendar": {"time", "value"},
    },
    "map": {"geo": {"itemName", "value"}},
    "parallel": {"parallel": set()},
}
DEFAULT_COORDINATE_SYSTEM = {
    "line": "cartesian2d", "bar": "cartesian2d", "pie": "none",
    "scatter": "cartesian2d", "effectScatter": "cartesian2d", "radar": "radar",
    "funnel": "none", "pictorialBar": "cartesian2d", "themeRiver": "singleAxis",
    "boxplot": "cartesian2d", "candlestick": "cartesian2d", "heatmap": "cartesian2d",
    "map": "geo", "parallel": "parallel",
}
DATASET_ALLOWED_FIELDS = {"id", "source", "dimensions", "sourceHeader"}
DATASET_DIMENSION_ALLOWED_FIELDS = {"name", "type", "displayName"}
ENCODE_ALLOWED_FIELDS = {
    "x", "y", "radius", "angle", "itemName", "value", "lng", "lat",
    "time", "single", "tooltip", "itemId", "itemGroupId", "itemChildGroupId",
    "seriesName",
}
DIRECT_DATA_ITEM_ALLOWED_FIELDS = {
    "id", "name", "value", "groupId", "childGroupId", "selected", "symbol",
    "symbolSize", "symbolRotate", "symbolKeepAspect", "symbolOffset", "cursor",
    "itemStyle", "lineStyle", "areaStyle", "label", "labelLine", "endLabel",
    "title", "detail", "emphasis", "blur", "select", "tooltip",
}
GRAPH_NODE_ALLOWED_FIELDS = {
    "id", "name", "value", "category", "symbol", "symbolSize", "symbolRotate",
    "symbolKeepAspect", "symbolOffset", "x", "y", "fixed", "draggable", "cursor",
    "itemStyle", "label", "emphasis", "blur", "select", "tooltip",
}
GRAPH_LINK_ALLOWED_FIELDS = {
    "source", "target", "value", "symbol", "symbolSize", "lineStyle", "label",
    "emphasis", "blur", "select",
}
GRAPH_CATEGORY_ALLOWED_FIELDS = {
    "name", "symbol", "symbolSize", "symbolRotate", "symbolKeepAspect",
    "symbolOffset", "itemStyle", "label", "emphasis", "blur", "select", "tooltip",
}
HIERARCHY_NODE_ALLOWED_FIELDS = {
    "id", "name", "value", "children", "collapsed", "selected", "symbol",
    "symbolSize", "symbolRotate", "symbolKeepAspect", "symbolOffset", "itemStyle",
    "lineStyle", "areaStyle", "label", "upperLabel", "emphasis", "blur", "select",
    "tooltip", "visualDimension", "link",
}
LINES_DATA_ITEM_ALLOWED_FIELDS = {
    "name", "fromName", "toName", "value", "coords", "symbol", "symbolSize",
    "lineStyle", "label", "effect", "emphasis", "blur", "select",
}
SERIES_ALLOWED_FIELDS = {
    "id", "name", "type", "coordinateSystem", "xAxisIndex", "yAxisIndex",
    "polarIndex", "geoIndex", "calendarIndex", "radarIndex", "singleAxisIndex",
    "parallelIndex", "datasetIndex", "datasetId", "encode", "dimensions",
    "seriesLayoutBy", "data", "nodes", "links", "edges", "categories",
    "markPoint", "markLine", "markArea", "z", "zlevel", "silent", "cursor",
    "colorBy", "blendMode", "dataGroupId",
    "animation", "animationThreshold", "animationDuration", "animationEasing",
    "animationDelay", "animationDurationUpdate", "animationEasingUpdate",
    "animationDelayUpdate", "universalTransition", "selectedMode", "stack",
    "stackStrategy", "label", "endLabel", "labelLine", "labelLayout", "itemStyle",
    "lineStyle", "areaStyle", "emphasis", "blur", "select", "tooltip", "symbol",
    "symbolSize", "symbolRotate", "symbolKeepAspect", "symbolOffset", "showSymbol",
    "showAllSymbol", "legendHoverLink", "hoverAnimation", "clip", "connectNulls",
    "smooth", "smoothMonotone", "sampling", "step", "large", "largeThreshold",
    "progressive", "progressiveThreshold", "progressiveChunkMode", "realtimeSort",
    "barWidth", "barMaxWidth", "barMinWidth", "barGap", "barCategoryGap",
    "barMinHeight", "barMinAngle", "roundCap", "showBackground", "backgroundStyle",
    "center", "radius", "roseType", "minAngle", "minShowLabelAngle",
    "avoidLabelOverlap", "stillShowZeroSum", "percentPrecision", "clockwise",
    "startAngle", "endAngle", "padAngle", "layout", "orient", "edgeShape",
    "edgeForkPosition", "roam", "expandAndCollapse", "initialTreeDepth", "leaves",
    "squareRatio", "leafDepth", "drillDownIcon", "visibleMin", "childrenVisibleMin",
    "upperLabel", "breadcrumb", "nodeClick", "zoomToNodeRatio", "levels",
    "colorMappingBy", "visualDimension", "visualMin", "visualMax", "sort",
    "highlightPolicy", "downplay", "circular", "force", "draggable", "edgeSymbol",
    "edgeSymbolSize", "edgeLabel", "focusNodeAdjacency", "nodeAlign", "nodeGap",
    "nodeWidth", "layoutIterations", "min", "max", "minSize", "maxSize", "gap",
    "funnelAlign", "left", "top", "right", "bottom", "width", "height",
    "splitNumber", "axisLine", "progress", "splitLine", "axisTick", "axisLabel",
    "pointer", "anchor", "title", "detail", "symbolRepeat", "symbolRepeatDirection",
    "symbolMargin", "symbolClip", "symbolBoundingData", "symbolPosition",
    "singleAxisIndex", "boundaryGap", "boxWidth", "pointSize", "blurSize",
    "minOpacity", "maxOpacity", "map", "nameMap", "nameProperty", "aspectScale",
    "boundingCoords", "zoom", "scaleLimit", "projection", "polyline", "effect",
    "inactiveOpacity", "activeOpacity",
    "animationType", "animationTypeUpdate", "layoutCenter", "layoutSize",
}
OPTION_ALLOWED_FIELDS = {
    "backgroundColor", "darkMode", "color", "colorLayer", "aria", "textStyle",
    "title", "legend", "grid", "xAxis", "yAxis", "polar", "radiusAxis",
    "angleAxis", "radar", "dataZoom", "visualMap", "tooltip", "axisPointer",
    "toolbox", "brush", "geo", "parallel", "parallelAxis", "singleAxis",
    "calendar", "dataset", "series",
    "animation", "animationThreshold", "animationDuration", "animationEasing",
    "animationDelay", "animationDurationUpdate", "animationEasingUpdate",
    "animationDelayUpdate", "stateAnimation", "blendMode", "hoverLayerThreshold",
    "useUTC", "locale",
}
TITLE_ALLOWED_FIELDS = {
    "id", "show", "text", "link", "target", "subtext", "sublink", "subtarget",
    "left", "top", "right", "bottom", "backgroundColor", "borderColor",
    "borderWidth", "borderRadius", "padding", "itemGap", "textStyle",
    "subtextStyle", "textAlign", "textVerticalAlign", "triggerEvent", "zlevel", "z",
}
LEGEND_ALLOWED_FIELDS = {
    "id", "type", "show", "zlevel", "z", "left", "top", "right", "bottom",
    "width", "height", "orient", "align", "padding", "itemGap", "itemWidth",
    "itemHeight", "itemStyle", "lineStyle", "symbolRotate", "formatter",
    "selectedMode", "inactiveColor", "inactiveBorderColor", "inactiveBorderWidth",
    "selected", "textStyle", "tooltip", "icon", "data", "backgroundColor",
    "borderColor", "borderWidth", "borderRadius", "shadowBlur", "shadowColor",
    "shadowOffsetX", "shadowOffsetY", "scrollDataIndex", "pageButtonItemGap",
    "pageButtonGap", "pageButtonPosition", "pageFormatter", "pageIcons",
    "pageIconColor", "pageIconInactiveColor", "pageIconSize", "pageTextStyle",
    "animationDurationUpdate", "emphasis", "selector", "selectorLabel",
    "selectorPosition", "selectorItemGap", "selectorButtonGap",
}
GRID_ALLOWED_FIELDS = {
    "id", "show", "zlevel", "z", "left", "top", "right", "bottom", "width",
    "height", "containLabel", "backgroundColor", "borderColor", "borderWidth",
    "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY", "tooltip",
}
CALENDAR_ALLOWED_FIELDS = {
    "id", "zlevel", "z", "left", "top", "right", "bottom", "width", "height",
    "range", "cellSize", "orient", "splitLine", "itemStyle", "dayLabel",
    "monthLabel", "yearLabel", "silent",
}
RADAR_ALLOWED_FIELDS = {
    "id", "zlevel", "z", "center", "radius", "startAngle", "nameGap",
    "splitNumber", "shape", "scale", "silent", "triggerEvent", "axisLine",
    "axisTick", "axisLabel", "splitLine", "splitArea", "indicator",
}
POLAR_ALLOWED_FIELDS = {"id", "zlevel", "z", "center", "radius", "tooltip"}
GEO_ALLOWED_FIELDS = {
    "id", "show", "map", "roam", "center", "aspectScale", "boundingCoords",
    "zoom", "scaleLimit", "nameMap", "nameProperty", "selectedMode", "label",
    "itemStyle", "emphasis", "select", "blur", "regions", "silent",
    "left", "top", "right", "bottom", "layoutCenter", "layoutSize", "zlevel", "z",
    "tooltip",
}
PARALLEL_ALLOWED_FIELDS = {
    "id", "zlevel", "z", "left", "top", "right", "bottom", "width", "height",
    "layout", "parallelAxisDefault",
}
AXIS_POINTER_ALLOWED_FIELDS = {
    "id", "show", "type", "snap", "z", "label", "lineStyle", "shadowStyle",
    "triggerTooltip", "value", "status", "link", "triggerOn",
}
ARIA_ALLOWED_FIELDS = {"enabled", "label", "decal"}
STATE_ANIMATION_ALLOWED_FIELDS = {"duration", "easing"}
AXIS_ALLOWED_FIELDS = {
    "id", "show", "gridIndex", "polarIndex", "position", "offset", "type", "name",
    "nameLocation", "nameTextStyle", "nameGap", "nameRotate", "inverse", "boundaryGap",
    "min", "max", "scale", "splitNumber", "minInterval", "maxInterval", "interval",
    "logBase", "silent", "triggerEvent", "axisLine", "axisTick", "minorTick",
    "axisLabel", "splitLine", "minorSplitLine", "splitArea", "axisPointer", "data",
    "zlevel", "z", "startValue", "clockwise", "startAngle", "endAngle", "center",
    "radius", "tooltip", "realtime", "parallelIndex", "dim", "areaSelectStyle",
}
SINGLE_AXIS_ALLOWED_FIELDS = AXIS_ALLOWED_FIELDS | {
    "left", "top", "right", "bottom", "width", "height", "orient",
}
VISUAL_MAP_ALLOWED_FIELDS = {
    "id", "type", "min", "max", "range", "calculable", "realtime", "inverse",
    "precision", "itemWidth", "itemHeight", "align", "text", "textGap", "show",
    "dimension", "seriesIndex", "hoverLink", "inRange", "outOfRange", "controller",
    "formatter", "pieces", "categories", "selected", "selectedMode", "orient",
    "left", "top", "right", "bottom", "padding", "backgroundColor", "borderColor",
    "borderWidth", "color", "textStyle", "zlevel", "z",
}
ITEM_STYLE_ALLOWED_FIELDS = {
    "color", "borderColor", "borderWidth", "borderType", "borderDashOffset",
    "borderCap", "borderJoin", "borderMiterLimit", "shadowBlur", "shadowColor",
    "shadowOffsetX", "shadowOffsetY", "opacity", "decal",
}
LINE_STYLE_ALLOWED_FIELDS = {
    "color", "width", "type", "dashOffset", "cap", "join", "miterLimit",
    "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY", "opacity",
    "curveness",
}
AREA_STYLE_ALLOWED_FIELDS = {
    "color", "origin", "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY",
    "opacity",
}
LABEL_ALLOWED_FIELDS = {
    "show", "position", "distance", "rotate", "offset", "formatter", "color",
    "fontStyle", "fontWeight", "fontFamily", "fontSize", "align", "verticalAlign",
    "lineHeight", "backgroundColor", "borderColor", "borderWidth", "borderType",
    "borderDashOffset", "borderRadius", "padding", "shadowColor", "shadowBlur",
    "shadowOffsetX", "shadowOffsetY", "width", "height", "textBorderColor",
    "textBorderWidth", "textBorderType", "textBorderDashOffset", "textShadowColor",
    "textShadowBlur", "textShadowOffsetX", "textShadowOffsetY", "overflow", "ellipsis",
    "rich", "valueAnimation", "precision", "minMargin", "margin",
}
TEXT_STYLE_ALLOWED_FIELDS = {
    "color", "fontStyle", "fontWeight", "fontFamily", "fontSize", "align",
    "verticalAlign", "lineHeight", "width", "height", "textBorderColor",
    "textBorderWidth", "textBorderType", "textBorderDashOffset",
    "textShadowColor", "textShadowBlur", "textShadowOffsetX",
    "textShadowOffsetY", "overflow", "ellipsis", "rich",
}
TOOLTIP_ALLOWED_FIELDS = {
    "show", "trigger", "axisPointer", "showContent", "alwaysShowContent", "triggerOn",
    "showDelay", "hideDelay", "enterable", "renderMode", "confine", "appendToBody",
    "className", "transitionDuration", "position", "formatter", "valueFormatter",
    "backgroundColor", "borderColor", "borderWidth", "padding", "textStyle",
    "extraCssText", "order",
}
MARK_COMPONENT_ALLOWED_FIELDS = {
    "silent", "symbol", "symbolSize", "symbolRotate", "symbolKeepAspect", "symbolOffset",
    "precision", "label", "itemStyle", "lineStyle", "emphasis", "blur", "data",
    "animation", "animationThreshold", "animationDuration", "animationEasing",
    "animationDelay", "animationDurationUpdate", "animationEasingUpdate",
    "animationDelayUpdate", "zlevel", "z",
}
MARK_ITEM_ALLOWED_FIELDS = {
    "name", "type", "valueIndex", "valueDim", "coord", "x", "y", "xAxis", "yAxis",
    "radiusAxis", "angleAxis", "value", "symbol", "symbolSize", "symbolRotate",
    "symbolKeepAspect", "symbolOffset", "itemStyle", "lineStyle", "label", "emphasis",
    "blur",
}
MARK_LOCATOR_FIELDS = {"type", "coord", "xAxis", "yAxis", "radiusAxis", "angleAxis", "singleAxis"}
VISUAL_MAP_STATIC_CHANNELS = {
    "color", "colorAlpha", "colorLightness", "colorSaturation", "colorHue",
    "symbol", "symbolSize", "opacity",
}
STATE_ALLOWED_FIELDS = {
    "disabled", "focus", "blurScope", "scale", "scaleSize", "label", "endLabel",
    "itemStyle", "lineStyle", "areaStyle", "labelLine", "upperLabel", "edgeLabel",
}
CALENDAR_LABEL_ALLOWED_FIELDS = TEXT_STYLE_ALLOWED_FIELDS | {
    "show", "firstDay", "margin", "position", "nameMap",
}
AXIS_LINE_ALLOWED_FIELDS = {
    "show", "onZero", "onZeroAxisIndex", "symbol", "symbolSize", "symbolOffset",
    "lineStyle",
}
AXIS_TICK_ALLOWED_FIELDS = {
    "show", "alignWithLabel", "interval", "inside", "length", "lineStyle",
}
SPLIT_LINE_ALLOWED_FIELDS = {"show", "interval", "lineStyle"}
SPLIT_AREA_ALLOWED_FIELDS = {"show", "interval", "areaStyle"}
LABEL_LINE_ALLOWED_FIELDS = {
    "show", "showAbove", "length", "length2", "smooth", "minTurnAngle", "lineStyle",
}
AXIS_POINTER_LABEL_ALLOWED_FIELDS = TEXT_STYLE_ALLOWED_FIELDS | {
    "show", "precision", "formatter", "margin", "padding", "backgroundColor",
    "borderColor", "borderWidth", "borderRadius", "shadowBlur", "shadowColor",
    "shadowOffsetX", "shadowOffsetY",
}
AXIS_POINTER_LINK_ALLOWED_FIELDS = {
    "xAxisIndex", "yAxisIndex", "radiusAxisIndex", "angleAxisIndex", "singleAxisIndex",
}
RADAR_INDICATOR_ALLOWED_FIELDS = {"name", "max", "min", "color"}
GEO_REGION_ALLOWED_FIELDS = {
    "name", "selected", "label", "itemStyle", "emphasis", "select", "blur", "tooltip",
}
VISUAL_MAP_PIECE_ALLOWED_FIELDS = {
    "min", "max", "gt", "gte", "lt", "lte", "value", "label", "color",
    "colorAlpha", "colorLightness", "colorSaturation", "colorHue", "symbol",
    "symbolSize", "opacity",
}
AXIS_DATA_ITEM_ALLOWED_FIELDS = {"value", "textStyle"}
LEGEND_DATA_ITEM_ALLOWED_FIELDS = {
    "name", "icon", "itemStyle", "lineStyle", "textStyle", "tooltip",
}
LEGEND_SELECTOR_ITEM_ALLOWED_FIELDS = {"type", "title"}
DECAL_ALLOWED_FIELDS = {
    "symbol", "symbolSize", "symbolKeepAspect", "color", "backgroundColor",
    "dashArrayX", "dashArrayY", "rotation", "maxTileWidth", "maxTileHeight",
}
ARIA_LABEL_ALLOWED_FIELDS = {"enabled", "description", "general", "series", "data"}
ARIA_GENERAL_ALLOWED_FIELDS = {"withTitle", "withoutTitle"}
ARIA_SERIES_ALLOWED_FIELDS = {"maxCount", "single", "multiple"}
ARIA_SERIES_SINGLE_ALLOWED_FIELDS = {"prefix", "withName", "withoutName"}
ARIA_SERIES_MULTIPLE_ALLOWED_FIELDS = {
    "prefix", "withName", "withoutName", "separator",
}
ARIA_DATA_ALLOWED_FIELDS = {"maxCount", "allData", "partialData", "withName"}
ARIA_DECAL_ALLOWED_FIELDS = {"show", "decals"}
TOOLTIP_AXIS_POINTER_ALLOWED_FIELDS = {
    "type", "axis", "snap", "z", "label", "lineStyle", "shadowStyle",
    "crossStyle", "animation", "animationDurationUpdate", "animationEasingUpdate",
}
UNIVERSAL_TRANSITION_ALLOWED_FIELDS = {"enabled", "divideShape", "seriesKey"}
FORCE_ALLOWED_FIELDS = {
    "initLayout", "repulsion", "gravity", "edgeLength", "layoutAnimation", "friction",
}
CIRCULAR_ALLOWED_FIELDS = {"rotateLabel"}
SCALE_LIMIT_ALLOWED_FIELDS = {"min", "max"}
EFFECT_ALLOWED_FIELDS = {
    "show", "period", "delay", "constantSpeed", "symbol", "symbolSize",
    "trailLength", "loop", "roundTrip", "color",
}
POINTER_ALLOWED_FIELDS = {
    "show", "showAbove", "icon", "offsetCenter", "length", "width", "keepAspect",
    "itemStyle",
}
ANCHOR_ALLOWED_FIELDS = {
    "show", "showAbove", "size", "icon", "offsetCenter", "keepAspect", "itemStyle",
}
PROGRESS_ALLOWED_FIELDS = {
    "show", "overlap", "width", "roundCap", "clip", "itemStyle",
}
BREADCRUMB_ALLOWED_FIELDS = {
    "show", "height", "left", "top", "right", "bottom", "emptyItemWidth",
    "itemStyle", "emphasis",
}
SERIES_LEVEL_ALLOWED_FIELDS = {
    "visualDimension", "visualMin", "visualMax", "color", "colorAlpha",
    "colorSaturation", "colorMappingBy", "itemStyle", "upperLabel",
}
SERIES_LEAVES_ALLOWED_FIELDS = {
    "label", "itemStyle", "emphasis", "blur", "select",
}
AREA_SELECT_STYLE_ALLOWED_FIELDS = {
    "width", "borderWidth", "borderColor", "color", "opacity",
}
VISUAL_MAP_CONTROLLER_ALLOWED_FIELDS = {"inRange", "outOfRange"}

ECHARTS_PROFILE_MAX_DEPTH = 32
ECHARTS_PROFILE_NODE_BUDGET = 4096

# Child kinds are interpreted by validate_echarts_profile(). Declarative data
# surfaces remain delegated to the existing source-binding and series validators.
ECHARTS_COMPONENT_PROFILES: dict[str, dict[str, Any]] = {
    "option": {
        "label": "option",
        "allowed": OPTION_ALLOWED_FIELDS,
        "children": {
            "aria": ("object", "aria"),
            "textStyle": ("object", "text_style"),
            "title": ("object_or_array", "title"),
            "legend": ("object_or_array", "legend"),
            "grid": ("object_or_array", "grid"),
            "xAxis": ("object_or_array", "axis"),
            "yAxis": ("object_or_array", "axis"),
            "polar": ("object_or_array", "polar"),
            "radiusAxis": ("object_or_array", "axis"),
            "angleAxis": ("object_or_array", "axis"),
            "radar": ("object_or_array", "radar"),
            "visualMap": ("object_or_array", "visual_map"),
            "tooltip": ("object", "tooltip"),
            "axisPointer": ("object", "axis_pointer"),
            "geo": ("object_or_array", "geo"),
            "parallel": ("object_or_array", "parallel"),
            "parallelAxis": ("object_or_array", "axis"),
            "singleAxis": ("object_or_array", "single_axis"),
            "calendar": ("object_or_array", "calendar"),
            "dataset": ("object_or_array", "dataset"),
            "series": ("array_objects", "series"),
            "stateAnimation": ("object", "state_animation"),
        },
    },
    "title": {
        "label": "title", "allowed": TITLE_ALLOWED_FIELDS,
        "children": {
            "textStyle": ("object", "text_style"),
            "subtextStyle": ("object", "text_style"),
        },
    },
    "legend": {
        "label": "legend", "allowed": LEGEND_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "selected": ("wildcard_scalars", None),
            "textStyle": ("object", "text_style"),
            "tooltip": ("object", "tooltip"),
            "data": ("mixed_array_objects", "legend_data_item"),
            "pageIcons": ("object", "page_icons"),
            "pageTextStyle": ("object", "text_style"),
            "emphasis": ("object", "state"),
            "selector": ("mixed_array_objects", "legend_selector_item"),
            "selectorLabel": ("object", "label"),
        },
    },
    "legend_data_item": {
        "label": "legend.data item", "allowed": LEGEND_DATA_ITEM_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "textStyle": ("object", "text_style"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "legend_selector_item": {
        "label": "legend.selector item", "allowed": LEGEND_SELECTOR_ITEM_ALLOWED_FIELDS,
        "children": {},
    },
    "page_icons": {
        "label": "legend.pageIcons", "allowed": {"horizontal", "vertical"}, "children": {},
    },
    "grid": {
        "label": "grid", "allowed": GRID_ALLOWED_FIELDS,
        "children": {"tooltip": ("object", "tooltip")},
    },
    "calendar": {
        "label": "calendar", "allowed": CALENDAR_ALLOWED_FIELDS,
        "children": {
            "splitLine": ("object", "split_line"),
            "itemStyle": ("object", "item_style"),
            "dayLabel": ("object", "calendar.dayLabel"),
            "monthLabel": ("object", "calendar.monthLabel"),
            "yearLabel": ("object", "calendar.yearLabel"),
        },
    },
    "calendar.dayLabel": {
        "label": "calendar.dayLabel", "allowed": CALENDAR_LABEL_ALLOWED_FIELDS, "children": {},
    },
    "calendar.monthLabel": {
        "label": "calendar.monthLabel", "allowed": CALENDAR_LABEL_ALLOWED_FIELDS, "children": {},
    },
    "calendar.yearLabel": {
        "label": "calendar.yearLabel", "allowed": CALENDAR_LABEL_ALLOWED_FIELDS, "children": {},
    },
    "radar": {
        "label": "radar", "allowed": RADAR_ALLOWED_FIELDS,
        "children": {
            "axisLine": ("object", "radar.axisLine"),
            "axisTick": ("object", "axis_tick"),
            "axisLabel": ("object", "label"),
            "splitLine": ("object", "split_line"),
            "splitArea": ("object", "split_area"),
            "indicator": ("array_objects", "radar_indicator"),
        },
    },
    "radar.axisLine": {
        "label": "radar.axisLine", "allowed": AXIS_LINE_ALLOWED_FIELDS,
        "children": {"lineStyle": ("object", "line_style")},
    },
    "radar_indicator": {
        "label": "radar.indicator item", "allowed": RADAR_INDICATOR_ALLOWED_FIELDS, "children": {},
    },
    "polar": {
        "label": "polar", "allowed": POLAR_ALLOWED_FIELDS,
        "children": {"tooltip": ("object", "tooltip")},
    },
    "geo": {
        "label": "geo", "allowed": GEO_ALLOWED_FIELDS,
        "children": {
            "scaleLimit": ("object", "scale_limit"),
            "nameMap": ("wildcard_scalars", None),
            "label": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "emphasis": ("object", "state"),
            "select": ("object", "state"),
            "blur": ("object", "state"),
            "regions": ("array_objects", "geo.region"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "geo.region": {
        "label": "geo.region", "allowed": GEO_REGION_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "emphasis": ("object", "state"),
            "select": ("object", "state"),
            "blur": ("object", "state"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "parallel": {
        "label": "parallel", "allowed": PARALLEL_ALLOWED_FIELDS,
        "children": {"parallelAxisDefault": ("object", "parallel.axis")},
    },
    "parallel.axis": {
        "label": "parallel.axis", "allowed": AXIS_ALLOWED_FIELDS,
        "children": {
            "nameTextStyle": ("object", "text_style"),
            "axisLine": ("object", "axis_line"),
            "axisTick": ("object", "axis_tick"),
            "minorTick": ("object", "axis_tick"),
            "axisLabel": ("object", "label"),
            "splitLine": ("object", "split_line"),
            "minorSplitLine": ("object", "split_line"),
            "splitArea": ("object", "split_area"),
            "axisPointer": ("object", "axis_pointer"),
            "tooltip": ("object", "tooltip"),
            "areaSelectStyle": ("object", "area_select_style"),
            "data": ("mixed_array_objects", "axis_data_item"),
        },
    },
    "axis": {
        "label": "axis", "allowed": AXIS_ALLOWED_FIELDS,
        "children": {
            "nameTextStyle": ("object", "text_style"),
            "axisLine": ("object", "axis_line"),
            "axisTick": ("object", "axis_tick"),
            "minorTick": ("object", "axis_tick"),
            "axisLabel": ("object", "label"),
            "splitLine": ("object", "split_line"),
            "minorSplitLine": ("object", "split_line"),
            "splitArea": ("object", "split_area"),
            "axisPointer": ("object", "axis_pointer"),
            "tooltip": ("object", "tooltip"),
            "areaSelectStyle": ("object", "area_select_style"),
            "data": ("mixed_array_objects", "axis_data_item"),
        },
    },
    "single_axis": {
        "label": "singleAxis", "allowed": SINGLE_AXIS_ALLOWED_FIELDS,
        "children": {
            "nameTextStyle": ("object", "text_style"),
            "axisLine": ("object", "axis_line"),
            "axisTick": ("object", "axis_tick"),
            "minorTick": ("object", "axis_tick"),
            "axisLabel": ("object", "label"),
            "splitLine": ("object", "split_line"),
            "minorSplitLine": ("object", "split_line"),
            "splitArea": ("object", "split_area"),
            "axisPointer": ("object", "axis_pointer"),
            "tooltip": ("object", "tooltip"),
            "areaSelectStyle": ("object", "area_select_style"),
            "data": ("mixed_array_objects", "axis_data_item"),
        },
    },
    "axis_data_item": {
        "label": "axis.data item", "allowed": AXIS_DATA_ITEM_ALLOWED_FIELDS,
        "children": {"textStyle": ("object", "text_style")},
    },
    "axis_line": {
        "label": "axisLine", "allowed": AXIS_LINE_ALLOWED_FIELDS,
        "children": {"lineStyle": ("object", "line_style")},
    },
    "axis_tick": {
        "label": "axisTick", "allowed": AXIS_TICK_ALLOWED_FIELDS,
        "children": {"lineStyle": ("object", "line_style")},
    },
    "split_line": {
        "label": "splitLine", "allowed": SPLIT_LINE_ALLOWED_FIELDS,
        "children": {"lineStyle": ("object", "line_style")},
    },
    "split_area": {
        "label": "splitArea", "allowed": SPLIT_AREA_ALLOWED_FIELDS,
        "children": {"areaStyle": ("object", "area_style")},
    },
    "area_select_style": {
        "label": "areaSelectStyle", "allowed": AREA_SELECT_STYLE_ALLOWED_FIELDS, "children": {},
    },
    "axis_pointer": {
        "label": "axisPointer", "allowed": AXIS_POINTER_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "axisPointer.label"),
            "lineStyle": ("object", "line_style"),
            "shadowStyle": ("object", "area_style"),
            "link": ("array_objects", "axis_pointer_link"),
        },
    },
    "axisPointer.label": {
        "label": "axisPointer.label", "allowed": AXIS_POINTER_LABEL_ALLOWED_FIELDS,
        "children": {"rich": ("wildcard_objects", "text_style")},
    },
    "axis_pointer_link": {
        "label": "axisPointer.link item", "allowed": AXIS_POINTER_LINK_ALLOWED_FIELDS, "children": {},
    },
    "aria": {
        "label": "aria", "allowed": ARIA_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "aria.label"),
            "decal": ("object", "aria_decal"),
        },
    },
    "aria.label": {
        "label": "aria.label", "allowed": ARIA_LABEL_ALLOWED_FIELDS,
        "children": {
            "general": ("object", "aria_general"),
            "series": ("object", "aria_series"),
            "data": ("object", "aria_data"),
        },
    },
    "aria_general": {
        "label": "aria.label.general", "allowed": ARIA_GENERAL_ALLOWED_FIELDS, "children": {},
    },
    "aria_series": {
        "label": "aria.label.series", "allowed": ARIA_SERIES_ALLOWED_FIELDS,
        "children": {
            "single": ("object", "aria_series_single"),
            "multiple": ("object", "aria_series_multiple"),
        },
    },
    "aria_series_single": {
        "label": "aria.label.series.single", "allowed": ARIA_SERIES_SINGLE_ALLOWED_FIELDS,
        "children": {},
    },
    "aria_series_multiple": {
        "label": "aria.label.series.multiple", "allowed": ARIA_SERIES_MULTIPLE_ALLOWED_FIELDS,
        "children": {},
    },
    "aria_data": {
        "label": "aria.label.data", "allowed": ARIA_DATA_ALLOWED_FIELDS, "children": {},
    },
    "aria_decal": {
        "label": "aria.decal", "allowed": ARIA_DECAL_ALLOWED_FIELDS,
        "children": {"decals": ("array_objects", "decal")},
    },
    "visual_map": {
        "label": "visualMap", "allowed": VISUAL_MAP_ALLOWED_FIELDS,
        "children": {
            "inRange": ("object", "visual_map_channels"),
            "outOfRange": ("object", "visual_map_channels"),
            "controller": ("object", "visual_map_controller"),
            "pieces": ("array_objects", "visual_map_piece"),
            "selected": ("wildcard_scalars", None),
            "textStyle": ("object", "text_style"),
        },
    },
    "visual_map_channels": {
        "label": "visualMap channel", "allowed": VISUAL_MAP_STATIC_CHANNELS, "children": {},
    },
    "visual_map_controller": {
        "label": "visualMap.controller", "allowed": VISUAL_MAP_CONTROLLER_ALLOWED_FIELDS,
        "children": {
            "inRange": ("object", "visual_map_channels"),
            "outOfRange": ("object", "visual_map_channels"),
        },
    },
    "visual_map_piece": {
        "label": "visualMap.piece", "allowed": VISUAL_MAP_PIECE_ALLOWED_FIELDS, "children": {},
    },
    "tooltip": {
        "label": "tooltip", "allowed": TOOLTIP_ALLOWED_FIELDS,
        "children": {
            "axisPointer": ("object", "tooltip_axis_pointer"),
            "textStyle": ("object", "text_style"),
        },
    },
    "tooltip_axis_pointer": {
        "label": "tooltip.axisPointer", "allowed": TOOLTIP_AXIS_POINTER_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "axisPointer.label"),
            "lineStyle": ("object", "line_style"),
            "shadowStyle": ("object", "area_style"),
            "crossStyle": ("object", "line_style"),
        },
    },
    "text_style": {
        "label": "textStyle", "allowed": TEXT_STYLE_ALLOWED_FIELDS,
        "children": {"rich": ("wildcard_objects", "text_style")},
    },
    "label": {
        "label": "label", "allowed": LABEL_ALLOWED_FIELDS,
        "children": {"rich": ("wildcard_objects", "text_style")},
    },
    "item_style": {
        "label": "itemStyle", "allowed": ITEM_STYLE_ALLOWED_FIELDS,
        "children": {"decal": ("object", "decal")},
    },
    "decal": {
        "label": "decal", "allowed": DECAL_ALLOWED_FIELDS, "children": {},
    },
    "line_style": {
        "label": "lineStyle", "allowed": LINE_STYLE_ALLOWED_FIELDS, "children": {},
    },
    "area_style": {
        "label": "areaStyle", "allowed": AREA_STYLE_ALLOWED_FIELDS, "children": {},
    },
    "label_line": {
        "label": "labelLine", "allowed": LABEL_LINE_ALLOWED_FIELDS,
        "children": {"lineStyle": ("object", "line_style")},
    },
    "state": {
        "label": "state", "allowed": STATE_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "label"),
            "endLabel": ("object", "label"),
            "upperLabel": ("object", "label"),
            "edgeLabel": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "areaStyle": ("object", "area_style"),
            "labelLine": ("object", "label_line"),
        },
    },
    "state_animation": {
        "label": "stateAnimation", "allowed": STATE_ANIMATION_ALLOWED_FIELDS, "children": {},
    },
    "dataset": {
        "label": "dataset", "allowed": DATASET_ALLOWED_FIELDS,
        "children": {
            "source": ("special", None),
            "dimensions": ("string_or_objects", "dataset.dimension"),
        },
    },
    "dataset.dimension": {
        "label": "dataset.dimension", "allowed": DATASET_DIMENSION_ALLOWED_FIELDS,
        "children": {},
    },
    "series": {
        "label": "series", "allowed": SERIES_ALLOWED_FIELDS,
        "children": {
            "data": ("special", None),
            "nodes": ("special", None),
            "links": ("special", None),
            "edges": ("special", None),
            "categories": ("special", None),
            "encode": ("special", None),
            "dimensions": ("string_or_objects", "series.dimension"),
            "markPoint": ("object", "mark_component"),
            "markLine": ("object", "mark_component"),
            "markArea": ("object", "mark_component"),
            "label": ("object", "label"),
            "endLabel": ("object", "label"),
            "upperLabel": ("object", "label"),
            "edgeLabel": ("object", "label"),
            "detail": ("object", "label"),
            "title": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "backgroundStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "areaStyle": ("object", "area_style"),
            "labelLine": ("object", "label_line"),
            "tooltip": ("object", "tooltip"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
            "universalTransition": ("object", "universal_transition"),
            "force": ("object", "force"),
            "circular": ("object", "circular"),
            "leaves": ("object", "series_leaves"),
            "breadcrumb": ("object", "breadcrumb"),
            "levels": ("array_objects", "series_level"),
            "progress": ("object", "progress"),
            "axisLine": ("object", "axis_line"),
            "splitLine": ("object", "split_line"),
            "axisTick": ("object", "axis_tick"),
            "axisLabel": ("object", "label"),
            "pointer": ("object", "pointer"),
            "anchor": ("object", "anchor"),
            "effect": ("object", "effect"),
            "scaleLimit": ("object", "scale_limit"),
            "nameMap": ("wildcard_scalars", None),
            "labelLayout": ("object", "label_layout"),
        },
    },
    "mark_component": {
        "label": "mark component", "allowed": MARK_COMPONENT_ALLOWED_FIELDS,
        "children": {
            "data": ("special", None),
            "label": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
        },
    },
    "series.dimension": {
        "label": "series.dimension", "allowed": DATASET_DIMENSION_ALLOWED_FIELDS,
        "children": {},
    },
    "direct_data_item": {
        "label": "data item", "allowed": DIRECT_DATA_ITEM_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "areaStyle": ("object", "area_style"),
            "label": ("object", "label"),
            "labelLine": ("object", "label_line"),
            "endLabel": ("object", "label"),
            "title": ("object", "label"),
            "detail": ("object", "label"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "graph_node": {
        "label": "graph node", "allowed": GRAPH_NODE_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "label": ("object", "label"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "graph_link": {
        "label": "graph link", "allowed": GRAPH_LINK_ALLOWED_FIELDS,
        "children": {
            "lineStyle": ("object", "line_style"),
            "label": ("object", "label"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
        },
    },
    "graph_category": {
        "label": "graph category", "allowed": GRAPH_CATEGORY_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "label": ("object", "label"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "hierarchy_node": {
        "label": "hierarchy node", "allowed": HIERARCHY_NODE_ALLOWED_FIELDS,
        "children": {
            "children": ("special", None),
            "itemStyle": ("object", "item_style"),
            "lineStyle": ("object", "line_style"),
            "areaStyle": ("object", "area_style"),
            "label": ("object", "label"),
            "upperLabel": ("object", "label"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
            "tooltip": ("object", "tooltip"),
        },
    },
    "lines_data_item": {
        "label": "lines data item", "allowed": LINES_DATA_ITEM_ALLOWED_FIELDS,
        "children": {
            "coords": ("special", None),
            "lineStyle": ("object", "line_style"),
            "label": ("object", "label"),
            "effect": ("object", "effect"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
        },
    },
    "universal_transition": {
        "label": "universalTransition", "allowed": UNIVERSAL_TRANSITION_ALLOWED_FIELDS,
        "children": {},
    },
    "force": {"label": "force", "allowed": FORCE_ALLOWED_FIELDS, "children": {}},
    "circular": {"label": "circular", "allowed": CIRCULAR_ALLOWED_FIELDS, "children": {}},
    "scale_limit": {"label": "scaleLimit", "allowed": SCALE_LIMIT_ALLOWED_FIELDS, "children": {}},
    "effect": {"label": "effect", "allowed": EFFECT_ALLOWED_FIELDS, "children": {}},
    "pointer": {
        "label": "pointer", "allowed": POINTER_ALLOWED_FIELDS,
        "children": {"itemStyle": ("object", "item_style")},
    },
    "anchor": {
        "label": "anchor", "allowed": ANCHOR_ALLOWED_FIELDS,
        "children": {"itemStyle": ("object", "item_style")},
    },
    "progress": {
        "label": "progress", "allowed": PROGRESS_ALLOWED_FIELDS,
        "children": {"itemStyle": ("object", "item_style")},
    },
    "breadcrumb": {
        "label": "breadcrumb", "allowed": BREADCRUMB_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "emphasis": ("object", "state"),
        },
    },
    "series_level": {
        "label": "series.level", "allowed": SERIES_LEVEL_ALLOWED_FIELDS,
        "children": {
            "itemStyle": ("object", "item_style"),
            "upperLabel": ("object", "label"),
        },
    },
    "series_leaves": {
        "label": "series.leaves", "allowed": SERIES_LEAVES_ALLOWED_FIELDS,
        "children": {
            "label": ("object", "label"),
            "itemStyle": ("object", "item_style"),
            "emphasis": ("object", "state"),
            "blur": ("object", "state"),
            "select": ("object", "state"),
        },
    },
    "label_layout": {
        "label": "labelLayout",
        "allowed": {
            "hideOverlap", "moveOverlap", "x", "y", "dx", "dy", "rotate",
            "width", "height", "fontSize", "labelLinePoints", "draggable",
        },
        "children": {},
    },
}
FORMATTER_PLACEHOLDER_RE = re.compile(
    r"\{(?:[abcd]|name|value2?|@(?:\[(?:0|[1-9][0-9]*)\]|[^{}\s]+))\}"
)
FORMATTER_PLACEHOLDERS_BY_KIND = {
    "axis_label": {"value"},
    "legend": {"name"},
    "visualMap": {"value", "value2"},
    "series_label": {"a", "b", "c", "d", "value"},
    "series_end_label": {"a", "b", "c", "d", "value"},
    "mark_label": {"a", "b", "c", "d", "value"},
    "gauge_detail": {"value"},
    "gauge_axis_label": {"value"},
    "tooltip": {"a", "b", "c", "d", "name", "value", "value2"},
}
SERIES_ONLY_SURFACES = {"data", "nodes", "links", "edges", "categories"}
URL_RE = re.compile(r"(?:https?:|//|data:|blob:|javascript:|file:)", re.IGNORECASE)
REMOTE_SCHEME_RE = re.compile(r"^(?:https?|ftp|ftps|sftp|ws|wss|data|blob|file|javascript):", re.IGNORECASE)
FUNCTION_RE = re.compile(
    r"(?:\b(?:async\s+)?function\s*\*?\s*(?:[A-Za-z_$][\w$]*\s*)?\(|=>|"
    r"\bnew\s+Function\b|\b(?:eval|setTimeout|setInterval|require|import)\s*\(|"
    r"(?:^|[;{}])\s*(?:return|throw)\b[^;{}]*(?:;|})|"
    r"(?:^|[;{}])\s*(?:if|for|while|switch|catch)\s*\(|"
    r"(?:^|[;{}])\s*(?:var|let|const)\s+[A-Za-z_$])",
    re.IGNORECASE | re.DOTALL,
)
RESOURCE_RE = re.compile(r"(?:^|[/\\])[^/\\]+\.(?:png|jpe?g|gif|webp|svg|json|js|css|woff2?|ttf|otf)(?:[?#]|$)", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ATTRIBUTE_URL_RE = re.compile(r"url\s*\(", re.IGNORECASE)
RESOURCE_ATTRIBUTES = {
    "src", "srcset", "poster", "background", "formaction", "action", "ping",
    "cite", "manifest", "data", "codebase", "archive", "longdesc", "profile",
}
GL_VALUE_RE = re.compile(r"(?:3d|gl)$", re.IGNORECASE)
JS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
JS_LINE_COMMENT_RE = re.compile(r"//[^\r\n]*")
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
EXECUTABLE_SENSITIVE_KEYS = {
    "formatter", "labelLayout", "symbolSize", "symbolRotate", "position",
    "sort", "min", "max", "color",
}

def walk_echarts(value: Any, path: str = "echarts.option") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "public_projection":
                fail(f"public_projection is forbidden at {child_path}")
            if key == "renderItem":
                fail(f"renderItem is forbidden at {child_path}")
            if key == "graphic":
                fail("ECharts graphic is forbidden")
            if is_gl_surface_name(key):
                fail(f"ECharts GL component {key} is forbidden")
            if key.lower() in {"onclick", "ondblclick", "onmouseover", "onmouseout", "onmousemove", "onmousedown", "onmouseup", "globalout", "contextmenu", "$action"}:
                fail(f"ECharts events or executable actions are forbidden at {child_path}")
            walk_echarts(child, child_path)
    elif isinstance(value, list):
        if len(value) > 1000:
            fail(f"ECharts arrays must contain at most 1000 items at {path}")
        for index, child in enumerate(value):
            walk_echarts(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if value.startswith(("/", "./", "../", "image://", "path://")) or (
            RESOURCE_RE.search(value) and not URL_RE.search(value) and not REMOTE_SCHEME_RE.search(value)
        ):
            fail(f"ECharts resource string is forbidden at {path}")
        if URL_RE.search(value) or REMOTE_SCHEME_RE.search(value):
            fail(f"remote or executable URL is forbidden at {path}")
        executable_view = normalize_executable_string(value)
        option_key = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if FUNCTION_RE.search(executable_view) or (
            option_key in EXECUTABLE_SENSITIVE_KEYS
            and re.search(r"\byield\b", executable_view, re.IGNORECASE)
        ):
            fail(f"executable or function-like string is forbidden at {path}")
        stripped = value.strip()
        if stripped.lower() == "globe" or GL_VALUE_RE.search(stripped):
            if path.endswith(".type") and stripped in GL_SERIES:
                fail("ECharts GL series type is forbidden")
            fail(f"ECharts GL-bearing string {value} is forbidden")
    elif isinstance(value, float) and not math.isfinite(value):
        fail(f"non-finite ECharts number is forbidden at {path}")


def pointer_contains(parent: str, child: str) -> bool:
    return parent == child or parent == "" or child.startswith(parent + "/")


def component_objects(option: dict[str, Any], name: str) -> list[tuple[str, dict[str, Any]]]:
    value = option.get(name)
    if isinstance(value, dict):
        return [(f"/{name}", value)]
    if isinstance(value, list):
        return [
            (f"/{name}/{index}", item)
            for index, item in enumerate(value)
            if isinstance(item, dict)
        ]
    return []


def strict_component_objects(
    option: dict[str, Any], name: str, *, allow_array: bool = True
) -> list[tuple[str, dict[str, Any]]]:
    if name not in option:
        return []
    value = option[name]
    if isinstance(value, dict):
        return [(f"/{name}", value)]
    if allow_array and isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return [(f"/{name}/{index}", item) for index, item in enumerate(value)]
    expected = "an object or array of objects" if allow_array else "an object"
    fail(f"ECharts {name} must be {expected}")


def validate_allowed_fields(value: Any, allowed: set[str], label: str, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"ECharts {label} {path} must be an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        fail(f"ECharts {label} {path} contains unknown field {unknown[0]}")
    return value


def escape_json_pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def profile_pointer(parent: str, field: str) -> str:
    token = escape_json_pointer_token(field)
    return f"{parent}/{token}" if parent else f"/{token}"


def consume_echarts_profile_node(
    budget: dict[str, int], path: str, depth: int
) -> None:
    if depth > ECHARTS_PROFILE_MAX_DEPTH:
        fail(f"ECharts recursive option profile exceeds maximum depth at {path or '/'}")
    budget["nodes"] += 1
    if budget["nodes"] > ECHARTS_PROFILE_NODE_BUDGET:
        fail(f"ECharts recursive option profile exceeds node budget at {path or '/'}")


def traverse_delegated_echarts_value(
    value: Any, path: str, budget: dict[str, int], depth: int
) -> None:
    consume_echarts_profile_node(budget, path, depth)
    if isinstance(value, dict):
        for key, child in value.items():
            traverse_delegated_echarts_value(
                child, profile_pointer(path, key), budget, depth + 1
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            traverse_delegated_echarts_value(
                child, f"{path}/{index}", budget, depth + 1
            )


def validate_unprofiled_echarts_value(
    value: Any, label: str, path: str, budget: dict[str, int], depth: int
) -> None:
    consume_echarts_profile_node(budget, path, depth)
    if isinstance(value, dict):
        fail(f"ECharts {label} {path} has unsupported nested object")
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_unprofiled_echarts_value(
                child, label, f"{path}/{index}", budget, depth + 1
            )


def validate_echarts_profile(
    value: Any,
    profile_name: str,
    path: str,
    *,
    budget: dict[str, int] | None = None,
    depth: int = 0,
    label_override: str | None = None,
    close_option: bool = True,
) -> None:
    if budget is None:
        budget = {"nodes": 0}
    consume_echarts_profile_node(budget, path, depth)
    profile = ECHARTS_COMPONENT_PROFILES[profile_name]
    label = label_override or str(profile["label"])
    if not isinstance(value, dict):
        fail(f"ECharts {label} {path} must be an object")
    if profile_name != "option" or close_option:
        patterns = tuple(profile.get("allowed_key_patterns", ()))
        unknown = sorted(
            key for key in value
            if key not in profile["allowed"]
            and not any(re.fullmatch(pattern, key) for pattern in patterns)
        )
        if unknown:
            if profile_name == "option":
                fail(f"echarts.option contains unknown field {unknown[0]}")
            if profile_name == "series" and re.fullmatch(r"/series/[0-9]+", path):
                series_index = path.rsplit("/", 1)[-1]
                fail(f"echarts.option.series[{series_index}] contains unknown field {unknown[0]}")
            fail(f"ECharts {label} {path} contains unknown field {unknown[0]}")
    children: dict[str, tuple[str, str | None]] = profile["children"]
    for field, child in value.items():
        child_path = profile_pointer(path, field)
        rule = children.get(field)
        if rule is None:
            if profile_name == "option" and field not in profile["allowed"] and not close_option:
                traverse_delegated_echarts_value(child, child_path, budget, depth + 1)
                continue
            validate_unprofiled_echarts_value(
                child, label, child_path, budget, depth + 1
            )
            continue
        kind, target = rule
        child_label = (
            field if profile_name == "option" else str(ECHARTS_COMPONENT_PROFILES[target]["label"])
        ) if target is not None else field
        if target == "mark_component":
            child_label = field
        shape_label = field if profile_name == "option" else f"{label}.{field}"
        shape_path = "" if profile_name == "option" else f" {child_path}"
        if kind == "object":
            if not isinstance(child, dict):
                fail(f"ECharts {shape_label}{shape_path} must be an object")
            validate_echarts_profile(
                child, str(target), child_path, budget=budget, depth=depth + 1,
                label_override=child_label,
            )
        elif kind == "object_or_array":
            if isinstance(child, dict):
                items = [(child_path, child)]
            elif isinstance(child, list) and child and all(isinstance(item, dict) for item in child):
                consume_echarts_profile_node(budget, child_path, depth + 1)
                items = [(f"{child_path}/{index}", item) for index, item in enumerate(child)]
            else:
                fail(f"ECharts {shape_label} must be an object or array of objects")
            for item_path, item in items:
                validate_echarts_profile(
                    item, str(target), item_path, budget=budget, depth=depth + 1,
                    label_override=child_label,
                )
        elif kind in {"array_objects", "mixed_array_objects", "string_or_objects"}:
            if not isinstance(child, list) or (
                kind == "array_objects" and any(not isinstance(item, dict) for item in child)
            ):
                fail(f"ECharts {shape_label} {child_path} must be an array of objects")
            consume_echarts_profile_node(budget, child_path, depth + 1)
            for index, item in enumerate(child):
                item_path = f"{child_path}/{index}"
                if isinstance(item, dict):
                    validate_echarts_profile(
                        item, str(target), item_path, budget=budget, depth=depth + 2,
                        label_override=child_label,
                    )
                elif kind == "string_or_objects" and isinstance(item, str) and item:
                    consume_echarts_profile_node(budget, item_path, depth + 2)
                elif kind == "mixed_array_objects" and not isinstance(item, list):
                    consume_echarts_profile_node(budget, item_path, depth + 2)
                else:
                    expected_items = (
                        "non-empty strings or objects"
                        if kind == "string_or_objects"
                        else "objects or scalar items"
                    )
                    fail(f"ECharts {shape_label} {child_path} must contain {expected_items}")
        elif kind == "wildcard_objects":
            if not isinstance(child, dict):
                fail(f"ECharts {shape_label} {child_path} must be an object map")
            consume_echarts_profile_node(budget, child_path, depth + 1)
            for dynamic_key, item in child.items():
                item_path = profile_pointer(child_path, dynamic_key)
                if not dynamic_key or not isinstance(item, dict):
                    fail(f"ECharts {shape_label} {child_path} must map names to objects")
                validate_echarts_profile(
                    item, str(target), item_path, budget=budget, depth=depth + 2,
                    label_override=child_label,
                )
        elif kind == "wildcard_scalars":
            if not isinstance(child, dict):
                fail(f"ECharts {label} {child_path} must be an object map")
            consume_echarts_profile_node(budget, child_path, depth + 1)
            for dynamic_key, item in child.items():
                item_path = profile_pointer(child_path, dynamic_key)
                if not dynamic_key or isinstance(item, (dict, list)):
                    fail(f"ECharts {label} {child_path} must map names to scalar values")
                consume_echarts_profile_node(budget, item_path, depth + 2)
        elif kind in {"delegated", "special"}:
            traverse_delegated_echarts_value(child, child_path, budget, depth + 1)
        else:
            raise AssertionError(f"unknown ECharts profile child kind {kind}")


def validate_nested_style_components(container: dict[str, Any], pointer: str) -> None:
    child_profiles = {
        "itemStyle": "item_style",
        "lineStyle": "line_style",
        "areaStyle": "area_style",
        "label": "label",
        "endLabel": "label",
        "axisLabel": "label",
        "detail": "label",
        "tooltip": "tooltip",
        "emphasis": "state",
        "blur": "state",
        "select": "state",
    }
    budget = {"nodes": 0}
    for field, profile_name in child_profiles.items():
        if field not in container:
            continue
        child_path = profile_pointer(pointer, field)
        validate_echarts_profile(
            container[field], profile_name, child_path, budget=budget,
            label_override=field,
        )


def validate_known_echarts_components(option: dict[str, Any]) -> None:
    validate_echarts_profile(option, "option", "", close_option=False)


def validate_closed_echarts_components(option: dict[str, Any]) -> None:
    unknown = sorted(set(option) - OPTION_ALLOWED_FIELDS)
    if unknown:
        fail(f"echarts.option contains unknown field {unknown[0]}")
