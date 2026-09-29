// J-PRO 쿠키 자동 동기화 (Chrome MV3 Service Worker 호환)
// content.js, tabs, cookies.onChanged, focus 실시간 무결성 동기화 엔진

let lastHdCookie = "";
let lastHdSyncTime = 0;
let lastAutoplusCookie = "";
let lastAutoplusSyncTime = 0;

let hdTimer = null;
let apTimer = null;

// ── 헤이딜러 쿠키 지연/후행 동기화 (페이지 로드 완료 시 최종 쿠키 유실 방지) ──
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
    const [cUrl1, cUrl2, cUrl3, cDom1, cDom2, cDom3] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://dealer.heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://api.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'heydealer.com' }),
      chrome.cookies.getAll({ domain: '.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'dealer.heydealer.com' })
    ]);

    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cDom1, ...cDom2, ...cDom3].forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) return;

    // 헤이딜러 로그인 인증의 핵심 키(sessionid) 존재 여부 검증
    if (!allMap.has('sessionid')) return;

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    const now = Date.now();

    // 동일 쿠키 중복 전송 방지 (단, 쿠키가 변경되었거나 force=true면 즉시 전송)
    if (!force && cookieStr === lastHdCookie && (now - lastHdSyncTime < 15000)) return;

    lastHdCookie = cookieStr;
    lastHdSyncTime = now;

    await fetch('http://localhost:8502/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieStr, target: 'heydealer' })
    });
    console.log('[J-PRO AutoSync] 헤이딜러 최신 로그인 쿠키 동기화 완료');
  } catch (e) {
    // 로컬 서버 미실행 시 무시
  }
}

// ── 오토플러스 (차얼마2) 쿠키 동기화 ──
async function syncAutoplusCookiesToLocalServer(force = false) {
  try {
    const [cUrl1, cUrl2, cUrl3, cUrl4, cDom1, cDom2, cDom3, cDom4] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'http://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/purchase/PCVP010001' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/login/login.do' }),
      chrome.cookies.getAll({ domain: 'purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.autoplus.co.kr' })
    ]);

    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cUrl4, ...cDom1, ...cDom2, ...cDom3, ...cDom4].forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) return;

    // 중요: JSESSIONID 또는 remember-me 로그인 세션 쿠키가 있어야만 전송
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

    await fetch('http://localhost:8502/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieStr, target: 'autoplus' })
    });
    console.log('[J-PRO AutoSync] 오토플러스(차얼마2) 로그인 세션 쿠키 동기화 완료');
  } catch (e) {
    // 로컬 서버 미실행 시 무시
  }
}

// ── 전체 동기화 ──
function syncAll(force = false) {
  requestHdSync(force, 100);
  requestApSync(force, 100);
}

// ── 1) Service Worker 시작 및 확장프로그램 기동 시 즉시 1회 동기화 ──
syncAll(true);
chrome.runtime.onStartup.addListener(() => syncAll(true));
chrome.runtime.onInstalled.addListener(() => syncAll(true));

// ── 2) 주기적 알람 동기화 (MV3 백그라운드 슬립 방지 및 주기적 갱신) ──
chrome.alarms.create('jpro-cookie-sync', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jpro-cookie-sync') {
    syncAll(false);
  }
});

// ── 3) 🚀 [content.js로부터 메시지 수신] 페이지가 열리거나 로드되거나 포커스될 때 즉시 동기화 ──
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

// ── 4) 🚀 [새 창 / 새 탭 생성 감지] ──
chrome.tabs.onCreated.addListener((tab) => {
  syncAll(true);
});

// ── 5) 🚀 [탭 URL 변경/네비게이션/SPA 페이지 이동 감지] ──
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = tab.url || changeInfo.url || '';
  if (url.includes('heydealer.com')) {
    requestHdSync(true, 150);
  } else if (url.includes('autoplus.co.kr')) {
    requestApSync(true, 150);
  }
});

// ── 6) 🚀 [탭 전환/클릭 감지] 헤이딜러 창이나 탭을 보거나 클릭할 때 즉시 동기화 ──
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

// ── 7) 🚀 [브라우저 윈도우 포커스 감지] ──
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

// ── 8) 쿠키 실시간 변경 감지 ──
chrome.cookies.onChanged.addListener((changeInfo) => {
  const domain = changeInfo.cookie.domain || '';
  if (domain.includes('heydealer.com')) {
    requestHdSync(true, 150);
  } else if (domain.includes('autoplus.co.kr')) {
    requestApSync(true, 150);
  }
});
