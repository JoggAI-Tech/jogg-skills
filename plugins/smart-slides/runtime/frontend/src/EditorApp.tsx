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
};
type HtmlSource = { custom_html?: string; custom_css?: string };

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
  const source = shot.html_design as VideoStudioShot['html_design'] & HtmlSource;
  return { custom_html: override?.custom_html ?? source.custom_html ?? '', custom_css: override?.custom_css ?? source.custom_css ?? '' };
}

function selectedBroll(project: VideoStudioProject, shot: VideoStudioShot) {
  const selectedId = project.editor_state.selected_broll_by_shot?.[shot.id];
  return shot.broll_options.find((option) => option.id === selectedId) ?? shot.broll_options.find((option) => option.asset_url || option.asset_path) ?? shot.broll_options[0];
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

  const createPreview = async () => {
    if (!project) return;
    setBusy(true); setStatus('正在生成本地合成预览');
    try {
      const response = await videoStudioApi.createCompositionPreview(project.id);
      setProject(response.project); setStatus('本地预览已刷新');
      window.open(response.preview_url, '_blank', 'noopener,noreferrer');
    } catch (error) { setStatus(error instanceof Error ? error.message : '预览生成失败'); }
    finally { setBusy(false); }
  };

  const createRender = async () => {
    if (!project) return;
    setBusy(true); setStatus('正在创建本地渲染任务');
    try {
      const response = await videoStudioApi.createWork(project.id);
      setWork(response.work); setStatus(`本地任务：${response.work.status}`);
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
          <button className="icon-command" title="刷新项目" onClick={() => void loadProject()}><RefreshCw size={18} /></button>
          <button className="command secondary" onClick={() => void createPreview()}><MonitorPlay size={17} />预览</button>
          <button className="command" onClick={() => void createRender()}><Film size={17} />渲染 MP4</button>
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
            {visualUrl ? (visualUrl.match(/\.(png|jpe?g|webp)(\?|$)/i) ? <img src={visualUrl} alt="" /> : <video ref={videoRef} src={visualUrl} muted playsInline onTimeUpdate={(event) => setShotPlaybackSeconds(event.currentTarget.currentTime)} onEnded={() => setIsPlaying(false)} />) : <div className="missing-media"><ImagePlus size={34} /><span>等待本地画面素材</span></div>}
            {htmlSource.custom_html && <iframe title="HTML/MG 信息层" sandbox="" srcDoc={previewDocument(htmlSource)} />}
            <div className="stage-caption">{project.editor_state.shot_scripts[selectedShot?.id ?? ''] || selectedShot?.narration}</div>
            {avatarAsset && <div className="avatar-flag"><UserRound size={15} />Jogg 数字人</div>}
          </div>
          <div className="transport"><button className="icon-command" title={isPlaying ? '暂停当前素材' : '播放当前素材'} disabled={!visualUrl || Boolean(visualUrl.match(/\.(png|jpe?g|webp)(\?|$)/i))} onClick={() => void togglePlayback()}>{isPlaying ? <Pause size={18} /> : <Play size={18} />}</button><span>{formatTime(shotStartSeconds + shotPlaybackSeconds)}</span><div className="transport-line"><i style={{ width: `${Math.min(100, ((shotStartSeconds + shotPlaybackSeconds) / Math.max(1, duration)) * 100)}%` }} /></div><span>{formatTime(duration)}</span></div>
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
            {activeTool === 'html' && selectedShot && <HtmlPanel source={htmlSource} onSave={saveHtml} />}
            {activeTool === 'avatar' && <AvatarPanel editorState={editorState} shot={selectedShot} />}
            {activeTool === 'bgm' && <BgmPanel project={project} tracks={bgmTracks} onUpdate={updateEditor} onSelect={async (trackId) => { const response = await videoStudioApi.selectBgmTrack(project.id, trackId); setProject(response.project); setStatus(`BGM 已应用：${response.track.title}`); }} />}
          </div>
        </aside>
      </section>

      <section className="timeline-band">
        <div className="timeline-heading"><strong>画面 / HTML / 声音</strong><span>{work ? `渲染 ${work.status} · ${work.progress?.percent ?? 0}%` : status}</span>{busy && <LoaderCircle className="spin" size={16} />}</div>
        <div className="timeline-scroll">
          {shots.map((shot, index) => <button key={shot.id} className={`timeline-shot ${shot.id === selectedShot?.id ? 'active' : ''}`} style={{ flexGrow: Math.max(1, shot.duration_seconds) }} onClick={() => selectShot(shot.id)}>
            <span>{String(index + 1).padStart(2, '0')} {shot.title}</span><i className="track visual-track" /><i className="track html-track" /><i className="track voice-track" />
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

function HtmlPanel({ source, onSave }: { source: HtmlSource; onSave: (html: string, css: string) => void }) {
  const [htmlValue, setHtmlValue] = useState(source.custom_html ?? '');
  const [cssValue, setCssValue] = useState(source.custom_css ?? '');
  useEffect(() => { setHtmlValue(source.custom_html ?? ''); setCssValue(source.custom_css ?? ''); }, [source.custom_html, source.custom_css]);
  const editable = useMemo(() => ensureHtmlEditableBlocks(htmlValue), [htmlValue]);
  const blocks = useMemo(() => extractHtmlEditableBlocks(editable, cssValue), [editable, cssValue]);
  return <div className="tool-panel"><div className="tool-title"><h2>HTML/MG</h2><span>{blocks.length} 个可编辑块</span></div>{blocks.slice(0, 6).map((block) => <label className="field" key={block.id}><span>{block.name}</span><input value={block.text} onChange={(event) => setHtmlValue(replaceHtmlEditableBlockText(editable, block.id, event.target.value))} /></label>)}<label className="field code"><span>HTML</span><textarea value={htmlValue} onChange={(event) => setHtmlValue(event.target.value)} /></label><label className="field code"><span>CSS</span><textarea value={cssValue} onChange={(event) => setCssValue(event.target.value)} /></label><button className="command wide" onClick={() => onSave(editable, upsertHtmlBlockAdjustCss(cssValue, blocks))}><Save size={17} />保存 HTML/MG</button></div>;
}

function AvatarPanel({ editorState, shot }: { editorState?: LocalEditorState; shot?: VideoStudioShot }) {
  const avatar = shot ? editorState?.avatar_assets_by_shot?.[shot.id] : undefined;
  const voice = shot ? editorState?.voice_assets_by_shot?.[shot.id] : undefined;
  return <div className="tool-panel"><div className="tool-title"><h2>Jogg 数字人</h2><span>{editorState?.avatar_mode || '未设置'}</span></div><dl className="facts"><div><dt>Avatar ID</dt><dd>{editorState?.selected_avatar_id || '未选择'}</dd></div><div><dt>Voice ID</dt><dd>{editorState?.selected_voice_id || '未选择'}</dd></div><div><dt>当前画面</dt><dd>{avatar ? '保留静音数字人' : '不显示数字人'}</dd></div><div><dt>当前声音</dt><dd>{voice ? 'Jogg 音频已就绪' : '等待 Jogg 音频'}</dd></div></dl><p className="note">数字人范围由 run 的 avatar_mode 固定。修改范围或声音后，由 Codex 执行 resume 生成缺失资产。</p></div>;
}

function BgmPanel({ project, tracks, onUpdate, onSelect }: { project: VideoStudioProject; tracks: VideoStudioBgmTrack[]; onUpdate: (patch: Partial<LocalEditorState>, message: string) => Promise<void>; onSelect: (id: string) => Promise<void> }) {
  return <div className="tool-panel"><div className="tool-title"><h2>背景音乐</h2><span>{project.editor_state.bgm_enabled ? '已启用' : '已关闭'}</span></div><label className="toggle-row"><span><Volume2 size={17} />启用 BGM</span><input type="checkbox" checked={project.editor_state.bgm_enabled} onChange={(event) => void onUpdate({ bgm_enabled: event.target.checked }, 'BGM 设置已保存')} /></label><label className="field"><span>本地曲目</span><select value={project.editor_state.selected_bgm_track_id || ''} onChange={(event) => void onSelect(event.target.value)}><option value="">选择曲目</option>{tracks.map((track) => <option key={track.id} value={track.id}>{track.title} · {track.mood}</option>)}</select></label><label className="field"><span>音量 {Math.round(project.editor_state.bgm_volume * 100)}%</span><input type="range" min="0" max="0.8" step="0.05" value={project.editor_state.bgm_volume} onChange={(event) => void onUpdate({ bgm_volume: Number(event.target.value) }, 'BGM 音量已保存')} /></label></div>;
}
