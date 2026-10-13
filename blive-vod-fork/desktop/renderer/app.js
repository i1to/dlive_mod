(() => {
  const params = new URLSearchParams(location.search);
  const port = params.get('port') || '17820';
  const API = `http://127.0.0.1:${port}`;
  const WS_URL = `ws://127.0.0.1:${port}/ws`;
  const MAX_LOGS = 500;
  const MAX_RECENT = 20;

  const state = {
    status: null,
    events: [],
    logs: [],
    wsConnected: false,
    autoScroll: true,
  };

  const $ = (id) => document.getElementById(id);
  const pageTitle = {
    overview: ['概览', '实时状态与快捷操作'],
    queue: ['点歌队列', '最近提交的点歌记录'],
    logs: ['弹幕日志', '实时弹幕与系统日志'],
    settings: ['设置', '房间号与黑名单热更新'],
  };

  async function api(path, options = {}) {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.message || `请求失败: ${res.status}`);
    }
    return data;
  }

  /** 按钮进入忙碌态，返回恢复函数；避免重复点击与状态错乱 */
  function beginBusy(button) {
    if (!button) return () => {};
    const wasDisabled = button.disabled;
    button.disabled = true;
    button.classList.add('busy');
    button.setAttribute('aria-busy', 'true');
    return () => {
      button.classList.remove('busy');
      button.removeAttribute('aria-busy');
      button.disabled = wasDisabled;
      syncActionButtons();
    };
  }

  /** 包装一次异步操作：忙碌态 + 成功/失败提示 */
  async function runAction(button, task, { successToast, silent } = {}) {
    const done = beginBusy(button);
    try {
      const result = await task();
      if (!silent) {
        const message = successToast || (result && result.message);
        if (message) toast(message, 'ok');
      }
      return result;
    } catch (err) {
      toast(err.message, 'error');
      pushLog(`[错误] ${err.message}`, 'error');
      return null;
    } finally {
      done();
    }
  }

  function toast(message, level = 'info', timeout = 3200) {
    if (!message) return;
    const host = $('toastHost');
    const node = document.createElement('div');
    node.className = `toast ${level}`;
    node.textContent = message;
    host.appendChild(node);
    setTimeout(() => node.remove(), timeout);
    while (host.childElementCount > 4) host.firstElementChild.remove();
  }

  function setActivePage(name) {
    document.querySelectorAll('.nav-item').forEach((btn) => {
      const active = btn.dataset.page === name;
      btn.classList.toggle('active', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
    document.querySelectorAll('.page').forEach((page) => {
      page.classList.toggle('active', page.id === `page-${name}`);
    });
    const [title, desc] = pageTitle[name] || ['页面', ''];
    $('pageTitle').textContent = title;
    $('pageDesc').textContent = desc;
    if (name === 'logs' && state.autoScroll) scrollLogsToEnd();
  }

  /** 顶部操作按钮的可用状态统一由后端状态推导 */
  function syncActionButtons() {
    const status = state.status || {};
    const listening = !!status.listening;
    const loggingIn = !!status.logging_in;
    const qrVisible = !!(status.qr && status.qr.visible);

    const btnStart = $('btnStart');
    const btnStop = $('btnStop');
    const btnSkip = $('btnSkip');
    const btnLogin = $('btnLogin');

    if (!btnStart.classList.contains('busy')) {
      btnStart.disabled = listening || loggingIn;
      btnStart.textContent = listening ? '监听中' : '开始监听';
    }
    if (!btnStop.classList.contains('busy')) btnStop.disabled = !listening;
    if (!btnSkip.classList.contains('busy')) btnSkip.disabled = !listening;
    if (!btnLogin.classList.contains('busy')) {
      btnLogin.disabled = loggingIn || qrVisible;
      btnLogin.textContent = loggingIn ? '登录中...' : '检查登录';
    }
  }

  function renderStatus(status) {
    if (!status) return;
    state.status = status;
    const listening = !!status.listening;
    const badge = $('connBadge');
    if (!state.wsConnected) {
      badge.textContent = '未连接';
      badge.className = 'badge offline';
    } else if (listening) {
      badge.textContent = '监听中';
      badge.className = 'badge online';
    } else {
      badge.textContent = '待机';
      badge.className = 'badge pending';
    }

    const uname = status.user && status.user.uname ? status.user.uname : '未登录';
    const accountLabel = $('accountLabel');
    accountLabel.textContent = uname;
    accountLabel.title = uname;

    $('statRoom').textContent = status.roomid || '-';
    $('statListen').textContent = listening ? '监听中' : '未监听';
    $('statDanmaku').textContent = String((status.stats && status.stats.danmaku_total) || 0);
    $('statSongOk').textContent = String((status.stats && status.stats.song_success) || 0);

    const roomInput = $('roomInput');
    if (document.activeElement !== roomInput && !roomInput.value && status.roomid) {
      roomInput.value = status.roomid;
    }

    renderQueue(status.song_queue || []);
    renderQr(status.qr);
    syncActionButtons();
  }

  function renderQueue(items) {
    const root = $('queueList');
    if (!items.length) {
      root.innerHTML = '<div class="empty">暂无点歌记录</div>';
      return;
    }
    root.innerHTML = items
      .slice()
      .reverse()
      .map((item) => {
        const chip = item.ok ? 'ok' : 'fail';
        const text = item.ok ? '成功' : '失败';
        const meta = [item.source_label || item.source, item.requester].filter(Boolean).join(' · ');
        return `
        <div class="item">
          <div class="item-main">
            <div class="item-title">${escapeHtml(item.name || '')} - ${escapeHtml(item.singer || '未知歌手')}</div>
            <div class="meta">${escapeHtml(meta)}</div>
          </div>
          <span class="chip ${chip}">${text}</span>
        </div>
      `;
      })
      .join('');
  }

  function drawQr(matrix) {
    const canvas = $('qrCanvas');
    const ctx = canvas.getContext('2d');
    const size = canvas.width;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);
    if (!matrix || !matrix.length) return;
    const cells = matrix.length;
    const scale = Math.floor(size / cells) || 1;
    const offset = Math.floor((size - scale * cells) / 2);
    ctx.fillStyle = '#000000';
    for (let y = 0; y < cells; y += 1) {
      for (let x = 0; x < cells; x += 1) {
        if (matrix[y][x]) {
          ctx.fillRect(offset + x * scale, offset + y * scale, scale, scale);
        }
      }
    }
  }

  function renderQr(qr) {
    const modal = $('qrModal');
    if (!qr || !qr.visible) {
      modal.classList.add('hidden');
      syncActionButtons();
      return;
    }
    modal.classList.remove('hidden');
    if (qr.matrix && qr.matrix.length) drawQr(qr.matrix);
    const status = $('qrStatus');
    status.textContent = qr.message || '等待扫码中...';
    status.className = 'qr-status';
    if (qr.state === 'success') status.classList.add('success');
    if (['expired', 'error', 'timeout'].includes(qr.state)) status.classList.add('error');
    syncActionButtons();
  }

  function scrollLogsToEnd() {
    const root = $('logList');
    root.scrollTop = root.scrollHeight;
  }

  function pushLog(message, level = 'info') {
    if (!message) return;
    const root = $('logList');
    const nearBottom = root.scrollHeight - root.scrollTop - root.clientHeight < 40;
    state.logs.push({ message, level, ts: Date.now() });
    if (state.logs.length > MAX_LOGS) {
      state.logs.shift();
      if (root.firstElementChild) root.firstElementChild.remove();
    }
    const line = document.createElement('div');
    line.className = `log-line ${level}`;
    line.textContent = message;
    root.appendChild(line);
    if (state.autoScroll && nearBottom) scrollLogsToEnd();
  }

  function pushRecent(event) {
    state.events.unshift(event);
    state.events = state.events.slice(0, MAX_RECENT);
    const root = $('recentEvents');
    root.innerHTML = state.events
      .map((e) => {
        const title = formatEvent(e);
        return `<div class="item"><div class="item-main"><div class="item-title">${escapeHtml(title)}</div></div><span class="chip">${escapeHtml(e.type || '')}</span></div>`;
      })
      .join('');
  }

  function formatEvent(e) {
    if (e.type === 'danmaku') return `${e.user}: ${e.msg}`;
    if (e.type === 'song_result') return `${e.name} - ${e.singer} (${e.source_label || e.source})`;
    if (e.type === 'log') return e.message;
    if (e.type === 'action') return e.message || e.action;
    return e.message || e.type || '事件';
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  function setBlacklistValue(items) {
    const list = items || [];
    if (document.activeElement !== $('blacklistInput')) {
      $('blacklistInput').value = list.join('\n');
    }
    $('blacklistCount').textContent = `共 ${list.length} 项`;
  }

  function handleEvent(event) {
    if (!event || !event.type) return;
    if (event.type === 'status') {
      renderStatus(event);
      return;
    }
    if (event.type === 'hello') {
      renderStatus(event.status);
      (event.events || []).forEach((e) => {
        if (e.type === 'log') pushLog(e.message, e.level || 'info');
      });
      scrollLogsToEnd();
      return;
    }
    if (event.type === 'qr') {
      renderQr(event);
      return;
    }
    if (event.type === 'log') {
      pushLog(event.message, event.level || 'info');
      pushRecent(event);
      return;
    }
    if (event.type === 'blacklist') {
      setBlacklistValue(event.items);
      return;
    }
    if (['danmaku', 'song_result', 'action'].includes(event.type)) {
      pushRecent(event);
      if (event.type === 'song_result' && state.status) {
        const queue = (state.status.song_queue || []).concat([event]);
        state.status.song_queue = queue.slice(-50);
        renderQueue(state.status.song_queue);
      }
    }
  }

  function connectWs() {
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => {
      state.wsConnected = true;
      renderStatus(state.status);
    };
    ws.onmessage = (ev) => {
      try {
        handleEvent(JSON.parse(ev.data));
      } catch (_) {}
    };
    ws.onclose = () => {
      state.wsConnected = false;
      renderStatus(state.status);
      pushLog('[系统] WebSocket 断开，3 秒后重连', 'warn');
      setTimeout(connectWs, 3000);
    };
    ws.onerror = () => {
      try { ws.close(); } catch (_) {}
    };
  }

  async function refreshAll() {
    const statusRes = await api('/api/status');
    renderStatus(statusRes.status);
    const cfg = await api('/api/config');
    const roomid = (cfg.config && cfg.config.roomid) || '';
    if (document.activeElement !== $('roomInput')) $('roomInput').value = roomid;
    setBlacklistValue(cfg.blacklist || []);
  }

  function bindUi() {
    document.querySelectorAll('.nav-item').forEach((btn) => {
      btn.addEventListener('click', () => setActivePage(btn.dataset.page));
    });

    $('btnLogin').addEventListener('click', (ev) => {
      runAction(ev.currentTarget, async () => api('/api/login', { method: 'POST', body: '{}' }));
    });

    $('btnStart').addEventListener('click', (ev) => {
      const roomInput = $('roomInput');
      const roomid = roomInput.value.trim();
      if (roomid && !/^\d+$/.test(roomid)) {
        roomInput.classList.add('invalid');
        toast('直播间号必须是数字，请在设置中修正', 'error');
        setActivePage('settings');
        roomInput.focus();
        return;
      }
      roomInput.classList.remove('invalid');
      runAction(ev.currentTarget, async () =>
        api('/api/listen/start', { method: 'POST', body: JSON.stringify({ roomid }) })
      ).then((res) => {
        if (res && res.status) renderStatus(res.status);
      });
    });

    $('btnStop').addEventListener('click', (ev) => {
      runAction(ev.currentTarget, async () => api('/api/listen/stop', { method: 'POST', body: '{}' })).then((res) => {
        if (res && res.status) renderStatus(res.status);
      });
    });

    $('btnSkip').addEventListener('click', (ev) => {
      runAction(ev.currentTarget, async () => api('/api/skip', { method: 'POST', body: '{}' }));
    });

    $('btnQrCancel').addEventListener('click', (ev) => {
      runAction(ev.currentTarget, async () => api('/api/login/cancel', { method: 'POST', body: '{}' })).then((res) => {
        if (res && res.status) renderStatus(res.status);
        else renderQr({ visible: false });
      });
    });

    $('songForm').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const nameInput = $('songName');
      const name = nameInput.value.trim();
      if (!name) {
        nameInput.classList.add('invalid');
        nameInput.focus();
        toast('请填写歌名', 'error');
        return;
      }
      nameInput.classList.remove('invalid');
      const singer = $('songSinger').value.trim();
      runAction($('btnRequest'), async () =>
        api('/api/song/request', { method: 'POST', body: JSON.stringify({ name, singer }) })
      ).then((res) => {
        if (res) {
          nameInput.value = '';
          $('songSinger').value = '';
          nameInput.focus();
        }
      });
    });

    $('roomForm').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const roomInput = $('roomInput');
      const roomid = roomInput.value.trim();
      if (roomid && !/^\d+$/.test(roomid)) {
        roomInput.classList.add('invalid');
        toast('直播间号必须是数字', 'error');
        return;
      }
      roomInput.classList.remove('invalid');
      runAction($('btnSaveRoom'), async () =>
        api('/api/config', { method: 'POST', body: JSON.stringify({ roomid }) }), { successToast: '房间号已保存' }
      ).then((res) => {
        if (res && res.status) renderStatus(res.status);
      });
    });

    $('btnSaveBlacklist').addEventListener('click', (ev) => {
      const items = $('blacklistInput').value
        .split(/\r?\n/)
        .map((x) => x.trim())
        .filter(Boolean);
      runAction(ev.currentTarget, async () =>
        api('/api/blacklist', { method: 'POST', body: JSON.stringify({ items }) }),
        { successToast: `黑名单已保存，共 ${items.length} 项` }
      ).then((res) => {
        if (res) setBlacklistValue(res.items || items);
      });
    });

    $('logAutoScroll').addEventListener('change', (ev) => {
      state.autoScroll = ev.currentTarget.checked;
      if (state.autoScroll) scrollLogsToEnd();
    });

    $('btnClearLogs').addEventListener('click', () => {
      state.logs = [];
      $('logList').innerHTML = '';
      toast('日志已清空', 'ok');
    });

    ['songName', 'roomInput'].forEach((id) => {
      $(id).addEventListener('input', (ev) => ev.currentTarget.classList.remove('invalid'));
    });

    $('blacklistInput').addEventListener('input', (ev) => {
      const count = ev.currentTarget.value.split(/\r?\n/).filter((x) => x.trim()).length;
      $('blacklistCount').textContent = `共 ${count} 项`;
    });

    document.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape' && !$('qrModal').classList.contains('hidden')) {
        $('btnQrCancel').click();
      }
    });
  }

  bindUi();
  renderQueue([]);
  syncActionButtons();
  connectWs();
  refreshAll().catch((err) => pushLog(`[错误] 初始化失败: ${err.message}`, 'error'));
})();
