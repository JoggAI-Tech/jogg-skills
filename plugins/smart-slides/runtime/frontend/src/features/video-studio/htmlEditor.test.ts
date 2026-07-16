import assert from 'node:assert/strict';
import {
  defaultHtmlLayerAdjust,
  ensureHtmlEditableBlocks,
  extractHtmlAdjustedBlockIds,
  extractHtmlEditableBlocks,
  replaceHtmlEditableBlockText,
  upsertHtmlBlockAdjustCss,
  upsertHtmlLayerAdjustCss,
} from './htmlEditor.ts';

const html = ensureHtmlEditableBlocks('<div class="mg"><h2>植被退化</h2><p>压力转嫁给土地</p></div>');
assert.match(html, /data-ai-edit-block="block-1"/);
assert.match(html, /data-ai-edit-block="block-2"/);

const duplicateHtml = ensureHtmlEditableBlocks(
  '<div><span data-ai-edit-block="block-1">A</span><span data-ai-edit-block="block-1">B</span></div>',
);
assert.match(duplicateHtml, /class="ai-html-edit-block"/);
assert.match(duplicateHtml, /data-ai-edit-block="block-1"/);
assert.match(duplicateHtml, /data-ai-edit-block="block-1-2"/);

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
assert.match(layerCss, /--ai-layer-x: 42px/);
assert.match(layerCss, /--ai-layer-mask-opacity: 0.35/);

const visualHtml = ensureHtmlEditableBlocks('<svg viewBox="0 0 100 40"><path d="M0 20 C20 5 80 35 100 20" stroke="#eab308"/></svg>');
assert.match(visualHtml, /data-ai-edit-kind="visual"/);
const visualBlocks = extractHtmlEditableBlocks(visualHtml, '');
assert.ok(visualBlocks.some((block) => block.kind === 'visual' && block.tagName === 'path'));
const visualCss = upsertHtmlBlockAdjustCss('', [{ ...visualBlocks.find((block) => block.tagName === 'path')!, color: '#eab308', fontSize: 118 }]);
assert.match(visualCss, /stroke:var\(--ai-block-color\)!important/);
assert.match(visualCss, /scale\(calc\(var\(--ai-block-font-size\) \/ 100\)\)/);

console.log('video studio html editor test passed');
