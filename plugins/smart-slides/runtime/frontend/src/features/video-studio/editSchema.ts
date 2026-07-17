export const editableBlockProperties = [
  'text',
  'x',
  'y',
  'width',
  'height',
  'fontSize',
  'scale',
  'color',
  'opacity',
  'motion',
] as const;

export type EditableBlockProperty = (typeof editableBlockProperties)[number];
export type EditableBlockKind = 'text' | 'visual' | 'group';
export type EditableBlockColorMode = 'self' | 'descendants';

export type EditableBlock = {
  id: string;
  name: string;
  kind: EditableBlockKind;
  selector: string;
  allowed: EditableBlockProperty[];
  colorMode?: EditableBlockColorMode;
};

export type EditableBlockValue = string | number;
export type EditableBlockOverride = Partial<Record<EditableBlockProperty, EditableBlockValue>>;
export type HtmlBlockOverrides = Record<string, EditableBlockOverride>;

export type NormalizedEditSchema = {
  blocks: EditableBlock[];
  errors: string[];
  isSemantic: boolean;
  isLegacy: boolean;
};

const propertyAliases: Record<string, EditableBlockProperty | undefined> = {
  text: 'text',
  x: 'x',
  y: 'y',
  width: 'width',
  height: 'height',
  fontSize: 'fontSize',
  font_size: 'fontSize',
  scale: 'scale',
  color: 'color',
  opacity: 'opacity',
  motion: 'motion',
};

// Semantic editing deliberately accepts one simple selector per block. A
// descendant selector would let one editor control reach through an editable
// group and mutate implementation details that the director did not expose.
const simpleSelectorPattern = /^(?:[a-zA-Z][\w:-]*)?(?:(?:#[\w-]+|\.[\w-]+|\[[a-zA-Z_][\w:-]*(?:=(?:"[^"]*"|'[^']*'|[^\]\s]+))?\]))+$|^[a-zA-Z][\w:-]*$/;

function recordValue(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function normalizeKind(value: unknown): EditableBlockKind | null {
  const kind = String(value ?? '').trim();
  if (kind === 'text') return 'text';
  if (kind === 'group' || kind === 'visual_group') return 'group';
  if (kind === 'visual' || kind.startsWith('visual_')) return 'visual';
  return null;
}

function normalizeAllowed(value: unknown): EditableBlockProperty[] {
  if (!Array.isArray(value)) return [];
  const allowed: EditableBlockProperty[] = [];
  value.forEach((item) => {
    const property = propertyAliases[String(item ?? '').trim()];
    if (property && !allowed.includes(property)) allowed.push(property);
  });
  return allowed;
}

export function isSimpleSemanticSelector(selector: string) {
  return simpleSelectorPattern.test(selector.trim());
}

export function normalizeEditSchema(value: unknown): NormalizedEditSchema {
  const schema = recordValue(value);
  const rawBlocks = Array.isArray(schema?.editable_blocks) ? schema.editable_blocks : [];
  if (!rawBlocks.length) {
    const declaresSemanticBlocks = Boolean(schema && ('editable_blocks' in schema || schema.version === 'edit_schema_v2'));
    return {
      blocks: [],
      errors: declaresSemanticBlocks ? ['edit_schema editable_blocks 不能为空'] : [],
      isSemantic: false,
      isLegacy: !declaresSemanticBlocks,
    };
  }

  const errors: string[] = [];
  const blocks: EditableBlock[] = [];
  const ids = new Set<string>();
  rawBlocks.forEach((item, index) => {
    const source = recordValue(item);
    if (!source) {
      errors.push(`editable_blocks[${index}] 必须是对象`);
      return;
    }
    const id = String(source.id ?? '').trim();
    const name = String(source.name ?? '').trim();
    const kind = normalizeKind(source.kind ?? source.type);
    const selector = String(source.selector ?? '').trim();
    const allowed = normalizeAllowed(source.allowed ?? source.controls);
    const rawColorMode = String(source.colorMode ?? source.color_mode ?? '').trim();
    const colorMode = rawColorMode === 'self' || rawColorMode === 'descendants'
      ? rawColorMode as EditableBlockColorMode
      : undefined;

    if (!id) errors.push(`editable_blocks[${index}] 缺少 id`);
    else if (ids.has(id)) errors.push(`editable_blocks 存在重复 id：${id}`);
    else ids.add(id);
    if (!name) errors.push(`${id || `editable_blocks[${index}]`} 缺少 name`);
    if (!kind) errors.push(`${id || `editable_blocks[${index}]`} 的 kind 无效`);
    if (!selector || !isSimpleSemanticSelector(selector)) {
      errors.push(`${id || `editable_blocks[${index}]`} 必须使用单元素简单 selector，不能使用后代或组合 selector`);
    }
    if (!allowed.length) errors.push(`${id || `editable_blocks[${index}]`} 没有有效的 allowed 属性`);
    if (kind === 'group' && allowed.includes('color') && colorMode !== 'descendants') {
      errors.push(`${id || `editable_blocks[${index}]`} 编辑组颜色时必须声明 colorMode: descendants`);
    }
    if (rawColorMode && !colorMode) errors.push(`${id || `editable_blocks[${index}]`} 的 colorMode 无效`);

    if (id && name && kind && selector && allowed.length) {
      blocks.push({ id, name, kind, selector, allowed, ...(colorMode ? { colorMode } : {}) });
    }
  });

  return {
    blocks,
    errors,
    isSemantic: blocks.length > 0 && errors.length === 0,
    isLegacy: false,
  };
}

export function createSparseBlockOverride(
  block: EditableBlock,
  property: EditableBlockProperty,
  value: EditableBlockValue,
): HtmlBlockOverrides {
  if (!block.allowed.includes(property)) {
    throw new Error(`${block.name} 不允许编辑 ${property}`);
  }
  if (block.kind === 'group' && property === 'color' && block.colorMode !== 'descendants') {
    throw new Error(`${block.name} 的组颜色编辑需要 colorMode: descendants`);
  }
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw new Error(`${block.name} 的 ${property} 必须是有限数值`);
  }
  return { [block.id]: { [property]: value } };
}

export function mergeSparseBlockOverrides(
  current: HtmlBlockOverrides,
  patch: HtmlBlockOverrides,
): HtmlBlockOverrides {
  const merged: HtmlBlockOverrides = { ...current };
  Object.entries(patch).forEach(([blockId, properties]) => {
    merged[blockId] = { ...(merged[blockId] ?? {}), ...properties };
  });
  return merged;
}

export function hasSparseBlockOverrides(overrides: HtmlBlockOverrides) {
  return Object.values(overrides).some((properties) => Object.keys(properties).length > 0);
}

export function semanticBlockText(customHtml: string, blockId: string) {
  const escapedId = blockId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matcher = new RegExp(
    `<([a-z][\\w:-]*)[^>]*data-ai-edit-block=(['"])${escapedId}\\2[^>]*>([\\s\\S]*?)<\\/\\1>`,
    'i',
  );
  const match = customHtml.match(matcher);
  return (match?.[3] ?? '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}
