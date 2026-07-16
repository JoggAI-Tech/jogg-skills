import assert from 'node:assert/strict';
import {
  activateGeneratedHtmlLayers,
  defaultHtmlLayerAdjust,
  ensureHtmlEditableBlocks,
  extractHtmlAdjustedBlockIds,
  extractHtmlEditableBlocks,
  replaceHtmlEditableBlockText,
  resolveHtmlPreviewSource,
  upsertHtmlBlockAdjustCss,
  upsertHtmlLayerAdjustCss,
} from './htmlEditor.ts';
import { mergeVideoStudioHtmlDesignOverrides, resolveVideoStudioHtmlClipState } from './model.ts';

assert.equal(
  activateGeneratedHtmlLayers('<main data-ai-generated-html="true"><div data-ai-generated-html="true"></div></main>'),
  '<main data-ai-generated-html="true" data-state="active"><div data-ai-generated-html="true" data-state="active"></div></main>',
);
assert.equal(
  activateGeneratedHtmlLayers('<main data-ai-generated-html="true" data-state="paused"></main>'),
  '<main data-ai-generated-html="true" data-state="paused"></main>',
);

assert.deepEqual(
  mergeVideoStudioHtmlDesignOverrides(
    { 'shot-01': { scene_design_spec: { custom_css: '.old-mask{}' } } },
    { 'shot-01': { scene_design_spec: { custom_html: '<main>edited</main>', custom_css: '.new-mask{}' } } },
  ),
  { 'shot-01': { scene_design_spec: { custom_html: '<main>edited</main>', custom_css: '.new-mask{}' } } },
);

assert.deepEqual(
  resolveHtmlPreviewSource({
    overrideHtml: '',
    overrideCss: '',
    generatedHtml: '',
    generatedCss: '',
    defaultHtml: '<main>default</main>',
    defaultCss: '.default{}',
  }),
  { html: '<main>default</main>', css: '.default{}', source: 'default' },
);

assert.deepEqual(
  resolveHtmlPreviewSource({
    overrideHtml: '',
    overrideCss: '',
    generatedHtml: '<main>new ai html</main>',
    generatedCss: '.new{}',
    defaultHtml: '<main>default</main>',
    defaultCss: '.default{}',
  }),
  { html: '<main>new ai html</main>', css: '.new{}', source: 'generated' },
);

assert.deepEqual(
  resolveHtmlPreviewSource({
    overrideHtml: '<main>edited</main>',
    overrideCss: '.edited{}',
    generatedHtml: '<main>new ai html</main>',
    generatedCss: '.new{}',
    defaultHtml: '<main>default</main>',
    defaultCss: '.default{}',
  }),
  { html: '<main>edited</main>', css: '.edited{}', source: 'override' },
);

assert.deepEqual(
  resolveHtmlPreviewSource({
    overrideHtml: '',
    overrideCss: '.edited{}',
    generatedHtml: '<main>new ai html</main>',
    generatedCss: '.new{}',
    defaultHtml: '<main>default</main>',
    defaultCss: '.default{}',
  }),
  { html: '<main>new ai html</main>', css: '.edited{}', source: 'override' },
);

assert.deepEqual(
  resolveVideoStudioHtmlClipState({
    clipId: 'mg-01',
    metric: { clip_id: 'mg-01', state: 'queued' },
  }),
  { state: 'queued', label: 'AI HTML 已入队', tone: 'pending', error: '', canRetry: false },
);

assert.deepEqual(
  resolveVideoStudioHtmlClipState({
    clipId: 'mg-01',
    metric: { clip_id: 'mg-01', state: 'ready' },
  }),
  { state: 'ready', label: 'AI HTML 已生成', tone: 'ready', error: '', canRetry: false },
);

assert.deepEqual(
  resolveVideoStudioHtmlClipState({
    clipId: 'mg-02',
    metric: { clip_id: 'mg-02', state: 'failed', error: '' },
    failedClipId: 'mg-02',
    failureError: '模型返回的 HTML 未通过校验',
    globalError: '批量生成失败',
  }),
  {
    state: 'failed',
    label: 'AI HTML 生成失败',
    tone: 'failed',
    error: '模型返回的 HTML 未通过校验',
    canRetry: true,
  },
);

assert.deepEqual(
  resolveVideoStudioHtmlClipState({
    clipId: 'mg-02',
    metric: { clip_id: 'mg-02', state: 'queued', error: '' },
    failedClipId: 'mg-02',
    failureError: '上一次生成失败',
  }),
  { state: 'queued', label: 'AI HTML 已入队', tone: 'pending', error: '', canRetry: false },
);

const html = ensureHtmlEditableBlocks('<div class="mg"><h2>植被退化</h2><p>压力转嫁给土地</p></div>');
assert.match(html, /data-ai-edit-block="block-1"/);
assert.match(html, /data-ai-edit-block="block-2"/);

const duplicateHtml = ensureHtmlEditableBlocks(
  '<div><span data-ai-edit-block="block-1">A</span><span data-ai-edit-block="block-1">B</span></div>',
);
assert.match(duplicateHtml, /class="ai-html-edit-block"/);
assert.match(duplicateHtml, /data-ai-edit-block="block-1"/);
assert.match(duplicateHtml, /data-ai-edit-block="block-1-2"/);

const mixedEditableHtml = ensureHtmlEditableBlocks(
  '<svg data-ai-edit-block="hero" data-ai-edit-kind="visual"><rect width="100" height="50"/></svg><h1>130</h1><p>资本关系</p>',
);
assert.match(mixedEditableHtml, /data-ai-edit-block="text-2"[^>]*>130<\/h1>/);
assert.match(mixedEditableHtml, /data-ai-edit-block="text-3"[^>]*>资本关系<\/p>/);
const mixedBlocks = extractHtmlEditableBlocks(mixedEditableHtml, '');
assert.equal(mixedBlocks.find((block) => block.id === 'text-2')?.text, '130');
assert.equal(mixedBlocks.find((block) => block.id === 'text-3')?.text, '资本关系');

const css = upsertHtmlBlockAdjustCss('', [
  {
    id: 'block-1',
    kind: 'text',
    name: '标题',
    tagName: 'span',
    text: '植被退化',
    x: 120,
    y: -40,
    width: 380,
    height: 90,
    rotate: -6,
    zIndex: 14,
    color: '#f8fafc',
    fontSize: 128,
    opacity: 0.82,
    hidden: false,
    locked: false,
    motion: 'scan',
    motionStart: 0.6,
    motionDuration: 1.4,
  },
]);

assert.match(css, /--ai-block-width:380px/);
assert.match(css, /--ai-block-height:90px/);
assert.match(css, /--ai-block-rotate:-6deg/);
assert.match(css, /--ai-block-z:14/);
assert.match(css, /animation-delay:0.6s/);
assert.match(css, /animation-duration:1.4s/);
assert.doesNotMatch(css, /font-size:calc\(1em/);
assert.match(css, /translate:var\(--ai-block-x\) var\(--ai-block-y\)/);
assert.match(css, /scale:calc\(var\(--ai-block-font-size\) \/ 100\)/);
assert.deepEqual([...extractHtmlAdjustedBlockIds(css)], ['block-1']);
assert.equal(upsertHtmlBlockAdjustCss(css, []), '');

const extracted = extractHtmlEditableBlocks(html, css);
assert.equal(extracted[0].width, 380);
assert.equal(extracted[0].height, 90);
assert.equal(extracted[0].rotate, -6);
assert.equal(extracted[0].zIndex, 14);
assert.equal(extracted[0].motionStart, 0.6);
assert.equal(extracted[0].motionDuration, 1.4);

const clearedHtml = replaceHtmlEditableBlockText(html, 'block-2', '');
assert.match(clearedHtml, /data-ai-edit-block="block-2"[^>]*><\/span>/);

const hiddenCss = upsertHtmlBlockAdjustCss(css, [{ ...extracted[0], hidden: true }]);
assert.match(hiddenCss, /visibility:hidden!important/);

const layerCss = upsertHtmlLayerAdjustCss('', {
  ...defaultHtmlLayerAdjust,
  x: 42,
  y: -24,
  scale: 1.12,
  opacity: 0.7,
  maskColor: '#111827',
  maskOpacity: 0.35,
  maskHeight: 18,
});
assert.match(layerCss, /--ai-layer-x: 2\.1875%/);
assert.match(layerCss, /--ai-layer-mask-opacity: 0.35/);
assert.doesNotMatch(layerCss, /z-index:\s*999/);
assert.match(layerCss, /isolation:\s*isolate/);
assert.match(layerCss, /\.ai-html-user-adjust::after[\s\S]*?z-index:\s*0/);
assert.match(layerCss, /:where\(\.ai-html-user-adjust\s*>\s*:not\(svg\)[\s\S]*?z-index:\s*1/);
assert.match(layerCss, /:where\(\.ai-html-user-adjust\s*>\s*svg\)[\s\S]*?z-index:\s*1/);

const visualHtml = ensureHtmlEditableBlocks('<svg viewBox="0 0 100 40"><path d="M0 20 C20 5 80 35 100 20" stroke="#eab308"/></svg>');
assert.match(visualHtml, /data-ai-edit-kind="visual"/);
const visualBlocks = extractHtmlEditableBlocks(visualHtml, '');
assert.ok(visualBlocks.some((block) => block.kind === 'visual' && block.tagName === 'path'));
const visualCss = upsertHtmlBlockAdjustCss('', [{ ...visualBlocks.find((block) => block.tagName === 'path')!, color: '#eab308', fontSize: 118 }]);
assert.match(visualCss, /stroke:var\(--ai-block-color\)!important/);
assert.match(visualCss, /scale:calc\(var\(--ai-block-font-size\) \/ 100\)/);

const denseSvg = `<svg>${Array.from({ length: 20 }, (_, index) => `<path data-ai-edit-block="visual-${index + 1}" data-ai-edit-kind="visual" d="M0 ${index} L100 ${index}"/>`).join('')}</svg><strong data-ai-edit-block="headline" data-ai-edit-kind="text">130</strong>`;
const denseBlocks = extractHtmlEditableBlocks(denseSvg, '');
assert.equal(denseBlocks[0].id, 'headline');
assert.ok(denseBlocks.some((block) => block.id === 'visual-20'));

console.log('video studio html editor test passed');
