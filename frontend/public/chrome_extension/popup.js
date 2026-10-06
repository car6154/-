// chrome_extension/popup.js
// 헤이딜러 & 차얼마(오토플러스) 전수 쿠키 추출 및 3중 로컬 서버(8502, 3000, 8000) 동기화 & 클립보드 복사 엔진

async function getHeydealerCookies() {
  const queryPromises = [
    chrome.cookies.getAll({ url: 'https://dealer.heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ url: 'https://api.heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ url: 'https://heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ domain: 'heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ domain: '.heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ domain: 'dealer.heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({ domain: 'api.heydealer.com' }).catch(() => []),
    chrome.cookies.getAll({}).catch(() => [])
  ];

  const results = await Promise.all(queryPromises);
  const allMap = new Map();

  // 1. chrome.cookies API 결과 병합
  results.flat().forEach(c => {
    if (c && c.name && c.value) {
      const d = (c.domain || '').toLowerCase();
      if (d.includes('heydealer') || c.name === 'sessionid' || c.name === 'csrftoken' || c.name === 'ga_dsi') {
        allMap.set(c.name, c.value);
      }
    }
  });

  // 2. 현재 활성 탭이 헤이딜러인 경우 document.cookie 보강 추출
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.id && tab.url && tab.url.includes('heydealer.com')) {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => document.cookie
      });
      if (res && res.result) {
        res.result.split(';').forEach(pair => {
          const [k, v] = pair.trim().split('=');
          if (k && v && !allMap.has(k)) {
            allMap.set(k, v);
          }
        });
      }
    }
  } catch (_) {}

  return allMap;
}

async function getAutoplusCookies() {
  const queryPromises = [
    chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }).catch(() => []),
    chrome.cookies.getAll({ domain: 'autoplus.co.kr' }).catch(() => []),
    chrome.cookies.getAll({ domain: '.autoplus.co.kr' }).catch(() => []),
    chrome.cookies.getAll({ domain: 'purchase.autoplus.co.kr' }).catch(() => []),
    chrome.cookies.getAll({}).catch(() => [])
  ];

  const results = await Promise.all(queryPromises);
  const allMap = new Map();

  results.flat().forEach(c => {
    if (c && c.name && c.value) {
      const d = (c.domain || '').toLowerCase();
      if (d.includes('autoplus') || c.name.toUpperCase() === 'JSESSIONID' || c.name.toUpperCase() === 'REMEMBER-ME') {
        allMap.set(c.name, c.value);
      }
    }
  });

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.id && tab.url && tab.url.includes('autoplus.co.kr')) {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => document.cookie
      });
      if (res && res.result) {
        res.result.split(';').forEach(pair => {
          const [k, v] = pair.trim().split('=');
          if (k && v && !allMap.has(k)) {
            allMap.set(k, v);
          }
        });
      }
    }
  } catch (_) {}

  return allMap;
}

async function broadcastCookieToServers(cookieStr, target) {
  const payload = {
    cookie: cookieStr,
    target: target,
    secretToken: 'jpro_sec_9981_live_auth'
  };

  const endpoints = [
    'http://localhost:8502/api/save_cookie',
    'http://localhost:3000/api/save_cookie',
    'http://localhost:3000/api/session/cookie',
    'http://localhost:8000/api/save_cookie'
  ];

  const results = await Promise.allSettled(
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

  return results.some(r => r.status === 'fulfilled' && r.value.ok);
}

// 1. 헤이딜러 쿠키 전송 버튼
document.getElementById('syncBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncBtn');
  btn.disabled = true;
  statusDiv.textContent = '헤이딜러 쿠키 전수 추출 중...';
  statusDiv.className = '';

  try {
    const allMap = await getHeydealerCookies();
    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 헤이딜러 쿠키를 찾지 못했습니다.<br><a href="https://dealer.heydealer.com" target="_blank" style="color:#38bdf8;">헤이딜러 딜러 로그인 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    const hasSession = allMap.has('sessionid');

    try { await navigator.clipboard.writeText(cookieStr); } catch (_) {}

    statusDiv.textContent = 'J-PRO 전산 프로그램으로 전송 중...';
    const isSaved = await broadcastCookieToServers(cookieStr, 'heydealer');

    if (hasSession) {
      statusDiv.innerHTML = `✅ <b>헤이딜러 세션(sessionid) 연동 완료!</b> (${cookieStr.length}자)<br><span style="font-size:11px;color:#94a3b8;">클립보드 복사 완료</span>`;
      statusDiv.className = 'success';
      
      if (chrome.tabs) {
        chrome.tabs.query({}, (tabs) => {
          tabs.forEach(tab => {
            if (tab.url && (tab.url.includes(':8501') || tab.url.includes(':3000'))) {
              chrome.tabs.reload(tab.id);
            }
          });
        });
      }
    } else {
      statusDiv.innerHTML = `⚠️ <b>주의: 로그인 세션(sessionid) 없음</b><br><span style="font-size:11px;color:#fbbf24;">현재 ga_dsi(통계)만 감지됨. dealer.heydealer.com 로그인 필요</span>`;
      statusDiv.className = 'error';
    }
  } catch (err) {
    statusDiv.textContent = '❌ 오류: ' + err.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

// 2. 헤이딜러 쿠키 클립보드 복사 버튼
document.getElementById('copyBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  try {
    const allMap = await getHeydealerCookies();
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 헤이딜러 쿠키가 없습니다.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    broadcastCookieToServers(cookieStr, 'heydealer').catch(() => {});

    const hasSession = allMap.has('sessionid');
    if (hasSession) {
      statusDiv.innerHTML = `📋 <b>헤이딜러 쿠키 (${cookieStr.length}자) 복사 완료!</b><br><span style="font-size:11px; color:#38bdf8;">(sessionid 세션 포함)</span>`;
      statusDiv.className = 'success';
    } else {
      statusDiv.innerHTML = `⚠️ <b>복사됨: ${cookieStr.length}자</b><br><span style="font-size:11px; color:#fbbf24;">(sessionid 없음 - dealer.heydealer.com 로그인 확인 필요)</span>`;
      statusDiv.className = 'error';
    }
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});

// 3. 차얼마(오토플러스) 쿠키 전송 버튼
document.getElementById('syncApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncApBtn');
  btn.disabled = true;
  statusDiv.textContent = '차얼마 쿠키 전수 추출 중...';
  statusDiv.className = '';

  try {
    const allMap = await getAutoplusCookies();
    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 차얼마 로그인 쿠키를 찾지 못했습니다.<br><a href="https://purchase.autoplus.co.kr/login/login.do" target="_blank" style="color:#38bdf8;">차얼마 로그인 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    try { await navigator.clipboard.writeText(cookieStr); } catch (_) {}

    statusDiv.textContent = 'J-PRO 전산 프로그램으로 전송 중...';
    await broadcastCookieToServers(cookieStr, 'autoplus');

    statusDiv.textContent = `✅ 차얼마 쿠키 (${cookieStr.length}자) 연동 완료!`;
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 오류: ' + e.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

// 4. 차얼마 쿠키 복사 버튼
document.getElementById('copyApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  try {
    const allMap = await getAutoplusCookies();
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 차얼마 쿠키를 찾지 못했습니다.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    broadcastCookieToServers(cookieStr, 'autoplus').catch(() => {});
    statusDiv.textContent = `📋 차얼마 쿠키 (${cookieStr.length}자) 복사 완료!`;
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});
