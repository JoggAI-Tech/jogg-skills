"""ECharts source truth, series semantics, formatters, marks, and bindings."""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any

from .contracts import *
from .echarts_profiles import *
from .shared import (
    decode_json_pointer_token,
    json_leaf_pointers,
    normalize_text,
    resolve_json_pointer,
)

def echarts_dataset_layout(
    dataset: dict[str, Any],
    base: str,
    series_layout_by: str = "column",
) -> tuple[list[str | None], dict[int, list[str]]] | None:
    unknown_fields = sorted(set(dataset) - DATASET_ALLOWED_FIELDS)
    if unknown_fields:
        fail(f"ECharts dataset {base} contains unknown field {unknown_fields[0]}")
    source = dataset.get("source")
    names: list[str | None]
    leaves_by_dimension: dict[int, list[str]] = {}
    if isinstance(source, list):
        if not source:
            return None
        if all(isinstance(row, dict) for row in source):
            names = list(source[0])
            if not names or any(not isinstance(name, str) or not name for name in names):
                return None
            if any(set(row) != set(names) for row in source):
                return None
            for dimension_index, name in enumerate(names):
                escaped = escape_json_pointer_token(name)
                leaves_by_dimension[dimension_index] = [
                    f"{base}/source/{row_index}/{escaped}"
                    for row_index in range(len(source))
                ]
        else:
            if not all(isinstance(row, list) and row for row in source):
                return None
            column_count = len(source[0])
            if column_count <= 0 or any(len(row) != column_count for row in source):
                return None
            source_header = dataset.get("sourceHeader")
            if series_layout_by not in {"column", "row"}:
                fail(f"ECharts seriesLayoutBy {series_layout_by} is unsupported")
            first_dimension_values = source[0] if series_layout_by == "column" else [row[0] for row in source]
            has_header = source_header is True or (
                source_header is None
                and all(isinstance(item, str) and item for item in first_dimension_values)
            )
            if has_header:
                if (len(source) < 2 or column_count < 2
                        or not all(isinstance(item, str) and item for item in first_dimension_values)):
                    return None
                names = list(first_dimension_values)
                if len(set(names)) != len(names):
                    return None
            elif source_header is not None and source_header is not False:
                return None
            else:
                names = [None] * (column_count if series_layout_by == "column" else len(source))
            if series_layout_by == "column":
                for dimension_index in range(column_count):
                    leaves_by_dimension[dimension_index] = [
                        f"{base}/source/{row_index}/{dimension_index}"
                        for row_index in range(len(source))
                    ]
            else:
                for dimension_index in range(len(source)):
                    leaves_by_dimension[dimension_index] = [
                        f"{base}/source/{dimension_index}/{column_index}"
                        for column_index in range(column_count)
                    ]
    elif isinstance(source, dict) and source:
        if not all(isinstance(key, str) and key and isinstance(column, list) and column for key, column in source.items()):
            return None
        column_lengths = {len(column) for column in source.values()}
        if len(column_lengths) != 1:
            return None
        names = list(source)
        for dimension_index, name in enumerate(names):
            escaped = escape_json_pointer_token(name)
            leaves_by_dimension[dimension_index] = [
                f"{base}/source/{escaped}/{item_index}"
                for item_index in range(len(source[name]))
            ]
    else:
        return None
    explicit_dimensions = dataset.get("dimensions")
    if explicit_dimensions is not None:
        if not isinstance(explicit_dimensions, list) or not explicit_dimensions:
            return None
        explicit_names: list[str] = []
        for dimension_index, dimension in enumerate(explicit_dimensions):
            if isinstance(dimension, str) and dimension:
                explicit_names.append(dimension)
            elif isinstance(dimension, dict) and isinstance(dimension.get("name"), str) and dimension["name"]:
                unknown_dimension_fields = sorted(set(dimension) - DATASET_DIMENSION_ALLOWED_FIELDS)
                if unknown_dimension_fields:
                    fail(
                        f"ECharts dataset {base} dimensions[{dimension_index}] contains unknown field "
                        f"{unknown_dimension_fields[0]}"
                    )
                explicit_names.append(dimension["name"])
            else:
                return None
        if len(set(explicit_names)) != len(explicit_names) or len(explicit_names) != len(names):
            return None
        inferred_names = [name for name in names if name is not None]
        if inferred_names and inferred_names != explicit_names:
            return None
        names = explicit_names
    return names, leaves_by_dimension


def static_echarts_encode_dimensions(
    value: Any,
    dataset_layout: tuple[list[str | None], dict[int, list[str]]],
    series: dict[str, Any],
) -> set[int] | None:
    if not isinstance(value, dict) or not value:
        return None
    dimension_names, _leaves = dataset_layout
    dimension_count = len(dimension_names)
    series_type = str(series["type"])
    coordinate_system = series.get("coordinateSystem", DEFAULT_COORDINATE_SYSTEM[series_type])
    if not isinstance(coordinate_system, str) or not coordinate_system:
        fail(f"ECharts coordinateSystem for {series_type} dataset encoding must be a non-empty string")
    coordinate_channels = STATIC_ENCODE_CHANNELS[series_type].get(coordinate_system)
    if coordinate_channels is None:
        fail(f"ECharts coordinateSystem {coordinate_system} is not supported for {series_type} dataset encoding")

    def dimension_index(dimension: Any) -> int | None:
        if isinstance(dimension, str) and dimension in dimension_names:
            return dimension_names.index(dimension)
        if type(dimension) is int and 0 <= dimension < dimension_count:
            return dimension
        return None

    consumed_dimensions: set[int] = set()
    for channel, dimension in value.items():
        if not isinstance(channel, str) or not channel:
            return None
        if channel in INTERACTION_ONLY_ENCODE_CHANNELS:
            fail(f"ECharts encode channel {channel} is interaction-only and cannot prove static rendering")
        parallel_channel = (
            series_type == "parallel"
            and re.fullmatch(r"dim(?:0|[1-9][0-9]*)", channel) is not None
        )
        if channel not in coordinate_channels and not parallel_channel:
            fail(f"ECharts encode channel {channel} is not statically rendered for {series_type}")
        dimensions = dimension if isinstance(dimension, list) else [dimension]
        if not dimensions:
            return None
        required_count: int | None = 1
        if series_type == "candlestick" and channel == "y":
            required_count = 4
        elif series_type == "boxplot" and channel == "y":
            required_count = 5
        elif series_type == "radar" and channel == "value":
            required_count = None
        if required_count is not None and len(dimensions) != required_count:
            fail(
                f"ECharts encode channel {channel} for {series_type} requires exactly "
                f"{required_count} dimension{'s' if required_count != 1 else ''}"
            )
        resolved = [dimension_index(item) for item in dimensions]
        if any(index is None for index in resolved):
            return None
        consumed_dimensions.update(index for index in resolved if index is not None)
    return consumed_dimensions


def consumed_dataset_bases(
    option: dict[str, Any],
) -> tuple[set[str], set[str], dict[str, dict[str, Any]]]:
    raw_datasets = option.get("dataset")
    if isinstance(raw_datasets, dict):
        datasets = [(0, "/dataset", raw_datasets)]
    elif isinstance(raw_datasets, list):
        if not raw_datasets or any(not isinstance(dataset, dict) for dataset in raw_datasets):
            fail("ECharts dataset must be an object or a non-empty array of objects")
        datasets = [(index, f"/dataset/{index}", dataset) for index, dataset in enumerate(raw_datasets)]
    elif raw_datasets is not None:
        fail("ECharts dataset must be an object or a non-empty array of objects")
    else:
        datasets = []
    all_bases = {base for _index, base, _dataset in datasets}
    consumed: set[str] = set()
    visibility: dict[str, dict[str, Any]] = {}
    id_to_bases: dict[str, list[str]] = {}
    index_to_dataset = {index: (base, dataset) for index, base, dataset in datasets}
    for _index, base, dataset in datasets:
        dataset_id = dataset.get("id")
        if isinstance(dataset_id, str) and dataset_id:
            id_to_bases.setdefault(dataset_id, []).append(base)
    series = option.get("series")
    if not isinstance(series, list):
        return consumed, all_bases
    for series_index, item in enumerate(series):
        if not isinstance(item, dict) or "data" in item:
            continue
        series_type = item.get("type")
        if series_type not in DATASET_SERIES:
            continue
        has_index = "datasetIndex" in item
        has_id = "datasetId" in item
        if has_index == has_id:
            continue
        base: str | None = None
        if has_index:
            dataset_index = item["datasetIndex"]
            if type(dataset_index) is int and dataset_index in index_to_dataset:
                base = index_to_dataset[dataset_index][0]
        else:
            dataset_id = item["datasetId"]
            if isinstance(dataset_id, str) and len(id_to_bases.get(dataset_id, [])) == 1:
                base = id_to_bases[dataset_id][0]
        if base is None:
            continue
        dataset = next(value for _index, candidate, value in datasets if candidate == base)
        series_layout_by = item.get("seriesLayoutBy", "column")
        if not isinstance(series_layout_by, str) or series_layout_by not in {"column", "row"}:
            fail(f"ECharts seriesLayoutBy for series {series_index} must be column or row")
        layout = echarts_dataset_layout(dataset, base, series_layout_by)
        if layout is None:
            continue
        static_dimensions = static_echarts_encode_dimensions(item.get("encode"), layout, item)
        if static_dimensions is not None:
            consumed.add(base)
            if base not in visibility:
                visibility[base] = {
                    "dimension_names": layout[0],
                    "leaves_by_dimension": layout[1],
                    "static_dimensions": set(),
                    "series_indices": set(),
                    "series_layout_by": series_layout_by,
                }
            elif visibility[base]["series_layout_by"] != series_layout_by:
                fail(f"ECharts dataset {base} cannot mix column and row series layouts")
            visibility[base]["static_dimensions"].update(static_dimensions)
            visibility[base]["series_indices"].add(series_index)
    return consumed, all_bases, visibility


def valid_node_identity(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value)
    ) or (
        type(value) is int
    )


def validate_series_fields(series: dict[str, Any], path: str) -> None:
    unknown_fields = sorted(set(series) - SERIES_ALLOWED_FIELDS)
    if unknown_fields:
        fail(f"{path} contains unknown field {unknown_fields[0]}")


def validate_series_encode(
    series: dict[str, Any], series_type: str, pointer: str
) -> None:
    if "encode" not in series:
        return
    encode = series["encode"]
    if not isinstance(encode, dict):
        fail(f"ECharts encode {pointer}/encode must be an object")
    for channel, dimension in encode.items():
        if channel in INTERACTION_ONLY_ENCODE_CHANNELS:
            fail(f"ECharts encode channel {channel} is interaction-only and cannot prove static rendering")
        parallel_channel = (
            series_type == "parallel"
            and re.fullmatch(r"dim(?:0|[1-9][0-9]*)", channel) is not None
        )
        if channel not in ENCODE_ALLOWED_FIELDS and not parallel_channel:
            if "data" in series:
                fail(f"ECharts encode {pointer}/encode contains unknown field {channel}")
            fail(f"ECharts encode channel {channel} is not statically rendered for {series_type}")
        dimensions = dimension if isinstance(dimension, list) else [dimension]
        if not dimensions or any(isinstance(item, (dict, list)) for item in dimensions):
            fail(f"ECharts encode channel {channel} must contain scalar dimension references")


def validate_hierarchy_data(value: Any, path: str, pointer: str) -> None:
    if not isinstance(value, list):
        fail(f"{path} must be an array")
    for index, node in enumerate(value):
        node_path = f"{path}[{index}]"
        node_pointer = f"{pointer}/{index}"
        if not isinstance(node, dict):
            fail(f"{node_path} must be an object")
        validate_echarts_profile(
            node, "hierarchy_node", node_pointer, label_override="hierarchy node"
        )
        if not valid_node_identity(node.get("id")) and not valid_node_identity(node.get("name")):
            fail(f"{node_path} must have a stable id or name")
        if "children" in node:
            validate_hierarchy_data(
                node["children"], f"{node_path}.children", f"{node_pointer}/children"
            )


def validate_graph_series_shapes(
    series: dict[str, Any], series_type: str, path: str, pointer: str
) -> None:
    node_aliases = [field for field in ("data", "nodes") if field in series]
    if len(node_aliases) != 1:
        fail(f"ECharts {series_type} series must use exactly one of data or nodes")
    link_aliases = [field for field in ("links", "edges") if field in series]
    if len(link_aliases) > 1:
        fail(f"ECharts {series_type} series must use at most one of links or edges")
    if series_type == "sankey" and len(link_aliases) != 1:
        fail("ECharts sankey series must use exactly one of links or edges")
    node_field = node_aliases[0]
    nodes = series[node_field]
    if not isinstance(nodes, list):
        fail(f"{path}.{node_field} must be an array")
    id_owners: dict[tuple[type, Any], set[int]] = {}
    name_owners: dict[tuple[type, Any], set[int]] = {}
    for index, node in enumerate(nodes):
        node_path = f"{path}.{node_field}[{index}]"
        if not isinstance(node, dict):
            fail(f"{node_path} must be an object")
        validate_echarts_profile(
            node, "graph_node", f"{pointer}/{node_field}/{index}",
            label_override="graph node",
        )
        node_id = node.get("id")
        node_name = node.get("name")
        if "id" in node and not valid_node_identity(node_id):
            fail(f"{node_path}.id must be a stable string or integer")
        if "name" in node and not valid_node_identity(node_name):
            fail(f"{node_path}.name must be a stable string or integer")
        if not valid_node_identity(node_id) and not valid_node_identity(node_name):
            fail(f"{node_path} must have a stable id or name")
        if valid_node_identity(node_id):
            id_owners.setdefault((type(node_id), node_id), set()).add(index)
        if valid_node_identity(node_name):
            name_owners.setdefault((type(node_name), node_name), set()).add(index)
    duplicate_ids = [identity[1] for identity, owners in id_owners.items() if len(owners) != 1]
    if duplicate_ids:
        fail(f"{path}.{node_field} contains duplicate node identity {duplicate_ids[0]}")
    for index, node in enumerate(nodes):
        node_id = node.get("id")
        node_name = node.get("name")
        has_unique_id = valid_node_identity(node_id) and len(id_owners[(type(node_id), node_id)]) == 1
        has_unique_name = (
            valid_node_identity(node_name)
            and len(name_owners[(type(node_name), node_name)]) == 1
        )
        if not has_unique_id and not has_unique_name:
            fail(f"{path}.{node_field}[{index}] has no unique id or unambiguous name")
    endpoint_owners: dict[tuple[type, Any], set[int]] = {}
    for identity, owners in id_owners.items():
        endpoint_owners.setdefault(identity, set()).update(owners)
    for identity, owners in name_owners.items():
        endpoint_owners.setdefault(identity, set()).update(owners)
    if link_aliases:
        link_field = link_aliases[0]
        links = series[link_field]
        if not isinstance(links, list):
            fail(f"{path}.{link_field} must be an array")
        for index, link in enumerate(links):
            link_path = f"{path}.{link_field}[{index}]"
            if not isinstance(link, dict):
                fail(f"{link_path} must be an object")
            validate_echarts_profile(
                link, "graph_link", f"{pointer}/{link_field}/{index}",
                label_override="graph link",
            )
            if not valid_node_identity(link.get("source")) or not valid_node_identity(link.get("target")):
                fail(f"{link_path} must have stable source and target identities")
            for endpoint in ("source", "target"):
                identity = link[endpoint]
                if type(identity) is int:
                    if not 0 <= identity < len(nodes):
                        fail(f"{link_path}.{endpoint} node index {identity} is out of range")
                    continue
                owners = endpoint_owners.get((type(identity), identity), set())
                if len(owners) != 1:
                    fail(
                        f"{link_path}.{endpoint} references undeclared or ambiguous node identity "
                        f"{identity}"
                    )
    if "categories" in series:
        categories = series["categories"]
        if not isinstance(categories, list):
            fail(f"{path}.categories must be an array")
        for index, category in enumerate(categories):
            if isinstance(category, dict):
                validate_echarts_profile(
                    category, "graph_category", f"{pointer}/categories/{index}",
                    label_override="graph category",
                )
            if not (
                valid_node_identity(category)
                or isinstance(category, dict) and valid_node_identity(category.get("name"))
            ):
                fail(f"{path}.categories[{index}] must have a stable name")


def data_item_value(item: Any) -> Any:
    return item.get("value") if isinstance(item, dict) else item


def validate_fixed_tuple_data(data: list[Any], series_type: str, count: int, description: str) -> None:
    for index, item in enumerate(data):
        value = data_item_value(item)
        if not isinstance(value, list) or len(value) != count:
            fail(f"{series_type} data item {index} must contain exactly {count} {description}")


def validate_minimum_tuple_data(data: list[Any], series_type: str, count: int, description: str) -> None:
    for index, item in enumerate(data):
        value = data_item_value(item)
        if not isinstance(value, list) or len(value) < count:
            fail(f"{series_type} data item {index} must contain at least {description}")


def validate_lines_data(data: list[Any], pointer: str) -> None:
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not isinstance(item.get("coords"), list):
            fail(f"lines data item {index} must be an object with a coordinate path")
        validate_echarts_profile(
            item, "lines_data_item", f"{pointer}/{index}",
            label_override="lines data item",
        )
        coords = item["coords"]
        if len(coords) < 2:
            fail(f"lines data item {index} must contain at least two coordinate points")
        for point_index, point in enumerate(coords):
            if not isinstance(point, list) or len(point) != 2:
                fail(f"lines data item {index} coordinate point {point_index} must contain exactly two values")


def axis_for_series(option: dict[str, Any], axis_name: str, series: dict[str, Any]) -> dict[str, Any] | None:
    raw = option.get(axis_name)
    axes = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    index = series.get(f"{axis_name}Index", 0)
    if type(index) is not int or not 0 <= index < len(axes):
        return None
    return axes[index]


def valid_mark_coordinate_value(value: Any) -> bool:
    return (
        isinstance(value, str) and bool(value)
    ) or (
        type(value) in {int, float} and math.isfinite(value)
    )


def validate_mark_locator(
    value: Any, mark_name: str, item_path: str, coordinate_system: str
) -> None:
    built_in_types = {"min", "max", "average", "median"}
    coordinate_locator_fields = {
        "cartesian2d": {"coord", "xAxis", "yAxis"},
        "polar": {"coord", "radiusAxis", "angleAxis"},
        "geo": {"coord"},
        "calendar": {"coord"},
        "radar": {"coord"},
        "singleAxis": {"coord", "singleAxis"},
    }
    all_locator_fields = {"coord", "xAxis", "yAxis", "radiusAxis", "angleAxis", "singleAxis"}
    if not isinstance(value, dict):
        fail(f"{mark_name} data item {item_path} must define a rendered locator")
    allowed_fields = coordinate_locator_fields.get(coordinate_system)
    if allowed_fields is None:
        fail(f"{mark_name} does not support coordinate system {coordinate_system}")
    for field in sorted(all_locator_fields.intersection(value)):
        if field not in allowed_fields:
            fail(f"{mark_name} data item {item_path} locator field {field} is incompatible with {coordinate_system}")
    axis_fields = allowed_fields - {"coord"}
    present_axis_fields = axis_fields.intersection(value)
    locator_form_count = sum(("type" in value, "coord" in value, bool(present_axis_fields)))
    if locator_form_count > 1:
        fail(f"{mark_name} data item {item_path} mixes locator forms")
    has_locator = False
    if "type" in value:
        mark_type = value["type"]
        if mark_type not in built_in_types:
            fail(f"{mark_name} data item {item_path} has unsupported statistical type {mark_type}")
        has_locator = True
    if "coord" in value:
        coord = value["coord"]
        if not isinstance(coord, list) or len(coord) != 2:
            fail(f"{mark_name} data item {item_path} coord must contain exactly two values")
        if not all(valid_mark_coordinate_value(item) for item in coord):
            fail(f"{mark_name} data item {item_path} coord values must be non-null scalar values")
        has_locator = True
    for field in sorted(present_axis_fields):
        if not valid_mark_coordinate_value(value[field]):
            fail(f"{mark_name} data item {item_path} locator field {field} must be a non-null scalar value")
    if present_axis_fields:
        if mark_name == "markPoint" and coordinate_system in {"cartesian2d", "polar"}:
            required = {"xAxis", "yAxis"} if coordinate_system == "cartesian2d" else {"radiusAxis", "angleAxis"}
            if not required <= present_axis_fields:
                fail(f"{mark_name} data item {item_path} must define both coordinate axes")
        has_locator = True
    if not has_locator:
        fail(f"{mark_name} data item {item_path} must define a rendered locator")


def validate_mark_data(
    mark_name: str,
    mark: dict[str, Any],
    path: str,
    coordinate_system: str,
) -> None:
    validate_allowed_fields(mark, MARK_COMPONENT_ALLOWED_FIELDS, mark_name, path)
    data = mark.get("data")
    if not isinstance(data, list) or not data:
        fail(f"ECharts {mark_name} {path}.data must be a non-empty array")
    for index, item in enumerate(data):
        if mark_name == "markPoint":
            validate_mark_locator(item, mark_name, str(index), coordinate_system)
            if isinstance(item, dict):
                validate_allowed_fields(item, MARK_ITEM_ALLOWED_FIELDS, f"{mark_name} data item", f"{path}/data/{index}")
                validate_nested_style_components(item, f"{path}/data/{index}")
            continue
        if mark_name == "markLine" and isinstance(item, dict):
            validate_mark_locator(item, mark_name, str(index), coordinate_system)
            validate_allowed_fields(item, MARK_ITEM_ALLOWED_FIELDS, f"{mark_name} data item", f"{path}/data/{index}")
            validate_nested_style_components(item, f"{path}/data/{index}")
            continue
        if not isinstance(item, list) or len(item) != 2:
            if isinstance(item, dict):
                validate_mark_locator(item, mark_name, str(index), coordinate_system)
            fail(f"{mark_name} data item {index} must define a rendered locator pair")
        for endpoint_index, endpoint in enumerate(item):
            validate_mark_locator(endpoint, mark_name, f"{index}/{endpoint_index}", coordinate_system)
            validate_allowed_fields(endpoint, MARK_ITEM_ALLOWED_FIELDS, f"{mark_name} data item", f"{path}/data/{index}/{endpoint_index}")
            validate_nested_style_components(endpoint, f"{path}/data/{index}/{endpoint_index}")


def validate_direct_series_shapes(
    option: dict[str, Any], series: dict[str, Any], series_type: str, path: str,
    pointer: str,
) -> None:
    if series_type in {"graph", "sankey"}:
        validate_graph_series_shapes(series, series_type, path, pointer)
        return
    for field in SERIES_DATA_SURFACES[series_type]:
        if field in series and not isinstance(series[field], list):
            fail(f"ECharts series type {series_type} {field} must be an array")
    data = series.get("data")
    if isinstance(data, list):
        if series_type not in {"tree", "treemap", "sunburst", "lines"}:
            for index, item in enumerate(data):
                if isinstance(item, dict):
                    validate_echarts_profile(
                        item, "direct_data_item", f"{pointer}/data/{index}",
                        label_override=f"{series_type} data item",
                    )
        if series_type == "candlestick":
            validate_fixed_tuple_data(data, series_type, 4, "OHLC values")
        elif series_type == "boxplot":
            validate_fixed_tuple_data(data, series_type, 5, "values")
        elif series_type == "heatmap":
            validate_minimum_tuple_data(data, series_type, 3, "x, y, and value")
        elif series_type in {"scatter", "effectScatter"}:
            x_axis = axis_for_series(option, "xAxis", series)
            category_one_dimension = isinstance(x_axis, dict) and x_axis.get("type") == "category"
            if category_one_dimension:
                for index, item in enumerate(data):
                    value = data_item_value(item)
                    if isinstance(value, list) and len(value) >= 1:
                        continue
                    if not isinstance(value, (dict, list)) and value is not None:
                        continue
                    fail(f"{series_type} data item {index} must contain at least one category-axis value")
            else:
                validate_minimum_tuple_data(data, series_type, 2, "two coordinate values")
        elif series_type == "lines":
            validate_lines_data(data, f"{pointer}/data")
    if series_type in {"tree", "treemap", "sunburst"} and "data" in series:
        validate_hierarchy_data(series["data"], f"{path}.data", f"{pointer}/data")


def resolve_dataset_dimension(reference: Any, dimension_names: list[str | None]) -> int | None:
    if isinstance(reference, str) and reference in dimension_names:
        return dimension_names.index(reference)
    if type(reference) is int and 0 <= reference < len(dimension_names):
        return reference
    return None


def visual_map_series_indices(value: Any, series_count: int, path: str) -> set[int]:
    if value is None or value == "all":
        return set(range(series_count))
    values = value if isinstance(value, list) else [value]
    if not values or any(type(index) is not int or not 0 <= index < series_count for index in values):
        fail(f"{path}.seriesIndex must select existing series indices")
    return set(values)


def direct_series_dimension_count(option: dict[str, Any], series: dict[str, Any]) -> int | None:
    data = series.get("data")
    if not isinstance(data, list) or not data:
        return None
    widths: set[int] = set()
    for item in data:
        value = data_item_value(item)
        if isinstance(value, list):
            widths.add(len(value))
        elif series.get("type") in {"scatter", "effectScatter"}:
            x_axis = axis_for_series(option, "xAxis", series)
            if isinstance(x_axis, dict) and x_axis.get("type") == "category":
                widths.add(1)
            else:
                return None
        else:
            return None
    return next(iter(widths)) if len(widths) == 1 else None


def apply_visual_map_static_dimensions(
    option: dict[str, Any],
    dataset_visibility: dict[str, dict[str, Any]],
) -> None:
    series = option.get("series")
    series_count = len(series) if isinstance(series, list) else 0
    for base, visual_map in component_objects(option, "visualMap"):
        if "dimension" not in visual_map:
            continue
        selected_series = visual_map_series_indices(visual_map.get("seriesIndex"), series_count, base)
        in_range = visual_map.get("inRange")
        has_static_encoding = False
        if in_range is not None:
            if not isinstance(in_range, dict) or not in_range:
                fail(f"ECharts visualMap {base}.inRange must be a non-empty object")
            unknown_channels = sorted(set(in_range) - VISUAL_MAP_STATIC_CHANNELS)
            if unknown_channels:
                fail(f"ECharts visualMap {base}.inRange contains unsupported channel {unknown_channels[0]}")
            has_static_encoding = True
        statically_visible = visual_map.get("show", True) is True or has_static_encoding
        if not statically_visible:
            continue
        matched_dataset = False
        for details in dataset_visibility.values():
            if not selected_series.intersection(details["series_indices"]):
                continue
            matched_dataset = True
            dimension_index = resolve_dataset_dimension(
                visual_map["dimension"], details["dimension_names"]
            )
            if dimension_index is None:
                fail(f"ECharts visualMap {base}.dimension does not resolve against its consumed dataset")
            details["static_dimensions"].add(dimension_index)
        matched_direct = False
        if isinstance(series, list):
            for series_index in selected_series:
                item = series[series_index]
                if not isinstance(item, dict) or "data" not in item:
                    continue
                if item.get("type") not in {"scatter", "effectScatter", "heatmap"}:
                    continue
                matched_direct = True
                dimension_count = direct_series_dimension_count(option, item)
                dimension = visual_map["dimension"]
                if type(dimension) is not int or dimension_count is None or not 0 <= dimension < dimension_count:
                    fail(f"ECharts visualMap {base}.dimension does not resolve against selected direct series data")
        if not matched_dataset and not matched_direct:
            fail(f"ECharts visualMap {base}.dimension is not applied to a consumed dataset or direct series")


def collect_visible_formatters(option: dict[str, Any]) -> list[dict[str, Any]]:
    formatters: list[dict[str, Any]] = []

    def add(
        container: Any,
        pointer: str,
        *,
        visible: bool,
        kind: str,
        series_index: int | None = None,
        mark_item_pointer: str | None = None,
    ) -> None:
        if visible and isinstance(container, dict) and "formatter" in container:
            formatters.append({
                "pointer": f"{pointer}/formatter",
                "value": container["formatter"],
                "kind": kind,
                "series_index": series_index,
                "mark_item_pointer": mark_item_pointer,
            })

    for component in ("xAxis", "yAxis", "angleAxis", "radiusAxis", "singleAxis", "parallelAxis"):
        for base, axis in component_objects(option, component):
            axis_label = axis.get("axisLabel")
            add(
                axis_label,
                f"{base}/axisLabel",
                visible=axis.get("show", True) is True and isinstance(axis_label, dict)
                and axis_label.get("show", True) is True,
                kind="axis_label",
            )
    for component in ("legend", "visualMap"):
        for base, value in component_objects(option, component):
            add(value, base, visible=value.get("show", True) is True, kind=component)
    for base, value in component_objects(option, "tooltip"):
        add(value, base, visible=True, kind="tooltip")
    series = option.get("series")
    if isinstance(series, list):
        for series_index, item in enumerate(series):
            if not isinstance(item, dict):
                continue
            base = f"/series/{series_index}"
            for field in ("label", "endLabel"):
                label = item.get(field)
                add(
                    label,
                    f"{base}/{field}",
                    visible=isinstance(label, dict) and label.get("show") is True,
                    kind="series_label" if field == "label" else "series_end_label",
                    series_index=series_index,
                )
            add(
                item.get("tooltip"),
                f"{base}/tooltip",
                visible=True,
                kind="tooltip",
                series_index=series_index,
            )
            if item.get("type") == "gauge":
                detail = item.get("detail")
                add(
                    detail,
                    f"{base}/detail",
                    visible=isinstance(detail, dict) and detail.get("show", True) is True,
                    kind="gauge_detail",
                    series_index=series_index,
                )
                axis_label = item.get("axisLabel")
                add(
                    axis_label,
                    f"{base}/axisLabel",
                    visible=isinstance(axis_label, dict) and axis_label.get("show", True) is True,
                    kind="gauge_axis_label",
                    series_index=series_index,
                )
            for mark in ("markPoint", "markLine", "markArea"):
                mark_value = item.get(mark)
                label = mark_value.get("label") if isinstance(mark_value, dict) else None
                mark_data = mark_value.get("data") if isinstance(mark_value, dict) else None
                add(
                    label,
                    f"{base}/{mark}/label",
                    visible=isinstance(label, dict) and label.get("show") is True
                    and isinstance(mark_data, list) and bool(mark_data),
                    kind="mark_label",
                    series_index=series_index,
                )
                if isinstance(mark_data, list):
                    def collect_item_labels(value: Any, pointer: str) -> None:
                        if isinstance(value, dict):
                            item_label = value.get("label")
                            add(
                                item_label,
                                f"{pointer}/label",
                                visible=isinstance(item_label, dict) and item_label.get("show") is True,
                                kind="mark_label",
                                series_index=series_index,
                                mark_item_pointer=pointer,
                            )
                        elif isinstance(value, list):
                            for child_index, child in enumerate(value):
                                collect_item_labels(child, f"{pointer}/{child_index}")
                    for data_index, data_item in enumerate(mark_data):
                        collect_item_labels(data_item, f"{base}/{mark}/data/{data_index}")
    return formatters


def declarative_formatter_parts(value: str) -> tuple[list[str], list[str]] | None:
    matches = list(FORMATTER_PLACEHOLDER_RE.finditer(value))
    segments: list[str] = []
    offset = 0
    for match in matches:
        segments.append(value[offset:match.start()])
        offset = match.end()
    segments.append(value[offset:])
    if any("{" in segment or "}" in segment for segment in segments):
        return None
    return [match.group(0) for match in matches], segments


def validate_visible_formatters(
    visible_formatters: list[dict[str, Any]],
    bindings: list[dict[str, str | None]],
    dataset_visibility: dict[str, dict[str, Any]],
    literal_bindings: list[dict[str, str]],
) -> set[str]:
    safe_derived: set[str] = set()
    for formatter in visible_formatters:
        pointer = str(formatter["pointer"])
        value = formatter["value"]
        if not isinstance(value, str):
            fail(f"visible formatter {pointer} must be a declarative string")
        source_bound = any(
            str(binding["option_pointer"]) == pointer and binding.get("literal_fragment") is None
            for binding in bindings
        )
        parsed_formatter = declarative_formatter_parts(value)
        if parsed_formatter is None:
            if not source_bound:
                fail(f"visible formatter {pointer} contains unbound literal text")
            continue
        placeholders, static_segments = parsed_formatter
        if source_bound:
            static_segments = ["" for _segment in static_segments]
        for literal_binding in literal_bindings:
            if literal_binding["formatter_pointer"] == pointer:
                literal = literal_binding["literal"]
                for index, segment in enumerate(static_segments):
                    if literal in segment:
                        static_segments[index] = segment.replace(literal, "", 1)
                        break
        remaining_literal = "".join(segment for segment in static_segments if segment.strip())
        if any(character.isalnum() or character == "_" for character in remaining_literal):
            fail(f"visible formatter {pointer} contains unbound literal text")
        if remaining_literal:
            fail(f"visible formatter {pointer} contains unbound static literal")
        allowed_placeholders = FORMATTER_PLACEHOLDERS_BY_KIND[str(formatter["kind"])]
        for placeholder in placeholders:
            name = placeholder[1:-1]
            if name.startswith("@"):
                if formatter["kind"] not in {"series_label", "series_end_label", "mark_label"}:
                    fail(f"visible formatter {pointer} uses unsupported placeholder {placeholder}")
            elif name not in allowed_placeholders:
                fail(f"visible formatter {pointer} uses unsupported placeholder {placeholder}")
        dataset_placeholders: list[str | int] = [
            int(placeholder[3:-2]) if placeholder.startswith("{@[") else placeholder[2:-1]
            for placeholder in placeholders
            if placeholder.startswith("{@")
        ]
        if dataset_placeholders:
            series_index = formatter["series_index"]
            if formatter["kind"] not in {"series_label", "series_end_label", "mark_label"} or series_index is None:
                fail(f"visible formatter {pointer} cannot resolve dataset placeholders")
            matching_details = [
                details
                for details in dataset_visibility.values()
                if series_index in details["series_indices"]
            ]
            if len(matching_details) != 1:
                fail(f"visible formatter {pointer} is not attached to one consumed dataset series")
            details = matching_details[0]
            mark_item_pointer = formatter.get("mark_item_pointer")
            if formatter["kind"] == "mark_label" and mark_item_pointer is not None:
                if not any(
                    mark_locator_binding_matches(
                        str(mark_item_pointer), str(binding["option_pointer"])
                    )
                    for binding in bindings
                ):
                    fail(f"visible formatter {pointer} dataset placeholder requires a source-bound mark locator")
            for dimension_name in dataset_placeholders:
                dimension_index = resolve_dataset_dimension(
                    dimension_name, details["dimension_names"]
                )
                if dimension_index is None:
                    fail(f"visible formatter {pointer} references unknown dataset dimension {dimension_name}")
                details["static_dimensions"].add(dimension_index)
        safe_derived.add(pointer)
    return safe_derived


def mark_locator_binding_matches(mark_item_pointer: str, binding_pointer: str) -> bool:
    if pointer_contains(binding_pointer, mark_item_pointer):
        return True
    if not pointer_contains(mark_item_pointer, binding_pointer):
        return False
    relative = binding_pointer[len(mark_item_pointer):].lstrip("/")
    first_token = relative.split("/", 1)[0]
    return decode_json_pointer_token(first_token) in MARK_LOCATOR_FIELDS


def rendered_echarts_surface_roots(
    option: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    roots: list[str] = []
    core_roots: list[str] = []
    component_fields = {
        "title": ("text", "subtext"),
        "legend": ("data",),
        "radar": ("indicator",),
        "visualMap": ("categories", "pieces"),
        "calendar": ("range",),
        "xAxis": ("data", "name"),
        "yAxis": ("data", "name"),
        "angleAxis": ("data", "name"),
        "radiusAxis": ("data", "name"),
        "singleAxis": ("data", "name"),
        "parallelAxis": ("data", "name"),
    }
    for component, fields in component_fields.items():
        for base, value in component_objects(option, component):
            roots.extend(f"{base}/{field}" for field in fields if field in value)
    consumed_datasets, all_datasets, dataset_visibility = consumed_dataset_bases(option)
    unconsumed_datasets = all_datasets - consumed_datasets
    if unconsumed_datasets:
        fail(f"ECharts dataset {sorted(unconsumed_datasets)[0]} is not consumed by any series")
    apply_visual_map_static_dimensions(option, dataset_visibility)
    for base, value in component_objects(option, "dataset"):
        if base not in consumed_datasets:
            continue
        for field in ("source", "dimensions"):
            if field in value:
                root = f"{base}/{field}"
                roots.append(root)
                if field == "source":
                    core_roots.append(root)
    series = option.get("series")
    if isinstance(series, list):
        for index, item in enumerate(series):
            if not isinstance(item, dict):
                continue
            base = f"/series/{index}"
            series_type = item.get("type")
            consumed_fields = SERIES_DATA_SURFACES.get(series_type, set())
            if isinstance(series_type, str) and series_type in SERIES_DATA_SURFACES:
                validate_direct_series_shapes(
                    option, item, series_type, f"echarts.option.series[{index}]", base
                )
            coordinate_system = item.get(
                "coordinateSystem",
                DEFAULT_COORDINATE_SYSTEM.get(series_type, "none"),
            )
            for mark_name in ("markPoint", "markLine", "markArea"):
                mark_value = item.get(mark_name)
                if isinstance(mark_value, dict) and "data" in mark_value:
                    validate_mark_data(
                        mark_name,
                        mark_value,
                        f"{base}/{mark_name}",
                        str(coordinate_system),
                    )
            for field in SERIES_ONLY_SURFACES:
                if field in item:
                    if field not in consumed_fields:
                        fail(f"ECharts series type {series_type} does not consume data surface {field}")
                    root = f"{base}/{field}"
                    roots.append(root)
                    if field != "categories":
                        core_roots.append(root)
            if "name" in item:
                roots.append(f"{base}/name")
            for mark in ("markPoint", "markLine", "markArea"):
                mark_value = item.get(mark)
                if isinstance(mark_value, dict) and "data" in mark_value:
                    roots.append(f"{base}/{mark}/data")
    visible_formatters = collect_visible_formatters(option)
    roots.extend(str(formatter["pointer"]) for formatter in visible_formatters)
    return roots, core_roots, dataset_visibility, visible_formatters


def option_leaf_is_nonfactual(option: dict[str, Any], pointer: str, surface_root: str) -> bool:
    relative = pointer[len(surface_root):].lstrip("/")
    tokens = [decode_json_pointer_token(token) for token in relative.split("/") if token]
    visual_branches = {
        "itemStyle", "lineStyle", "areaStyle", "label", "labelLine", "emphasis",
        "blur", "select", "tooltip", "symbol", "symbolSize", "symbolRotate",
        "symbolOffset", "color", "borderColor", "borderWidth", "opacity",
    }
    if any(token in visual_branches for token in tokens):
        return True
    if "/markPoint/data" in surface_root or "/markLine/data" in surface_root or "/markArea/data" in surface_root:
        if tokens and tokens[-1] == "type":
            value = resolve_json_pointer(option, pointer, "ECharts option data surface")
            if value in {"min", "max", "average", "median"}:
                return True
    return False


def validate_echarts_data_bindings(spec: dict[str, Any], request: dict[str, Any]) -> None:
    bindings = spec["data_bindings"]
    if not isinstance(bindings, list):
        fail("echarts.data_bindings must be an array")
    expected_source_leaves = json_leaf_pointers(spec["source_data"])
    rendered_roots, core_roots, dataset_visibility, visible_formatters = rendered_echarts_surface_roots(
        spec["option"]
    )
    formatter_values = {
        str(formatter["pointer"]): formatter["value"]
        for formatter in visible_formatters
    }
    authorized_duplicates = {
        binding["id"]
        for binding in request["source_content"]["source_bindings"]
        if isinstance(binding, dict)
        and isinstance(binding.get("id"), str)
        and binding.get("allow_duplicate_display") is True
    }
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(bindings):
        path = f"echarts.data_bindings[{index}]"
        binding = strict_object(
            raw,
            path,
            {"source_pointer", "option_pointer"},
            {"duplicate_display_authorization_id"},
        )
        source_pointer = require_json_pointer(binding["source_pointer"], f"{path}.source_pointer")
        option_pointer = require_json_pointer(binding["option_pointer"], f"{path}.option_pointer")
        authorization_id = binding.get("duplicate_display_authorization_id")
        if authorization_id is not None:
            authorization_id = require_string(authorization_id, f"{path}.duplicate_display_authorization_id")
        if not any(pointer_contains(root, option_pointer) for root in rendered_roots):
            fail(f"ECharts option binding destination {option_pointer} is not a recognized rendered data surface")
        if source_pointer:
            parent_pointer = source_pointer.rsplit("/", 1)[0]
            parent = resolve_json_pointer(spec["source_data"], parent_pointer, f"{path}.source_pointer")
            if isinstance(parent, list):
                fail(f"source subtree binding {source_pointer} splits array {parent_pointer}")
        source_value = resolve_json_pointer(spec["source_data"], source_pointer, f"{path}.source_pointer")
        option_value = resolve_json_pointer(spec["option"], option_pointer, f"{path}.option_pointer")
        literal_fragment: str | None = None
        if canonical_json_bytes(option_value) != canonical_json_bytes(source_value):
            formatter_value = formatter_values.get(option_pointer)
            formatter_parts = (
                declarative_formatter_parts(formatter_value)
                if isinstance(formatter_value, str) else None
            )
            formatter_segments = formatter_parts[1] if formatter_parts is not None else []
            if (
                not isinstance(source_value, str)
                or not source_value
                or not any(source_value in segment for segment in formatter_segments)
            ):
                fail(f"option subtree {option_pointer} does not match source subtree {source_pointer}")
            literal_fragment = source_value
        for previous in parsed:
            previous_source = str(previous["source_pointer"])
            previous_option = str(previous["option_pointer"])
            if source_pointer == previous_source:
                if (
                    authorization_id is None
                    or authorization_id != previous["authorization_id"]
                    or authorization_id not in authorized_duplicates
                ):
                    fail(f"overlapping ECharts source subtree binding {source_pointer}")
            elif pointer_contains(source_pointer, previous_source) or pointer_contains(previous_source, source_pointer):
                fail(f"overlapping ECharts source subtree binding {source_pointer}")
            if pointer_contains(option_pointer, previous_option) or pointer_contains(previous_option, option_pointer):
                separate_formatter_fragments = (
                    option_pointer == previous_option
                    and literal_fragment is not None
                    and previous.get("literal_fragment") is not None
                    and literal_fragment != previous["literal_fragment"]
                )
                if not separate_formatter_fragments:
                    fail(f"overlapping ECharts option subtree binding {option_pointer}")
        parsed.append({
            "source_pointer": source_pointer,
            "option_pointer": option_pointer,
            "authorization_id": authorization_id,
            "literal_fragment": literal_fragment,
        })

    literal_bindings = [
        {
            "formatter_pointer": str(binding["option_pointer"]),
            "source_pointer": str(binding["source_pointer"]),
            "literal": str(binding["literal_fragment"]),
        }
        for binding in parsed
        if binding.get("literal_fragment") is not None
    ]

    by_source: dict[str, list[dict[str, str | None]]] = {}
    for binding in parsed:
        by_source.setdefault(str(binding["source_pointer"]), []).append(binding)
    for source_pointer, duplicates in by_source.items():
        if len(duplicates) < 2:
            continue
        authorization_ids = {binding["authorization_id"] for binding in duplicates}
        if len(authorization_ids) != 1 or None in authorization_ids or not authorization_ids <= authorized_duplicates:
            fail(f"overlapping ECharts source subtree binding {source_pointer}")

    safe_derived_formatters = validate_visible_formatters(
        visible_formatters, parsed, dataset_visibility, literal_bindings
    )
    supplemental_roots = [root for root in rendered_roots if not root.startswith("/dataset")]
    for dataset_base, details in dataset_visibility.items():
        dimension_names = details["dimension_names"]
        leaves_by_dimension = details["leaves_by_dimension"]
        static_dimensions = details["static_dimensions"]
        for dimension_index, option_leaves in leaves_by_dimension.items():
            if dimension_index in static_dimensions:
                continue
            statically_bound = True
            for option_leaf in option_leaves:
                mapped_source_leaves: list[str] = []
                for binding in parsed:
                    binding_option = str(binding["option_pointer"])
                    if pointer_contains(binding_option, option_leaf):
                        suffix = option_leaf[len(binding_option):]
                        mapped_source_leaves.append(str(binding["source_pointer"]) + suffix)
                if not mapped_source_leaves or not any(
                    pointer_contains(str(binding["source_pointer"]), source_leaf)
                    and any(
                        pointer_contains(root, str(binding["option_pointer"]))
                        for root in supplemental_roots
                    )
                    for source_leaf in mapped_source_leaves
                    for binding in parsed
                ):
                    statically_bound = False
                    break
            if not statically_bound:
                name = dimension_names[dimension_index]
                label = name if name is not None else str(dimension_index)
                fail(f"ECharts dataset {dataset_base} factual dimension {label} is not statically rendered")

    for pointer in expected_source_leaves:
        covering_sources = [binding for binding in parsed if pointer_contains(str(binding["source_pointer"]), pointer)]
        if not covering_sources:
            fail(f"source_data leaf {pointer} is unbound")
    has_core_binding = False
    for binding in parsed:
        option_pointer = str(binding["option_pointer"])
        for core_root in core_roots:
            if pointer_contains(core_root, option_pointer) and not option_leaf_is_nonfactual(
                spec["option"], option_pointer, core_root
            ):
                has_core_binding = True
                break
        if has_core_binding:
            break
    if not has_core_binding:
        fail("ECharts bindings must include a consumed series data surface")
    for surface_root in rendered_roots:
        surface_value = resolve_json_pointer(spec["option"], surface_root, "ECharts option data surface")
        for pointer in json_leaf_pointers(surface_value, surface_root):
            if pointer in safe_derived_formatters:
                continue
            if option_leaf_is_nonfactual(spec["option"], pointer, surface_root):
                continue
            if not any(pointer_contains(str(binding["option_pointer"]), pointer) for binding in parsed):
                fail(f"data-bearing option leaf {pointer} is unbound")


def validate_echarts(value: Any, request: dict[str, Any]) -> dict[str, Any]:
    spec = strict_object(
        value,
        "echarts",
        {"schema_id", "version", "stage", "identity", "design_strategy", "visual_system", "render_mode", "source_data", "source_data_sha256", "final_frame_review_status", "data_bindings", "option"},
    )
    reject_public_projection(spec, "echarts")
    if spec["schema_id"] != "smart-video.echarts-author-spec.v1" or type(spec["version"]) is not int or spec["version"] != 1:
        fail("ECharts schema/version must be smart-video.echarts-author-spec.v1 version 1")
    stage = require_enum_string(spec["stage"], "echarts.stage")
    if stage != "llm_author":
        fail("echarts.stage must be llm_author")
    if spec["final_frame_review_status"] != "pending_render":
        fail("echarts.final_frame_review_status must be pending_render")
    validate_identity(spec["identity"], "echarts.identity")
    validate_strategy(spec["design_strategy"], "echarts.design_strategy", spec)
    validate_visual_system(spec["visual_system"], "echarts.visual_system", require_locked=False)
    render_mode = require_enum_string(spec["render_mode"], "echarts.render_mode")
    if render_mode != "echarts":
        fail("ECharts author spec render_mode must be echarts")
    for field in ("identity", "design_strategy", "render_mode", "source_data", "source_data_sha256"):
        if spec[field] != request[field]:
            if field == "source_data":
                fail("ECharts source_data differs from request.source_data")
            fail(f"echarts.{field} does not match request")
    expected_system = {key: request["visual_system"][key] for key in ("id", "version")}
    if spec["visual_system"] != expected_system:
        fail("echarts.visual_system does not match request")
    if require_sha256(spec["source_data_sha256"], "echarts.source_data_sha256") != sha256_bytes(canonical_json_bytes(spec["source_data"])):
        fail("echarts.source_data_sha256 does not match source_data")
    option = spec["option"]
    if not isinstance(option, dict) or not option:
        fail("echarts.option must be a non-empty declarative object")
    for key in option:
        if is_gl_surface_name(key):
            fail(f"ECharts GL component {key} is forbidden")
    walk_echarts(option)
    for key in ("toolbox", "brush", "dataZoom"):
        if key in option:
            fail(f"interactive ECharts option {key} is forbidden")
    validate_known_echarts_components(option)
    series = option.get("series")
    if not isinstance(series, list) or not series:
        fail("echarts.option.series must be a non-empty array")
    if len(series) > 8:
        fail("echarts.option.series must contain at most 8 series")
    for index, item in enumerate(series):
        if not isinstance(item, dict):
            fail(f"echarts.option.series[{index}] must be an object")
        validate_series_fields(item, f"echarts.option.series[{index}]")
        series_type = require_enum_string(item.get("type"), f"echarts.option.series[{index}].type")
        if series_type in GL_SERIES:
            fail("ECharts GL series type is forbidden")
        if series_type == "custom":
            fail("custom ECharts series is forbidden")
        if series_type not in STANDARD_SERIES:
            fail(f"unsupported ECharts series type {series_type}")
        validate_series_encode(item, series_type, f"/series/{index}")
        if series_type == "map" and item.get("map") != "USA":
            fail("ECharts map must use a supported bundled local map")
    geo = option.get("geo")
    if geo is not None:
        geos = geo if isinstance(geo, list) else [geo]
        if not isinstance(geo, (dict, list)) or any(not isinstance(item, dict) for item in geos):
            fail("ECharts geo must be an object or array of objects")
        for item in geos:
            map_name = item.get("map")
            if map_name != "USA":
                fail(f"ECharts geo map {map_name} is not bundled")
    validate_echarts_data_bindings(spec, request)
    validate_closed_echarts_components(option)
    encoded_size = len(canonical_json_bytes(option))
    if encoded_size > 65536:
        fail("echarts.option exceeds 64 KiB")
    return spec


def validate_echarts_actions(spec: dict[str, Any], manifest: dict[str, Any]) -> None:
    series_by_id: dict[str, dict[str, Any]] = {}
    for index, series in enumerate(spec["option"]["series"]):
        if "id" not in series:
            continue
        series_id = require_string(series["id"], f"echarts.option.series[{index}].id")
        if series_id in series_by_id:
            fail(f"ECharts series id {series_id} does not resolve uniquely")
        series_by_id[series_id] = series

    def resolve_series(series_id: Any) -> dict[str, Any]:
        normalized_id = require_string(series_id, "ECharts action series_id")
        series = series_by_id.get(normalized_id)
        if series is None:
            fail(f"ECharts action series id {normalized_id} does not resolve uniquely")
        return series

    for phase in manifest["motion_phases"]:
        action = phase["echarts_action"]
        action_type = action["type"]
        if action_type == "reveal_series":
            for series_id in action["series_ids"]:
                resolve_series(series_id)
        elif action_type == "highlight_data":
            series_id = action["series_id"]
            series = resolve_series(series_id)
            direct_data = series.get("data")
            if not isinstance(direct_data, list):
                fail(f"highlight_data requires direct series data for {series_id}")
            for data_index in action["data_indices"]:
                if data_index >= len(direct_data):
                    fail(f"data index {data_index} is outside direct series {series_id} data")
        elif action_type == "show_annotation":
            series_id = action["series_id"]
            series = resolve_series(series_id)
            annotation = action["annotation"]
            mark = series.get(annotation)
            if not isinstance(mark, dict) or not isinstance(mark.get("data"), list) or not mark["data"]:
                fail(f"show_annotation target {series_id} has no nonempty {annotation}")
