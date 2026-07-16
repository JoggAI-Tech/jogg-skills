import {
  createVideoStudioManifest,
  videoStudioEditorSideTools,
  videoStudioEditorTimelineLayers,
  videoStudioHtmlGenerationUiState,
  videoStudioProjectUrlWithId,
  videoStudioWorkflowStages,
} from './model.ts';

const manifest = createVideoStudioManifest({
  title: '上海咖啡店为什么越来越像共享办公室',
  brief: '上海咖啡店为什么越来越像共享办公室',
  format: 'short',
});

if (manifest.title !== '上海咖啡店为什么越来越像共享办公室') {
  throw new Error('manifest should keep the requested title');
}

if (manifest.script !== '') {
  throw new Error('empty UI manifest must not fake a generated script');
}

if (manifest.scene_groups.length !== 0) {
  throw new Error('empty UI manifest must not fake storyboard shots');
}

if (manifest.design_plan.scenes.length !== 0 || manifest.information_layer.length !== 0 || manifest.scene_plan_v2.length !== 0) {
  throw new Error('empty UI manifest must not fake render contracts');
}

if (manifest.render_manifest !== null) {
  throw new Error('empty UI manifest must not fake a render manifest');
}

if (manifest.director_document.summary !== '') {
  throw new Error('empty UI manifest must not fake a director document');
}

const serializedManifest = JSON.stringify(manifest);
for (const staleTemplateTerm of ['清晨喝水', '水杯', '缺水', '人体循环可视化']) {
  if (serializedManifest.includes(staleTemplateTerm)) {
    throw new Error(`empty UI manifest must not contain stale template content: ${staleTemplateTerm}`);
  }
}

if (manifest.production_format !== 'broll_html') {
  throw new Error('manifest should keep the selected production format');
}

if (manifest.aspect_ratio !== '16:9') {
  throw new Error('Video Studio manifest should default to the 16:9 long-video canvas');
}

if (manifest.avatar.id !== 'avatar-default-presenter') {
  throw new Error('manifest should include default avatar');
}

if (manifest.voice.id !== 'voice-clear-male') {
  throw new Error('manifest should include default voice');
}

if (!manifest.timeline_tracks.some((track) => track.kind === 'html_mg')) {
  throw new Error('fallback UI config should expose an HTML/MG track for projects that generate it');
}

const stageIds = videoStudioWorkflowStages.map((stage) => stage.id).join('>');
if (stageIds !== 'topic>producer>requirements>creative_plan>storyboard>editor') {
  throw new Error('workflow should follow the governed long-video production progression');
}

const timelineLayerIds = videoStudioEditorTimelineLayers.map((layer) => layer.id).join('>');
if (timelineLayerIds !== 'overview>html>broll') {
  throw new Error('editor timeline should expose overview, HTML, and B-roll as the only bottom-layer interactions');
}

const sideToolIds = videoStudioEditorSideTools.map((tool) => tool.id).join('>');
if (sideToolIds !== 'avatar>bgm') {
  throw new Error('editor side toolbar should only keep avatar and background music controls');
}

const runningHtmlState = videoStudioHtmlGenerationUiState({
  state: 'running',
  started_at: '2026-07-07T12:00:00Z',
  total: 8,
  completed: 3,
});
if (runningHtmlState.progressPercent !== 38 || !runningHtmlState.message.includes('3/8')) {
  throw new Error('AI HTML running state should expose visible progress instead of a vague badge');
}

const readyHtmlState = videoStudioHtmlGenerationUiState({ state: 'ready', total: 8, completed: 8 });
if (readyHtmlState.progressPercent !== 100 || !readyHtmlState.message.includes('已生成')) {
  throw new Error('AI HTML ready state should be explicit after refresh or polling');
}

const projectUrl = videoStudioProjectUrlWithId('http://127.0.0.1:5174/tools/video-studio?foo=bar', 'project-123');
if (projectUrl !== 'http://127.0.0.1:5174/tools/video-studio?foo=bar&project_id=project-123') {
  throw new Error('project URL should preserve existing query params and append project_id immediately');
}

const replacedProjectUrl = videoStudioProjectUrlWithId('http://127.0.0.1:5174/tools/video-studio?project_id=old', 'project-456');
if (replacedProjectUrl !== 'http://127.0.0.1:5174/tools/video-studio?project_id=project-456') {
  throw new Error('project URL should replace stale project_id');
}

const brollOnlyManifest = createVideoStudioManifest({
  title: '纯素材版本',
  brief: '只用 B-roll 画面表达。',
  production_format: 'broll',
});

const brollOnlyHtmlLayers = brollOnlyManifest.scene_groups.flatMap((group) => group.html_layers);
if (brollOnlyHtmlLayers.length !== 0) {
  throw new Error('pure B-roll production should not include HTML/MG layers');
}

if (brollOnlyManifest.timeline_tracks.some((track) => track.kind === 'html_mg')) {
  throw new Error('pure B-roll production should not expose an HTML/MG timeline track');
}

const defaultOptions = brollOnlyManifest.scene_groups.flatMap((group) => group.shots).flatMap((shot) => shot.broll_options);
if (defaultOptions.some((option) => option.asset_url || option.asset_path)) {
  throw new Error('default B-roll options must not pretend to have generated media assets');
}

console.log('video studio model test passed');
