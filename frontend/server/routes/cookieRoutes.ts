import { Router } from 'express';
import path from 'path';
import fs from 'fs';

export const COOKIE_FILE = path.resolve(process.cwd(), '.session_cookie.json');
export const HD_COOKIE_FILE = path.resolve(process.cwd(), 'heydealer_cookie.txt');
export const AP_COOKIE_FILE = path.resolve(process.cwd(), 'autoplus_cookie.txt');
export const AP_DATA_COOKIE_FILE = path.resolve(process.cwd(), 'autoplus_data_cookie.txt');
export const LOG_FILE = path.resolve(process.cwd(), 'server.log');

let savedHeydealerCookie = '';
let savedAutoplusCookie = '';
let savedAutoplusDataCookie = '';

export function getSavedHeydealerCookie() {
  return savedHeydealerCookie;
}

export function getSavedAutoplusCookie() {
  return savedAutoplusCookie;
}

export function getSavedAutoplusDataCookie() {
  return savedAutoplusDataCookie;
}

export function setSavedHeydealerCookie(val: string) {
  savedHeydealerCookie = val;
}

export function setSavedAutoplusCookie(val: string) {
  savedAutoplusCookie = val;
}

export function setSavedAutoplusDataCookie(val: string) {
  savedAutoplusDataCookie = val;
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
    savedAutoplusDataCookie = data.autoplus_data_cookie || '';
  }
  if (!savedHeydealerCookie && fs.existsSync(HD_COOKIE_FILE)) {
    savedHeydealerCookie = fs.readFileSync(HD_COOKIE_FILE, 'utf8').trim();
  }
  if (!savedAutoplusCookie && fs.existsSync(AP_COOKIE_FILE)) {
    savedAutoplusCookie = fs.readFileSync(AP_COOKIE_FILE, 'utf8').trim();
  }
  if (!savedAutoplusDataCookie && fs.existsSync(AP_DATA_COOKIE_FILE)) {
    savedAutoplusDataCookie = fs.readFileSync(AP_DATA_COOKIE_FILE, 'utf8').trim();
  }
  logEvent('INIT', `저장된 세션 쿠키 복원 완료 - HD(${savedHeydealerCookie.length}B), AP_Admin(${savedAutoplusCookie.length}B), AP_Data(${savedAutoplusDataCookie.length}B)`);
} catch (e) {
  logEvent('WARN', '쿠키 복원 실패', e);
}

export function saveCookiesToDisk() {
  try {
    fs.writeFileSync(COOKIE_FILE, JSON.stringify({
      heydealer_cookie: savedHeydealerCookie,
      autoplus_cookie: savedAutoplusCookie,
      autoplus_data_cookie: savedAutoplusDataCookie,
      cookie: savedHeydealerCookie,
      updatedAt: new Date().toISOString()
    }, null, 2));
    if (savedHeydealerCookie) fs.writeFileSync(HD_COOKIE_FILE, savedHeydealerCookie);
    if (savedAutoplusCookie) fs.writeFileSync(AP_COOKIE_FILE, savedAutoplusCookie);
    if (savedAutoplusDataCookie) fs.writeFileSync(AP_DATA_COOKIE_FILE, savedAutoplusDataCookie);
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

  if (targetType === 'autoplus_data' || targetType === 'chaolma') {
    savedAutoplusDataCookie = trimmed;
    logEvent('COOKIE_SYNC', `[J-PRO] 오토플러스 차얼마(데이터) 쿠키 동기화 완료 (${trimmed.length}자)`);
  } else if (targetType === 'autoplus_admin' || targetType.includes('autoplus') || trimmed.includes('JSESSIONID') || trimmed.includes('remember-me')) {
    savedAutoplusCookie = trimmed;
    logEvent('COOKIE_SYNC', `[J-PRO] 오토플러스 어드민 쿠키 동기화 완료 (${trimmed.length}자)`);
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

  // 🔗 Python 백엔드(8000)로 쿠키 동시 전달 및 AutoplusSyncService.execute_sync() 트리거
  try {
    fetch('http://127.0.0.1:8000/api/save_cookie', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-JPRO-Token': 'jpro_sec_9981_live_auth'
      },
      body: JSON.stringify({
        cookie: trimmed,
        target: targetType || 'heydealer',
        secretToken: 'jpro_sec_9981_live_auth'
      }),
      signal: AbortSignal.timeout(3000)
    }).catch(() => {});
  } catch (_) {}

  return res.json({
    success: true,
    message: '세션 쿠키가 클라우드 금고에 안전하게 저장되었습니다.',
    heydealerLength: savedHeydealerCookie.length,
    autoplusLength: savedAutoplusCookie.length,
    autoplusDataLength: savedAutoplusDataCookie.length,
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
