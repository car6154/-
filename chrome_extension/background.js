// 헤이딜러 쿠키 변경 감지 시 디바운스(0.5초) 후 로컬 J-PRO 서버로 자동 전송
let syncTimer = null;

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

    // 로컬 서버로 무소음 전송 (헤이딜러 서버가 아닌 내 PC 프로그램으로만 전송)
    await fetch('http://localhost:8502/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieStr })
    });
    console.log('[J-PRO AutoSync] 헤이딜러 최신 쿠키 자동 동기화 완료');
  } catch (e) {
    // 로컬 서버가 꺼져있을 때는 조용히 무시
  }
}

// 크롬 브라우저에서 헤이딜러 쿠키가 새로 생기거나 갱신될 때 실시간 감지
chrome.cookies.onChanged.addListener((changeInfo) => {
  const domain = changeInfo.cookie.domain || '';
  if (domain.includes('heydealer.com')) {
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = setTimeout(() => {
      syncCookiesToLocalServer();
    }, 500); // 0.5초 디바운스로 연속 변경 시 1회만 전송
  }
});
