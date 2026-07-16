import axios from 'axios';

import type {
  VideoStudioEditorState,
  VideoStudioFormat,
  VideoStudioBgmTrack,
  VideoStudioBrollOption,
  VideoStudioLocalAsset,
  VideoStudioMgDesignDoc,
  VideoStudioProductionFormat,
  VideoStudioProject,
  VideoStudioWork,
  VideoStudioWorkflowStageId,
} from '@/features/video-studio/model';

export const VIDEO_STUDIO_API_URL = '/api/v1/video-studio';

const VIDEO_STUDIO_BACKEND_ORIGIN = '';

function absolutizeBackendUrl(url?: string): string | undefined {
  if (!url) return url;
  if (/^(https?:)?\/\//.test(url) || url.startsWith('data:') || url.startsWith('blob:')) return url;
  if (url.startsWith('/')) return `${VIDEO_STUDIO_BACKEND_ORIGIN}${url}`;
  return url;
}

function normalizeProjectUrls(project: VideoStudioProject): VideoStudioProject {
  return {
    ...project,
    composition_preview_url: absolutizeBackendUrl(project.composition_preview_url),
    final_video_url: absolutizeBackendUrl(project.final_video_url),
    editor_state: {
      ...project.editor_state,
      bgm_volume: typeof project.editor_state.bgm_volume === 'number' ? project.editor_state.bgm_volume : 0.35,
      selected_bgm_track: project.editor_state.selected_bgm_track
        ? normalizeBgmTrack(project.editor_state.selected_bgm_track)
        : null,
    },
    scene_groups: project.scene_groups.map((group) => ({
      ...group,
      shots: group.shots.map((shot) => ({
        ...shot,
        broll_options: shot.broll_options.map((option) => ({
          ...option,
          asset_url: absolutizeBackendUrl(option.asset_url),
          thumbnail_url: absolutizeBackendUrl(option.thumbnail_url),
          download_url: absolutizeBackendUrl(option.download_url),
        })),
      })),
    })),
    local_asset_library: (project.local_asset_library ?? []).map(normalizeLocalAsset),
  };
}

function normalizeProjectResponse<T extends { project: VideoStudioProject }>(payload: T): T {
  return { ...payload, project: normalizeProjectUrls(payload.project) };
}

function normalizeBgmTrack(track: VideoStudioBgmTrack): VideoStudioBgmTrack {
  return { ...track, asset_url: absolutizeBackendUrl(track.asset_url) };
}

function normalizeWork(work: VideoStudioWork): VideoStudioWork {
  const output = work.output && typeof work.output === 'object'
    ? {
        ...work.output,
        url: absolutizeBackendUrl(String(work.output.url ?? '')) || work.output.url,
      }
    : work.output;
  return {
    ...work,
    preview_artifact_url: absolutizeBackendUrl(work.preview_artifact_url) || '',
    output,
  };
}

function normalizeBrollOption(option: VideoStudioBrollOption): VideoStudioBrollOption {
  return {
    ...option,
    asset_url: absolutizeBackendUrl(option.asset_url),
    thumbnail_url: absolutizeBackendUrl(option.thumbnail_url),
    download_url: absolutizeBackendUrl(option.download_url),
  };
}

function normalizeLocalAsset(asset: VideoStudioLocalAsset): VideoStudioLocalAsset {
  return {
    ...asset,
    asset_url: absolutizeBackendUrl(asset.asset_url) || '',
  };
}

export interface CreateVideoStudioProjectPayload {
  topic: string;
  format: VideoStudioFormat;
  production_format: VideoStudioProductionFormat;
  target_duration_seconds?: number;
}

export type UpdateVideoStudioEditorStatePayload = Partial<VideoStudioEditorState>;

export interface UploadShotMaterialPayload {
  file_media: File;
  title: string;
  duration_seconds: number;
}

export interface UploadProjectLocalAssetPayload {
  file_media: File;
  title?: string;
  tags?: string;
  duration_seconds?: number;
}

export type UpdatePlanningStatePayload = Partial<Pick<
  VideoStudioProject,
  'topic' | 'target_duration_seconds' | 'script' | 'production_requirement_document' | 'director_document' | 'creative_plan' | 'scene_groups'
>>;

export const videoStudioApi = {
  createProject: async (payload: CreateVideoStudioProjectPayload): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects`, payload);
    return normalizeProjectResponse(response.data);
  },

  listProjects: async (status?: 'unfinished'): Promise<{ projects: VideoStudioProject[] }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/projects`, { params: status ? { status } : undefined });
    return { projects: (response.data.projects ?? []).map(normalizeProjectUrls) };
  },

  deleteProject: async (projectId: string): Promise<{ deleted: boolean; project_id: string }> => {
    const response = await axios.delete(`${VIDEO_STUDIO_API_URL}/projects/${projectId}`);
    return response.data;
  },

  getProject: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/projects/${projectId}`);
    return normalizeProjectResponse(response.data);
  },

  listBgmTracks: async (): Promise<{ tracks: VideoStudioBgmTrack[] }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/bgm-tracks`);
    return { tracks: (response.data.tracks ?? []).map(normalizeBgmTrack) };
  },

  cacheBgmTrack: async (trackId: string): Promise<{ track: VideoStudioBgmTrack }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/bgm-tracks/${trackId}/cache`);
    return { track: normalizeBgmTrack(response.data.track) };
  },

  generateScript: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-script`);
    return normalizeProjectResponse(response.data);
  },

  generateProducerAnalysis: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-producer-analysis`);
    return normalizeProjectResponse(response.data);
  },

  updateProductionOption: async (
    projectId: string,
    optionId: string,
    htmlRenderStrategy?: 'llm_bespoke_html' | 'template',
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/production-option`, {
      option_id: optionId,
      html_render_strategy: htmlRenderStrategy,
    });
    return normalizeProjectResponse(response.data);
  },

  generateRequirementDocument: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-requirement-document`);
    return normalizeProjectResponse(response.data);
  },

  generateCreativePlan: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-creative-plan`);
    return normalizeProjectResponse(response.data);
  },

  generateDirectorDocument: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-director-document`);
    return normalizeProjectResponse(response.data);
  },

  updateProductionFormat: async (
    projectId: string,
    productionFormat: VideoStudioProductionFormat,
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/production-format`, {
      production_format: productionFormat,
    });
    return normalizeProjectResponse(response.data);
  },

  updatePlanningState: async (
    projectId: string,
    payload: UpdatePlanningStatePayload,
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/planning-state`, payload);
    return normalizeProjectResponse(response.data);
  },

  updateTopic: async (projectId: string, topic: string, targetDurationSeconds?: number): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/topic`, {
      topic,
      target_duration_seconds: targetDurationSeconds,
    });
    return normalizeProjectResponse(response.data);
  },

  updateWorkflowStage: async (
    projectId: string,
    stage: VideoStudioWorkflowStageId,
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/workflow-stage`, { stage });
    return normalizeProjectResponse(response.data);
  },

  generateStoryboard: async (projectId: string): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/generate-storyboard`);
    return normalizeProjectResponse(response.data);
  },

  updateEditorState: async (
    projectId: string,
    payload: UpdateVideoStudioEditorStatePayload,
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/editor-state`, payload);
    return normalizeProjectResponse(response.data);
  },

  createCompositionPreview: async (projectId: string): Promise<{ project: VideoStudioProject; preview_url: string }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/composition-preview`);
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, preview_url: absolutizeBackendUrl(payload.preview_url) || '' };
  },

  prepareEditorAssets: async (
    projectId: string,
  ): Promise<{ project: VideoStudioProject; preview_url: string; asset_status?: VideoStudioProject['editor_asset_status'] }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/prepare-editor-assets`);
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, preview_url: absolutizeBackendUrl(payload.preview_url) || '' };
  },

  generateFinalVideo: async (projectId: string): Promise<{ project: VideoStudioProject; final_video_url: string }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/final-video`);
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, final_video_url: absolutizeBackendUrl(payload.final_video_url) || '' };
  },

  updateMgDesignDoc: async (
    projectId: string,
    payload: { mg_clip_id: string; design_doc: VideoStudioMgDesignDoc },
  ): Promise<{ project: VideoStudioProject; mg_clip_id: string; design_doc: VideoStudioMgDesignDoc }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/mg-design-doc`, payload);
    return normalizeProjectResponse(response.data);
  },

  deleteMgClip: async (
    projectId: string,
    mgClipId: string,
  ): Promise<{ project: VideoStudioProject; mg_clip_id: string; deleted_shot_ids: string[]; preview_url: string }> => {
    const response = await axios.delete(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/mg-clips/${encodeURIComponent(mgClipId)}`);
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, preview_url: absolutizeBackendUrl(payload.preview_url) || '' };
  },

  regenerateMgClipHtml: async (
    projectId: string,
    mgClipId: string,
    payload: { prompt: string; reference: string },
  ): Promise<{ project: VideoStudioProject; mg_clip_id: string; bound_shot_ids: string[]; preview_url: string; metrics?: Record<string, unknown> }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/mg-clips/${encodeURIComponent(mgClipId)}/regenerate-html`, payload);
    const normalized = normalizeProjectResponse(response.data);
    return { ...normalized, preview_url: absolutizeBackendUrl(normalized.preview_url) || '' };
  },

  selectBgmTrack: async (
    projectId: string,
    trackId: string,
  ): Promise<{ project: VideoStudioProject; track: VideoStudioBgmTrack }> => {
    const response = await axios.patch(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/bgm-track`, {
      track_id: trackId,
    });
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, track: normalizeBgmTrack(payload.track) };
  },

  createWork: async (projectId: string): Promise<{ work: VideoStudioWork }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/works`);
    return { work: normalizeWork(response.data.work) };
  },

  getWork: async (workId: string): Promise<{ work: VideoStudioWork }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/works/${workId}`);
    return { work: normalizeWork(response.data.work) };
  },

  listWorks: async (projectId?: string): Promise<{ works: VideoStudioWork[] }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/works`, { params: projectId ? { project_id: projectId } : undefined });
    return { works: (response.data.works ?? []).map(normalizeWork) };
  },

  uploadShotMaterial: async (
    projectId: string,
    shotId: string,
    payload: UploadShotMaterialPayload,
  ): Promise<{ project: VideoStudioProject }> => {
    const formData = new FormData();
    formData.append('file_media', payload.file_media);
    formData.append('title', payload.title);
    formData.append('duration_seconds', String(payload.duration_seconds));
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/shots/${shotId}/materials`, formData);
    return normalizeProjectResponse(response.data);
  },

  uploadProjectLocalAsset: async (
    projectId: string,
    payload: UploadProjectLocalAssetPayload,
  ): Promise<{ project: VideoStudioProject; asset: VideoStudioLocalAsset }> => {
    const formData = new FormData();
    formData.append('file_media', payload.file_media);
    formData.append('title', payload.title ?? '');
    formData.append('tags', payload.tags ?? '');
    formData.append('duration_seconds', String(payload.duration_seconds ?? 6));
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/local-assets`, formData);
    const normalized = normalizeProjectResponse(response.data);
    return { ...normalized, asset: normalizeLocalAsset(response.data.asset) };
  },

  searchAndDownloadBrollAssets: async (
    projectId: string,
    shotId: string,
  ): Promise<{ project: VideoStudioProject }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/shots/${shotId}/broll-assets`);
    return normalizeProjectResponse(response.data);
  },

  searchBrollCandidates: async (
    projectId: string,
    shotId: string,
    payload: { query?: string; slot_id?: string; per_page?: number; providers?: string },
  ): Promise<{ candidates: VideoStudioBrollOption[]; queries: string[] }> => {
    const response = await axios.get(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/shots/${shotId}/broll-search`, {
      params: payload,
    });
    return {
      candidates: (response.data.candidates ?? []).map(normalizeBrollOption),
      queries: response.data.queries ?? [],
    };
  },

  downloadBrollCandidate: async (
    projectId: string,
    shotId: string,
    candidate: VideoStudioBrollOption,
  ): Promise<{ project: VideoStudioProject; option: VideoStudioBrollOption }> => {
    const response = await axios.post(`${VIDEO_STUDIO_API_URL}/projects/${projectId}/shots/${shotId}/broll-assets/download`, {
      candidate,
    });
    const payload = normalizeProjectResponse(response.data);
    return { ...payload, option: normalizeBrollOption(response.data.option) };
  },
};
