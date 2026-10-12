import { Router } from 'express';
import path from 'path';
import fs from 'fs';

export const COOKIE_FILE = path.resolve(process.cwd(), '.session_cookie.json');
export const HD_COOKIE_FILE = path.resolve(process.cwd(), 'heydealer_cookie.txt');
export const AP_COOKIE_FILE = path.resolve(process.cwd(), 'autoplus_cookie.txt');
export const LOG_FILE = path.resolve(process.cwd(), 'server.log');

let savedHeydealerCookie = '';
let savedAutoplusCookie = '';

export function getSavedHeydealerCookie() {
  return savedHeydealerCookie;
}

export function getSavedAutoplusCookie() {
  return savedAutoplusCookie;
}

export function setSavedHeydealerCookie(val: string) {
  savedHeydealerCookie = val;
}

export function setSavedAutoplusCookie(val: string) {
  savedAutoplusCookie = val;
}

export function logEvent(type: string, message: string, details?: any) {
  const line = `[${new Date().toISOString()}] [${type}] ${message} ${details ? JSON.stringify(details) : ''}\n`;
  console.log(line.trim());
  try {
    fs.appendFileSync(LOG_FILE, line);
  } catch (e) {}
}

// 1. 초기화 시 저장된 쿠키 복원 (JSON 파일 및 텍스트 파일)
try {
  if (fs.existsSync(COOKIE_FILE)) {
    const data = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
    savedHeydealerCookie = data.heydealer_cookie || data.cookie || '';
    savedAutoplusCookie = data.autoplus_cookie || '';
  }
  if (!savedHeydealerCookie && fs.existsSync(HD_COOKIE_FILE)) {
    savedHeydealerCookie = fs.readFileSync(HD_COOKIE_FILE, 'utf8').trim();
  }
  if (!savedAutoplusCookie && fs.existsSync(AP_COOKIE_FILE)) {
    savedAutoplusCookie = fs.readFileSync(AP_COOKIE_FILE, 'utf8').trim();
  }
  logEvent('INIT', `저장된 세션 쿠키 복원 완료 - HD(${savedHeydealerCookie.length}B), AP(${savedAutoplusCookie.length}B)`);
} catch (e) {
  logEvent('WARN', '쿠키 복원 실패', e);
}

export function saveCookiesToDisk() {
  try {
    fs.writeFileSync(COOKIE_FILE, JSON.stringify({
      heydealer_cookie: savedHeydealerCookie,
      autoplus_cookie: savedAutoplusCookie,
      cookie: savedHeydealerCookie,
      updatedAt: new Date().toISOString()
    }, null, 2));
    if (savedHeydealerCookie) fs.writeFileSync(HD_COOKIE_FILE, savedHeydealerCookie);
    if (savedAutoplusCookie) fs.writeFileSync(AP_COOKIE_FILE, savedAutoplusCookie);
  } catch (e) {
    console.error('쿠키 파일 저장 오류:', e);
  }
}

export const cookieRouter = Router();

// 시스템 실시간 로그 조회 API
cookieRouter.get('/api/logs', (req, res) => {
  try {
    if (!fs.existsSync(LOG_FILE)) {
      return res.json({ logs: ['로그 파일이 아직 비어있습니다.'] });
    }
    const content = fs.readFileSync(LOG_FILE, 'utf8');
    const lines = content.trim().split('\n').slice(-150);
    return res.json({ logs: lines });
  } catch (err: any) {
    return res.status(500).json({ error: err.message });
  }
});

// 1. 크롬 확장프로그램 및 웹 UI 쿠키 저장 엔드포인트
cookieRouter.post(['/api/session/cookie', '/api/save_cookie'], (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-secret-token');

  const { cookie, target, secretToken } = req.body;
  if (secretToken && secretToken !== 'jpro_sec_9981_live_auth') {
    return res.status(403).json({ error: '인증 토큰이 일치하지 않습니다.' });
  }

  if (!cookie || typeof cookie !== 'string') {
    return res.status(400).json({ error: '유효한 쿠키 문자열을 전달해주세요.' });
  }

  const trimmed = cookie.trim();
  const targetType = (target || '').toLowerCase();

  if (targetType.includes('autoplus') || targetType.includes('chaolma') || trimmed.includes('JSESSIONID') || trimmed.includes('remember-me')) {
    savedAutoplusCookie = trimmed;
    logEvent('COOKIE_SYNC', `[J-PRO] 차얼마(오토플러스) 쿠키 동기화 완료 (${trimmed.length}자)`);
  } else {
    // 헤이딜러: 기존에 sessionid가 유효한데 새로 들어온 쿠키에 sessionid가 없으면 덮어쓰기 방지
    if (savedHeydealerCookie && savedHeydealerCookie.includes('sessionid=') && !trimmed.includes('sessionid=')) {
      logEvent('COOKIE_SYNC', `[J-PRO] 기존 유효 sessionid 보존 (새 쿠키에 sessionid 누락됨: ${trimmed.length}자)`);
    } else {
      savedHeydealerCookie = trimmed;
      logEvent('COOKIE_SYNC', `[J-PRO] 헤이딜러 쿠키 동기화 완료 (${trimmed.length}자)`);
    }
  }

  saveCookiesToDisk();

  return res.json({
    success: true,
    message: '세션 쿠키가 클라우드 금고에 안전하게 저장되었습니다.',
    heydealerLength: savedHeydealerCookie.length,
    autoplusLength: savedAutoplusCookie.length,
  });
});

// CORS Preflight
cookieRouter.options(['/api/session/cookie', '/api/save_cookie'], (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-secret-token');
  res.sendStatus(204);
});

// 2. 현재 쿠키 상태 확인 API
cookieRouter.get('/api/session/cookie', (req, res) => {
  return res.json({
    hasCookie: Boolean(savedHeydealerCookie),
    cookieLength: savedHeydealerCookie.length,
    hasAutoplusCookie: Boolean(savedAutoplusCookie),
    autoplusCookieLength: savedAutoplusCookie.length,
    heydealerCookie: savedHeydealerCookie ? savedHeydealerCookie.slice(0, 30) + '...' : '',
  });
});
