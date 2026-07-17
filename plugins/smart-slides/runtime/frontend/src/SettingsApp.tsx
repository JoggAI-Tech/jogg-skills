import { useEffect, useState } from 'react';
import axios from 'axios';
import { CheckCircle2, CircleAlert, CircleHelp, ExternalLink, Eye, EyeOff, KeyRound, LoaderCircle, ShieldCheck, Sparkles } from 'lucide-react';

type SettingsStatus = {
  jogg_api_key_configured: boolean;
  pexels_api_key_configured: boolean;
};

const SETTINGS_URL = '/api/v1/settings';
const JOGG_DOCS_URL = 'https://docs.jogg.ai/api-reference/v2/QuickStart/GettingStarted';
const JOGG_LOGIN_URL = 'https://app.jogg.ai/login';
const PEXELS_API_URL = 'https://www.pexels.com/api/';

function SecretInput({ label, value, onChange, configured, required, hint }: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  configured: boolean;
  required?: boolean;
  hint: string;
}) {
  const [visible, setVisible] = useState(false);
  return <label className="setup-field">
    <span className="setup-label">{label}{required && <b>必填</b>}</span>
    <span className="setup-input-row">
      <span className="setup-input-wrap">
        <KeyRound size={18} aria-hidden="true" />
        <input
          type={visible ? 'text' : 'password'}
          value={value}
          autoComplete="off"
          placeholder={configured ? '已保存，留空则保持不变' : '粘贴 API key'}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" className="setup-icon-button" onClick={() => setVisible((current) => !current)} aria-label={visible ? '隐藏 API key' : '显示 API key'}>
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </span>
      <span className={configured ? 'setup-config-status ok' : 'setup-config-status'}>{configured ? '已配置' : '未配置'}</span>
    </span>
    <small>{hint}</small>
  </label>;
}

export function SettingsApp() {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [joggKey, setJoggKey] = useState('');
  const [pexelsKey, setPexelsKey] = useState('');
  const [clearPexels, setClearPexels] = useState(false);
  const [busy, setBusy] = useState(true);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setBusy(true);
    try {
      const response = await axios.get<SettingsStatus>(SETTINGS_URL);
      setStatus(response.data);
    } catch {
      setError('无法读取本地设置服务。');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const save = async () => {
    setBusy(true); setError(''); setNotice('');
    try {
      const response = await axios.put(SETTINGS_URL, {
        jogg_api_key: joggKey || undefined,
        pexels_api_key: pexelsKey || undefined,
        clear_pexels_api_key: clearPexels,
      });
      const result = response.data as { jogg_valid: boolean; pexels_valid: boolean | null };
      setNotice(result.jogg_valid ? (result.pexels_valid === false ? '已保存。Pexels 未验证。' : '已保存并验证。') : '已保存，但 Jogg key 未验证。');
      setJoggKey(''); setPexelsKey(''); setClearPexels(false);
      await load();
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) setError(String(requestError.response?.data?.detail || '保存失败，请检查输入。'));
      else setError('保存失败，请检查输入。');
    } finally {
      setBusy(false);
    }
  };

  return <main className="setup-shell">
    <header className="setup-topbar" aria-label="Smart Slides 本地设置">
      <div className="setup-brand"><Sparkles size={19} /><strong>Smart Slides</strong></div>
    </header>

    <section className="setup-form-area">
      <div className="setup-form-heading">
        <ShieldCheck size={25} />
        <div><p>API</p><h2>密钥</h2></div>
        <div className="setup-help">
          <button type="button" aria-label="查看 Jogg API key 获取指引"><CircleHelp size={19} /></button>
          <div className="setup-help-popover" role="tooltip">
            <a className="setup-help-docs" href={JOGG_DOCS_URL} target="_blank" rel="noreferrer">官方 API 指引 <ExternalLink size={14} /></a>
            <img src="/jogg-api-menu.png" alt="Jogg 官方界面：在账户头像菜单中选择 API。" />
            <img src="/jogg-api-key.png" alt="Jogg 官方界面：复制 API key。" />
          </div>
        </div>
      </div>
      <div className="setup-fields">
        <SecretInput label="JOGG_API_KEY" value={joggKey} onChange={setJoggKey} configured={Boolean(status?.jogg_api_key_configured)} required hint="用于生成视频。" />
        <SecretInput label="PEXELS_API_KEY" value={pexelsKey} onChange={setPexelsKey} configured={Boolean(status?.pexels_api_key_configured)} hint="可选，用于 B-roll。" />
      </div>
      <div className="setup-pexels"><a href={JOGG_LOGIN_URL} target="_blank" rel="noreferrer">获取 Jogg key <ExternalLink size={15} /></a><a href={PEXELS_API_URL} target="_blank" rel="noreferrer">获取 Pexels key <ExternalLink size={15} /></a>{status?.pexels_api_key_configured && <button type="button" onClick={() => setClearPexels(true)}>{clearPexels ? '确认移除' : '移除 key'}</button>}</div>
      {error && <p className="setup-message error"><CircleAlert size={17} />{error}</p>}
      {notice && <p className="setup-message success"><CheckCircle2 size={17} />{notice}</p>}
      <button className="setup-save" type="button" disabled={busy || (!joggKey && !status?.jogg_api_key_configured)} onClick={() => void save()}>{busy ? <LoaderCircle className="spin" size={19} /> : <ShieldCheck size={19} />}保存并验证</button>
    </section>
  </main>;
}
