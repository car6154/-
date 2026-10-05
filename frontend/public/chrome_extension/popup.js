// J-PRO Chrome Extension Popup Script
// Auto-detects open J-PRO tab or local servers, extracts Heydealer & Chaolma cookies

async function sendCookieToServer(cookieStr, target) {
  const endpoints = [
    'http://localhost:3000/api/session/cookie',
    'http://localhost:3000/api/save_cookie',
    'http://localhost:8502/api/save_cookie',
  ];

  // Also look for currently open J-PRO Cloud tab URLs
  if (chrome.tabs) {
    const tabs = await chrome.tabs.query({});
    for (const tab of tabs) {
      if (tab.url && (tab.url.includes('run.app') || tab.url.includes('j-pro') || tab.url.includes('localhost:3000'))) {
        try {
          const origin = new URL(tab.url).origin;
          endpoints.unshift(`${origin}/api/session/cookie`);
          endpoints.unshift(`${origin}/api/save_cookie`);
        } catch (_) {}
      }
    }
  }

  let sentOk = false;
  for (const ep of endpoints) {
    try {
      const res = await fetch(ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          cookie: cookieStr, 
          target: target,
          secretToken: 'jpro_sec_9981_live_auth'
        })
      });
      if (res.ok) {
        sentOk = true;
        break;
      }
    } catch (_) {}
  }
  return sentOk;
}

// 1. 헤이딜러 쿠키 전송
document.getElementById('syncBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncBtn');
  btn.disabled = true;
  statusDiv.textContent = '헤이딜러 쿠키 추출 중...';
  statusDiv.className = '';

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
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });

    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 헤이딜러 쿠키를 찾지 못했습니다.<br><a href="https://dealer.heydealer.com" target="_blank" style="color:#38bdf8;">헤이딜러 로그인 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    try { await navigator.clipboard.writeText(cookieStr); } catch (_) {}

    statusDiv.textContent = 'J-PRO ERP로 전송 중...';
    const ok = await sendCookieToServer(cookieStr, 'heydealer');

    if (ok) {
      statusDiv.textContent = '✅ 헤이딜러 쿠키 연동 완료! (클립보드에도 복사됨)';
      statusDiv.className = 'success';
    } else {
      statusDiv.innerHTML = '📋 클립보드에 복사되었습니다!<br>(J-PRO 상단 [🔑 세션 연동]에 붙여넣기)';
      statusDiv.className = 'success';
    }
  } catch (err) {
    statusDiv.textContent = '❌ 오류: ' + err.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

// 2. 헤이딜러 쿠키 클립보드 복사
document.getElementById('copyBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
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
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 헤이딜러 쿠키가 없습니다.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    statusDiv.textContent = '📋 헤이딜러 쿠키 복사 완료!';
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});

// 3. 차얼마 쿠키 전송
document.getElementById('syncApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncApBtn');
  btn.disabled = true;
  statusDiv.textContent = '차얼마 쿠키 추출 중...';
  statusDiv.className = '';

  try {
    const cookies = await chrome.cookies.getAll({ domain: 'autoplus.co.kr' });
    const allMap = new Map();
    cookies.forEach(c => {
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });

    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 차얼마 쿠키를 찾지 못했습니다.<br><a href="https://purchase.autoplus.co.kr/login/login.do" target="_blank" style="color:#34d399;">차얼마 로그인 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    try { await navigator.clipboard.writeText(cookieStr); } catch (_) {}

    statusDiv.textContent = 'J-PRO ERP로 전송 중...';
    const ok = await sendCookieToServer(cookieStr, 'autoplus');

    if (ok) {
      statusDiv.textContent = '✅ 차얼마 쿠키 연동 완료! (클립보드 복사됨)';
      statusDiv.className = 'success';
    } else {
      statusDiv.innerHTML = '📋 클립보드에 복사되었습니다!<br>(J-PRO 상단 [🔑 세션 연동]에 붙여넣기)';
      statusDiv.className = 'success';
    }
  } catch (err) {
    statusDiv.textContent = '❌ 오류: ' + err.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

// 4. 차얼마 쿠키 클립보드 복사
document.getElementById('copyApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  try {
    const cookies = await chrome.cookies.getAll({ domain: 'autoplus.co.kr' });
    const allMap = new Map();
    cookies.forEach(c => {
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 차얼마 쿠키가 없습니다.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    statusDiv.textContent = '📋 차얼마 쿠키 복사 완료!';
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});
