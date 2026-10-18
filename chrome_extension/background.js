// J-PRO 쿠키 자동 동기화 (Chrome MV3 Service Worker 호환)
// content.js, tabs, cookies.onChanged, focus 실시간 무결성 동기화 엔진

let lastHdCookie = "";
let lastHdSyncTime = 0;
let lastChaeolmaCookie = "";
let lastChaeolmaSyncTime = 0;
let lastHighCookie = "";
let lastHighSyncTime = 0;

let hdTimer = null;
let apTimer = null;

// 공통 백엔드 전송 헬퍼 (:3000 프록시 우선 시도 + HTTP 200 검증)
async function postToJproBackend(path, payload) {
  const bases = [
    'http://jpro:3000',
    'http://100.95.238.123:3000',
    'http://100.95.238.123:8000',
    'http://jpro:8000',
    'http://localhost:8000',
    'http://localhost:3000'
  ];

  for (const base of bases) {
    try {
      const res = await fetch(`${base}${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-JPRO-Token': 'jpro_sec_9981_live_auth'
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        return true;
      }
      console.warn(`[J-PRO AutoSync] 응답 실패 (${base}${path}): HTTP ${res.status}`);
    } catch (err) {
      // 연결 불가 호스트는 다음 후보로 넘어감
    }
  }
  console.error(`[J-PRO AutoSync] 모든 백엔드 엔드포인트 전송 실패: ${path}`);
  return false;
}

async function broadcastToServer(cookieStr, target) {
  return await postToJproBackend('/api/save_cookie', {
    cookie: cookieStr,
    target: target,
    secretToken: 'jpro_sec_9981_live_auth'
  });
}

// ── 헤이딜러 쿠키 지연/후행 동기화 ──
function requestHdSync(force = false, delayMs = 150) {
  if (hdTimer) clearTimeout(hdTimer);
  hdTimer = setTimeout(() => {
    syncCookiesToLocalServer(force);
  }, delayMs);
}

// ── 오토플러스 쿠키 지연/후행 동기화 (차얼마, 하이오플 모바일만 동기화) ──
function requestApSync(force = false, delayMs = 150) {
  if (apTimer) clearTimeout(apTimer);
  apTimer = setTimeout(() => {
    syncChaolmaCookies(force);
    syncHighCookies(force);
  }, delayMs);
}

// ── 헤이딜러 쿠키 동기화 ──
async function syncCookiesToLocalServer(force = false) {
  try {
    const [byUrl1, byUrl2, byUrl3, byDomain1, byDomain2, byDomain3, byDomain4, all] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://dealer.heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ url: 'https://api.heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ url: 'https://heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ domain: '.heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'dealer.heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'api.heydealer.com' }).catch(() => []),
      chrome.cookies.getAll({}).catch(() => [])
    ]);
    const hdCookies = [
      ...byUrl1,
      ...byUrl2,
      ...byUrl3,
      ...byDomain1,
      ...byDomain2,
      ...byDomain3,
      ...byDomain4,
      ...all.filter(c => c && c.domain && (c.domain.includes('heydealer.com') || c.domain.includes('heydealer')))
    ];
    const allMap = new Map();
    hdCookies.forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) return;
    if (!allMap.has('sessionid')) return;

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    const now = Date.now();

    if (!force && cookieStr === lastHdCookie && (now - lastHdSyncTime < 15000)) return;

    lastHdCookie = cookieStr;
    lastHdSyncTime = now;

    await broadcastToServer(cookieStr, 'heydealer');
    console.log('[J-PRO AutoSync] 헤이딜러 최신 로그인 쿠키 동기화 완료');
  } catch (e) {
    // 무시
  }
}

// ── 차얼마(신차옵션/시세) 쿠키 동기화 (purchase.autoplus.co.kr -> autoplus_cookie.txt) ──
async function syncChaolmaCookies(force = false) {
  try {
    const [byUrl, byDomain] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'purchase.autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }).catch(() => [])
    ]);
    const apCookies = [...byUrl, ...byDomain];
    if (!apCookies || apCookies.length === 0) return false;

    const cookieMap = new Map();
    apCookies.forEach(c => {
      if (c && c.name && c.value) {
        const d = (c.domain || '').toLowerCase();
        if (d.includes('admin.') || d.includes('data.')) return;
        cookieMap.set(c.name, c.value);
      }
    });
    const cookieStr = Array.from(cookieMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (!cookieStr) return false;

    // 차얼마 필수 로그인 세션 키(JSESSIONID 또는 remember-me)가 없으면 전송 절대 차단 (깡통 쿠키로 정상 세션 덮어쓰기 방지)
    const upperStr = cookieStr.toUpperCase();
    const hasSessionKey = upperStr.includes('JSESSIONID') || upperStr.includes('REMEMBER-ME');
    if (!hasSessionKey || cookieStr.length < 50) {
      return false;
    }

    const now = Date.now();
    if (!force && cookieStr === lastChaeolmaCookie && (now - lastChaeolmaSyncTime < 15000)) {
      return true;
    }

    const ok = await broadcastToServer(cookieStr, 'autoplus');
    if (ok) {
      lastChaeolmaCookie = cookieStr;
      lastChaeolmaSyncTime = now;
      console.log('[J-PRO AutoSync] 차얼마 쿠키 동기화 완료 (autoplus_cookie.txt)');
    }
    return ok;
  } catch (e) {
    return false;
  }
}

// ── 하이오플 모바일 쿠키 동기화 (high.autoplus.co.kr 전용 -> high_cookie.txt) ──
async function syncHighCookies(force = false) {
  try {
    const [byUrl, byDomain] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://high.autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'high.autoplus.co.kr' }).catch(() => [])
    ]);
    const highCookies = [...byUrl, ...byDomain];
    if (!highCookies || highCookies.length === 0) return false;

    const cookieMap = new Map();
    highCookies.forEach(c => {
      if (c && c.name && c.value) cookieMap.set(c.name, c.value);
    });
    const cookieStr = Array.from(cookieMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (!cookieStr) return false;

    const now = Date.now();
    if (!force && cookieStr === lastHighCookie && (now - lastHighSyncTime < 15000)) {
      return true;
    }

    const ok = await broadcastToServer(cookieStr, 'autoplus_high');
    if (ok) {
      lastHighCookie = cookieStr;
      lastHighSyncTime = now;
      console.log('[J-PRO AutoSync] 하이오플(모바일) 쿠키 동기화 완료');
    }
    return ok;
  } catch (e) {
    return false;
  }
}

// ── high A+ 매입 데이터 백엔드 브로드캐스트 ──
async function broadcastHighplusBuyData(cars) {
  if (!cars || !cars.length) return false;
  return await postToJproBackend('/api/settlement/sync_highplus_buy', { cars });
}





// ── 전체 동기화 ──
function syncAll(force = false) {
  requestHdSync(force, 100);
  requestApSync(force, 100);
}

// 1) Service Worker 시작 및 기동 시 1회 동기화
syncAll(true);
chrome.runtime.onStartup.addListener(() => {
  syncAll(true);
});
chrome.runtime.onInstalled.addListener(() => {
  syncAll(true);
});

// 2) 주기적 알람 동기화 (쿠키: 1분 주기)
chrome.alarms.create('jpro-cookie-sync', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jpro-cookie-sync') {
    syncAll(false);
  }
});

// 3) content.js 및 외부 메시지 수신 시 동기화
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'trigger_sync') {
    const url = msg.url || (sender && sender.tab && sender.tab.url) || '';
    if (url.includes('heydealer.com')) {
      requestHdSync(true, 100);
    } else if (url.includes('autoplus.co.kr')) {
      requestApSync(true, 100);
    }
    sendResponse({ status: 'ok' });
  } else if (msg && msg.action === 'sync_highplus_buy_data') {
    broadcastHighplusBuyData(msg.data).then(ok => sendResponse({ status: ok ? 'ok' : 'error', synced: ok }));
    return true; // 비동기 sendResponse 유지
  }
});


// 4) 탭 생성 감지
chrome.tabs.onCreated.addListener(() => syncAll(true));

// 5) 탭 URL 변경 감지
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = tab.url || changeInfo.url || '';
  if (url.includes('heydealer.com')) {
    requestHdSync(true, 150);
  } else if (url.includes('autoplus.co.kr')) {
    requestApSync(true, 150);
  }
});

// 6) 탭 전환 감지
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab && tab.url) {
      if (tab.url.includes('heydealer.com')) {
        requestHdSync(true, 50);
      } else if (tab.url.includes('autoplus.co.kr')) {
        requestApSync(true, 50);
      }
    }
  } catch (e) {}
});

// 7) 윈도우 포커스 감지
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  try {
    const [tab] = await chrome.tabs.query({ active: true, windowId: windowId });
    if (tab && tab.url) {
      if (tab.url.includes('heydealer.com')) {
        requestHdSync(true, 50);
      } else if (tab.url.includes('autoplus.co.kr')) {
        requestApSync(true, 50);
      }
    }
  } catch (e) {}
});

// 8) 쿠키 실시간 변경 감지
chrome.cookies.onChanged.addListener((changeInfo) => {
  const domain = changeInfo.cookie.domain || '';
  if (domain.includes('heydealer.com')) {
    requestHdSync(true, 150);
  } else if (domain.includes('autoplus.co.kr')) {
    requestApSync(true, 150);
  }
});
