export type HtmlEditableBlockMotion = 'fade' | 'slide' | 'pop' | 'scan' | 'rise' | 'wipe' | 'none';
export type HtmlEditableBlockKind = 'text' | 'visual';

export type HtmlEditableBlock = {
  id: string;
  kind: HtmlEditableBlockKind;
  name: string;
  tagName: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotate: number;
  zIndex: number;
  color: string;
  fontSize: number;
  opacity: number;
  hidden: boolean;
  locked: boolean;
  motion: HtmlEditableBlockMotion;
  motionStart: number;
  motionDuration: number;
};

export type HtmlLayerAdjust = {
  x: number;
  y: number;
  scale: number;
  opacity: number;
  maskColor: string;
  maskOpacity: number;
  maskHeight: number;
};

type HtmlTextSegment = {
  index: number;
  text: string;
};

export const htmlLayerAdjustClass = 'ai-html-user-adjust';
export const htmlEditableBlockClass = 'ai-html-edit-block';
export const defaultHtmlLayerAdjust: HtmlLayerAdjust = {
  x: 0,
  y: 0,
  scale: 1,
  opacity: 1,
  maskColor: '#020617',
  maskOpacity: 0,
  maskHeight: 26,
};
export const defaultBlockColor = '#ffffff';
export const htmlMotionPresets: Array<{ value: HtmlEditableBlockMotion; label: string }> = [
  { value: 'fade', label: '淡入' },
  { value: 'slide', label: '滑入' },
  { value: 'rise', label: '上浮' },
  { value: 'wipe', label: '擦除' },
  { value: 'pop', label: '弹出' },
  { value: 'scan', label: '扫描揭示' },
  { value: 'none', label: '无' },
];

const htmlLayerAdjustStart = '/* hermes-html-layer-adjust:start */';
const htmlLayerAdjustEnd = '/* hermes-html-layer-adjust:end */';
const htmlBlockAdjustStart = '/* hermes-html-block-adjust:start */';
const htmlBlockAdjustEnd = '/* hermes-html-block-adjust:end */';
const visualEditableTags = new Set(['svg', 'path', 'polyline', 'line', 'circle', 'ellipse', 'rect', 'polygon', 'g']);

export function clampNumber(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function escapeHtmlText(value?: string | number) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function extractHtmlTextSegments(htmlSource: string): HtmlTextSegment[] {
  const segments: HtmlTextSegment[] = [];
  const matcher = />\s*([^<>{}][^<>]*?)\s*</g;
  let match: RegExpExecArray | null;
  while ((match = matcher.exec(htmlSource)) !== null) {
    const text = match[1].replace(/\s+/g, ' ').trim();
    if (!text || /^[;:,.，。！？、\s]+$/.test(text)) continue;
    segments.push({ index: match.index + match[0].indexOf(match[1]), text });
  }
  return segments.slice(0, 16);
}

function decodeHtmlText(value: string) {
  return value
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

export function ensureHtmlEditableBlocks(htmlSource: string) {
  if (htmlSource.includes(`data-ai-edit-block=`)) {
    const existingBlockCount = (htmlSource.match(/data-ai-edit-block=/g) ?? []).length;
    return normalizeHtmlEditableBlockTags(ensureHtmlVisualEditableBlocks(htmlSource, existingBlockCount));
  }
  const segments = extractHtmlTextSegments(htmlSource);
  let nextHtml = htmlSource;
  [...segments].reverse().forEach((segment, reverseIndex) => {
    const blockIndex = segments.length - reverseIndex;
    const blockId = `block-${blockIndex}`;
    const wrapped = `<span class="${htmlEditableBlockClass}" data-ai-edit-block="${blockId}" data-ai-edit-kind="text" data-ai-edit-name="文字 ${blockIndex}">${escapeHtmlText(segment.text)}</span>`;
    nextHtml = `${nextHtml.slice(0, segment.index)}${wrapped}${nextHtml.slice(segment.index + segment.text.length)}`;
  });
  return normalizeHtmlEditableBlockTags(ensureHtmlVisualEditableBlocks(nextHtml, segments.length));
}

function ensureClassName(attrSource: string, className: string) {
  const classMatcher = /\sclass=(["'])(.*?)\1/i;
  const classMatch = attrSource.match(classMatcher);
  if (!classMatch) return `${attrSource} class="${className}"`;
  if (new RegExp(`\\b${escapeRegExp(className)}\\b`).test(classMatch[2])) return attrSource;
  return attrSource.replace(classMatch[0], ` class=${classMatch[1]}${classMatch[2]} ${className}${classMatch[1]}`);
}

function normalizeHtmlEditableBlockTags(htmlSource: string) {
  const usedIds = new Set<string>();
  return htmlSource.replace(
    /<([a-z][\w:-]*)([^>]*data-ai-edit-block=(["'])(.*?)\3[^>]*)>/gi,
    (match, tagName: string, attrs: string, quote: string, rawId: string) => {
      if (/^(html|head|body|style|script|iframe|link|meta)$/i.test(tagName)) return match;
      const baseId = String(rawId || '').trim() || 'block';
      let nextId = baseId;
      let suffix = 2;
      while (usedIds.has(nextId)) {
        nextId = `${baseId}-${suffix}`;
        suffix += 1;
      }
      usedIds.add(nextId);
      const visualTag = visualEditableTags.has(tagName.toLowerCase());
      const selfClosing = /\/\s*$/.test(attrs);
      let nextAttrs = attrs.replace(/\/\s*$/, '').replace(/data-ai-edit-block=(["']).*?\1/i, `data-ai-edit-block=${quote}${nextId}${quote}`);
      nextAttrs = ensureClassName(nextAttrs, htmlEditableBlockClass);
      if (!/\sdata-ai-edit-kind=(["']).*?\1/i.test(nextAttrs)) {
        nextAttrs = `${nextAttrs} data-ai-edit-kind="${visualTag ? 'visual' : 'text'}"`;
      }
      if (!/\sdata-ai-edit-name=(["']).*?\1/i.test(nextAttrs)) {
        nextAttrs = `${nextAttrs} data-ai-edit-name="${visualTag ? visualBlockName(tagName, nextId) : nextId}"`;
      }
      return `<${tagName}${nextAttrs}${selfClosing ? ' /' : ''}>`;
    },
  );
}

function ensureHtmlVisualEditableBlocks(htmlSource: string, textBlockCount: number) {
  let visualIndex = 0;
  return htmlSource.replace(
    /<(?!(?:\/|html|head|body|style|script|iframe|link|meta)\b)(svg|path|polyline|line|circle|ellipse|rect|polygon|g)(\s[^<>]*?)?>/gi,
    (match, tagName: string, attrs = '') => {
      if (/data-ai-edit-block=(["']).*?\1/i.test(attrs)) return match;
      const lowerTag = tagName.toLowerCase();
      if (lowerTag === 'g' && !/\b(class|id)=/i.test(attrs)) return match;
      visualIndex += 1;
      if (visualIndex > 16) return match;
      const blockId = `visual-${textBlockCount + visualIndex}`;
      const selfClosing = /\/\s*$/.test(attrs);
      const cleanAttrs = (attrs || '').replace(/\/\s*$/, '');
      const nextAttrs = ensureClassName(cleanAttrs, htmlEditableBlockClass);
      return `<${tagName}${nextAttrs} data-ai-edit-block="${blockId}" data-ai-edit-kind="visual" data-ai-edit-name="${visualBlockName(tagName, blockId)}"${selfClosing ? ' /' : ''}>`;
    },
  );
}

function readAttr(attrs: string, name: string) {
  const match = attrs.match(new RegExp(`\\s${escapeRegExp(name)}=(["'])(.*?)\\1`, 'i'));
  return match?.[2] ?? '';
}

function visualBlockName(tagName: string, id: string) {
  const tag = tagName.toLowerCase();
  if (tag === 'path' || tag === 'polyline' || tag === 'line') return '路径 / 线条';
  if (tag === 'circle' || tag === 'ellipse') return '节点 / 圆点';
  if (tag === 'rect' || tag === 'polygon') return '形状块';
  if (tag === 'svg' || tag === 'g') return '视觉组合';
  return id;
}

export function extractHtmlEditableBlocks(htmlSource: string, cssSource: string): HtmlEditableBlock[] {
  const blocks: HtmlEditableBlock[] = [];
  const matcher = new RegExp(`<([a-z][\\w:-]*)([^>]*data-ai-edit-block=(["'])(.*?)\\3[^>]*)>([\\s\\S]*?)(?:<\\/\\1>)?`, 'gi');
  let match: RegExpExecArray | null;
  while ((match = matcher.exec(htmlSource)) !== null) {
    const tagName = match[1].toLowerCase();
    const attrs = match[2] ?? '';
    const id = match[4];
    const kind = (readAttr(attrs, 'data-ai-edit-kind') === 'visual' || visualEditableTags.has(tagName) ? 'visual' : 'text') as HtmlEditableBlockKind;
    const rawText = (match[5] ?? '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
    if (!id) continue;
    const escapedId = escapeRegExp(id);
    const selectorPattern = new RegExp(`\\.${htmlEditableBlockClass}\\[data-ai-edit-block=["']${escapedId}["']\\]\\s*\\{([\\s\\S]*?)\\}`, 'i');
    const cssMatch = cssSource.match(selectorPattern);
    const blockCss = cssMatch?.[1] ?? '';
    const readNumber = (name: string, fallback: number, min: number, max: number) => {
      const valueMatch = blockCss.match(new RegExp(`${escapeRegExp(name)}\\s*:\\s*(-?\\d+(?:\\.\\d+)?)`));
      return clampNumber(valueMatch ? Number(valueMatch[1]) : fallback, min, max);
    };
    const colorMatch = blockCss.match(/--ai-block-color\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|[a-zA-Z]+)|(?:color|stroke|fill)\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|[a-zA-Z]+)\s*!?/);
    const motionMatch = blockCss.match(/--ai-block-motion\s*:\s*([a-z]+)/);
    const hidden = /visibility\s*:\s*hidden/i.test(blockCss) || /display\s*:\s*none/i.test(blockCss);
    const locked = /--ai-block-locked\s*:\s*1/.test(blockCss);
    blocks.push({
      id,
      kind,
      name: readAttr(attrs, 'data-ai-edit-name') || (kind === 'visual' ? visualBlockName(tagName, id) : `文字 ${blocks.length + 1}`),
      tagName,
      text: decodeHtmlText(rawText),
      x: readNumber('--ai-block-x', 0, -960, 960),
      y: readNumber('--ai-block-y', 0, -540, 540),
      width: readNumber('--ai-block-width', 260, 40, 960),
      height: readNumber('--ai-block-height', 72, 24, 540),
      rotate: readNumber('--ai-block-rotate', 0, -45, 45),
      zIndex: Math.round(readNumber('--ai-block-z', blocks.length + 1, 0, 999)),
      color: colorMatch?.[1] ?? colorMatch?.[2] ?? defaultBlockColor,
      fontSize: readNumber('--ai-block-font-size', 100, 50, 220),
      opacity: readNumber('--ai-block-opacity', 1, 0, 1),
      hidden,
      locked,
      motion: (htmlMotionPresets.some((preset) => preset.value === motionMatch?.[1]) ? motionMatch?.[1] : 'fade') as HtmlEditableBlockMotion,
      motionStart: readNumber('--ai-block-motion-start', blocks.length * 0.08, 0, 60),
      motionDuration: readNumber('--ai-block-motion-duration', 0.58, 0.05, 12),
    });
  }
  return blocks.slice(0, 16);
}

export function extractHtmlAdjustedBlockIds(cssSource: string) {
  const ids = new Set<string>();
  const blockMatcher = new RegExp(`${escapeRegExp(htmlBlockAdjustStart)}[\\s\\S]*?${escapeRegExp(htmlBlockAdjustEnd)}`, 'm');
  const cssBlock = cssSource.match(blockMatcher)?.[0] ?? '';
  const selectorMatcher = new RegExp(`\\.${htmlEditableBlockClass}\\[data-ai-edit-block=(["'])(.*?)\\1\\]`, 'g');
  let match: RegExpExecArray | null;
  while ((match = selectorMatcher.exec(cssBlock)) !== null) {
    if (match[2]) ids.add(match[2]);
  }
  return ids;
}

export function replaceHtmlEditableBlockText(htmlSource: string, blockId: string, nextText: string) {
  const matcher = new RegExp(`(<([a-z][\\w:-]*)[^>]*data-ai-edit-block=(["'])${escapeRegExp(blockId)}\\3[^>]*>)([\\s\\S]*?)(<\\/\\2>)`, 'i');
  return htmlSource.replace(matcher, `$1${escapeHtmlText(nextText)}$5`);
}

export function upsertHtmlBlockAdjustCss(cssSource: string, blocks: HtmlEditableBlock[]) {
  const matcher = new RegExp(`${escapeRegExp(htmlBlockAdjustStart)}[\\s\\S]*?${escapeRegExp(htmlBlockAdjustEnd)}`, 'm');
  if (!blocks.length) return cssSource.replace(matcher, '').trim();

  const blockCss = blocks
    .map((block) => {
      const x = Math.round(clampNumber(block.x, -960, 960));
      const y = Math.round(clampNumber(block.y, -540, 540));
      const width = Math.round(clampNumber(block.width, 40, 960));
      const height = Math.round(clampNumber(block.height, 24, 540));
      const rotate = Math.round(clampNumber(block.rotate, -45, 45));
      const zIndex = Math.round(clampNumber(block.zIndex, 0, 999));
      const fontSize = Math.round(clampNumber(block.fontSize, 50, 220));
      const opacity = Number(clampNumber(block.opacity, 0, 1).toFixed(2));
      const color = block.color || defaultBlockColor;
      const motion = htmlMotionPresets.some((preset) => preset.value === block.motion) ? block.motion : 'fade';
      const motionStart = Number(clampNumber(block.motionStart, 0, 60).toFixed(2));
      const motionDuration = Number(clampNumber(block.motionDuration, 0.05, 12).toFixed(2));
      const animationName = {
        fade: 'aiBlockFade',
        slide: 'aiBlockSlide',
        rise: 'aiBlockRise',
        wipe: 'aiBlockWipe',
        pop: 'aiBlockPop',
        scan: 'aiBlockScan',
        none: 'none',
      }[motion];
      const animation =
        motion === 'none'
          ? 'none'
          : `${animationName} var(--ai-block-motion-duration) cubic-bezier(.2,.8,.2,1) both`;
      if (block.kind === 'visual') {
        const lineLike = ['path', 'polyline', 'line'].includes(block.tagName);
        const visualPaint = lineLike ? `stroke:var(--ai-block-color)!important;fill:none!important;stroke-width:max(2px,calc(var(--ai-block-height) / 18))!important;` : `fill:var(--ai-block-color)!important;stroke:var(--ai-block-color)!important;`;
        return `.${htmlEditableBlockClass}[data-ai-edit-block="${block.id}"]{--ai-block-x:${x}px;--ai-block-y:${y}px;--ai-block-width:${width}px;--ai-block-height:${height}px;--ai-block-rotate:${rotate}deg;--ai-block-z:${zIndex};--ai-block-font-size:${fontSize};--ai-block-opacity:${opacity};--ai-block-color:${color};--ai-block-motion:${motion};--ai-block-motion-start:${motionStart};--ai-block-motion-duration:${motionDuration}s;--ai-block-locked:${block.locked ? 1 : 0};opacity:var(--ai-block-opacity)!important;visibility:${block.hidden ? 'hidden' : 'visible'}!important;z-index:var(--ai-block-z)!important;transform-box:fill-box!important;transform-origin:center!important;transform:translate3d(var(--ai-block-x),var(--ai-block-y),0) rotate(var(--ai-block-rotate)) scale(calc(var(--ai-block-font-size) / 100))!important;${visualPaint}filter:drop-shadow(0 0 calc(var(--ai-block-height) / 12) color-mix(in srgb,var(--ai-block-color),transparent 55%));animation:${animation};animation-delay:${motionStart}s;animation-duration:${motionDuration}s;}`;
      }
      return `.${htmlEditableBlockClass}[data-ai-edit-block="${block.id}"]{--ai-block-x:${x}px;--ai-block-y:${y}px;--ai-block-width:${width}px;--ai-block-height:${height}px;--ai-block-rotate:${rotate}deg;--ai-block-z:${zIndex};--ai-block-font-size:${fontSize};--ai-block-opacity:${opacity};--ai-block-color:${color};--ai-block-motion:${motion};--ai-block-motion-start:${motionStart};--ai-block-motion-duration:${motionDuration}s;--ai-block-locked:${block.locked ? 1 : 0};display:inline-flex!important;align-items:center!important;position:relative!important;box-sizing:border-box!important;min-width:0!important;max-width:var(--ai-block-width)!important;min-height:0!important;color:var(--ai-block-color)!important;font-size:calc(1em * var(--ai-block-font-size) / 100)!important;opacity:var(--ai-block-opacity)!important;visibility:${block.hidden ? 'hidden' : 'visible'}!important;z-index:var(--ai-block-z)!important;transform:translate3d(var(--ai-block-x),var(--ai-block-y),0) rotate(var(--ai-block-rotate))!important;animation:${animation};animation-delay:${motionStart}s;animation-duration:${motionDuration}s;}`;
    })
    .join('\n');
  const baseCss = `.${htmlEditableBlockClass}{will-change:transform,opacity,color;font:inherit;pointer-events:auto}
@keyframes aiBlockFade{from{opacity:0}to{opacity:var(--ai-block-opacity,1)}}
@keyframes aiBlockSlide{from{opacity:0;transform:translate3d(calc(var(--ai-block-x,0px) - 34px),calc(var(--ai-block-y,0px) + 18px),0) rotate(var(--ai-block-rotate,0deg))}to{opacity:var(--ai-block-opacity,1);transform:translate3d(var(--ai-block-x,0px),var(--ai-block-y,0px),0) rotate(var(--ai-block-rotate,0deg))}}
@keyframes aiBlockRise{from{opacity:0;transform:translate3d(var(--ai-block-x,0px),calc(var(--ai-block-y,0px) + 42px),0) rotate(var(--ai-block-rotate,0deg))}to{opacity:var(--ai-block-opacity,1);transform:translate3d(var(--ai-block-x,0px),var(--ai-block-y,0px),0) rotate(var(--ai-block-rotate,0deg))}}
@keyframes aiBlockWipe{from{opacity:var(--ai-block-opacity,1);clip-path:inset(0 100% 0 0)}to{opacity:var(--ai-block-opacity,1);clip-path:inset(0 0 0 0)}}
@keyframes aiBlockPop{from{opacity:0;transform:translate3d(var(--ai-block-x,0px),var(--ai-block-y,0px),0) rotate(var(--ai-block-rotate,0deg)) scale(.86)}to{opacity:var(--ai-block-opacity,1);transform:translate3d(var(--ai-block-x,0px),var(--ai-block-y,0px),0) rotate(var(--ai-block-rotate,0deg)) scale(1)}}
@keyframes aiBlockScan{0%{opacity:0;clip-path:inset(0 100% 0 0)}100%{opacity:var(--ai-block-opacity,1);clip-path:inset(0 0 0 0)}}`;
  const block = `${htmlBlockAdjustStart}\n${baseCss}\n${blockCss}\n${htmlBlockAdjustEnd}`;
  return `${cssSource.replace(matcher, '').trim()}\n\n${block}`.trim();
}

export function readHtmlLayerAdjustCss(cssSource: string): HtmlLayerAdjust {
  const readVar = (name: string, fallback: number) => {
    const match = cssSource.match(new RegExp(`${escapeRegExp(name)}\\s*:\\s*(-?\\d+(?:\\.\\d+)?)`));
    return match ? Number(match[1]) : fallback;
  };
  const readColorVar = (name: string, fallback: string) => {
    const match = cssSource.match(new RegExp(`${escapeRegExp(name)}\\s*:\\s*(#[0-9a-fA-F]{3,8}|rgba?\\([^)]+\\)|[a-zA-Z]+)`));
    return match ? match[1] : fallback;
  };
  return {
    x: clampNumber(readVar('--ai-layer-x', defaultHtmlLayerAdjust.x), -960, 960),
    y: clampNumber(readVar('--ai-layer-y', defaultHtmlLayerAdjust.y), -540, 540),
    scale: clampNumber(readVar('--ai-layer-scale', defaultHtmlLayerAdjust.scale), 0.2, 2.4),
    opacity: clampNumber(readVar('--ai-layer-opacity', defaultHtmlLayerAdjust.opacity), 0, 1),
    maskColor: readColorVar('--ai-layer-mask-color', defaultHtmlLayerAdjust.maskColor),
    maskOpacity: clampNumber(readVar('--ai-layer-mask-opacity', defaultHtmlLayerAdjust.maskOpacity), 0, 0.9),
    maskHeight: clampNumber(readVar('--ai-layer-mask-height', defaultHtmlLayerAdjust.maskHeight), 0, 70),
  };
}

export function ensureHtmlRootClass(htmlSource: string, className: string) {
  if (!htmlSource.trim()) return `<div class="${className}"></div>`;
  const classMatcher = new RegExp(`class=(["'])[^"']*\\b${className}\\b[^"']*\\1`, 'i');
  if (classMatcher.test(htmlSource)) return htmlSource;
  const openingTagMatcher = /<([a-z][\w:-]*)(\s[^<>]*)?>/i;
  const openingMatch = htmlSource.match(openingTagMatcher);
  if (!openingMatch) {
    return `<div class="${className}">${htmlSource}</div>`;
  }
  if (/^(html|head|body|style|script|iframe|link|meta)$/i.test(openingMatch[1])) {
    return `<div class="${className}">${htmlSource}</div>`;
  }
  return htmlSource.replace(openingTagMatcher, (match, tagName: string, attrs = '') => {
    const classAttrMatcher = /\sclass=(["'])(.*?)\1/i;
    const classMatch = attrs.match(classAttrMatcher);
    if (classMatch) {
      return match.replace(classMatch[0], ` class=${classMatch[1]}${classMatch[2]} ${className}${classMatch[1]}`);
    }
    return `<${tagName}${attrs} class="${className}">`;
  });
}

export function upsertHtmlLayerAdjustCss(cssSource: string, adjust: HtmlLayerAdjust) {
  const nextAdjust = {
    x: Math.round(clampNumber(adjust.x, -960, 960)),
    y: Math.round(clampNumber(adjust.y, -540, 540)),
    scale: Number(clampNumber(adjust.scale, 0.2, 2.4).toFixed(2)),
    opacity: Number(clampNumber(adjust.opacity, 0, 1).toFixed(2)),
    maskColor: /^#[0-9a-fA-F]{6}$/.test(adjust.maskColor) ? adjust.maskColor : defaultHtmlLayerAdjust.maskColor,
    maskOpacity: Number(clampNumber(adjust.maskOpacity, 0, 0.9).toFixed(2)),
    maskHeight: Math.round(clampNumber(adjust.maskHeight, 0, 70)),
  };
  const block = `${htmlLayerAdjustStart}
.${htmlLayerAdjustClass} {
  --ai-layer-x: ${nextAdjust.x}px;
  --ai-layer-y: ${nextAdjust.y}px;
  --ai-layer-scale: ${nextAdjust.scale};
  --ai-layer-opacity: ${nextAdjust.opacity};
  --ai-layer-mask-color: ${nextAdjust.maskColor};
  --ai-layer-mask-opacity: ${nextAdjust.maskOpacity};
  --ai-layer-mask-height: ${nextAdjust.maskHeight}%;
  position: relative !important;
  transform: translate3d(var(--ai-layer-x), var(--ai-layer-y), 0) scale(var(--ai-layer-scale)) !important;
  transform-origin: center center !important;
  opacity: var(--ai-layer-opacity) !important;
}
.${htmlLayerAdjustClass}::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: var(--ai-layer-mask-height);
  pointer-events: none;
  background: linear-gradient(0deg, var(--ai-layer-mask-color), transparent);
  opacity: var(--ai-layer-mask-opacity);
  z-index: 999;
}
${htmlLayerAdjustEnd}`;
  const blockMatcher = new RegExp(`${escapeRegExp(htmlLayerAdjustStart)}[\\s\\S]*?${escapeRegExp(htmlLayerAdjustEnd)}`, 'm');
  return `${cssSource.replace(blockMatcher, '').trim()}\n\n${block}`.trim();
}
