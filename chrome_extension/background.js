// 쿠키 중복 전송 방지용 캐시
let lastHdCookie = "";
let lastAutoplusCookie = "";
let syncTimerHd = null;
let syncTimerAp = null;

// 헤이딜러 쿠키 동기화
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
    // 무시
  }
}

// 오토플러스 (차얼마2) 쿠키 동기화
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
    // 무시
  }
}

// 최초 기동 시 즉시 1회 동기화 시도
syncCookiesToLocalServer();
syncAutoplusCookiesToLocalServer();

// 크롬 브라우저에서 탭 업데이트 감지 (차얼마2나 헤이딜러 페이지 접속/이동 시 즉시 쿠키 동기화)
if (chrome.tabs && chrome.tabs.onUpdated) {
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
      if (tab.url.includes('autoplus.co.kr')) {
        syncAutoplusCookiesToLocalServer();
      } else if (tab.url.includes('heydealer.com')) {
        syncCookiesToLocalServer();
      }
    }
  });
}

// 1분 주기 자동 동기화 (Service Worker 살아있는 동안)
setInterval(() => {
  syncCookiesToLocalServer();
  syncAutoplusCookiesToLocalServer();
}, 60000);

