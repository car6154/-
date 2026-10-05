// J-PRO Background Service Worker
const SECRET_TOKEN = 'jpro_sec_9981_live_auth';

// 헤이딜러 쿠키 추출 및 J-PRO 서버로 전송
async function syncHeydealerCookies() {
  try {
    const cookies = await chrome.cookies.getAll({ domain: "heydealer.com" });
    if (!cookies || cookies.length === 0) {
      console.log('[J-PRO Extension] 헤이딜러 쿠키 없음');
      return { success: false, message: '헤이딜러에 먼저 로그인해주세요.' };
    }

    const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

    // 저장된 J-PRO 서버 주소 확인 (기본값 설정)
    const storage = await chrome.storage.local.get(['serverUrl']);
    const serverUrl = storage.serverUrl || 'https://ais-dev-2br46rkotrokqfzdwk6oxg-839480298953.asia-east1.run.app';

    const res = await fetch(`${serverUrl}/api/session/cookie`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cookie: cookieStr,
        secretToken: SECRET_TOKEN
      })
    });

    const result = await res.json();
    console.log('[J-PRO Extension] 동기화 결과:', result);
    return { success: true, count: cookies.length };
  } catch (err) {
    console.error('[J-PRO Extension] 전송 실패:', err);
    return { success: false, message: err.message };
  }
}

// 쿠키 변경 감지 시 자동 전송
chrome.cookies.onChanged.addListener((changeInfo) => {
  if (changeInfo.cookie.domain.includes('heydealer.com')) {
    syncHeydealerCookies();
  }
});

// 팝업에서 메시지 수신
chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action === 'SYNC_NOW') {
    syncHeydealerCookies().then(sendResponse);
    return true;
  }
});
