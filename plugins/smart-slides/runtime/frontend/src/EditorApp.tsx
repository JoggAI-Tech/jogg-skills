import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Download,
  Film,
  ImagePlus,
  LoaderCircle,
  MonitorPlay,
  Music2,
  Pause,
  Play,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  UserRound,
  Volume2,
} from 'lucide-react';

import { videoStudioApi } from '@/api/videoStudio';
import {
  ensureHtmlEditableBlocks,
  extractHtmlEditableBlocks,
  replaceHtmlEditableBlockText,
  upsertHtmlBlockAdjustCss,
} from '@/features/video-studio/htmlEditor';
import {
  createSparseBlockOverride,
  hasSparseBlockOverrides,
  mergeSparseBlockOverrides,
  normalizeEditSchema,
  semanticBlockText,
} from '@/features/video-studio/editSchema';
import type {
  EditableBlock,
  EditableBlockProperty,
  EditableBlockValue,
  HtmlBlockOverrides,
} from '@/features/video-studio/editSchema';
import type {
  VideoStudioBgmTrack,
  VideoStudioBrollOption,
  VideoStudioDesignPlanSceneOverride,
  VideoStudioProject,
  VideoStudioShot,
  VideoStudioWork,
} from '@/features/video-studio/model';

type LocalAsset = { path?: string; asset_path?: string; asset_url?: string; muted?: boolean; source?: string };
type LocalEditorState = VideoStudioProject['editor_state'] & {
  avatar_mode?: string;
  selected_avatar_id?: string;
  selected_voice_id?: string;
  voice_assets_by_shot?: Record<string, LocalAsset>;
  avatar_assets_by_shot?: Record<string, LocalAsset>;
  html_block_overrides_by_clip?: Record<string, HtmlBlockOverrides>;
};
type HtmlSource = {
  custom_html?: string;
  custom_css?: string;
  edit_schema?: unknown;
  clip_id?: string;
  overrides?: HtmlBlockOverrides;
};
type StyleSwatch = { role: string; color: string; token: string };

const defaultStyleSwatches: StyleSwatch[] = [
  { role: 'ink', color: '#F2EEE8', token: 'var(--mg-ink)' },
  { role: 'muted', color: '#B6B4AE', token: 'var(--mg-muted)' },
  { role: 'primary', color: '#E85D3F', token: 'var(--mg-primary)' },
  { role: 'highlight', color: '#F1C453', token: 'var(--mg-highlight)' },
  { role: 'danger', color: '#D7435B', token: 'var(--mg-danger)' },
];

const formatTime = (seconds: number) => {
  const value = Math.max(0, Math.round(seconds));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
};

const shotsFor = (project?: VideoStudioProject | null) => project?.scene_groups.flatMap((group) => group.shots) ?? [];

function projectIdFromUrl() {
  return new URLSearchParams(window.location.search).get('project_id') ?? '';
}

function htmlSourceFor(project: VideoStudioProject, shot: VideoStudioShot): HtmlSource {
  const override = project.editor_state.html_design_overrides?.[shot.id]?.scene_design_spec as HtmlSource | undefined;
  const source = shot.html_design as VideoStudioShot['html_design'] & HtmlSource & {
    ai_html_generation?: { clip_id?: string; edit_schema?: unknown };
  };
  const layerClip = project.mg_layer?.mg_clips.find((clip) => clip.bound_shots.includes(shot.id));
  const designClip = project.design_plan?.mg_clips?.find((clip) => clip.bound_shots.includes(shot.id));
  const clipId = source.ai_html_generation?.clip_id || shot.mg_clip?.id || layerClip?.id || designClip?.id || '';
  const editorState = project.editor_state as LocalEditorState;
  return {
    custom_html: override?.custom_html ?? source.custom_html ?? '',
    custom_css: override?.custom_css ?? source.custom_css ?? '',
    edit_schema: override?.edit_schema ?? source.edit_schema ?? source.ai_html_generation?.edit_schema,
    clip_id: clipId,
    overrides: clipId ? editorState.html_block_overrides_by_clip?.[clipId] ?? {} : {},
  };
}

function selectedBroll(project: VideoStudioProject, shot: VideoStudioShot) {
  const selectedId = project.editor_state.selected_broll_by_shot?.[shot.id];
  return shot.broll_options.find((option) => option.id === selectedId) ?? shot.broll_options.find((option) => option.asset_url || option.asset_path) ?? shot.broll_options[0];
}

function styleSwatchesFor(project: VideoStudioProject): StyleSwatch[] {
  const extended = project as VideoStudioProject & {
    visual_style_profile?: { palette?: Record<string, string> };
    render_manifest?: (VideoStudioProject['render_manifest'] & { visual_style_profile?: { palette?: Record<string, string> } }) | null;
  };
  const direction = project.production_requirement_document?.html_mg_direction as
    | ({ visual_style_profile?: { palette?: Record<string, string> } })
    | undefined;
  const palette = direction?.visual_style_profile?.palette
    ?? extended.render_manifest?.visual_style_profile?.palette
    ?? extended.visual_style_profile?.palette;
  if (!palette) return defaultStyleSwatches;
  return ['ink', 'muted', 'primary', 'highlight', 'danger', 'outline']
    .filter((role) => Boolean(palette[role]))
    .map((role) => ({ role, color: palette[role], token: `var(--mg-${role})` }));
}

function previewDocument(source: HtmlSource) {
  const markup = source.custom_html || '<div class="empty">这个分镜没有 HTML/MG 信息层</div>';
  return `<!doctype html><html><head><style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent;color:#fff;font-family:Arial,sans-serif}${source.custom_css ?? ''}.empty{position:absolute;inset:0;display:grid;place-items:center;color:#94a3b8;font-size:28px}</style></head><body>${markup}</body></html>`;
}

export function EditorApp() {
  const [project, setProject] = useState<VideoStudioProject | null>(null);
  const [selectedShotId, setSelectedShotId] = useState('');
  const [activeTool, setActiveTool] = useState<'broll' | 'html' | 'avatar' | 'bgm'>('broll');
  const [status, setStatus] = useState('正在读取本地项目');
  const [busy, setBusy] = useState(false);
  const [brollQuery, setBrollQuery] = useState('');
  const [candidates, setCandidates] = useState<VideoStudioBrollOption[]>([]);
  const [bgmTracks, setBgmTracks] = useState<VideoStudioBgmTrack[]>([]);
  const [work, setWork] = useState<VideoStudioWork | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [shotPlaybackSeconds, setShotPlaybackSeconds] = useState(0);
  const [previewNonce, setPreviewNonce] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const shots = useMemo(() => shotsFor(project), [project]);
  const selectedShot = shots.find((shot) => shot.id === selectedShotId) ?? shots[0];
  const selectedIndex = Math.max(0, shots.findIndex((shot) => shot.id === selectedShot?.id));
  const duration = shots.reduce((total, shot) => total + shot.duration_seconds, 0);
  const shotStartSeconds = shots.slice(0, selectedIndex).reduce((sum, shot) => sum + shot.duration_seconds, 0);
  const editorState = project?.editor_state as LocalEditorState | undefined;
  const avatarAsset = selectedShot ? editorState?.avatar_assets_by_shot?.[selectedShot.id] : undefined;
  const broll = project && selectedShot ? selectedBroll(project, selectedShot) : undefined;
  const visualUrl = avatarAsset?.asset_url || broll?.asset_url || '';
  const htmlSource = project && selectedShot ? htmlSourceFor(project, selectedShot) : { custom_html: '', custom_css: '' };
  const compositionPreviewUrl = project?.composition_preview_url
    ? `${project.composition_preview_url}${project.composition_preview_url.includes('?') ? '&' : '?'}v=${previewNonce}`
    : '';
  const workStatus = work?.status ?? 'idle';
  const renderPercent = typeof work?.progress?.percent === 'number'
    ? Math.round(work.progress.percent)
    : workStatus === 'success' ? 100 : 0;
  const finalVideoUrl = project?.final_video_url
    || (typeof work?.output?.url === 'string' ? work.output.url : '');
  const isRendering = ['queued', 'rendering', 'running'].includes(workStatus);
  const renderStatusLabel = busy
    ? status
    : workStatus === 'success'
      ? 'MP4 已完成，可打开或下载'
      : isRendering
        ? `正在渲染${work?.progress?.phase ? ` · ${String(work.progress.phase)}` : ''}`
        : workStatus === 'failed'
          ? `渲染失败${work?.error ? ` · ${work.error}` : ''}`
          : status;

  const loadProject = async () => {
    setBusy(true);
    try {
      let projectId = projectIdFromUrl();
      if (!projectId) {
        const response = await videoStudioApi.listProjects('unfinished');
        projectId = response.projects[0]?.id ?? '';
      }
      if (!projectId) {
        setStatus('没有可编辑项目，请先运行 smart-slides');
        return;
      }
      const response = await videoStudioApi.getProject(projectId);
      setProject(response.project);
      setSelectedShotId((current) => current || response.project.editor_state.selected_shot_id || shotsFor(response.project)[0]?.id || '');
      const works = await videoStudioApi.listWorks(projectId);
      setWork(works.works[0] ?? null);
      setStatus('本地项目已载入');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '项目载入失败');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { void loadProject(); }, []);
  useEffect(() => {
    videoStudioApi.listBgmTracks().then((response) => setBgmTracks(response.tracks)).catch(() => setBgmTracks([]));
  }, []);

  useEffect(() => {
    if (!work || !['queued', 'rendering', 'running'].includes(work.status)) return;
    const timer = window.setInterval(async () => {
      const response = await videoStudioApi.getWork(work.id);
      setWork(response.work);
      if (response.work.status === 'success') setStatus('本地 MP4 已完成');
      if (response.work.status === 'failed') setStatus(`渲染失败：${response.work.error}`);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [work?.id, work?.status]);

  useEffect(() => {
    setIsPlaying(false);
    setShotPlaybackSeconds(0);
    videoRef.current?.pause();
  }, [selectedShot?.id]);

  const togglePlayback = async () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      await video.play();
      setIsPlaying(true);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  };

  const updateEditor = async (patch: Partial<LocalEditorState>, message: string) => {
    if (!project) return;
    setBusy(true);
    try {
      const response = await videoStudioApi.updateEditorState(project.id, patch);
      setProject(response.project);
      setStatus(message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '保存失败');
    } finally {
      setBusy(false);
    }
  };

  const selectShot = (shotId: string) => {
    setSelectedShotId(shotId);
    if (project) void updateEditor({ selected_shot_id: shotId }, '分镜位置已保存');
  };

  const saveNarration = (value: string) => {
    if (!project || !selectedShot) return;
    void updateEditor({ shot_scripts: { ...project.editor_state.shot_scripts, [selectedShot.id]: value } }, '口播修改已保存；重新生成声音需由 Codex 恢复该 run');
  };

  const chooseBroll = (option: VideoStudioBrollOption) => {
    if (!project || !selectedShot) return;
    void updateEditor({ selected_broll_by_shot: { ...project.editor_state.selected_broll_by_shot, [selectedShot.id]: option.id } }, 'B-roll 选择已保存');
  };

  const searchBroll = async () => {
    if (!project || !selectedShot) return;
    setBusy(true); setStatus('正在搜索已允许的素材库');
    try {
      const response = await videoStudioApi.searchBrollCandidates(project.id, selectedShot.id, { query: brollQuery, per_page: 12, providers: 'pexels,pixabay' });
      setCandidates(response.candidates); setStatus(`找到 ${response.candidates.length} 个候选素材`);
    } catch (error) { setStatus(error instanceof Error ? error.message : '素材搜索失败'); }
    finally { setBusy(false); }
  };

  const downloadCandidate = async (candidate: VideoStudioBrollOption) => {
    if (!project || !selectedShot) return;
    setBusy(true); setStatus('正在下载素材到本机');
    try {
      const response = await videoStudioApi.downloadBrollCandidate(project.id, selectedShot.id, candidate);
      setProject(response.project); setCandidates([]); setStatus('素材已下载并应用');
    } catch (error) { setStatus(error instanceof Error ? error.message : '素材下载失败'); }
    finally { setBusy(false); }
  };

  const saveHtml = (customHtml: string, customCss: string) => {
    if (!project || !selectedShot) return;
    const current = project.editor_state.html_design_overrides?.[selectedShot.id] ?? {};
    const next: VideoStudioDesignPlanSceneOverride = {
      ...current,
      scene_design_spec: { ...(current.scene_design_spec ?? {}), custom_html: customHtml, custom_css: customCss },
    };
    void updateEditor({ html_design_overrides: { ...project.editor_state.html_design_overrides, [selectedShot.id]: next } }, 'HTML/MG 已保存');
  };

  const saveHtmlBlockOverrides = async (clipId: string, overrides: HtmlBlockOverrides) => {
    if (!project) return;
    setBusy(true);
    setStatus('正在保存语义化 HTML/MG 编辑');
    try {
      const response = await videoStudioApi.patchMgClipEditSchema(project.id, clipId, { overrides });
      setProject(response.project);
      setPreviewNonce((value) => value + 1);
      setStatus('HTML/MG 语义编辑已保存');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'HTML/MG 语义编辑保存失败');
      throw error;
    } finally {
      setBusy(false);
    }
  };

  const createPreview = async () => {
    if (!project) return;
    setBusy(true); setStatus('正在生成本地合成预览');
    try {
      const response = await videoStudioApi.createCompositionPreview(project.id);
      setProject(response.project); setPreviewNonce((value) => value + 1); setStatus('已按 Podcastor 编辑器合同刷新合成预览');
    } catch (error) { setStatus(error instanceof Error ? error.message : '预览生成失败'); }
    finally { setBusy(false); }
  };

  const createRender = async () => {
    if (!project) return;
    setBusy(true); setStatus('正在创建本地渲染任务');
    try {
      const response = await videoStudioApi.createWork(project.id);
      setWork(response.work);
      setStatus(response.work.status === 'success' ? '本地 MP4 已完成' : `本地任务：${response.work.status}`);
    } catch (error) { setStatus(error instanceof Error ? error.message : '渲染任务创建失败'); }
    finally { setBusy(false); }
  };

  if (!project) {
    return <main className="empty-page"><Clapperboard size={36} /><h1>Smart Slides</h1><p>{status}</p><button className="command" onClick={() => void loadProject()}><RefreshCw size={17} />刷新</button></main>;
  }

  return (
    <main className="editor-shell">
      <header className="topbar">
        <div className="brand"><Clapperboard size={22} /><strong>Smart Slides</strong><span>LOCAL</span></div>
        <div className="project-title"><h1>{project.topic}</h1><p>{shots.length} 个分镜 · {formatTime(duration)} · {project.production_format}</p></div>
        <div className="commands">
          <button className="icon-command" title="刷新项目" onClick={() => void loadProject()} disabled={busy}><RefreshCw size={18} /></button>
          <button className="command secondary" onClick={() => void createPreview()} disabled={busy}><MonitorPlay size={17} />刷新预览</button>
          <button className={`command render-command ${workStatus === 'success' ? 'is-complete' : ''}`} onClick={() => void createRender()} disabled={busy} aria-busy={busy}>
            {busy ? <LoaderCircle className="spin" size={17} /> : workStatus === 'success' ? <Check size={17} /> : <Film size={17} />}
            {busy ? '正在处理' : workStatus === 'success' ? '已完成' : isRendering ? '渲染中' : '渲染 MP4'}
          </button>
          {finalVideoUrl && <a className="command result-command" href={finalVideoUrl} target="_blank" rel="noreferrer" title="打开已生成的 MP4">
            <Download size={17} />打开 MP4
          </a>}
        </div>
      </header>

      <section className="workbench">
        <aside className="shot-list" aria-label="分镜列表">
          <div className="panel-heading"><span>分镜</span><span>{shots.length}</span></div>
          <div className="shot-scroll">
            {shots.map((shot, index) => {
              const hasAvatar = Boolean(editorState?.avatar_assets_by_shot?.[shot.id]);
              return <button key={shot.id} className={`shot-row ${shot.id === selectedShot?.id ? 'active' : ''}`} onClick={() => selectShot(shot.id)}>
                <span className="shot-number">{String(index + 1).padStart(2, '0')}</span>
                <span className="shot-copy"><strong>{shot.title}</strong><small>{formatTime(shot.duration_seconds)} · {hasAvatar ? '数字人' : 'B-roll'}</small></span>
                {hasAvatar ? <UserRound size={15} /> : <Film size={15} />}
              </button>;
            })}
          </div>
        </aside>

        <section className="stage-column">
          <div className="stage-toolbar">
            <button className="icon-command" title="上一分镜" disabled={selectedIndex === 0} onClick={() => selectShot(shots[selectedIndex - 1].id)}><ChevronLeft size={18} /></button>
            <span>{selectedShot?.title}</span>
            <button className="icon-command" title="下一分镜" disabled={selectedIndex >= shots.length - 1} onClick={() => selectShot(shots[selectedIndex + 1].id)}><ChevronRight size={18} /></button>
          </div>
          <div className="preview-stage">
            {compositionPreviewUrl ? <iframe className="composition-preview" title="Podcastor 合成预览" src={compositionPreviewUrl} /> : <div className="missing-media"><ImagePlus size={34} /><span>刷新后生成 Podcastor 合成预览</span></div>}
          </div>
          <div className="transport"><button className="icon-command" title="刷新原项目合成预览" onClick={() => void createPreview()}><RefreshCw size={18} /></button><span>合成预览</span><div className="transport-line"><i style={{ width: `${((selectedIndex + 1) / Math.max(1, shots.length)) * 100}%` }} /></div><span>{String(selectedIndex + 1).padStart(2, '0')} / {String(shots.length).padStart(2, '0')}</span></div>
        </section>

        <aside className="inspector">
          <nav className="tool-tabs">
            <button className={activeTool === 'broll' ? 'active' : ''} onClick={() => setActiveTool('broll')}><Film size={17} />B-roll</button>
            <button className={activeTool === 'html' ? 'active' : ''} onClick={() => setActiveTool('html')}><Sparkles size={17} />HTML</button>
            <button className={activeTool === 'avatar' ? 'active' : ''} onClick={() => setActiveTool('avatar')}><UserRound size={17} />数字人</button>
            <button className={activeTool === 'bgm' ? 'active' : ''} onClick={() => setActiveTool('bgm')}><Music2 size={17} />BGM</button>
          </nav>
          <div className="inspector-body">
            {activeTool === 'broll' && selectedShot && <BrollPanel shot={selectedShot} selected={broll} query={brollQuery} setQuery={setBrollQuery} candidates={candidates} onSearch={searchBroll} onChoose={chooseBroll} onDownload={downloadCandidate} />}
            {activeTool === 'html' && selectedShot && <HtmlPanel source={htmlSource} palette={styleSwatchesFor(project)} onSaveLegacy={saveHtml} onSaveOverrides={saveHtmlBlockOverrides} />}
            {activeTool === 'avatar' && <AvatarPanel editorState={editorState} shot={selectedShot} />}
            {activeTool === 'bgm' && <BgmPanel project={project} tracks={bgmTracks} onUpdate={updateEditor} onSelect={async (trackId) => { const response = await videoStudioApi.selectBgmTrack(project.id, trackId); setProject(response.project); setStatus(`BGM 已应用：${response.track.title}`); }} />}
          </div>
        </aside>
      </section>

      <section className="timeline-band">
        <div className="timeline-heading">
          <div className="timeline-title"><strong>时间线</strong><small>{shots.length} 个分镜 · {formatTime(duration)}</small></div>
          <div className="timeline-legend" aria-label="时间线图例">
            <span><i className="legend-swatch visual-track" />画面</span>
            <span><i className="legend-swatch html-track" />信息层</span>
            <span><i className="legend-swatch voice-track" />声音</span>
          </div>
          <div className={`render-status ${workStatus === 'success' ? 'is-success' : workStatus === 'failed' ? 'is-failed' : isRendering || busy ? 'is-running' : ''}`} aria-live="polite">
            {busy || isRendering ? <LoaderCircle className="spin" size={15} /> : workStatus === 'success' ? <Check size={15} /> : <Film size={15} />}
            <span>{renderStatusLabel}</span>
            {(busy || isRendering) && <b>{renderPercent}%</b>}
          </div>
        </div>
        <div className="timeline-scroll">
          {shots.map((shot, index) => <button key={shot.id} className={`timeline-shot ${shot.id === selectedShot?.id ? 'active' : ''}`} style={{ flexGrow: Math.max(1, shot.duration_seconds) }} aria-label={`第 ${index + 1} 个分镜：${shot.title}，包含画面、信息层和声音轨道`} onClick={() => selectShot(shot.id)}>
            <span>{String(index + 1).padStart(2, '0')} {shot.title}</span><i className="track visual-track" title="画面" aria-hidden="true" /><i className="track html-track" title="信息层" aria-hidden="true" /><i className="track voice-track" title="声音" aria-hidden="true" />
          </button>)}
        </div>
      </section>
    </main>
  );
}

function BrollPanel({ shot, selected, query, setQuery, candidates, onSearch, onChoose, onDownload }: { shot: VideoStudioShot; selected?: VideoStudioBrollOption; query: string; setQuery: (value: string) => void; candidates: VideoStudioBrollOption[]; onSearch: () => Promise<void>; onChoose: (option: VideoStudioBrollOption) => void; onDownload: (option: VideoStudioBrollOption) => Promise<void> }) {
  return <div className="tool-panel"><div className="tool-title"><h2>B-roll 素材</h2><span>{shot.broll_options.length} 个本地选项</span></div><div className="search-row"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={shot.broll_prompt || '搜索素材'} /><button className="icon-command" title="搜索 Pexels / Pixabay" onClick={() => void onSearch()}><Search size={18} /></button></div>
    <div className="asset-list">{(candidates.length ? candidates : shot.broll_options).map((option) => <div className={`asset-row ${selected?.id === option.id ? 'selected' : ''}`} key={option.id}>{option.thumbnail_url ? <img src={option.thumbnail_url} alt="" /> : <div className="asset-placeholder"><Film size={20} /></div>}<div><strong>{option.title}</strong><small>{option.provider || option.visual_style || '本地素材'}</small></div>{option.asset_path || option.asset_url ? <button className="icon-command" title="应用素材" onClick={() => onChoose(option)}>{selected?.id === option.id ? <Check size={17} /> : <Play size={17} />}</button> : <button className="icon-command" title="下载到本机" onClick={() => void onDownload(option)}><Download size={17} /></button>}</div>)}</div>
  </div>;
}

function HtmlPanel({
  source,
  palette,
  onSaveLegacy,
  onSaveOverrides,
}: {
  source: HtmlSource;
  palette: StyleSwatch[];
  onSaveLegacy: (html: string, css: string) => void;
  onSaveOverrides: (clipId: string, overrides: HtmlBlockOverrides) => Promise<void>;
}) {
  const [htmlValue, setHtmlValue] = useState(source.custom_html ?? '');
  const [cssValue, setCssValue] = useState(source.custom_css ?? '');
  const [pendingOverrides, setPendingOverrides] = useState<HtmlBlockOverrides>({});
  useEffect(() => {
    setHtmlValue(source.custom_html ?? '');
    setCssValue(source.custom_css ?? '');
    setPendingOverrides({});
  }, [source.clip_id, source.custom_html, source.custom_css]);
  const schema = useMemo(() => normalizeEditSchema(source.edit_schema), [source.edit_schema]);

  if (schema.isSemantic) {
    const persisted = source.overrides ?? {};
    const values = mergeSparseBlockOverrides(persisted, pendingOverrides);
    const updateBlock = (block: EditableBlock, property: EditableBlockProperty, value: EditableBlockValue) => {
      setPendingOverrides((current) => mergeSparseBlockOverrides(current, createSparseBlockOverride(block, property, value)));
    };
    return <div className="tool-panel">
      <div className="tool-title"><h2>HTML/MG</h2><span>{schema.blocks.length} 个语义对象</span></div>
      {!source.clip_id && <p className="note">当前分镜没有 clip_id，语义编辑暂时不能保存。</p>}
      {schema.blocks.map((block) => <SemanticBlockFields
        key={block.id}
        block={block}
        customHtml={htmlValue}
        values={values[block.id] ?? {}}
        palette={palette}
        onChange={(property, value) => updateBlock(block, property, value)}
      />)}
      <button
        className="command wide"
        disabled={!source.clip_id || !hasSparseBlockOverrides(pendingOverrides)}
        onClick={async () => {
          if (!source.clip_id) return;
          await onSaveOverrides(source.clip_id, pendingOverrides);
          setPendingOverrides({});
        }}
      ><Save size={17} />保存语义编辑</button>
    </div>;
  }

  if (!schema.isLegacy) {
    return <div className="tool-panel">
      <div className="tool-title"><h2>HTML/MG</h2><span>schema 无效</span></div>
      <p className="note">edit_schema 未通过校验：{schema.errors.join('；') || 'editable_blocks 为空'}。为避免破坏导演构图，已停止自动推断可编辑节点。</p>
    </div>;
  }

  const editable = ensureHtmlEditableBlocks(htmlValue);
  const blocks = extractHtmlEditableBlocks(editable, cssValue);
  return <div className="tool-panel">
    <div className="tool-title"><h2>HTML/MG</h2><span>{blocks.length} 个兼容块</span></div>
    <p className="note">这是没有语义 edit_schema 的旧项目，当前使用兼容编辑。保存会写回整段 HTML/CSS；重新生成 MG 后可迁移到语义编辑。</p>
    {blocks.slice(0, 6).map((block) => <label className="field" key={block.id}><span>{block.name}</span><input value={block.text} onChange={(event) => setHtmlValue(replaceHtmlEditableBlockText(editable, block.id, event.target.value))} /></label>)}
    <label className="field code"><span>HTML</span><textarea value={htmlValue} onChange={(event) => setHtmlValue(event.target.value)} /></label>
    <label className="field code"><span>CSS</span><textarea value={cssValue} onChange={(event) => setCssValue(event.target.value)} /></label>
    <button className="command wide" onClick={() => onSaveLegacy(editable, upsertHtmlBlockAdjustCss(cssValue, blocks))}><Save size={17} />保存兼容 HTML/MG</button>
  </div>;
}

const semanticMotionOptions = ['none', 'fade', 'slide', 'rise', 'wipe', 'pop', 'scan'];

function SemanticBlockFields({
  block,
  customHtml,
  values,
  palette,
  onChange,
}: {
  block: EditableBlock;
  customHtml: string;
  values: Partial<Record<EditableBlockProperty, EditableBlockValue>>;
  palette: StyleSwatch[];
  onChange: (property: EditableBlockProperty, value: EditableBlockValue) => void;
}) {
  const valueFor = (property: EditableBlockProperty) => {
    if (values[property] !== undefined) return values[property];
    if (property === 'text') return semanticBlockText(customHtml, block.id);
    if (property === 'opacity' || property === 'scale') return 1;
    return '';
  };
  const labelFor: Record<EditableBlockProperty, string> = {
    text: '文字',
    x: 'X 坐标偏移',
    y: 'Y 坐标偏移',
    width: '宽度（元素实际宽）',
    height: '高度（元素实际高）',
    fontSize: '字号（CSS font-size）',
    scale: block.kind === 'text' ? '缩放' : '视觉缩放（scale）',
    color: block.colorMode === 'descendants' ? '颜色（传播到组内）' : '颜色',
    opacity: '透明度',
    motion: '动效',
  };
  return <div>
    <div className="tool-title"><h2>{block.name}</h2><span>{block.kind}</span></div>
    {block.allowed.map((property) => {
      if (property === 'motion') {
        return <label className="field" key={property}><span>{labelFor[property]}</span><select value={String(valueFor(property) || 'none')} onChange={(event) => onChange(property, event.target.value)}>{semanticMotionOptions.map((motion) => <option key={motion} value={motion}>{motion}</option>)}</select></label>;
      }
      if (property === 'color') {
        const selected = String(valueFor(property) || '');
        return <div className="field" key={property}><span>{labelFor[property]}</span><div className="color-swatches" role="group" aria-label={labelFor[property]}>{palette.map((swatch) => <button type="button" key={swatch.role} className={selected === swatch.token ? 'active' : ''} style={{ backgroundColor: swatch.color }} title={swatch.role} aria-label={swatch.role} onClick={() => onChange(property, swatch.token)} />)}</div></div>;
      }
      if (property === 'text') {
        return <label className="field" key={property}><span>{labelFor[property]}</span><input value={String(valueFor(property))} onChange={(event) => onChange(property, event.target.value)} /></label>;
      }
      const limits: Partial<Record<EditableBlockProperty, { min: number; max: number; step: number }>> = {
        x: { min: -3840, max: 3840, step: 1 },
        y: { min: -2160, max: 2160, step: 1 },
        width: { min: 1, max: 3840, step: 1 },
        height: { min: 1, max: 2160, step: 1 },
        fontSize: { min: 1, max: 512, step: 1 },
        scale: { min: 0.05, max: 10, step: 0.05 },
        opacity: { min: 0, max: 1, step: 0.05 },
      };
      const limit = limits[property];
      return <label className="field" key={property}><span>{labelFor[property]}</span><input type="number" value={String(valueFor(property))} min={limit?.min} max={limit?.max} step={limit?.step} onChange={(event) => { if (event.target.value !== '') onChange(property, Number(event.target.value)); }} /></label>;
    })}
  </div>;
}

function AvatarPanel({ editorState, shot }: { editorState?: LocalEditorState; shot?: VideoStudioShot }) {
  const avatar = shot ? editorState?.avatar_assets_by_shot?.[shot.id] : undefined;
  const voice = shot ? editorState?.voice_assets_by_shot?.[shot.id] : undefined;
  return <div className="tool-panel"><div className="tool-title"><h2>Jogg 数字人</h2><span>{editorState?.avatar_mode || '未设置'}</span></div><dl className="facts"><div><dt>Avatar ID</dt><dd>{editorState?.selected_avatar_id || '未选择'}</dd></div><div><dt>Voice ID</dt><dd>{editorState?.selected_voice_id || '未选择'}</dd></div><div><dt>当前画面</dt><dd>{avatar ? '保留静音数字人' : '不显示数字人'}</dd></div><div><dt>当前声音</dt><dd>{voice ? 'Jogg 音频已就绪' : '等待 Jogg 音频'}</dd></div></dl><p className="note">数字人范围由 run 的 avatar_mode 固定。修改范围或声音后，由 Codex 执行 resume 生成缺失资产。</p></div>;
}

function BgmPanel({ project, tracks, onUpdate, onSelect }: { project: VideoStudioProject; tracks: VideoStudioBgmTrack[]; onUpdate: (patch: Partial<LocalEditorState>, message: string) => Promise<void>; onSelect: (id: string) => Promise<void> }) {
  return <div className="tool-panel"><div className="tool-title"><h2>背景音乐</h2><span>{project.editor_state.bgm_enabled ? '已启用' : '已关闭'}</span></div><label className="toggle-row"><span><Volume2 size={17} />启用 BGM</span><input type="checkbox" checked={project.editor_state.bgm_enabled} onChange={(event) => void onUpdate({ bgm_enabled: event.target.checked }, 'BGM 设置已保存')} /></label><label className="field"><span>本地曲目</span><select value={project.editor_state.selected_bgm_track_id || ''} onChange={(event) => void onSelect(event.target.value)}><option value="">选择曲目</option>{tracks.map((track) => <option key={track.id} value={track.id}>{track.title} · {track.mood}</option>)}</select></label><label className="field"><span>音量 {Math.round(project.editor_state.bgm_volume * 100)}%</span><input type="range" min="0" max="0.8" step="0.05" value={project.editor_state.bgm_volume} onChange={(event) => void onUpdate({ bgm_volume: Number(event.target.value) }, 'BGM 音量已保存')} /></label></div>;
}
