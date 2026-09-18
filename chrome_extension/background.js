// J-PRO 쿠키 자동 동기화 (Chrome MV3 Service Worker 호환)
// chrome.alarms 기반 - Service Worker 비활성화 후에도 안정적 주기 동기화

let lastHdCookie = "";
let lastAutoplusCookie = "";

// ── 헤이딜러 쿠키 동기화 ──
async function syncCookiesToLocalServer() {
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

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (cookieStr === lastHdCookie) return;
    lastHdCookie = cookieStr;

    await fetch('http://localhost:8502/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieStr, target: 'heydealer' })
    });
    console.log('[J-PRO AutoSync] 헤이딜러 최신 쿠키 동기화 완료');
  } catch (e) {
    // 서버 미실행 시 무시
  }
}

// ── 오토플러스 (차얼마2) 쿠키 동기화 ──
async function syncAutoplusCookiesToLocalServer() {
  try {
    const [cUrl1, cDom1, cDom2] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.autoplus.co.kr' })
    ]);

    const allMap = new Map();
    [...cUrl1, ...cDom1, ...cDom2].forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) return;

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (cookieStr === lastAutoplusCookie) return;
    lastAutoplusCookie = cookieStr;

    await fetch('http://localhost:8502/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieStr, target: 'autoplus' })
    });
    console.log('[J-PRO AutoSync] 오토플러스(차얼마2) 최신 쿠키 동기화 완료');
  } catch (e) {
    // 서버 미실행 시 무시
  }
}

// ── 전체 동기화 (두 서비스 모두) ──
function syncAll() {
  syncCookiesToLocalServer();
  syncAutoplusCookiesToLocalServer();
}

// ── 1) Service Worker 기동 시 즉시 1회 동기화 ──
syncAll();

// ── 2) chrome.alarms 기반 1분 주기 동기화 (MV3 안정적) ──
chrome.alarms.create('jpro-cookie-sync', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jpro-cookie-sync') {
    syncAll();
  }
});

// ── 3) 탭 업데이트 감지 (해당 사이트 접속 시 즉시 동기화) ──
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    if (tab.url.includes('autoplus.co.kr')) {
      syncAutoplusCookiesToLocalServer();
    } else if (tab.url.includes('heydealer.com')) {
      syncCookiesToLocalServer();
    }
  }
});

// ── 4) 쿠키 변경 실시간 감지 (즉시 동기화) ──
chrome.cookies.onChanged.addListener((changeInfo) => {
  const domain = changeInfo.cookie.domain || '';
  if (domain.includes('heydealer.com')) {
    // 중복 방지 위해 캐시 초기화 후 동기화
    lastHdCookie = "";
    syncCookiesToLocalServer();
  } else if (domain.includes('autoplus.co.kr')) {
    lastAutoplusCookie = "";
    syncAutoplusCookiesToLocalServer();
  }
});
