import assert from 'node:assert/strict';

import {
  createSparseBlockOverride,
  mergeSparseBlockOverrides,
  normalizeEditSchema,
} from './editSchema.ts';

const schema = normalizeEditSchema({
  editable_blocks: [
    {
      id: 'headline',
      name: '主标题',
      kind: 'text',
      selector: "[data-ai-edit-block='headline']",
      allowed: ['text', 'x', 'fontSize', 'color'],
    },
    {
      id: 'hero',
      name: '主视觉',
      kind: 'visual',
      selector: "[data-ai-edit-block='hero']",
      allowed: ['x', 'scale', 'opacity'],
    },
  ],
});

assert.equal(schema.isSemantic, true);
assert.deepEqual(schema.errors, []);
assert.deepEqual(schema.blocks[0].allowed, ['text', 'x', 'fontSize', 'color']);

const duplicate = normalizeEditSchema({
  editable_blocks: [
    { id: 'headline', name: '标题一', kind: 'text', selector: '.one', allowed: ['text'] },
    { id: 'headline', name: '标题二', kind: 'text', selector: '.two', allowed: ['text'] },
  ],
});
assert.equal(duplicate.isSemantic, false);
assert.match(duplicate.errors.join('\n'), /重复.*headline/);

const descendant = normalizeEditSchema({
  editable_blocks: [
    { id: 'nested', name: '嵌套节点', kind: 'visual', selector: '.hero path', allowed: ['color'] },
  ],
});
assert.equal(descendant.isSemantic, false);
assert.match(descendant.errors.join('\n'), /简单 selector/);

const groupWithoutPropagation = normalizeEditSchema({
  editable_blocks: [
    { id: 'cluster', name: '节点组', kind: 'group', selector: '.cluster', allowed: ['color'] },
  ],
});
assert.equal(groupWithoutPropagation.isSemantic, false);
assert.match(groupWithoutPropagation.errors.join('\n'), /colorMode.*descendants/);

const headline = schema.blocks[0];
const xOnly = createSparseBlockOverride(headline, 'x', 120);
assert.deepEqual(xOnly, { headline: { x: 120 } });
assert.deepEqual(Object.keys(xOnly.headline), ['x']);
assert.equal('color' in xOnly.headline, false);
assert.equal('opacity' in xOnly.headline, false);
assert.equal('motion' in xOnly.headline, false);
assert.equal('width' in xOnly.headline, false);
assert.equal('height' in xOnly.headline, false);

assert.deepEqual(
  mergeSparseBlockOverrides(
    { headline: { x: 120 } },
    createSparseBlockOverride(headline, 'text', '基础设施竞争'),
  ),
  { headline: { x: 120, text: '基础设施竞争' } },
);

assert.throws(() => createSparseBlockOverride(headline, 'opacity', 0.5), /不允许编辑 opacity/);

const legacy = normalizeEditSchema({ editable_text_selectors: ['.title'] });
assert.equal(legacy.isSemantic, false);
assert.equal(legacy.isLegacy, true);
assert.deepEqual(legacy.errors, []);

const emptySemantic = normalizeEditSchema({ version: 'edit_schema_v2', editable_blocks: [] });
assert.equal(emptySemantic.isSemantic, false);
assert.equal(emptySemantic.isLegacy, false);
assert.match(emptySemantic.errors.join('\n'), /editable_blocks 不能为空/);

console.log('editSchema tests passed');
