// src/services/cookieBridge.ts
// 로컬 IDE CookieServer(8502 포트) 및 크롬 확장프로그램과의 실시간 무중단 자동 동기화 브릿지

let lastHeydealerCookie = '';
let lastAutoplusCookie = '';
let isSyncing = false;

export interface CookieSyncStatus {
  hasHeydealer: boolean;
  heydealerLength: number;
  hasAutoplus: boolean;
  autoplusLength: number;
  isLocalAgentConnected: boolean;
  lastSyncedAt: string | null;
}

type StatusCallback = (status: CookieSyncStatus) => void;
const listeners = new Set<StatusCallback>();

export function subscribeCookieSync(cb: StatusCallback) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function notifyListeners(status: CookieSyncStatus) {
  listeners.forEach(cb => cb(status));
}

// 1. 클라우드 서버에 쿠키 업로드/동기화
export async function uploadCookieToServer(cookie: string, target: 'heydealer' | 'autoplus'): Promise<boolean> {
  try {
    const res = await fetch('/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cookie,
        target,
        secretToken: 'jpro_sec_9981_live_auth'
      })
    });
    const data = await res.json();
    return Boolean(data.success || data.ok);
  } catch (e) {
    console.warn('[CookieBridge] Server upload failed:', e);
    return false;
  }
}

// 2. 로컬 CookieServer(8502 포트)에서 최신 쿠키 자동 폴링 및 중계
export async function checkAndRelayLocalCookies(): Promise<boolean> {
  if (isSyncing) return false;
  isSyncing = true;

  let localConnected = false;
  let newSync = false;

  const ports = [8502, 3000];
  const hosts = ['http://localhost', 'http://127.0.0.1'];

  for (const host of hosts) {
    for (const port of ports) {
      if (port === 3000 && window.location.port === '3000') continue;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1200);

        const res = await fetch(`${host}:${port}/api/session/cookie`, {
          signal: controller.signal,
          headers: { 'Accept': 'application/json' }
        });
        clearTimeout(timeoutId);

        if (res.ok) {
          const data = await res.json();
          localConnected = true;

          // 헤이딜러 쿠키 변경 감지 시 자동 업로드
          if (data.heydealerCookie && data.heydealerCookie !== lastHeydealerCookie) {
            lastHeydealerCookie = data.heydealerCookie;
            localStorage.setItem('jpro_heydealer_cookie', data.heydealerCookie);
            await uploadCookieToServer(data.heydealerCookie, 'heydealer');
            newSync = true;
          }

          // 차얼마 쿠키 변경 감지 시 자동 업로드
          if (data.autoplusCookie && data.autoplusCookie !== lastAutoplusCookie) {
            lastAutoplusCookie = data.autoplusCookie;
            localStorage.setItem('jpro_autoplus_cookie', data.autoplusCookie);
            await uploadCookieToServer(data.autoplusCookie, 'autoplus');
            newSync = true;
          }

          break;
        }
      } catch (_) {
        // 로컬 포트 미기동 시 무시
      }
    }
    if (localConnected) break;
  }

  // 로컬 스토리지에 저장된 쿠키가 서버에 없을 경우 복원
  const cachedHd = localStorage.getItem('jpro_heydealer_cookie') || localStorage.getItem('jpro_session_cookie');
  const cachedAp = localStorage.getItem('jpro_autoplus_cookie');

  if (cachedHd && cachedHd !== lastHeydealerCookie) {
    lastHeydealerCookie = cachedHd;
    await uploadCookieToServer(cachedHd, 'heydealer');
  }
  if (cachedAp && cachedAp !== lastAutoplusCookie) {
    lastAutoplusCookie = cachedAp;
    await uploadCookieToServer(cachedAp, 'autoplus');
  }

  isSyncing = false;

  notifyListeners({
    hasHeydealer: Boolean(lastHeydealerCookie),
    heydealerLength: lastHeydealerCookie.length,
    hasAutoplus: Boolean(lastAutoplusCookie),
    autoplusLength: lastAutoplusCookie.length,
    isLocalAgentConnected: localConnected,
    lastSyncedAt: new Date().toLocaleTimeString('ko-KR')
  });

  return newSync;
}

// 3. 브라우저 실시간 자동 동기화 엔진 시작
export function startContinuousCookieSync() {
  // 최초 1회 실행
  checkAndRelayLocalCookies();

  // 10초마다 무중단 백그라운드 폴링 (IDE와 동일한 상시 최신 상태 유지)
  const intervalId = setInterval(checkAndRelayLocalCookies, 10000);

  // 창 활성화 / 탭 전환 시 즉시 동기화
  const handleVisibility = () => {
    if (document.visibilityState === 'visible') {
      checkAndRelayLocalCookies();
    }
  };
  window.addEventListener('visibilitychange', handleVisibility);
  window.addEventListener('focus', handleVisibility);

  // 크롬 확장프로그램이 window.postMessage로 전송하는 이벤트 수신
  const handleMessage = async (e: MessageEvent) => {
    if (e.data && e.data.type === 'JPRO_COOKIE_SYNC') {
      const { cookie, target } = e.data;
      if (cookie) {
        await uploadCookieToServer(cookie, target || 'heydealer');
        checkAndRelayLocalCookies();
      }
    }
  };
  window.addEventListener('message', handleMessage);

  return () => {
    clearInterval(intervalId);
    window.removeEventListener('visibilitychange', handleVisibility);
    window.removeEventListener('focus', handleVisibility);
    window.removeEventListener('message', handleMessage);
  };
}
