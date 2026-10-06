// J-PRO 쿠키 자동 동기화 (Chrome MV3 Service Worker 호환)
// content.js, tabs, cookies.onChanged, focus 실시간 무결성 동기화 엔진

let lastHdCookie = "";
let lastHdSyncTime = 0;
let lastAutoplusCookie = "";
let lastAutoplusSyncTime = 0;

let hdTimer = null;
let apTimer = null;

async function broadcastToServer(cookieStr, target) {
  const payload = {
    cookie: cookieStr,
    target: target,
    secretToken: 'jpro_sec_9981_live_auth'
  };

  const endpoints = [
    'http://localhost:8502/api/save_cookie',
    'http://localhost:3000/api/save_cookie',
    'http://localhost:8000/api/save_cookie'
  ];

  await Promise.allSettled(
    endpoints.map(url =>
      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-JPRO-Token': 'jpro_sec_9981_live_auth'
        },
        body: JSON.stringify(payload)
      })
    )
  );
}

// ── 헤이딜러 쿠키 지연/후행 동기화 ──
function requestHdSync(force = false, delayMs = 150) {
  if (hdTimer) clearTimeout(hdTimer);
  hdTimer = setTimeout(() => {
    syncCookiesToLocalServer(force);
  }, delayMs);
}

// ── 오토플러스 쿠키 지연/후행 동기화 ──
function requestApSync(force = false, delayMs = 150) {
  if (apTimer) clearTimeout(apTimer);
  apTimer = setTimeout(() => {
    syncAutoplusCookiesToLocalServer(force);
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

// ── 오토플러스 (차얼마) 쿠키 동기화 ──
async function syncAutoplusCookiesToLocalServer(force = false) {
  try {
    const [byUrl, byDomain, all] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({}).catch(() => [])
    ]);
    const apCookies = [
      ...byUrl,
      ...byDomain,
      ...all.filter(c => c && c.domain && (c.domain.includes('autoplus.co.kr') || c.domain.includes('autoplus')))
    ];
    const allMap = new Map();
    apCookies.forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) return;

    const hasSession = Array.from(allMap.keys()).some(k => {
      const u = k.toUpperCase();
      return u === 'JSESSIONID' || u === 'REMEMBER-ME';
    });

    if (!hasSession) return;

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    const now = Date.now();

    if (!force && cookieStr === lastAutoplusCookie && (now - lastAutoplusSyncTime < 15000)) return;

    lastAutoplusCookie = cookieStr;
    lastAutoplusSyncTime = now;

    await broadcastToServer(cookieStr, 'autoplus');
    console.log('[J-PRO AutoSync] 오토플러스(차얼마) 로그인 세션 쿠키 동기화 완료');
  } catch (e) {
    // 무시
  }
}

// ── 전체 동기화 ──
function syncAll(force = false) {
  requestHdSync(force, 100);
  requestApSync(force, 100);
}

// 1) Service Worker 시작 및 기동 시 1회 동기화
syncAll(true);
chrome.runtime.onStartup.addListener(() => syncAll(true));
chrome.runtime.onInstalled.addListener(() => syncAll(true));

// 2) 주기적 알람 동기화
chrome.alarms.create('jpro-cookie-sync', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jpro-cookie-sync') {
    syncAll(false);
  }
});

// 3) content.js 메시지 수신 시 동기화
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === 'trigger_sync') {
    const url = msg.url || (sender && sender.tab && sender.tab.url) || '';
    if (url.includes('heydealer.com')) {
      requestHdSync(true, 100);
    } else if (url.includes('autoplus.co.kr')) {
      requestApSync(true, 100);
    }
    sendResponse({ status: 'ok' });
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
