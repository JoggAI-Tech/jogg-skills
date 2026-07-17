import React from 'react';
import ReactDOM from 'react-dom/client';

import { EditorApp } from './EditorApp';
import { SettingsApp } from './SettingsApp';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>{window.location.pathname === '/settings' ? <SettingsApp /> : <EditorApp />}</React.StrictMode>,
);
