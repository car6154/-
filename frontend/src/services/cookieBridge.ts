// src/services/cookieBridge.ts
// 로컬 IDE CookieServer(8502 포트) 및 크롬 확장프로그램과의 실시간 무중단 자동 동기화 브릿지

let lastHeydealerCookie = '';
let lastAutoplusCookie = '';
let isSyncing = false;
let last8502CheckTime = 0;
let consecutive8502Failures = 0;

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

export const JPRO_COOKIE_SECRET_TOKEN = 'jpro_sec_9981_live_auth';

// 1. 클라우드 서버에 쿠키 업로드/동기화
export async function uploadCookieToServer(cookie: string, target: 'heydealer' | 'autoplus'): Promise<boolean> {
  try {
    const res = await fetch('/api/save_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cookie,
        target,
        secretToken: JPRO_COOKIE_SECRET_TOKEN
      })
    });
    const data = await res.json();
    return Boolean(data.success || data.ok);
  } catch (e) {
    console.warn('[CookieBridge] Server upload failed:', e);
    return false;
  }
}

// 2. 로컬 CookieServer(8502 포트) 및 자체 백엔드에서 최신 쿠키 자동 동기화
export async function checkAndRelayLocalCookies(): Promise<boolean> {
  if (isSyncing) return false;
  isSyncing = true;

  let localConnected = false;
  let newSync = false;

  // 2-1. 프론트엔드 자체 백엔드(/api/session/cookie)와 1차 동기화 (Same-Origin - CORS 에러 원천 차단)
  try {
    const res = await fetch('/api/session/cookie', {
      headers: { 'Accept': 'application/json' }
    });
    if (res.ok) {
      const data = await res.json();
      if (data.heydealerCookie && data.heydealerCookie !== lastHeydealerCookie) {
        lastHeydealerCookie = data.heydealerCookie;
        localStorage.setItem('jpro_heydealer_cookie', data.heydealerCookie);
        newSync = true;
      }
      if (data.autoplusCookie && data.autoplusCookie !== lastAutoplusCookie) {
        lastAutoplusCookie = data.autoplusCookie;
        localStorage.setItem('jpro_autoplus_cookie', data.autoplusCookie);
        newSync = true;
      }
    }
  } catch (_) {
    // 백엔드 미응답 시 조용히 통과
  }

  // 2-2. 로컬 8502 포트(Python/Companion Cookie Server) 점검
  // 실패 이력이 있으면 30초 백오프 후 조용히 재시도하여 브라우저 콘솔 에러 누적 방지
  const now = Date.now();
  const shouldProbe8502 = consecutive8502Failures === 0 || (now - last8502CheckTime >= 30000);

  if (shouldProbe8502) {
    last8502CheckTime = now;
    const currentHost = window.location.hostname || 'localhost';
    const hosts = [currentHost, currentHost === 'localhost' ? '127.0.0.1' : 'localhost'];

    for (const host of hosts) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1200);

        const res = await fetch(`http://${host}:8502/api/session/cookie`, {
          signal: controller.signal,
          mode: 'cors',
          headers: { 'Accept': 'application/json' }
        });
        clearTimeout(timeoutId);

        if (res.ok) {
          const data = await res.json();
          localConnected = true;
          consecutive8502Failures = 0;

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
        // 로컬 포트 미기동 또는 일시 오류 시 조용히 무시 (콘솔 노이즈 방지)
      }
    }

    if (!localConnected) {
      consecutive8502Failures++;
    }
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

  // 30초마다 무중단 백그라운드 폴링 (불필요한 과도 폴링 방지 및 콘솔 부하 제거)
  const intervalId = setInterval(checkAndRelayLocalCookies, 30000);

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
