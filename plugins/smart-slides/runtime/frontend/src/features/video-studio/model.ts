export type VideoStudioFormat = 'short' | 'long';
export type VideoStudioWorkflowStageId = 'topic' | 'producer' | 'requirements' | 'creative_plan' | 'script' | 'format' | 'director_doc' | 'storyboard' | 'editor';
export type VideoStudioProductionFormat = 'broll' | 'broll_html';
export type VideoStudioScriptStyle = 'adaptive_podcast' | 'storytelling_podcast' | 'debate_podcast';
export type VideoStudioLanguage = 'zh' | 'en';
export type VideoStudioSceneRole = 'broll_backdrop_overlay' | 'full_broll' | 'avatar_only';
export type VideoStudioVisualRole = 'hybrid_broll_html' | 'broll_primary' | 'avatar_primary';
export type VideoStudioMgVisualSystem = 'metric' | 'causal' | 'route' | 'timeline' | 'comparison' | string;
export type VideoStudioEditorTimelineLayerId = 'overview' | 'html' | 'broll';
export type VideoStudioEditorSideToolId = 'avatar' | 'bgm';

export interface VideoStudioWorkflowStage {
  id: VideoStudioWorkflowStageId;
  label: string;
  description: string;
}

export interface VideoStudioEditorTimelineLayer {
  id: VideoStudioEditorTimelineLayerId;
  label: string;
  description: string;
}

export interface VideoStudioEditorSideTool {
  id: VideoStudioEditorSideToolId;
  label: string;
}

export interface VideoStudioHtmlGenerationStatusInput {
  state?: string;
  error?: string;
  started_at?: string;
  finished_at?: string;
  total?: number;
  completed?: number;
  current_clip_id?: string;
  completed_clip_id?: string;
  failed_clip_id?: string;
  message?: string;
  manual_regeneration?: boolean;
}

export interface VideoStudioHtmlGenerationUiState {
  state: 'idle' | 'running' | 'ready' | 'failed' | 'skipped' | string;
  message: string;
  progressPercent: number;
  isBlockingPreview: boolean;
}

export const videoStudioEditorTimelineLayers: VideoStudioEditorTimelineLayer[] = [
  { id: 'overview', label: '画面总览', description: '选择分镜并查看当前合成画面。' },
  { id: 'html', label: 'HTML 编辑', description: '打开当前分镜或跨分镜 MG/HTML 设计。' },
  { id: 'broll', label: '换 B-roll', description: '打开当前分镜的素材候选和下载入口。' },
];

export const videoStudioEditorSideTools: VideoStudioEditorSideTool[] = [
  { id: 'avatar', label: '数字人' },
  { id: 'bgm', label: '背景音乐' },
];

export function videoStudioHtmlGenerationUiState(status?: VideoStudioHtmlGenerationStatusInput | null): VideoStudioHtmlGenerationUiState {
  const state = status?.state || 'idle';
  const total = Math.max(0, Math.round(Number(status?.total ?? 0)));
  const completed = Math.min(total, Math.max(0, Math.round(Number(status?.completed ?? 0))));
  if (state === 'running') {
    const progressPercent = total > 0 ? Math.round((completed / total) * 100) : 15;
    const countLabel = total > 0 ? `${completed}/${total}` : '生成中';
    return {
      state,
      progressPercent,
      isBlockingPreview: true,
      message: `AI HTML 正在生成 · ${countLabel}`,
    };
  }
  if (state === 'ready') {
    return {
      state,
      progressPercent: 100,
      isBlockingPreview: false,
      message: total > 0 ? `AI HTML 已生成 · ${total}/${total}` : 'AI HTML 已生成',
    };
  }
  if (state === 'failed') {
    return {
      state,
      progressPercent: 100,
      isBlockingPreview: false,
      message: `AI HTML 生成失败${status?.error ? `：${status.error}` : ''}`,
    };
  }
  if (state === 'skipped') {
    return {
      state,
      progressPercent: 100,
      isBlockingPreview: false,
      message: '当前项目不需要 AI HTML 生成',
    };
  }
  return {
    state,
    progressPercent: 0,
    isBlockingPreview: false,
    message: 'AI HTML 等待生成',
  };
}

export function videoStudioProjectUrlWithId(currentHref: string, projectId: string): string {
  const url = new URL(currentHref);
  url.searchParams.set('project_id', projectId);
  return url.toString();
}

/**
 * Project polling returns a fresh editor state. Keep the shot a user is
 * currently previewing unless that shot was actually removed from the plan.
 */
export function resolveVideoStudioSelectedShotId({
  currentShotId,
  persistedShotId,
  shotIds,
}: {
  currentShotId?: string;
  persistedShotId?: string;
  shotIds: string[];
}): string {
  if (currentShotId && shotIds.includes(currentShotId)) return currentShotId;
  if (persistedShotId && shotIds.includes(persistedShotId)) return persistedShotId;
  return shotIds[0] ?? '';
}

export interface VideoStudioProductionOption {
  id: string;
  label: string;
  production_format: VideoStudioProductionFormat;
  summary: string;
  recommended: boolean;
  reason: string;
  html_mg_render_strategy?: 'llm_bespoke_html' | 'template' | string;
  html_mg_template_policy?: string;
}

export interface VideoStudioProducerAnalysis {
  version: 'producer_analysis_v1' | string;
  input_assessment: {
    input_type: string;
    confidence: string;
    summary: string;
  };
  topic_blocks: Array<{
    title: string;
    description: string;
    production_value: string;
  }>;
  key_data_scenes: Array<{
    label: string;
    value: string;
    scene_hint: string;
  }>;
  asset_availability: {
    local_material_check: string;
    open_asset_keywords: string[];
    risk_notes: string[];
  };
  production_options: VideoStudioProductionOption[];
  recommended_option_id: string;
}

export interface VideoStudioRequirementDocument {
  version: 'production_requirement_document_v1' | string;
  title: string;
  summary: string;
  production_format: VideoStudioProductionFormat | string;
  era_background: string;
  production_strategy: string;
  reference_style: string;
  material_requirements: {
    material_types: string[];
    recommended_sources: string[];
    preferences: string[];
    timeliness: string;
    regions: string[];
    named_entities: string[];
  };
  html_mg_direction: {
    render_strategy: 'llm_bespoke_html' | 'template' | 'none' | string;
    template_policy: string;
    style: string;
    palette: string[];
    typography: string;
    icon_style: string;
    motion_principles: string[];
  };
  audio_avatar: {
    bgm: string;
    avatar: string;
    voice_tone: string;
  };
  ratio_plan: {
    broll: string;
    html_mg: string;
    avatar: string;
  };
  risk_notes: string[];
}

export interface VideoStudioCreativePlan {
  version: 'creative_plan_v1' | string;
  title: string;
  script_director: VideoStudioScriptDirector;
  script: string;
  scenes: VideoStudioCreativeScene[];
}

export interface VideoStudioCreativeScene {
  id: string;
  title: string;
  scene_type: string;
  voiceover_units: VideoStudioVoiceoverUnit[];
  asset_search_plan: VideoStudioAssetSearchPlan;
  mg_director?: VideoStudioMgDirector;
  director_note: string;
}

export interface VideoStudioVoiceoverUnit {
  id: string;
  text: string;
  duration_seconds: number;
}

export interface VideoStudioAssetSearchPlan {
  summary: string;
  search_queries: string[];
  material_types: string[];
  named_entities: string[];
  duration_seconds: number;
}

export interface VideoStudioMgDirector {
  version: 'mg_director_v1' | string;
  enabled: boolean;
  render_strategy: 'llm_bespoke_html' | 'template' | 'none' | string;
  scope: 'single_shot' | 'cross_shot' | string;
  bound_voiceover_unit_ids: string[];
  story_goal: string;
  core_question: string;
  one_learning_point: string;
  visual_system: VideoStudioMgVisualSystem | 'reveal' | string;
  main_visual_metaphor: string;
  visual_fx?: {
    fx_pack_id: 'none' | 'gradient_atmosphere' | 'ink_wash_reveal' | 'particle_field' | 'satellite_scan' | 'film_grain_archive' | 'data_glow' | string;
    intensity: 'low' | 'medium' | string;
    opacity: number;
    usage: string;
  };
  logic_chain: Array<{
    label: string;
    text: string;
    role?: string;
  }>;
  supporting_metric: {
    label?: string;
    text?: string;
    date?: string;
  };
  screen_slots: Array<{
    role: string;
    text: string;
    label?: string;
  }>;
  timeline: Array<{
    start_s: number;
    end_s: number;
    target: string;
    action: string;
    text?: string;
  }>;
  html_brief: string;
}

export interface VideoStudioShot {
  id: string;
  title: string;
  narration: string;
  duration_seconds: number;
  start_seconds?: number;
  end_seconds?: number;
  broll_prompt: string;
  scene_role: VideoStudioSceneRole;
  visual_role: VideoStudioVisualRole;
  creative_scene_id?: string;
  voiceover_unit_id?: string;
  asset_search_plan?: VideoStudioAssetSearchPlan;
  mg_director?: VideoStudioMgDirector;
  information_layer: VideoStudioInformationLayer;
  creator_mg_pattern?: VideoStudioCreatorMgPattern;
  html_render_strategy: 'llm_bespoke_html' | 'template' | 'none' | string;
  template_id: string;
  template_family: string;
  template_fallback_id?: string;
  slot_count: number;
  slot_schema: string[];
  requires_asset: boolean;
  requires_path_motion: boolean;
  motion_timing: VideoStudioMotionTiming;
  micro_beats: VideoStudioMicroBeat[];
  composition_beats: VideoStudioCompositionBeat[];
  html_design: VideoStudioHtmlDesign;
  bespoke_html_prompt: string;
  visual_groups: VideoStudioVisualGroup[];
  timeline_elements: VideoStudioTimelineElement[];
  mg_clip?: VideoStudioMgClip;
  html_contract_summary: string;
  broll_options: VideoStudioBrollOption[];
}

export interface VideoStudioCreatorMgAssetSlot {
  id: string;
  title: string;
  query: string;
  role?: string;
  usage_rule?: string;
}

export interface VideoStudioCreatorMgPattern {
  id: string;
  label: string;
  intent: string;
  reason: string;
  expression_contract?: {
    role?: string;
    html_usage?: string;
    broll_usage?: string;
  };
  advanced_effects?: Array<{
    id: string;
    label: string;
    usage: string;
  }>;
  asset_slots: VideoStudioCreatorMgAssetSlot[];
}

export interface VideoStudioRenderScene {
  id: string;
  title: string;
  caption: string;
  narration: string;
  visual_intent: string;
  start: number;
  end: number;
  duration_seconds: number;
  scene_role: VideoStudioSceneRole | string;
  visual_role: VideoStudioVisualRole | string;
}

export interface VideoStudioInformationLayer {
  version: 'information_layer_v1';
  scene_id: string;
  enabled: boolean;
  overlay_type: 'metric_callout' | 'route_trace' | 'causal_chain' | 'keyword_stamp' | 'field_labels';
  shape: string;
  keyword: string;
  primary_fact: string;
  takeaway: string;
  items: Array<{
    label: string;
    text: string;
  }>;
  density: 'light' | 'medium' | string;
  text_budget: {
    max_blocks: number;
    max_total_chars: number;
    max_label_chars: number;
  };
}

export interface VideoStudioBrollOption {
  id: string;
  title: string;
  description: string;
  duration_seconds: number;
  visual_style: string;
  color: string;
  asset_url?: string;
  asset_path?: string;
  search_query?: string;
  provider?: string;
  provider_id?: string;
  source_url?: string;
  license?: string;
  thumbnail_url?: string;
  download_url?: string;
  author?: string;
  similar_materials: VideoStudioSimilarMaterial[];
}

export interface VideoStudioMotionTiming {
  duration_mode: 'short' | 'standard' | 'long' | string;
  duration_seconds: number;
  enter_ratio: number;
  build_ratio: number;
  exit_ratio: number;
  enter_s: number;
  build_s: number;
  hold_s: number;
  exit_s: number;
  slot_count: number;
  phase_times: number[];
}

export interface VideoStudioMicroBeat {
  at: number;
  time_s: number;
  role: string;
  target: string;
  text: string;
  motion: string;
}

export interface VideoStudioCompositionBeat {
  at: number;
  layer: string;
  role: string;
  target: string;
  text: string;
  visual: string;
  motion: string;
}

export interface VideoStudioVisualGroup {
  id: string;
  layer: string;
  role: string;
  layout: string;
}

export interface VideoStudioTimelineElement {
  id: string;
  scene_id: string;
  type: 'broll' | 'html_scene' | 'avatar' | 'caption' | string;
  start: number;
  duration: number;
  end: number;
  track_index: number;
  visual_role?: string;
  scene_role?: string;
  layout?: string;
}

export interface VideoStudioHtmlDesign {
  version: 'html_scene_design_v1' | string;
  render_strategy: string;
  visual_system?: VideoStudioMgVisualSystem;
  visual_language: string;
  layout_principles: string[];
  html_scope: string;
  css_motion: string;
  safe_area: {
    avoid_avatar: boolean;
    avoid_caption: boolean;
    preferred_region: string;
  };
  visual_brief: string;
  illustration_plan?: VideoStudioHtmlIllustrationPlan;
  motion_sequence?: VideoStudioHtmlMotionSequenceItem[];
  content_slots: Array<{
    role: string;
    text?: string;
    label?: string;
  }>;
  design_contract?: VideoStudioMgDesignContract;
  custom_html?: string;
  custom_css?: string;
}

export interface VideoStudioDesignPlanScene {
  version: 'design_plan_scene_v1' | string;
  scene_id: string;
  source_signature: string;
  render_strategy: 'llm_bespoke_html' | 'template' | string;
  template_id: string;
  template_fallback_id: string;
  template_family: string;
  information_layer: VideoStudioInformationLayer;
  mg_clip?: VideoStudioMgClip;
  scene_design_spec: {
    visual_language: string;
    visual_task: string;
    layout_principles: string[];
    html_scope: string;
    css_motion: string;
    visual_system?: VideoStudioMgVisualSystem;
    safe_area: {
      avoid_avatar?: boolean;
      avoid_caption?: boolean;
      preferred_region?: string;
      [key: string]: unknown;
    };
    visual_brief: string;
    custom_html?: string;
    custom_css?: string;
    illustration_plan?: VideoStudioHtmlIllustrationPlan;
    motion_sequence?: VideoStudioHtmlMotionSequenceItem[];
    content_slots: Array<{
      role: string;
      text?: string;
      label?: string;
    }>;
    design_contract?: VideoStudioMgDesignContract;
  };
  motion_timing: VideoStudioMotionTiming;
  visual_groups: VideoStudioVisualGroup[];
  micro_beats: VideoStudioMicroBeat[];
  composition_beats: VideoStudioCompositionBeat[];
  asset_slots: VideoStudioAssetSlot[];
  caption_zone: string;
  avatar_zone: string;
  information_density: string;
  preview_contract: {
    requires_snapshot_check: boolean;
    forbid_split_broll: boolean;
    track_index: number;
  };
}

export interface VideoStudioHtmlIllustrationPlan {
  mode: 'drawn_html_overlay' | string;
  visual_system?: VideoStudioMgVisualSystem;
  subject: string;
  metaphor: string;
  layout: 'center_diagram' | 'split_focus' | 'flow_path' | 'radial_map' | string;
  palette: string[];
  shapes: Array<{
    role: string;
    label: string;
    shape: string;
  }>;
  text_blocks: Array<{
    role: string;
    text: string;
  }>;
}

export interface VideoStudioHtmlMotionSequenceItem {
  at_s: number;
  target: string;
  action: string;
  text?: string;
}

export interface VideoStudioAssetSlot {
  id: string;
  kind: string;
  title: string;
  search_query: string;
  duration_seconds: number;
  asset_url: string;
  asset_path: string;
  usage_rule: string;
}

export interface VideoStudioDesignPlan {
  version: 'video_studio_design_plan_v1' | string;
  strategy: 'llm_bespoke_html' | 'template' | 'none' | string;
  topic: string;
  template_policy: Record<string, unknown>;
  bespoke_html_policy: Record<string, unknown>;
  mg_clips?: VideoStudioMgClip[];
  scenes: VideoStudioDesignPlanScene[];
}

export interface VideoStudioMgClip {
  version: 'mg_clip_v1' | string;
  id: string;
  scene_id: string;
  title: string;
  clip_label: string;
  start: number;
  duration: number;
  end: number;
  status: string;
  render_strategy: string;
  template_strategy: string;
  mg_template: string;
  template_family: string;
  overlay_type: string;
  layout: string;
  visual_system?: VideoStudioMgVisualSystem;
  mg_director?: VideoStudioMgDirector;
  visual_style: string;
  design_prompt: string;
  thumbnail_prompt: string;
  regeneration_prompt: string;
  information_blocks: Array<{
    role: string;
    text?: string;
    label?: string;
  }>;
  illustration_plan?: VideoStudioHtmlIllustrationPlan;
  motion_sequence?: VideoStudioHtmlMotionSequenceItem[];
  design_contract?: VideoStudioMgDesignContract;
  timeline: {
    enter_s: number;
    build_s: number;
    hold_s: number;
    exit_s: number;
  };
  bound_shots: string[];
  track_index: number;
  design_doc?: VideoStudioMgDesignDoc;
}

export interface VideoStudioMgDesignContract {
  version: 'mg_design_contract_v1' | string;
  canvas: {
    width: number;
    height: number;
    safe_top: number;
    safe_bottom: number;
    safe_left: number;
    safe_right: number;
    avatar_reserved: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
  };
  visual_system?: VideoStudioMgVisualSystem | string;
  layout: string;
  layers: Array<{
    id: string;
    z: number;
    role: string;
  }>;
  elements: Array<{
    id: string;
    type: string;
    rect: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
    layer: string;
    text?: string;
    semantic?: string;
    style_role?: string;
  }>;
  timeline: Array<{
    at_s: number;
    target: string;
    action: string;
    duration_s?: number;
    text?: string;
  }>;
  acceptance: string[];
}

export interface VideoStudioMgDesignDoc {
  version: 'mg_design_doc_v1' | string;
  template_id: string;
  template_instance_id: string;
  template_name: string;
  canvas: {
    profile_id: string;
    width: number;
    height: number;
    aspect_ratio: string;
  };
  safe_zones: Record<string, unknown>;
  editable: boolean;
  mutation_scope: string;
  source_clip_id: string;
  bound_shots: string[];
  visual_system: string;
  timeline: {
    start_s: number;
    duration_seconds: number;
    end_s: number;
  };
  elements: VideoStudioMgDesignElement[];
}

export interface VideoStudioMgDesignElement {
  id: string;
  type: string;
  semantic_role: string;
  module?: string;
  text: string;
  label: string;
  rect: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  z_index: number;
  opacity: number;
  style: Record<string, unknown>;
  motion: {
    start_s: number;
    end_s: number;
    preset: string;
    [key: string]: unknown;
  };
  lock: {
    can_edit: boolean;
    can_delete: boolean;
    can_create_sibling: boolean;
  };
}

export interface VideoStudioScenePlanV2 {
  version: 'scene_plan_v2' | string;
  scene_id: string;
  timing: {
    start_s: number;
    end_s: number;
    source: string;
  };
  intent: {
    scene_role: VideoStudioSceneRole | string;
    visual_role: VideoStudioVisualRole | string;
    scene_type: string;
    overlay_family: string;
    html_role: string;
    information_layer: VideoStudioInformationLayer | Record<string, never>;
    overlay_type: string;
    information_density: string;
    tempo: string;
  };
  frame: {
    canvas_px: number[];
    layers: Array<{
      id: string;
      kind: string;
      rect_px: number[];
      [key: string]: unknown;
    }>;
  };
}

export interface VideoStudioRenderManifest {
  version: 'video_studio_render_manifest_v1' | string;
  topic: string;
  script: string;
  production_format: VideoStudioProductionFormat | string;
  resolution: string;
  composer: string;
  template_strategy: Record<string, unknown>;
  scenes: VideoStudioRenderScene[];
  information_layer: VideoStudioInformationLayer[];
  mg_clips?: VideoStudioMgClip[];
  director_timeline: VideoStudioDirectorTimelineItem[];
  design_plan: VideoStudioDesignPlan;
  scene_plan_v2: VideoStudioScenePlanV2[];
}

export interface VideoStudioDirectorTimelineItem {
  scene_id: string;
  start: number;
  end: number;
  visual_mode: string;
  scene_role: VideoStudioSceneRole | string;
  visual_role: VideoStudioVisualRole | string;
  scene_type: string;
  overlay_family: string;
  motion_profile: string;
  narrative_function: string;
  html_role: string;
  template_id: string;
  template_fallback_id: string;
  template_family: string;
  motion_timing: VideoStudioMotionTiming;
  motion_phases: VideoStudioMicroBeat[];
  composition_beats: VideoStudioCompositionBeat[];
  broll: Record<string, unknown>;
  avatar: Record<string, unknown>;
  information_layer: VideoStudioInformationLayer | Record<string, never>;
  html_design_ref: string;
  mg_clip?: VideoStudioMgClip;
}

export interface VideoStudioSimilarMaterial {
  id: string;
  title: string;
  duration_seconds: number;
  color: string;
}

export interface VideoStudioHtmlLayer {
  id: string;
  title: string;
  shot_ids: string[];
  description: string;
  style: {
    palette: string[];
    typography: string;
    motion: string;
  };
  safe_area: 'center' | 'lower_third' | 'full_frame';
  template_id?: string;
  template_family?: string;
  motion_timing?: VideoStudioMotionTiming;
  timeline_elements?: VideoStudioTimelineElement[];
  mg_clip?: VideoStudioMgClip;
}

export interface VideoStudioDirectorDocument {
  title: string;
  summary: string;
  production_format: VideoStudioProductionFormat;
  reference_style: string;
  material_types: string[];
  material_sources: string[];
  material_preferences: string[];
  html_mg_style?: {
    animation_style: string;
    palette: string[];
    typography: string;
    icon_style: string;
  };
  html_motion_director?: {
    version: 'html_motion_director_v1' | string;
    render_strategy: 'llm_bespoke_html' | 'template' | string;
    strategy_reason: string;
    visual_language: string;
    layout_principles: string[];
    timing_principles: {
      enter_s: number;
      build_s: number;
      lock_s: number;
      exit_s: number;
    };
    template_policy: {
      use_templates_as: string;
      allowed_families: string[];
      avoid_when: string[];
    };
    bespoke_html_policy: {
      html_scope: string;
      css_motion: string;
      must_include: string[];
      avoid: string[];
    };
  };
}

export interface VideoStudioScriptDirector {
  topic_understanding: string;
  audience_question: string;
  hook_strategy: string;
  structure: string[];
  tone: string;
  writing_notes: string[];
}

export interface VideoStudioSceneGroup {
  id: string;
  title: string;
  intent: string;
  shots: VideoStudioShot[];
  html_layers: VideoStudioHtmlLayer[];
}

export interface VideoStudioVoice {
  id: string;
  name: string;
  speed: number;
  volume: number;
}

export interface VideoStudioAvatar {
  id: string;
  name: string;
  enabled: boolean;
  placement: 'none' | 'lower_right' | 'center';
}

export interface VideoStudioTimelineTrack {
  id: string;
  kind: 'broll' | 'html_mg' | 'avatar' | 'voice' | 'subtitle' | 'music';
  label: string;
}

export interface VideoStudioManifest {
  id: string;
  title: string;
  brief: string;
  format: VideoStudioFormat;
  aspect_ratio: '16:9' | '9:16';
  scene_groups: VideoStudioSceneGroup[];
  information_layer: VideoStudioInformationLayer[];
  mg_clips?: VideoStudioMgClip[];
  director_timeline: VideoStudioDirectorTimelineItem[];
  design_plan: VideoStudioDesignPlan;
  scene_plan_v2: VideoStudioScenePlanV2[];
  render_manifest: VideoStudioRenderManifest | null;
  composition_preview_url?: string;
  final_video_url?: string;
  script: string;
  production_format: VideoStudioProductionFormat;
  director_document: VideoStudioDirectorDocument;
  voice: VideoStudioVoice;
  avatar: VideoStudioAvatar;
  subtitle: {
    enabled: boolean;
    size: 'small' | 'regular' | 'large';
    style: string;
  };
  music: {
    enabled: boolean;
    mood: string;
  };
  timeline_tracks: VideoStudioTimelineTrack[];
}

export interface VideoStudioCanvasProfile {
  id: 'landscape_16_9' | string;
  aspect_ratio: '16:9' | '9:16' | string;
  width: number;
  height: number;
  safe_area: {
    left: number;
    right: number;
    top: number;
    bottom: number;
  };
}

export interface VideoStudioWorkflowStatus {
  status: 'pending' | 'running' | 'ready' | 'failed' | 'stale' | string;
  updated_at: string;
  error: string;
  depends_on: string[];
  message?: string;
  step?: string;
  completed?: number;
  total?: number;
  job_id?: string;
  started_at?: string;
  finished_at?: string;
}

export interface VideoStudioDataGovernance {
  version: 'video_studio_data_governance_v1' | string;
  schema_versions: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface VideoStudioAssetLayer {
  version: 'video_studio_asset_layer_v1' | string;
  canvas_profile_id: string;
  assets: Array<Record<string, unknown>>;
  selected_asset_ids_by_shot: Record<string, string>;
  readiness_summary: Record<string, number>;
}

export interface VideoStudioLocalAsset {
  id: string;
  title: string;
  filename: string;
  media_type: 'video' | 'image' | 'file' | string;
  mime: string;
  duration_seconds: number;
  tags: string[];
  keywords: string[];
  semantic_text: string;
  analysis: {
    version: string;
    status: string;
    method: string;
    summary: string;
  };
  asset_url: string;
  asset_path: string;
  provider: 'local_library' | string;
  source: string;
  created_at: string;
}

export interface VideoStudioMgLayer {
  version: 'video_studio_mg_layer_v1' | string;
  canvas_profile_id: string;
  mg_clips: VideoStudioMgClip[];
  html_assets: Array<Record<string, unknown>>;
  readiness_summary: Record<string, number>;
}

export interface VideoStudioAuditLogItem {
  at: string;
  action: string;
  source: string;
  details: Record<string, unknown>;
}

export interface VideoStudioChangeSet {
  id: string;
  base_revision_id: string;
  status: 'preview_ready' | 'confirmed' | 'discarded' | string;
  user_message: string;
  patch: Record<string, unknown>;
  summary: string;
  field_changes: Array<Record<string, unknown>>;
  invalidated_stages: string[];
  retained_stages: string[];
  earliest_stage: string;
  estimated_generation_tasks: string[];
  created_at: string;
  confirmed_at?: string | null;
  discarded_at?: string | null;
}

export interface VideoStudioRevision {
  id: string;
  parent_revision_id: string;
  status: 'published' | string;
  created_at: string;
  created_by: string;
  change_set_id?: string;
  snapshot: Record<string, unknown>;
  workflow_state: Record<string, VideoStudioWorkflowStatus>;
}

export interface VideoStudioRevisionState {
  version: string;
  published_revision_id: string;
  pending_change_set_id: string;
  revisions: VideoStudioRevision[];
  change_sets: VideoStudioChangeSet[];
}

export interface VideoStudioEditorState {
  selected_shot_id: string;
  shot_scripts: Record<string, string>;
  selected_broll_by_shot: Record<string, string>;
  html_design_overrides: Record<string, VideoStudioDesignPlanSceneOverride>;
  mg_design_doc_overrides: Record<string, VideoStudioMgDesignDoc>;
  avatar_enabled: boolean;
  bgm_enabled: boolean;
  bgm_volume: number;
  selected_bgm_track_id: string;
  selected_bgm_track: VideoStudioBgmTrack | null;
}

export interface VideoStudioBgmTrack {
  id: string;
  title: string;
  mood: string;
  bpm: number;
  duration_seconds: number;
  provider: string;
  license: string;
  usage_rule: string;
  attribution?: string;
  source_url?: string;
  asset_url?: string;
  asset_path?: string;
  storage_key?: string;
  cached?: boolean;
  mime?: string;
}

export interface VideoStudioWork {
  version: 'video_studio_work_v1' | string;
  id: string;
  project_id: string;
  project_title: string;
  status: 'waiting_render_worker' | 'running' | 'success' | 'failed' | string;
  validation: {
    status: 'passed' | 'failed' | string;
    errors: string[];
    checked_at: string;
  };
  preview_artifact_url: string;
  output: null | Record<string, unknown>;
  progress?: { phase?: string; percent?: number } | Record<string, unknown>;
  renderer?: Record<string, unknown>;
  error: string;
  logs: Array<{ at: string; level: string; message: string }>;
  created_at: string;
  updated_at: string;
}

export interface VideoStudioEditorAssetStatus {
  version: 'editor_asset_status_v1' | string;
  state: 'ready' | 'partial' | string;
  total_shots: number;
  broll_ready_count: number;
  mg_ready_count: number;
  errors: string[];
  html_generation?: {
    version: 'video_studio_html_generation_status_v1' | string;
    state: 'running' | 'ready' | 'failed' | 'skipped' | string;
    error?: string;
    started_at?: string;
    finished_at?: string;
    total?: number;
    completed?: number;
    current_clip_id?: string;
    completed_clip_id?: string;
    failed_clip_id?: string;
    message?: string;
    manual_regeneration?: boolean;
  };
}

export interface VideoStudioHtmlClipGenerationMetric {
  clip_id: string;
  state: 'queued' | 'running' | 'ready' | 'failed' | 'cached' | string;
  error?: string;
  started_at?: string;
  finished_at?: string;
  duration_seconds?: number | null;
  model?: string;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface VideoStudioHtmlGenerationDraft {
  clip_metrics?: Record<string, VideoStudioHtmlClipGenerationMetric>;
  failures_by_clip_id?: Record<string, { clip_id?: string; error?: string }>;
  failed_clip_id?: string;
  manual_regeneration?: { clip_id?: string; prompt?: string; reference?: string };
}

export interface VideoStudioHtmlClipUiState {
  state: string;
  label: string;
  tone: 'pending' | 'ready' | 'failed' | 'empty';
  error: string;
  canRetry: boolean;
}

export function resolveVideoStudioHtmlClipState({
  clipId,
  metric,
  failedClipId,
  failureError,
  globalError,
}: {
  clipId: string;
  metric?: VideoStudioHtmlClipGenerationMetric;
  failedClipId?: string;
  failureError?: string;
  globalError?: string;
}): VideoStudioHtmlClipUiState {
  const metricHasNewerTerminalOrActiveState = ['queued', 'running', 'ready', 'cached'].includes(metric?.state ?? '');
  const isFailed = metric?.state === 'failed' || (failedClipId === clipId && !metricHasNewerTerminalOrActiveState);
  if (isFailed) {
    return {
      state: 'failed',
      label: 'AI HTML 生成失败',
      tone: 'failed',
      error: metric?.error || failureError || globalError || 'AI HTML 生成失败',
      canRetry: true,
    };
  }
  if (metric?.state === 'queued') {
    return { state: 'queued', label: 'AI HTML 已入队', tone: 'pending', error: '', canRetry: false };
  }
  if (metric?.state === 'running') {
    return { state: 'running', label: 'AI HTML 生成中', tone: 'pending', error: '', canRetry: false };
  }
  if (metric?.state === 'ready' || metric?.state === 'cached') {
    return { state: 'ready', label: 'AI HTML 已生成', tone: 'ready', error: '', canRetry: false };
  }
  return { state: metric?.state || 'idle', label: 'AI HTML 未生成', tone: 'empty', error: '', canRetry: false };
}

export type VideoStudioDesignPlanSceneOverride = Partial<Omit<VideoStudioDesignPlanScene, 'scene_design_spec'>> & {
  scene_design_spec?: Partial<VideoStudioDesignPlanScene['scene_design_spec']>;
};

export function mergeVideoStudioHtmlDesignOverrides(
  persisted: Record<string, VideoStudioDesignPlanSceneOverride> = {},
  local: Record<string, VideoStudioDesignPlanSceneOverride> = {},
): Record<string, VideoStudioDesignPlanSceneOverride> {
  return { ...persisted, ...local };
}

export interface VideoStudioProject {
  id: string;
  project_schema_version?: string;
  topic: string;
  format: VideoStudioFormat;
  production_format: VideoStudioProductionFormat;
  target_duration_seconds?: number;
  script_style?: VideoStudioScriptStyle | string;
  language?: VideoStudioLanguage | string;
  stage: VideoStudioWorkflowStageId;
  canvas_profile?: VideoStudioCanvasProfile;
  data_governance?: VideoStudioDataGovernance;
  workflow_state?: Record<string, VideoStudioWorkflowStatus>;
  producer_analysis: VideoStudioProducerAnalysis | null;
  selected_production_option: VideoStudioProductionOption | null;
  production_requirement_document: VideoStudioRequirementDocument | null;
  creative_plan: VideoStudioCreativePlan | null;
  script: string;
  script_director: VideoStudioScriptDirector | null;
  director_document: VideoStudioDirectorDocument | null;
  scene_groups: VideoStudioSceneGroup[];
  information_layer: VideoStudioInformationLayer[];
  mg_clips?: VideoStudioMgClip[];
  director_timeline: VideoStudioDirectorTimelineItem[];
  design_plan: VideoStudioDesignPlan;
  scene_plan_v2: VideoStudioScenePlanV2[];
  asset_layer?: VideoStudioAssetLayer;
  local_asset_library?: VideoStudioLocalAsset[];
  mg_layer?: VideoStudioMgLayer;
  editor_layer?: Record<string, unknown>;
  render_layer?: Record<string, unknown>;
  render_manifest: VideoStudioRenderManifest | null;
  composition_preview_url?: string;
  final_video_url?: string;
  editor_state: VideoStudioEditorState;
  editor_asset_status?: VideoStudioEditorAssetStatus;
  html_generation_draft?: VideoStudioHtmlGenerationDraft;
  audit_log?: VideoStudioAuditLogItem[];
  revision_state?: VideoStudioRevisionState;
  created_at: string;
  updated_at: string;
}

interface CreateVideoStudioManifestInput {
  title: string;
  brief: string;
  format?: VideoStudioFormat;
  production_format?: VideoStudioProductionFormat;
}

const timelineTracks: VideoStudioTimelineTrack[] = [
  { id: 'track-broll', kind: 'broll', label: 'B-roll 素材' },
  { id: 'track-html-mg', kind: 'html_mg', label: 'HTML 信息层' },
  { id: 'track-avatar', kind: 'avatar', label: 'Avatar' },
  { id: 'track-voice', kind: 'voice', label: '口播' },
  { id: 'track-subtitle', kind: 'subtitle', label: '字幕' },
  { id: 'track-music', kind: 'music', label: '音乐' },
];

export const videoStudioWorkflowStages: VideoStudioWorkflowStage[] = [
  {
    id: 'topic',
    label: '主题',
    description: '用户只输入一个主题，点击下一步。',
  },
  {
    id: 'producer',
    label: '制片分析',
    description: '判断输入类型、主题板块、关键数据场景和可制作方案。',
  },
  {
    id: 'requirements',
    label: '需求文档',
    description: '输出标题、摘要、素材要求、HTML/MG 风格和成片比例。',
  },
  {
    id: 'creative_plan',
    label: '创作规划',
    description: '生成脚本导演、口播脚本和场景级四列规划。',
  },
  {
    id: 'storyboard',
    label: '分镜表',
    description: '把创作规划拆成可编辑分镜，并生成素材候选和 MG contract。',
  },
  {
    id: 'editor',
    label: '编辑器',
    description: '确认分镜后进入编辑器，调整素材、HTML、口播、字幕和时间轴。',
  },
];

export function createVideoStudioManifest(input: CreateVideoStudioManifestInput): VideoStudioManifest {
  const format = input.format ?? 'short';
  const productionFormat = input.production_format ?? 'broll_html';
  const htmlMgTimelineTracks =
    productionFormat === 'broll_html' ? timelineTracks : timelineTracks.filter((track) => track.kind !== 'html_mg');

  return {
    id: `video-studio-${format}`,
    title: input.title,
    brief: input.brief,
    format,
    aspect_ratio: '16:9',
    script: '',
    production_format: productionFormat,
    director_document: {
      title: input.title,
      summary: '',
      production_format: productionFormat,
      reference_style: '',
      material_types: [],
      material_sources: [],
      material_preferences: [],
      html_mg_style: undefined,
    },
    scene_groups: [],
    information_layer: [],
    director_timeline: [],
    design_plan: {
      version: 'video_studio_design_plan_v1',
      strategy: productionFormat === 'broll_html' ? 'llm_bespoke_html' : 'none',
      topic: input.title,
      template_policy: {},
      bespoke_html_policy: {},
      mg_clips: [],
      scenes: [],
    },
    scene_plan_v2: [],
    render_manifest: null,
    composition_preview_url: '',
    final_video_url: '',
    voice: {
      id: 'voice-clear-male',
      name: '清亮男声',
      speed: 1,
      volume: 75,
    },
    avatar: {
      id: 'avatar-default-presenter',
      name: '默认讲解员',
      enabled: true,
      placement: 'lower_right',
    },
    subtitle: {
      enabled: true,
      size: 'regular',
      style: 'clean-bold',
    },
    music: {
      enabled: true,
      mood: 'light-explainer',
    },
    timeline_tracks: htmlMgTimelineTracks,
  };
}
