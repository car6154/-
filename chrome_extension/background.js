// J-PRO 쿠키 자동 동기화 (Chrome MV3 Service Worker 호환)
// content.js, tabs, cookies.onChanged, focus 실시간 무결성 동기화 엔진

let lastHdCookie = "";
let lastHdSyncTime = 0;
let lastAdminCookie = "";
let lastAdminSyncTime = 0;
let lastDataCookie = "";
let lastDataSyncTime = 0;

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

// ── 오토플러스 쿠키 지연/후행 동기화 (어드민 & 데이터 각각 전송) ──
function requestApSync(force = false, delayMs = 150) {
  if (apTimer) clearTimeout(apTimer);
  apTimer = setTimeout(() => {
    syncAdminCookies(force);
    syncDataCookies(force);
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

// ── 오토플러스 어드민 쿠키 동기화 (admin.autoplus.co.kr 전용 -> autoplus_cookie.txt) ──
async function syncAdminCookies(force = false) {
  try {
    const adminCookies = await chrome.cookies.getAll({ url: 'https://admin.autoplus.co.kr' }).catch(() => []);
    if (!adminCookies || adminCookies.length === 0) return false;

    const cookieMap = new Map();
    adminCookies.forEach(c => {
      if (c && c.name && c.value) cookieMap.set(c.name, c.value);
    });
    const cookieStr = Array.from(cookieMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (!cookieStr) return false;

    const now = Date.now();
    if (!force && cookieStr === lastAdminCookie && (now - lastAdminSyncTime < 15000)) {
      return true;
    }

    const ok = await broadcastToServer(cookieStr, 'autoplus_admin');
    if (ok) {
      lastAdminCookie = cookieStr;
      lastAdminSyncTime = now;
      console.log('[J-PRO AutoSync] 오토플러스 어드민 쿠키 동기화 완료');
    }
    return ok;
  } catch (e) {
    return false;
  }
}

// ── 오토플러스 차얼마(데이터) 쿠키 동기화 (data.autoplus.co.kr 전용 -> autoplus_data_cookie.txt) ──
async function syncDataCookies(force = false) {
  try {
    const dataCookies = await chrome.cookies.getAll({ url: 'https://data.autoplus.co.kr' }).catch(() => []);
    if (!dataCookies || dataCookies.length === 0) return false;

    const cookieMap = new Map();
    dataCookies.forEach(c => {
      if (c && c.name && c.value) cookieMap.set(c.name, c.value);
    });
    const cookieStr = Array.from(cookieMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    if (!cookieStr) return false;

    const now = Date.now();
    if (!force && cookieStr === lastDataCookie && (now - lastDataSyncTime < 15000)) {
      return true;
    }

    const ok = await broadcastToServer(cookieStr, 'autoplus_data');
    if (ok) {
      lastDataCookie = cookieStr;
      lastDataSyncTime = now;
      console.log('[J-PRO AutoSync] 오토플러스 차얼마(데이터) 쿠키 동기화 완료');
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

// ── SPPOL10001 매입조회 탭 대상 자동 검색 & 스캔 트리거 (탭 없으면 자동 생성 후 대기) ──
async function triggerActiveAutoplusTabScan() {
  await syncAdminCookies(true);
  await syncDataCookies(true);

  const SPPOL_URL = 'https://admin.autoplus.co.kr/spot/syspo/SPPOL10001';

  async function triggerTab(tabId) {
    try {
      // 1. chrome.tabs.sendMessage 전송
      chrome.tabs.sendMessage(tabId, { action: 'triggerActiveAutoplusTabScan' }).catch(() => {});

      // 2. content.js 최신 스크립트 전 프레임(allFrames: true) 주입
      await chrome.scripting.executeScript({
        target: { tabId: tabId, allFrames: true },
        files: ['content.js']
      }).catch(() => {});

      // 3. [핵심] iframe 내부까지 100% 신호 직접 침투 (allFrames: true)
      await chrome.scripting.executeScript({
        target: { tabId: tabId, allFrames: true },
        func: () => {
          window.postMessage({ type: 'JPRO_TRIGGER_INTERNAL_SCAN' }, '*');
        }
      }).catch(() => {});

      setTimeout(async () => {
        chrome.tabs.sendMessage(tabId, { action: 'triggerActiveAutoplusTabScan' }).catch(() => {});
        await chrome.scripting.executeScript({
          target: { tabId: tabId, allFrames: true },
          func: () => {
            window.postMessage({ type: 'JPRO_TRIGGER_INTERNAL_SCAN' }, '*');
          }
        }).catch(() => {});
      }, 300);
    } catch (e) {
      console.warn('[J-PRO AutoScan] 탭 스크립트 트리거 예외:', e.message);
    }
  }

  // 1. 이미 열려 있는 SPPOL10001 탭이 있는지 확인 (대소문자/title 유연 검색)
  const allApTabs = await chrome.tabs.query({ url: '*://admin.autoplus.co.kr/*' }).catch(() => []);
  const existingTab = allApTabs.find(t => t.url && t.url.toLowerCase().includes('sppol10001')) ||
                      allApTabs.find(t => t.title && t.title.includes('매입조회'));

  if (existingTab && existingTab.id) {
    console.log(`[J-PRO AutoScan] 기존 SPPOL10001 탭(ID: ${existingTab.id}) 발견 -> 즉시 전 프레임 스캔 신호 전송`);
    await triggerTab(existingTab.id);
    return;
  }

  // 2. 없으면 백그라운드에서 SPPOL10001 탭 자동 생성
  console.log('[J-PRO AutoScan] 열린 SPPOL10001 탭 없음 -> 탭 자동 생성 후 로드 대기');
  const newTab = await chrome.tabs.create({ url: SPPOL_URL, active: false });
  if (!newTab || !newTab.id) return;

  const targetTabId = newTab.id;

  // 3. 탭 로드 완료 대기 (chrome.tabs.onUpdated)
  return new Promise((resolve) => {
    let resolved = false;

    const timeoutTimer = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        chrome.tabs.onUpdated.removeListener(onTabUpdated);
        console.warn('[J-PRO AutoScan] 탭 로드 15초 타임아웃 -> 강제 트리거 시도');
        triggerTab(targetTabId).then(resolve);
      }
    }, 15000);

    function onTabUpdated(tabId, changeInfo, tab) {
      if (tabId === targetTabId && changeInfo.status === 'complete') {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeoutTimer);
          chrome.tabs.onUpdated.removeListener(onTabUpdated);
          console.log(`[J-PRO AutoScan] 새 SPPOL10001 탭(ID: ${tabId}) 로드 완료 -> 자동 검색 파이프라인 가동`);
          setTimeout(() => {
            triggerTab(targetTabId).then(resolve);
          }, 400);
        }
      }
    }

    chrome.tabs.onUpdated.addListener(onTabUpdated);
  });
}

// ── high A+ 매입 데이터 백그라운드 자동 수집 (화면 안 열어도 무인 실행) ──
let isFetchingHighplus = false;
async function fetchHighplusBuyDataInBackground() {
  if (isFetchingHighplus) return;
  isFetchingHighplus = true;

  try {
    const [byUrl, byDomain] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://admin.autoplus.co.kr' }).catch(() => []),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }).catch(() => [])
    ]);
    const adminCookies = [...byUrl, ...byDomain];
    const hasSession = adminCookies.some(c => c && c.name && (c.name.toUpperCase().includes('SESSION') || c.name.toUpperCase().includes('REMEMBER')));
    if (!hasSession && adminCookies.length === 0) {
      isFetchingHighplus = false;
      return;
    }

    const resp = await fetch('https://admin.autoplus.co.kr/spot/syspo/SPPOL10001', {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    if (!resp.ok) {
      isFetchingHighplus = false;
      return;
    }

    const html = await resp.text();
    if (!html || html.includes('login/login.do')) {
      isFetchingHighplus = false;
      return;
    }

    const foundCars = [];
    const CAR_NO_REGEX = /\b\d{2,3}[가-힣]\s*\d{4}\b/;
    const PID_REGEX = /\bC\d{11}\b/;
    const DATE_REGEX = /\b20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b/;

    const trMatches = html.match(/<tr[^>]*>[\s\S]*?<\/tr>/gi) || [];
    for (const tr of trMatches) {
      const carMatch = tr.match(CAR_NO_REGEX);
      if (!carMatch) continue;
      const carNo = carMatch[0].replace(/\s+/g, '');

      const pidMatch = tr.match(PID_REGEX);
      const pid = pidMatch ? pidMatch[0] : '';

      const poMatch = tr.match(/poId=(\d+)/i) || tr.match(/poIdList['"\s:=]+(\d+)/i);
      const poId = poMatch ? poMatch[1] : '';

      const dates = tr.match(new RegExp(DATE_REGEX, 'g')) || [];
      const transferDate = dates.length > 0 ? dates[dates.length - 1] : '';
      const billDate = dates.length > 1 ? dates[0] : transferDate;

      // 2026년 9월 이전 매입건 제외 (2026-09-01 이후만 수집)
      const targetDate = transferDate || billDate;
      if (targetDate) {
        const ymMatch = targetDate.match(/(\d{4})[-/.](\d{1,2})/);
        if (ymMatch) {
          const y = parseInt(ymMatch[1], 10);
          const m = parseInt(ymMatch[2], 10);
          if (y < 2026 || (y === 2026 && m < 9)) {
            continue;
          }
        }
      }

      const numMatches = tr.match(/\b\d{1,3}(?:,\d{3}){2,}\b/g) || [];
      let buyPrice = 0;
      for (const nm of numMatches) {
        const val = parseInt(nm.replace(/,/g, ''), 10);
        if (val >= 1000000) {
          buyPrice = val;
          break;
        }
      }

      const yearMatch = tr.match(/\b(201\d|202\d)\b/);
      const modelYear = yearMatch ? yearMatch[1] : '';

      let scrapDeduction = 0;
      const allNums = tr.match(/\b\d{1,3}(?:,\d{3})+\b/g) || [];
      for (const an of allNums) {
        const val = parseInt(an.replace(/,/g, ''), 10);
        if (val >= 100000 && val < 10000000 && val !== buyPrice) {
          scrapDeduction = val;
          break;
        }
      }

      const cleanTr = tr.replace(/<[^>]+>/g, ' ');
      const nameMatch = cleanTr.match(/(현대|기아|제네시스|쉐보레|르노|쌍용|KGM|BMW|벤츠|아우디|볼보|폭스바겐|포르쉐|렉서스|카니발|아반떼|투싼|캐스퍼|쏘렌토|그랜저|스포티지)[^\n\r\t,]{2,30}/);
      const carName = nameMatch ? nameMatch[0].trim() : '';

      const manager = tr.includes("김재현") ? "김재현" : "";

      foundCars.push({
        carNumber: carNo,
        carName: carName,
        modelYear: modelYear,
        buyPrice: buyPrice,
        transferDate: transferDate,
        billDate: billDate,
        pid: pid,
        poId: poId,
        manager: manager,
        scrapDeduction: scrapDeduction
      });
    }

    for (const car of foundCars) {
      if (car.poId) {
        try {
          const detailResp = await fetch(`https://admin.autoplus.co.kr/spot/syspo/SPPOR20001?poId=${car.poId}&vw=1&showGbn=H`, {
            credentials: 'include'
          }).catch(() => null);
          if (detailResp && detailResp.ok) {
            const detailHtml = await detailResp.text();
            const mEtc = detailHtml.match(/기타비용[^\d]*([\d,]{4,})/);
            if (mEtc) car.etcFee = parseInt(mEtc[1].replace(/,/g, ''), 10) || 0;
          }
        } catch (err) {}
      }
    }

    if (foundCars.length > 0) {
      await broadcastHighplusBuyData(foundCars);
      console.log(`[J-PRO AutoSync] 백그라운드 high A+ 매입 데이터 ${foundCars.length}건 무인 자동 동기화 성공`);
    }
  } catch (e) {
    console.error('[J-PRO AutoSync] high A+ 백그라운드 fetch 에러:', e);
  } finally {
    isFetchingHighplus = false;
  }
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
  setTimeout(fetchHighplusBuyDataInBackground, 4000);
});
chrome.runtime.onInstalled.addListener(() => {
  syncAll(true);
  setTimeout(fetchHighplusBuyDataInBackground, 4000);
});

// 2) 주기적 알람 동기화 (쿠키: 1분 주기, 매입데이터: 5분 주기)
chrome.alarms.create('jpro-cookie-sync', { periodInMinutes: 1 });
chrome.alarms.create('jpro-highplus-buy-sync', { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'jpro-cookie-sync') {
    syncAll(false);
  } else if (alarm.name === 'jpro-highplus-buy-sync') {
    fetchHighplusBuyDataInBackground();
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
  } else if (msg && (msg.action === 'triggerActiveAutoplusTabScan' || msg.action === 'trigger_highplus_buy_sync_from_tab')) {
    console.log('[J-PRO Background] triggerActiveAutoplusTabScan 수신! SPPOL10001 탭 생성 및 자동 검색 시작');
    triggerActiveAutoplusTabScan().then(() => sendResponse({ status: 'ok' }));
    return true;
  } else if (msg && msg.action === 'trigger_highplus_buy_sync') {
    triggerActiveAutoplusTabScan().then(() => {
      fetchHighplusBuyDataInBackground().then(() => {
        sendResponse({ status: 'ok' });
      }).catch(e => {
        sendResponse({ status: 'error', message: e.message });
      });
    });
    return true;
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
