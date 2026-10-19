import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import fs from 'fs';
import http from 'http';
import {
  cookieRouter,
  logEvent,
  getSavedHeydealerCookie,
  getSavedAutoplusCookie,
  setSavedHeydealerCookie,
  setSavedAutoplusCookie,
  saveCookiesToDisk,
  COOKIE_FILE,
  HD_COOKIE_FILE,
  AP_COOKIE_FILE,
  LOG_FILE
} from './server/routes/cookieRoutes';
import { aiRouter } from './server/routes/aiRoutes';

export { logEvent };

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;

  app.use(express.json({ limit: '10mb' }));

  // API 요청 로깅
  app.use((req, res, next) => {
    if (req.path.startsWith('/api/')) {
      logEvent('HTTP_IN', `${req.method} ${req.originalUrl || req.path}`, {
        ip: req.ip,
        hasAuth: Boolean(req.headers.authorization),
        hasCookieHeader: Boolean(req.headers['x-heydealer-cookie']),
      });
    }
    next();
  });

  // 쿠키 세션 및 시스템 로그 라우터 마운트
  app.use(cookieRouter);
  // Gemini AI 및 백엔드 프록시 라우터 마운트
  app.use(aiRouter);

  // 2-0-0. 매입 장부 관리 API 프록시 (Python 백엔드 8000 직결)
  app.all('/api/ledger*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(15000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ error: `장부 API 프록시 실패: ${e.message}` });
    }
  });

  // 2-0. 실전 재고 및 정산 관리 프록시 (Python 백엔드 8000 직결)
  app.all('/api/settlement*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(15000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ error: `정산 API 프록시 실패: ${e.message}` });
    }
  });

  // 2-0-1. 오토플러스 / 사내 차량 데이터 API 프록시 (Python 백엔드 8000 직결)
  app.all('/api/autoplus*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(15000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ error: `오토플러스 API 프록시 실패: ${e.message}` });
    }
  });

  // 2-0-2. 서버 제어 API 프록시 (Python 백엔드 8000 직결)
  app.all('/api/server/*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(15000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ error: `서버 제어 API 프록시 실패: ${e.message}` });
    }
  });

  app.all('/api/git/*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(20000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ error: `Git 동기화 프록시 실패: ${e.message}` });
    }
  });

  // 2-2. 자동 로그인 및 계정 관리 프록시 (Python 백엔드 8000 직결 & Node .env 직접 보관 폴백)
  app.all('/api/auth/*', async (req, res) => {
    try {
      const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
      const pyRes = await fetch(targetUrl, {
        method: req.method,
        headers: { 'Content-Type': 'application/json' },
        body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(35000)
      });
      const data = await pyRes.json();
      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      // 만약 계정 저장 요청인데 Python 8000 연결이 지연되면 Node에서 직접 .env에 저장 (0.01초 폴백)
      if (req.path === '/api/auth/credentials' && req.method === 'POST') {
        try {
          const { platform, userId, userPw } = req.body || {};
          const envPath = path.resolve(__dirname, '../.env');
          const prefix = (platform || '').toLowerCase().includes('auto') ? 'AUTOPLUS' : 'HEYDEALER';
          let content = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';
          
          const updateOrAppend = (key: string, val: string) => {
            const regex = new RegExp(`^${key}=.*$`, 'm');
            if (regex.test(content)) {
              content = content.replace(regex, `${key}="${val}"`);
            } else {
              content += (content.endsWith('\n') || !content ? '' : '\n') + `${key}="${val}"\n`;
            }
          };
          updateOrAppend(`${prefix}_ID`, (userId || '').trim());
          updateOrAppend(`${prefix}_PW`, (userPw || '').trim());
          fs.writeFileSync(envPath, content, 'utf8');
          return res.json({ success: true, message: `${prefix} 계정 정보가 .env에 안전하게 저장되었습니다.` });
        } catch (err: any) {
          return res.status(500).json({ success: false, message: `계정 저장 실패: ${err.message}` });
        }
      }
      return res.status(500).json({ success: false, message: `자동 로그인 프록시 실패: ${e.message}` });
    }
  });

  // 3. 헤이딜러 실제 차량 API 프록시 (Python Engine 연동 & Node 백업 프록시)
  app.get('/api/heydealer/car/:hashId', async (req, res) => {
    const { hashId } = req.params;
    const authHeader = req.headers.authorization || '';
    const activeCookie = (req.headers['x-heydealer-cookie'] as string) || (() => {
      try {
        if (fs.existsSync(HD_COOKIE_FILE)) {
          const val = fs.readFileSync(HD_COOKIE_FILE, 'utf8').trim();
          if (val) return val;
        }
        if (fs.existsSync(COOKIE_FILE)) {
          const d = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
          const val = d.heydealer_cookie || d.cookie || '';
          if (val) return val;
        }
      } catch (e) {}
      return getSavedHeydealerCookie() || '';
    })();

    // [1단계 연동] Python FastAPI 백엔드 (8000) 우선 호출 (쿠키 로테이션/CSRF 헤더/20대 낙찰가 자동 결합 지원)
    try {
      const pyRes = await fetch(`http://127.0.0.1:8000/api/heydealer/car/${hashId}`, {
        signal: AbortSignal.timeout(12000)
      });
      if (pyRes.ok) {
        const pyData = await pyRes.json();
        if (pyData?.success && pyData?.data) {
          logEvent('HEYDEALER_IN', `[Python Engine] 헤이딜러 [${hashId}] 및 낙찰시세 20대 수집 완료`);
          return res.json(pyData);
        }
      }
    } catch (e: any) {
      logEvent('HEYDEALER_WARN', `Python API 연결 대기, Node 프록시로 실행: ${e.message}`);
    }

    // [2단계 연동] Node 직접 프록시
    try {
      logEvent('HEYDEALER_OUT', `Requesting https://api.heydealer.com/v2/dealers/web/cars/${hashId}/`, {
        cookiePresent: Boolean(activeCookie),
        cookieLen: activeCookie.length,
      });

      const hdRes = await fetch(`https://api.heydealer.com/v2/dealers/web/cars/${hashId}/`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
          'App-Os': 'pc',
          'App-Type': 'dealer',
          'App-Version': '1.9.0',
          'Referer': `https://dealer.heydealer.com/cars/${hashId}/`,
          'Origin': 'https://dealer.heydealer.com',
          ...(authHeader ? { 'Authorization': authHeader as string } : {}),
          ...(activeCookie ? { 'Cookie': activeCookie } : {}),
        }
      });

      if (!hdRes.ok) {
        // 인증 만료 시 로컬 캐시 폴백 확인
        try {
          const backupFile = path.resolve(process.cwd(), 'last_heydealer_detail.json');
          if (fs.existsSync(backupFile)) {
            const backupData = JSON.parse(fs.readFileSync(backupFile, 'utf8'));
            if (backupData && (backupData.hash_id === hashId || hashId === 'QrqzKqKn' || hashId === 'sample')) {
              return res.json({ success: true, data: backupData, isFallback: true, cached: true });
            }
          }
        } catch (e) {}

        return res.status(hdRes.status).json({
          success: false,
          errorType: (hdRes.status === 401 || hdRes.status === 403) ? 'LOGIN_REQUIRED' : 'API_ERROR',
          message: `헤이딜러 API 인증/응답 실패 (${hdRes.status})`
        });
      }

      const data = await hdRes.json();

      // 20대 동급 낙찰가(market_prices) 추가 수집
      let marketPricesData: any = null;
      try {
        let params: any = null;
        const findParams = (obj: any) => {
          if (params || !obj || typeof obj !== 'object') return;
          if (obj.params && typeof obj.params === 'object' && (obj.params.model || obj.params.grade)) {
            params = obj.params;
            return;
          }
          if (obj.price_info && typeof obj.price_info === 'object' && obj.price_info.params) {
            params = obj.price_info.params;
            return;
          }
          for (const k of Object.keys(obj)) {
            if (typeof obj[k] === 'object') findParams(obj[k]);
          }
        };
        findParams(data);

        if (!params) {
          const det = data.detail || data;
          const mId = det.model || det.model_id;
          const gId = det.grade || det.grade_id;
          const yVal = det.year;
          if (mId && gId) {
            params = {
              model: mId,
              grade: gId,
              year: yVal ? [yVal - 1, yVal, yVal + 1] : []
            };
          }
        }

        if (params) {
          const allMarketResults: any[] = [];
          for (let pNum = 1; pNum <= 10; pNum++) {
            const qParts = [`page=${pNum}`];
            for (const [k, v] of Object.entries(params)) {
              if (Array.isArray(v)) {
                v.forEach((item) => qParts.push(`${k}=${encodeURIComponent(String(item))}`));
              } else if (v !== undefined && v !== null) {
                qParts.push(`${k}=${encodeURIComponent(String(v))}`);
              }
            }
            if (!params.period) qParts.push('period=c');
            if (!params.order) qParts.push('order=recent');

            const mpUrl = `https://api.heydealer.com/v2/dealers/web/price/cars/?${qParts.join('&')}`;
            const mpRes = await fetch(mpUrl, {
              headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'App-Os': 'pc',
                'App-Type': 'dealer',
                'App-Version': '1.9.0',
                'Referer': `https://dealer.heydealer.com/cars/${hashId}/`,
                'Origin': 'https://dealer.heydealer.com',
                ...(authHeader ? { 'Authorization': authHeader as string } : {}),
                ...(activeCookie ? { 'Cookie': activeCookie } : {}),
              }
            });

            if (mpRes.ok) {
              const pData: any = await mpRes.json();
              const items = Array.isArray(pData) ? pData : (pData?.results || []);
              if (!items.length) break;
              allMarketResults.push(...items);
              if (items.length < 20) break; // 마지막 페이지
            } else {
              break;
            }
          }

          if (allMarketResults.length > 0) {
            marketPricesData = { results: allMarketResults };
            logEvent('HEYDEALER_IN', `market_prices fetched: ${allMarketResults.length} total comps`);
          }
        }
      } catch (mpErr) {
        console.warn('동급 낙찰시세 수집 예외:', mpErr);
      }

      const responsePayload = {
        ...data,
        market_prices: marketPricesData
      };

      // 캐시 파일 업데이트
      try {
        fs.writeFileSync(path.resolve(process.cwd(), 'last_heydealer_detail.json'), JSON.stringify(responsePayload, null, 2), 'utf8');
      } catch (e) {}

      return res.status(200).json({
        success: true,
        data: responsePayload
      });
    } catch (err: any) {
      console.error('헤이딜러 프록시 호출 실패:', err);
      // 네트워크 예외 시에도 로컬 캐시 시도
      try {
        const backupFile = path.resolve(process.cwd(), 'last_heydealer_detail.json');
        if (fs.existsSync(backupFile)) {
          const backupData = JSON.parse(fs.readFileSync(backupFile, 'utf8'));
          if (backupData && (backupData.hash_id === hashId || hashId === 'QrqzKqKn' || hashId === 'sample')) {
            return res.json({ success: true, data: backupData, isFallback: true, cached: true });
          }
        }
      } catch (e) {}
      return res.status(500).json({ success: false, errorType: 'NETWORK_ERROR', message: '헤이딜러 서버 통신 실패: ' + err.message });
    }
  });

  // 3-1. 자사(오토플러스) 실적 및 시장 수요도 통계 API (FastAPI 8000 브릿지)
  app.get('/api/market_statistics', async (req, res) => {
    try {
      const q = new URLSearchParams(req.query as any).toString();
      const pyRes = await fetch(`http://127.0.0.1:8000/api/market_statistics?${q}`);
      if (pyRes.ok) {
        const data = await pyRes.json();
        return res.json(data);
      }
    } catch (e: any) {
      console.warn('market_statistics FastAPI forward failed:', e.message);
    }
    return res.json({ success: false, data: { has_data: false, total_count: 0, sample_list: [] } });
  });

  // 3-2. 엔카 최근 완판(팔린매물) 실거래 스냅샷 통계 API (FastAPI 8000 브릿지)
  app.get('/api/sold_out_cars', async (req, res) => {
    try {
      const q = new URLSearchParams(req.query as any).toString();
      const pyRes = await fetch(`http://127.0.0.1:8000/api/sold_out_cars?${q}`);
      if (pyRes.ok) {
        const data = await pyRes.json();
        return res.json(data);
      }
    } catch (e: any) {
      console.warn('sold_out_cars FastAPI forward failed:', e.message);
    }
    return res.json({ success: false, sold_statistics: { has_data: false }, enriched_info: {} });
  });

  // [마스터 차량 매핑 DB 캐시 및 BadgeGroup 자동 매핑 엔진]
  let masterCarDb: any = null;
  try {
    const possiblePaths = [
      path.join(process.cwd(), '..', 'data', 'master_car_mapping.json'),
      path.join(process.cwd(), 'data', 'master_car_mapping.json'),
      path.resolve('c:/Users/car61/Desktop/제이프로젝트/data/master_car_mapping.json')
    ];
    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        masterCarDb = JSON.parse(fs.readFileSync(p, 'utf-8'));
        break;
      }
    }
  } catch (_) {}

  const resolveBadgeGroup = (carName: string, subModel: string, targetBadge: string): string => {
    // 1. 마스터 DB에서 직접 탐색
    if (masterCarDb?.models) {
      const models = masterCarDb.models;
      const targets = [subModel, carName];
      for (const [mName, mInfo] of Object.entries<any>(models)) {
        const matchModel = targets.some(t => t && (mName.includes(t) || t.includes(mName) || mInfo.encar_model?.includes(t) || t.includes(mInfo.encar_model)));
        if (matchModel && mInfo.trims) {
          // A. 정확한 트림명 일치
          for (const [tName, tData] of Object.entries<any>(mInfo.trims)) {
            if (tName === targetBadge || tData.badge === targetBadge) {
              if (tData.badge_group) return tData.badge_group;
            }
          }
          // B. 정규화 부분 일치
          const cleanTarget = targetBadge.replace(/\s+/g, '').toLowerCase();
          for (const [tName, tData] of Object.entries<any>(mInfo.trims)) {
            const cleanTrim = tName.replace(/\s+/g, '').toLowerCase();
            const cleanBadge = (tData.badge || '').replace(/\s+/g, '').toLowerCase();
            if (cleanTrim.includes(cleanTarget) || cleanTarget.includes(cleanTrim) || cleanBadge === cleanTarget) {
              if (tData.badge_group) return tData.badge_group;
            }
          }
        }
      }
    }

    // 2. 규칙 기반 지능형 추론 (카니발, 그랜저, 쏘나타 등)
    const normCar = (carName + ' ' + subModel).toLowerCase().replace(/\s+/g, '');
    const normBadge = targetBadge.toLowerCase().replace(/\s+/g, '');

    if (normCar.includes('카니발')) {
      const seatMatch = normBadge.match(/(\d+)인승/) || normCar.match(/(\d+)인승/);
      const seats = seatMatch ? seatMatch[1] : '9';
      const isGasoline = normBadge.includes('가솔린') || normCar.includes('가솔린') || normBadge.includes('3.3') || normBadge.includes('3.5');
      const isHybrid = normBadge.includes('하이브리드');
      if (isHybrid) return `하이브리드 ${seats}인승`;
      if (isGasoline) return `가솔린 ${seats} 인승`;
      return `디젤 ${seats} 인승`; // 엔카 공식: "디젤 9 인승", "디젤 11 인승", "디젤 7 인승"
    }

    if (normCar.includes('그랜저')) {
      if (normBadge.includes('하이브리드')) return '하이브리드';
      if (normBadge.includes('2.4') || normBadge.includes('240')) return '가솔린 2400cc';
      if (normBadge.includes('2.5')) return '가솔린 2500cc';
      if (normBadge.includes('3.0') || normBadge.includes('300')) return normBadge.includes('lpi') ? 'LPG 3000cc' : '가솔린 3000cc';
      if (normBadge.includes('3.3') || normBadge.includes('330')) return '가솔린 3300cc';
    }

    if (normCar.includes('쏘나타')) {
      if (normBadge.includes('하이브리드')) return '하이브리드';
      if (normBadge.includes('1.6') || normBadge.includes('터보')) return '가솔린 1600cc';
      if (normBadge.includes('2.0')) return normBadge.includes('lpi') ? 'LPG 2000cc' : '가솔린 2000cc';
    }

    if (normCar.includes('아반떼')) {
      if (normBadge.includes('하이브리드')) return '하이브리드';
      if (normBadge.includes('1.6')) return '가솔린 1600cc';
      if (normBadge.includes('2.0') || normBadge.includes(' n')) return '가솔린 2000cc';
    }

    if (normCar.includes('k5')) {
      if (normBadge.includes('하이브리드')) return '하이브리드';
      if (normBadge.includes('1.6')) return '가솔린 1600cc';
      if (normBadge.includes('2.0')) return '가솔린 2000cc';
    }

    if (normCar.includes('쏘렌토') || normCar.includes('싼타페')) {
      if (normBadge.includes('하이브리드')) return '하이브리드';
      if (normBadge.includes('2.0')) return '디젤 2000cc';
      if (normBadge.includes('2.2')) return '디젤 2200cc';
      if (normBadge.includes('2.5')) return '가솔린 2500cc';
    }

    if (normCar.includes('레이') || normCar.includes('캐스퍼') || normCar.includes('모닝') || normCar.includes('스파크')) {
      return '가솔린 1000cc';
    }

    return '';
  };

  // 4. 엔카 실시간 동급 매물 및 시세 검색 API (URL 파싱 + 모델/연식/주행거리 자동 쿼리 빌더)
  app.all('/api/encar/search', async (req, res) => {
    const rawUrl = (req.body?.url || req.query.url) as string || '';
    const carName = (req.body?.carName || req.body?.keyword || req.query.keyword || req.body?.model || req.query.model) as string || '';
    const manufacturer = (req.body?.manufacturer || req.query.manufacturer) as string || '';
    const yearVal = Number(req.body?.year || req.query.year) || 0;
    const mileageVal = Number(req.body?.mileage || req.query.mileage) || 0;

    const detailModel = (req.body?.detailModel || req.query.detailModel) as string || '';
    const gradeName = (req.body?.gradeName || req.query.gradeName) as string || '';
    const gradeDetailName = (req.body?.gradeDetailName || req.query.gradeDetailName) as string || '';

    const carNumber = (req.body?.carNumber || req.query.carNumber) as string || '';

    // [3단계 연동] 로컬 파이썬 실시간 엔카 크롤러 & SoldOutTracker 스냅샷 자동 누적 연동 (엔드포인트 미구현 시 즉시 Express로 전환)
    try {
      const pyRes = await fetch('http://127.0.0.1:8000/api/encar/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: rawUrl,
          carName,
          detailModel,
          gradeName,
          gradeDetailName,
          manufacturer,
          year: yearVal,
          mileage: mileageVal,
          carNumber
        }),
        signal: AbortSignal.timeout(30000)
      });
      if (pyRes.ok) {
        const pyData = await pyRes.json();
        if (pyData?.success && Array.isArray(pyData?.items) && pyData.items.length > 0) {
          logEvent('ENCAR_OUT', `[Python Engine] 실시간 매물 ${pyData.items.length}건 수집 & 스냅샷 저장 완료`);
          return res.json(pyData);
        }
      }
    } catch (_) {}


    try {
      let condition = '';
      let conditionModelOnly = '';
      let directSearchUrl = '';

      if (rawUrl) {
        let str = String(rawUrl).trim();
        for (let i = 0; i < 3; i++) {
          if (str.includes('%7B') || str.includes('%22') || str.includes('%28') || str.includes('%20')) {
            try { str = decodeURIComponent(str); } catch (e) { break; }
          }
        }
        str = str.replace(/\+/g, ' ');
        
        const jsonMatch = str.match(/#!(\{.*\})/) || str.match(/(\{.*\})/);
        if (jsonMatch) {
          try {
            const parsed = JSON.parse(jsonMatch[1]);
            condition = parsed.action || '';
          } catch (e) {}
        }
        if (!condition) {
          const actionMatch = str.match(/"action"\s*:\s*"([^"]+)"/);
          if (actionMatch) {
            condition = actionMatch[1];
          } else if (str.includes('q=')) {
            condition = str.split('q=')[1]?.split('&')[0] || '';
          }
        }
        directSearchUrl = rawUrl;
      }

      // URL에서 직접 condition을 못 뽑은 경우, 차량명/연식/주행거리 기반으로 엔카 규격 쿼리 자동 생성
      if (!condition && (carName || manufacturer)) {
        let brand = manufacturer || '현대';
        let modelGroup = carName;
        let subModel = '';

        const nameLower = carName.toLowerCase().replace(/\s+/g, '');
        if (nameLower.includes('모닝')) {
          brand = '기아';
          modelGroup = '모닝';
          if (nameLower.includes('올뉴모닝') || nameLower.includes('ja') || yearVal >= 17) {
            subModel = '올 뉴 모닝 (JA)';
          }
        } else if (nameLower.includes('아반떼')) {
          brand = '현대';
          modelGroup = '아반떼';
          if (nameLower.includes('ad') || nameLower.includes('더뉴아반떼ad')) {
            subModel = '더 뉴 아반떼 AD';
          } else if (nameLower.includes('cn7') || yearVal >= 20) {
            subModel = '아반떼 (CN7)';
          }
        } else if (nameLower.includes('카니발')) {
          brand = '기아';
          modelGroup = '카니발';
          if (nameLower.includes('더뉴카니발') || yearVal >= 18 && yearVal < 21) {
            subModel = '더 뉴 카니발';
          } else if (nameLower.includes('올뉴카니발') || (yearVal >= 14 && yearVal <= 18)) {
            subModel = '올 뉴 카니발';
          } else if (yearVal >= 21) {
            subModel = '카니발 4세대';
          }
        } else if (nameLower.includes('레이')) {
          brand = '기아';
          modelGroup = '레이';
          if (yearVal >= 18) {
            subModel = '더 뉴 레이';
          } else {
            subModel = '레이';
          }
        } else if (nameLower.includes('그랜저')) {
          brand = '현대';
          modelGroup = '그랜저';
          if (nameLower.includes('ig') || (yearVal >= 19 && yearVal <= 22)) {
            subModel = '더 뉴 그랜저 IG';
          } else if (yearVal >= 23 || nameLower.includes('gn7')) {
            subModel = '그랜저 (GN7)';
          }
        } else if (nameLower.includes('쏘나타')) {
          brand = '현대';
          modelGroup = '쏘나타';
          if (nameLower.includes('dn8') || yearVal >= 19) {
            subModel = '쏘나타 (DN8)';
          }
        } else if (nameLower.includes('k5')) {
          brand = '기아';
          modelGroup = 'K5';
          if (yearVal >= 20 || nameLower.includes('3세대') || nameLower.includes('dl3')) {
            subModel = 'K5 3세대';
          }
        } else if (nameLower.includes('k7')) {
          brand = '기아';
          modelGroup = 'K7';
          if (yearVal >= 20 || nameLower.includes('프리미어')) {
            subModel = 'K7 프리미어';
          } else {
            subModel = '올 뉴 K7';
          }
        } else if (nameLower.includes('엑센트')) {
          brand = '현대';
          modelGroup = '엑센트';
          subModel = '엑센트(신형)';
        } else if (nameLower.includes('캐스퍼')) {
          brand = '현대';
          modelGroup = '캐스퍼';
          subModel = '캐스퍼';
        } else if (nameLower.includes('qm6')) {
          brand = '르노코리아(삼성_)';
          modelGroup = 'QM6';
          subModel = '더 뉴 QM6';
        } else if (nameLower.includes('스파크')) {
          brand = '쉐보레(GM대우_)';
          modelGroup = '스파크';
          if (nameLower.includes('더뉴스파크') || (yearVal >= 18 && yearVal <= 24)) {
            subModel = '더 뉴 스파크';
          } else if (nameLower.includes('더넥스트스파크') || (yearVal >= 15 && yearVal < 18)) {
            subModel = '더 넥스트 스파크';
          } else {
            subModel = '스파크';
          }
        }

        if (brand === '쉐보레' || brand === '쉐보레(대우)' || brand === '쉐보레(GM대우)') {
          brand = '쉐보레(GM대우_)';
        } else if (brand === '르노코리아' || brand === '르노' || brand === '르노코리아(삼성)') {
          brand = '르노코리아(삼성_)';
        } else if (brand === '쌍용' || brand === 'KG모빌리티' || brand === 'KGM') {
          brand = 'KG모빌리티(쌍용_)';
        }

        // 1. 기준 등급(targetBadge) 및 인승 결합 추출 (원칙 1: 조회 차량 등급과 정확히 일치)
        let targetBadge = String(req.body?.detailModel || req.query.detailModel || '').trim();
        const seatingMatch = (carName + ' ' + (req.body?.model || '')).match(/(\d+인승)/);
        if (seatingMatch && targetBadge && !targetBadge.includes(seatingMatch[1])) {
          targetBadge = `${seatingMatch[1]} ${targetBadge}`.trim();
        }

        // 2. detailModel에서 BadgeGroup 자동 매핑 (예: "9인승 프레스티지" -> "디젤 9 인승")
        const targetBadgeGroup = resolveBadgeGroup(carName, subModel, targetBadge);

        // 엔카 계층 트리 구성 (모델 전용 vs BadgeGroup/배지 포함 스트림릿 정답 규격)
        let coreTreeModelOnly = '';
        let coreTreeWithBadge = '';
        if (subModel) {
          coreTreeModelOnly = `(C.CarType.Y._.(C.Manufacturer.${brand}._.(C.ModelGroup.${modelGroup}._.Model.${subModel}.)))`;
          if (targetBadge && targetBadgeGroup) {
            coreTreeWithBadge = `(C.CarType.Y._.(C.Manufacturer.${brand}._.(C.ModelGroup.${modelGroup}._.(C.Model.${subModel}._.(C.BadgeGroup.${targetBadgeGroup}._.Badge.${targetBadge}.)))))`;
          } else if (targetBadge) {
            coreTreeWithBadge = `(C.CarType.Y._.(C.Manufacturer.${brand}._.(C.ModelGroup.${modelGroup}._.(C.Model.${subModel}._.Badge.${targetBadge}.))))`;
          }
        } else {
          coreTreeModelOnly = `(C.CarType.Y._.(C.Manufacturer.${brand}._.ModelGroup.${modelGroup}.))`;
        }

        const specRanges: string[] = [];
        // 연식 범위 필터 (기준 연식 ± 1년)
        if (yearVal > 0) {
          const fullYear = yearVal < 100 ? (2000 + yearVal) : yearVal;
          const startYr = fullYear - 1;
          const endYr = fullYear + 1;
          specRanges.push(`Year.range(${startYr}01..${endYr}12)`);
        }

        // 주행거리 범위 필터: 제이 님 지침 기준 ± 30,000km 정밀 수집
        if (mileageVal > 0) {
          const minMil = Math.max(0, Math.floor((mileageVal - 30000) / 10000) * 10000);
          const maxMil = Math.ceil((mileageVal + 30000) / 10000) * 10000;
          specRanges.push(`Mileage.range(${minMil}..${maxMil})`);
        }

        const specPart = specRanges.length > 0 ? `_.${specRanges.join('._.')}.` : '';
        conditionModelOnly = `(And.Hidden.N._.${coreTreeModelOnly}${specPart})`;
        const conditionWithBadge = coreTreeWithBadge ? `(And.Hidden.N._.${coreTreeWithBadge}${specPart})` : '';

        // 기본 condition은 BadgeGroup/targetBadge 쿼리 우선 설정
        condition = conditionWithBadge || conditionModelOnly;

        const payload = {
          action: condition,
          toggle: {},
          layer: '',
          sort: 'ModifiedDate',
          page: 1,
          limit: 100
        };
        directSearchUrl = `https://www.encar.com/dc/dc_carsearchlist.do?carType=kor&searchType=model#!${JSON.stringify(payload)}`;
      }

      if (!condition) {
        return res.json({
          success: false,
          message: '엔카 실시간 매물을 불러오지 못했습니다.',
          count: 0,
          totalModelCount: 0,
          filteredCount: 0,
          items: [],
          stats: { count: 0, min: 0, max: 0, avg: 0 }
        });
      }

      // [원칙 2: 엔카 API 레벨에서 등급 필터가 가능하면 API에서 적용, 불가능하면 로컬 필터링에서 엄격하게 제외]
      let allRawCars: any[] = [];
      let totalModelCount = 0;
      let totalCount = 0;
      let usedBadgeApi = false;
      const pageSize = 100;

      // 1단계: targetBadge / BadgeGroup이 존재하면 엔카 API 쿼리에 직접 적용 시도
      let activeQueryCondition = condition;
      if (condition.includes('Badge.') && condition.includes('Model.')) {
        try {
          let badgeRes = await fetch(`https://api.encar.com/search/car/list/general?count=true&q=${encodeURIComponent(condition)}&sr=%7CModifiedDate%7C0%7C100`, {
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
              'Referer': 'http://www.encar.com/',
              'Accept': 'application/json, text/plain, */*'
            }
          });
          if (badgeRes.status === 429) {
            await new Promise(r => setTimeout(r, 1500));
            badgeRes = await fetch(`https://api.encar.com/search/car/list/general?count=true&q=${encodeURIComponent(condition)}&sr=%7CModifiedDate%7C0%7C100`, {
              headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'http://www.encar.com/',
                'Accept': 'application/json, text/plain, */*'
              }
            });
          }
          if (badgeRes.ok) {
            const badgeData = await badgeRes.json();
            if (badgeData?.Count && badgeData.Count > 0) {
              usedBadgeApi = true;
              totalCount = badgeData.Count;
              allRawCars = badgeData.SearchResults || [];
              totalModelCount = totalCount;
              logEvent('ENCAR_OUT', `[Encar API] Badge/BadgeGroup 필터 적용 성공: ${totalCount}대 발견 (Condition: ${condition.slice(0, 100)}...)`);
            }
          }
        } catch (e: any) {
          logEvent('ENCAR_WARN', `Badge API search failed, falling back to model-only search: ${e.message}`);
        }

        // 만약 BadgeGroup 포함 조건으로 0건인 경우, Badge 단독 조건으로 1회 안전 재시도
        if (!usedBadgeApi && condition.includes('BadgeGroup.')) {
          const fallbackBadgeCond = condition.replace(/\(C\.BadgeGroup\.[^._]+\._\./g, '').replace(/\.\)\)\)/g, '.))');
          try {
            const fbRes = await fetch(`https://api.encar.com/search/car/list/general?count=true&q=${encodeURIComponent(fallbackBadgeCond)}&sr=%7CModifiedDate%7C0%7C100`, {
              headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Referer': 'http://www.encar.com/',
                'Accept': 'application/json'
              }
            });
            if (fbRes.ok) {
              const fbData = await fbRes.json();
              if (fbData?.Count && fbData.Count > 0) {
                usedBadgeApi = true;
                totalCount = fbData.Count;
                allRawCars = fbData.SearchResults || [];
                totalModelCount = totalCount;
                condition = fallbackBadgeCond;
                activeQueryCondition = fallbackBadgeCond;
                logEvent('ENCAR_OUT', `[Encar API] Badge 단독 필터 적용 성공: ${totalCount}대 발견`);
              }
            }
          } catch (_) {}
        }
      }

      // 2단계: Badge API가 사용되지 않았거나 0건인 경우, 모델 전체 쿼리로 조회 (로컬 엄격 제외 준비)
      if (!usedBadgeApi) {
        // Badge 절이 포함되어 있으면 제거하여 모델 전체 조건식으로 복원
        let safeCondition = condition.replace(/\._\.Badge\.[^)]+\./g, '').replace(/Badge\.[^)]+\./g, '');
        activeQueryCondition = safeCondition;

        const apiEncarUrl = `https://api.encar.com/search/car/list/general?count=true&q=${encodeURIComponent(safeCondition)}&sr=%7CModifiedDate%7C0%7C100`;
        logEvent('ENCAR_OUT', `Searching Encar (Model All): ${safeCondition.slice(0, 80)}...`);

        try {
          const firstRes = await fetch(apiEncarUrl, {
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
              'Referer': 'http://www.encar.com/',
              'Accept': 'application/json'
            }
          });
          if (firstRes.ok) {
            const firstData = await firstRes.json();
            totalCount = firstData?.Count || 0;
            totalModelCount = totalCount;
            allRawCars = firstData?.SearchResults || [];
          }
        } catch (e) {}

        // 만약 1차 요청 결과가 없거나 실패한 경우 차종 기본 쿼리로 안전 재시도
        if (!allRawCars || allRawCars.length === 0) {
          let fallbackCond = '';
          if (carName.toLowerCase().includes('k7')) {
            fallbackCond = '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.기아._.ModelGroup.K7.)))';
          } else if (carName.includes('모닝')) {
            fallbackCond = '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.기아._.ModelGroup.모닝.)))';
          } else if (carName.includes('아반떼')) {
            fallbackCond = '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.현대._.ModelGroup.아반떼.)))';
          } else if (carName.includes('카니발')) {
            fallbackCond = '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.기아._.ModelGroup.카니발.)))';
          } else if (carName.includes('레이')) {
            fallbackCond = '(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.기아._.ModelGroup.레이.)))';
          }

          if (fallbackCond) {
            try {
              const fallbackRes = await fetch(`https://api.encar.com/search/car/list/general?count=true&q=${encodeURIComponent(fallbackCond)}&sr=%7CModifiedDate%7C0%7C100`, {
                headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.encar.com/', 'Accept': 'application/json' }
              });
              if (fallbackRes.ok) {
                const fbData = await fallbackRes.json();
                totalCount = fbData?.Count || 0;
                totalModelCount = totalCount;
                allRawCars = fbData?.SearchResults || [];
              }
            } catch (e) {}
          }
        }
      }

      // 매물 수가 100대를 초과할 경우 잔여 페이지 전수 병렬 수집 (최대 1,000대 안전 보호)
      // 매물 수가 100대를 초과할 경우 잔여 페이지 전수 수집 (최대 1,000대 안전 보호)
      if (totalCount > pageSize && totalCount <= 1000) {
        const remainingPages = Math.min(Math.ceil(totalCount / pageSize), 10);
        for (let p = 1; p < remainingPages; p++) {
          const offset = p * pageSize;
          try {
            let pRes = await fetch(`https://api.encar.com/search/car/list/general?count=false&q=${encodeURIComponent(activeQueryCondition)}&sr=%7CModifiedDate%7C${offset}%7C${pageSize}`, {
              headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'http://www.encar.com/',
                'Accept': 'application/json, text/plain, */*'
              }
            });
            if (pRes.status === 429) {
              await new Promise(r => setTimeout(r, 1200));
              pRes = await fetch(`https://api.encar.com/search/car/list/general?count=false&q=${encodeURIComponent(activeQueryCondition)}&sr=%7CModifiedDate%7C${offset}%7C${pageSize}`, {
                headers: {
                  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                  'Referer': 'http://www.encar.com/',
                  'Accept': 'application/json, text/plain, */*'
                }
              });
            }
            if (pRes.ok) {
              const pd = await pRes.json();
              if (pd.SearchResults && Array.isArray(pd.SearchResults)) {
                allRawCars = allRawCars.concat(pd.SearchResults);
              }
            }
          } catch (_) {}
        }
      }

      // 1. 유효 매물 1차 정제 및 ID 기준 중복 제거 (렌트/리스 제외)
      const seenIds = new Set<string>();
      let rawCars = allRawCars.filter((c: any) => {
        const id = String(c.Id || '');
        if (!id || seenIds.has(id)) return false;
        const sellType = String(c.SellType || '');
        if (sellType.includes('렌트') || sellType.includes('리스') || c.LeaseType) return false;
        seenIds.add(id);
        return true;
      });

      // [원칙 1: 조회 차량의 등급(배지)과 정확히 일치하는 매물만 포함, 하이리무진/타인승/타트림 무조건 제외]
      let targetDetail = String(req.body?.detailModel || req.query.detailModel || '').trim();
      if (gradeName) {
        if (gradeDetailName && !gradeName.includes(gradeDetailName)) {
          targetDetail = `${gradeName} ${gradeDetailName}`.trim();
        } else {
          targetDetail = gradeName;
        }
      }
      const targetSeatingMatch = (carName + ' ' + (req.body?.model || '')).match(/(\d+인승)/);
      let strictTargetBadge = targetDetail;
      if (targetSeatingMatch && strictTargetBadge && !strictTargetBadge.includes(targetSeatingMatch[1])) {
        strictTargetBadge = `${targetSeatingMatch[1]} ${strictTargetBadge}`.trim();
      }

      const isStrictMatch = (c: any, target: string): boolean => {
        if (!target) return true;
        const normTarget = target.replace(/\s+/g, '').toLowerCase();
        const b = String(c.Badge || '').trim();
        const bd = String(c.BadgeDetail || '').trim();
        const fullBadge = `${b} ${bd}`.trim();
        const normBadge = b.replace(/\s+/g, '').toLowerCase();
        const normFull = fullBadge.replace(/\s+/g, '').toLowerCase();

        // 1. 하이리무진 검사: 조회 차량이 하이리무진이 아닌데 매물에 하이리무진/리무진이 있으면 무조건 제외!
        const targetIsLimousine = normTarget.includes('하이리무진') || normTarget.includes('리무진');
        const carIsLimousine = normBadge.includes('하이리무진') || normBadge.includes('리무진') || normFull.includes('하이리무진') || normFull.includes('리무진');
        if (!targetIsLimousine && carIsLimousine) return false;
        if (targetIsLimousine && !carIsLimousine) return false;

        // 2. 인승 검사: 인승이 다르면 무조건 제외 (예: 9인승 != 11인승, 7인승)
        const seatMatch = normTarget.match(/(\d+)인승/);
        if (seatMatch) {
          const seats = seatMatch[1];
          const carSeatMatch = normFull.match(/(\d+)인승/);
          if (carSeatMatch && carSeatMatch[1] !== seats) return false;
          if (!normFull.includes(`${seats}인승`)) return false;
        }

        // 3. 주요 트림 검사: 트림이 다르면 무조건 제외
        const knownTrims = ['프레스티지', '노블레스', '럭셔리', '디럭스', '스마트', '모던', '프리미엄', '익스클루시브', '캘리그래피', '인스퍼레이션', '시그니처', '트렌디'];
        for (const t of knownTrims) {
          const targetHasTrim = normTarget.includes(t);
          const carHasTrim = normFull.includes(t);
          if (targetHasTrim && !carHasTrim) return false;
          if (!targetHasTrim && carHasTrim) {
            const targetOtherTrim = knownTrims.find(ot => normTarget.includes(ot));
            if (targetOtherTrim && targetOtherTrim !== t) return false;
          }
        }

        // 4. 완전 일치 (Exact Match)
        if (normBadge === normTarget || normFull === normTarget) return true;

        // 5. 인승 + 트림 조합 일치 (예: target "9인승 프레스티지" -> badge "9인승 프레스티지")
        if (seatMatch) {
          const seatStr = `${seatMatch[1]}인승`;
          const remainingTrim = normTarget.replace(seatStr, '');
          if (normBadge.includes(seatStr) && normBadge.includes(remainingTrim)) {
            return true;
          }
        }

        return false;
      };

      let validCars = rawCars;
      let excludedByBadge = 0;

      if (strictTargetBadge) {
        validCars = rawCars.filter((c: any) => isStrictMatch(c, strictTargetBadge));
        if (usedBadgeApi) {
          // BadgeGroup/Badge API로 이미 타겟 등급만 정밀 수집되었으므로 불필요한 제외 문구 제거
          excludedByBadge = 0;
          totalModelCount = rawCars.length;
        } else {
          // 로컬 필터링으로 걸러진 대수 (모델 전체에서 로컬로 제외했을 때만 노출)
          excludedByBadge = rawCars.length - validCars.length;
        }
      } else {
        totalModelCount = rawCars.length;
      }

      // [원칙 1-1: 주행거리 2차 엄격 필터 - 기준 주행거리 ±30,000km 범위를 벗어나는 매물 원천 차단]
      if (mileageVal > 0) {
        const allowedMinMil = Math.max(0, mileageVal - 30000);
        const allowedMaxMil = mileageVal + 30000;
        validCars = validCars.filter((c: any) => {
          const mil = Number(c.Mileage) || 0;
          if (mil <= 0) return true; // 주행거리 미상 매물은 보존
          return mil >= allowedMinMil && mil <= allowedMaxMil;
        });
      }

      // [원칙 2: 스트림릿 8501 정답 기준과 100% 동일한 중복 제거 및 가격 이상치 정제 파이프라인]
      // 2-1. 실물 매물 중복 제거 (스트림릿 Scraper.dedupe_after_scan 기준: 차량명 + 연식 + 주행거리 + 판매가)
      const seenSpecs = new Set<string>();
      const dedupedCars: any[] = [];
      const carsWithPrice = validCars.filter((c: any) => c.Price && Number(c.Price) > 0);

      // 정보 풍부도 높은 매물 우선 보존 (스트림릿 data_score 반영)
      const sortedByDataRichness = [...carsWithPrice].sort((a: any, b: any) => {
        const scoreA = (a.Photos?.length || 0) + (a.BadgeDetail ? 1 : 0);
        const scoreB = (b.Photos?.length || 0) + (b.BadgeDetail ? 1 : 0);
        return scoreB - scoreA;
      });

      for (const c of sortedByDataRichness) {
        const modelStr = String(c.Model || '').trim();
        const rawYear = String(c.Year || '');
        const rawFormYear = String(c.FormYear || c.Year || '');
        const yearStr = rawYear.length >= 4 
          ? `${rawYear.slice(2, 4)}(${rawFormYear.length === 4 ? rawFormYear.slice(2) : rawFormYear})` 
          : `${rawYear}(${rawFormYear})`;
        const mileageNum = Number(c.Mileage) || 0;
        const priceNum = Number(c.Price) || 0;

        const specKey = `${modelStr}_${yearStr}_${mileageNum}_${priceNum}`;
        if (seenSpecs.has(specKey)) continue;
        seenSpecs.add(specKey);
        dedupedCars.push(c);
      }

      const duplicateRemovedCount = carsWithPrice.length - dedupedCars.length;

      // 2-2. 가격 이상치(Outlier) 제거 (스트림릿 DataProcessor.standardize 기준: 상하위 1% quantile 절사)
      // 극단적 저가(허위/미끼/전손) 및 극단적 고가(딜러 호가 거품) 배제
      let targetPool = dedupedCars;
      let outlierRemovedCount = 0;

      const quantile = (arr: number[], q: number): number => {
        const sorted = [...arr].sort((a, b) => a - b);
        const pos = (sorted.length - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        if (sorted[base + 1] !== undefined) {
          return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
        }
        return sorted[base];
      };

      const pricesArr = dedupedCars.map((c: any) => Number(c.Price) || 0).filter(p => p > 0);
      if (pricesArr.length > 10) {
        const lowBound = quantile(pricesArr, 0.01);
        const highBound = quantile(pricesArr, 0.99);
        const beforeOutlierCount = targetPool.length;
        targetPool = dedupedCars.filter((c: any) => {
          const p = Number(c.Price) || 0;
          return p >= lowBound && p <= highBound;
        });
        outlierRemovedCount = beforeOutlierCount - targetPool.length;
      }

      // [원칙 3: 제외된 매물 수와 사유 통계 객체 생성]
      const filterStats = {
        targetBadge: strictTargetBadge || '전체',
        totalModelCount: totalModelCount || rawCars.length,
        excludedByBadge: excludedByBadge,
        excludedByDuplicate: duplicateRemovedCount,
        excludedByOutlier: outlierRemovedCount,
        validCount: targetPool.length,
        filterMethod: usedBadgeApi ? 'API' : 'LOCAL',
        reason: [
          excludedByBadge > 0 ? `등급 불일치 ${excludedByBadge}대 제외` : '',
          duplicateRemovedCount > 0 ? `중복 실물 매물 ${duplicateRemovedCount}대 제외` : '',
          outlierRemovedCount > 0 ? `상하위 1% 가격 이상치 ${outlierRemovedCount}대 제외` : ''
        ].filter(Boolean).join(', ') || '전체 매물이 기준과 일치함'
      };

      const filteredComparableCount = targetPool.length;
      const topCars = targetPool.slice(0, 30);

      // 상위 30대 매물 실시간 성능점검, 제원 및 옵션 카탈로그 병렬 수집 (8501과 100% 동일)
      const detailPromises = topCars.map(async (c: any) => {
        const cid = String(c.Id || '');
        let inspData: any = null;
        let vehData: any = null;
        let choiceCatalog: any[] = [];
        let diagData: any = null;

        try {
          const [iRes, vRes] = await Promise.allSettled([
            fetch(`https://api.encar.com/v1/readside/inspection/vehicle/${cid}`, {
              headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': `https://fem.encar.com/cars/detail/${cid}` }
            }).then(r => r.ok ? r.json() : null),
            fetch(`https://api.encar.com/v1/readside/vehicle/${cid}`, {
              headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': `https://fem.encar.com/cars/detail/${cid}` }
            }).then(r => r.ok ? r.json() : null)
          ]);
          if (iRes.status === 'fulfilled') inspData = iRes.value;
          if (vRes.status === 'fulfilled') vehData = vRes.value;

          // 옵션 카탈로그 조회
          const choiceCodes = vehData?.options?.choice || [];
          if (Array.isArray(choiceCodes) && choiceCodes.length > 0) {
            try {
              const cRes = await fetch(`https://api.encar.com/v1/readside/vehicles/car/${cid}/options/choice`, {
                headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': `https://fem.encar.com/cars/detail/${cid}` }
              });
              if (cRes.ok) {
                choiceCatalog = await cRes.json();
              }
            } catch (_) {}
          }

          // 진단 데이터 조회 (inspection 미발견 부위 보강용)
          try {
            const dRes = await fetch(`https://api.encar.com/v1/readside/diagnosis/vehicle/${cid}`, {
              headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': `https://fem.encar.com/cars/detail/${cid}` }
            });
            if (dRes.ok) {
              diagData = await dRes.json();
            }
          } catch (_) {}
        } catch (_) {}

        return { id: cid, inspData, vehData, choiceCatalog, diagData };
      });

      const detailResults = await Promise.all(detailPromises);
      const detailMap = new Map(detailResults.map(d => [d.id, d]));

      const mapCar = (c: any) => {
        const id = String(c.Id || '');
        const rawYear = String(c.Year || '');
        const rawFormYear = String(c.FormYear || c.Year || '');
        const yearStr = rawYear.length >= 4 ? `${rawYear.slice(2, 4)}(${rawFormYear.slice(2, 4)})` : rawYear;
        const mileageNum = Number(c.Mileage) || 0;
        const priceNum = Number(c.Price) || 0;
        
        const details = detailMap.get(id);
        const insp = details?.inspData;
        const veh = details?.vehData;
        const choiceCatalog = details?.choiceCatalog || [];
        const diag = details?.diagData;

        // 1. 등록일 및 재고일수
        const registDateStr = veh?.manage?.registDateTime || c.ModifiedDate;
        let registrationDate = '-';
        let registDateObj: Date | null = null;
        if (registDateStr) {
          registDateObj = new Date(registDateStr);
          if (!isNaN(registDateObj.getTime())) {
            const y = registDateObj.getFullYear();
            const m = String(registDateObj.getMonth() + 1).padStart(2, '0');
            const d = String(registDateObj.getDate()).padStart(2, '0');
            registrationDate = `${String(y).slice(2, 4)}-${m}-${d}`;
          }
        }
        const holdingDays = registDateObj && !isNaN(registDateObj.getTime())
          ? Math.max(1, Math.floor((Date.now() - registDateObj.getTime()) / 86400000))
          : 15;

        // 2. 성능점검일자 (순수 issueDate 기준, 등록일 임의 대체 금지)
        let inspectionDate = '-';
        const issueRaw = insp?.master?.detail?.issueDate;
        if (issueRaw) {
          const clean = String(issueRaw).replace(/[^\d]/g, '');
          if (clean.length >= 8) {
            inspectionDate = `${clean.slice(2, 4)}-${clean.slice(4, 6)}-${clean.slice(6, 8)}`;
          }
        }
        const checkDate = inspectionDate !== '-' ? inspectionDate : registrationDate;

        // 3. 교환/판금 부위 및 사고유무 판별 (8501 PART_COORDS와 100% 동일하게 매핑)
        const damageData: Record<string, string> = {};
        const replaces: string[] = [];
        const repairs: string[] = [];
        const allParts = [
          ...(insp?.outers || []), 
          ...(insp?.inners || []),
          ...(insp?.master?.outers || []),
          ...(insp?.master?.inners || []),
          ...(diag?.outers || []),
          ...(diag?.inners || [])
        ];

        if (Array.isArray(allParts) && allParts.length > 0) {
          allParts.forEach((o: any) => {
            const title = String(o.type?.title || o.name || '');
            const statuses = o.statusTypes || [];
            const isReplace = statuses.some((s: any) => s.code === 'X' || String(s.title).includes('교환')) ||
              ['REPLACEMENT', 'EXCHANGE', 'X'].includes(String(o.resultCode || '').toUpperCase()) ||
              String(o.result || '').includes('교환');
            const isRepair = statuses.some((s: any) => ['W', 'C', 'A', 'U', 'T'].includes(s.code) || String(s.title).includes('판금') || String(s.title).includes('용접')) ||
              ['SHEET_METAL', 'WELD', 'W', 'C', 'A', 'U', 'T'].includes(String(o.resultCode || '').toUpperCase()) ||
              ['판금', '용접', '도색', '수리'].some(k => String(o.result || '').includes(k));
            
            // 8501 normalize_part_name과 동일하게 치환
            let normTitle = title.replace(/\s+/g, '')
              .replace(/프론트/g, '앞')
              .replace(/리어/g, '뒤')
              .replace(/도어/g, '문')
              .replace(/펜더/g, '휀더')
              .replace(/보닛/g, '후드');

            if (normTitle) {
              if (isReplace) {
                damageData[normTitle] = '교환';
                if (!replaces.includes(normTitle)) replaces.push(normTitle);
              } else if (isRepair) {
                if (damageData[normTitle] !== '교환') {
                  damageData[normTitle] = '판금';
                  if (!repairs.includes(normTitle)) repairs.push(normTitle);
                }
              }
            }
          });
        }

        // diagnosis items 항목 보강
        if (diag?.items && Array.isArray(diag.items)) {
          diag.items.forEach((it: any) => {
            const rawN = String(it.name || '');
            if (['CHECKER_COMMENT', 'OUTER_PANEL_COMMENT'].includes(rawN)) return;
            const rc = String(it.resultCode || '').toUpperCase();
            const rt = String(it.result || '');
            let normN = rawN.replace(/\s+/g, '')
              .replace(/FRONT_DOOR_LEFT/g, '앞문(좌)')
              .replace(/FRONT_DOOR_RIGHT/g, '앞문(우)')
              .replace(/REAR_DOOR_LEFT|BACK_DOOR_LEFT/g, '뒤문(좌)')
              .replace(/REAR_DOOR_RIGHT|BACK_DOOR_RIGHT/g, '뒤문(우)')
              .replace(/FRONT_FENDER_LEFT/g, '앞휀더(좌)')
              .replace(/FRONT_FENDER_RIGHT/g, '앞휀더(우)')
              .replace(/QUARTER_LEFT|BACK_FENDER_LEFT/g, '쿼터(좌)')
              .replace(/QUARTER_RIGHT|BACK_FENDER_RIGHT/g, '쿼터(우)')
              .replace(/HOOD|BONNET/g, '후드')
              .replace(/TRUNK_LID|TRUNK/g, '트렁크리드')
              .replace(/ROOF/g, '루프');

            if (rc === 'REPLACEMENT' || rc === 'EXCHANGE' || rc === 'X' || rt.includes('교환')) {
              damageData[normN] = '교환';
              if (!replaces.includes(normN)) replaces.push(normN);
            } else if (['SHEET_METAL', 'WELD', 'W', 'C', 'A', 'U', 'T'].includes(rc) || ['판금', '용접', '도색', '수리'].some(k => rt.includes(k))) {
              if (damageData[normN] !== '교환') {
                damageData[normN] = '판금';
                if (!repairs.includes(normN)) repairs.push(normN);
              }
            }
          });
        }

        let accidentStr = '-';
        if (insp?.master) {
          if (replaces.length > 0 && repairs.length > 0) {
            accidentStr = `▲ 단순(교환/판금) [교환:${replaces.length} / 판금:${repairs.length}]`;
          } else if (replaces.length > 0) {
            accidentStr = replaces.length > 3 ? `■ 사고 (교환 ${replaces.length})` : `▲ 단순교환 (교환 ${replaces.length})`;
          } else if (repairs.length > 0) {
            accidentStr = `▲ 단순판금 (판금 ${repairs.length})`;
          } else if (insp.master.accdient) {
            accidentStr = '■ 사고';
          } else if (insp.master.simpleRepair) {
            accidentStr = '▲ 단순교환';
          } else if (insp.master.accdient === false && insp.master.simpleRepair === false) {
            accidentStr = '● 완전무사고';
          } else {
            accidentStr = '정보없음';
          }
        } else if (diag) {
          if (replaces.length > 0 && repairs.length > 0) {
            accidentStr = `▲ 단순(교환/판금) [교환:${replaces.length} / 판금:${repairs.length}]`;
          } else if (replaces.length > 0) {
            accidentStr = replaces.length > 3 ? `■ 사고 (교환 ${replaces.length})` : `▲ 단순교환 (교환 ${replaces.length})`;
          } else if (repairs.length > 0) {
            accidentStr = `▲ 단순판금 (판금 ${repairs.length})`;
          }
        }

        // 4. 색상
        const color = veh?.spec?.colorName || c.Color || '흰색';

        // 5. 신차 추가 옵션 (choiceCatalog 매핑하여 실제 옵션명 및 가격 반영 - 8501 동일)
        const choiceCodes = veh?.options?.choice || [];
        let optionsText = '추가 옵션 없음 (기본 출고 사양)';
        if (Array.isArray(choiceCodes) && choiceCodes.length > 0 && Array.isArray(choiceCatalog) && choiceCatalog.length > 0) {
          const appliedList: string[] = [];
          choiceCatalog.forEach((opt: any) => {
            if (choiceCodes.map(String).includes(String(opt.optionCd))) {
              const name = String(opt.optionName || '').replace(/\([^)]*\)|\[[^\]]*\]/g, '').trim();
              const price = Number(opt.price) || 0;
              if (name && !name.includes('외장컬러')) {
                appliedList.push(price > 0 ? `${name} (${price}만)` : name);
              }
            }
          });
          if (appliedList.length > 0) {
            optionsText = appliedList.join(' / ');
          } else {
            optionsText = `+ ${choiceCodes.length}개 추가 선택 옵션`;
          }
        } else if (choiceCodes.length > 0) {
          optionsText = `+ ${choiceCodes.length}개 추가 선택 옵션`;
        } else if (c.BadgeDetail) {
          optionsText = c.BadgeDetail;
        }

        return {
          id: id,
          carName: `${c.Model || ''} ${c.Badge || ''}`.trim(),
          modelName: String(c.Model || '').trim() || String(c.ModelGroup || '').trim(),
          subModel: String(c.Badge || c.BadgeDetail || '').trim(),
          year: yearStr,
          mileage: mileageNum,
          price: priceNum,
          accidentType: accidentStr,
          color: color,
          optionsText: optionsText,
          checkDate: checkDate,
          inspectionDate: inspectionDate,
          registrationDate: registrationDate,
          holdingDays: holdingDays,
          replaces: replaces,
          repairs: repairs,
          damageData: damageData,
          encarUrl: `https://fem.encar.com/cars/detail/${String(id).replace(/\D/g, '')}`,
          photo: c.Photos?.[0]?.location ? `https://ci.encar.com/carpicture${c.Photos[0].location}` : ''
        };
      };

      const mappedCars = targetPool.map(mapCar);

      const prices = mappedCars.map((c: any) => c.price);
      const minPrice = prices.length ? Math.min(...prices) : 0;
      const maxPrice = prices.length ? Math.max(...prices) : 0;
      const avgPrice = prices.length ? Math.round(prices.reduce((a: number, b: number) => a + b, 0) / prices.length) : 0;

      // 8501 밸류에이션 공식과 동일한 연산 (실제 매물이 있을 때만 산출)
      const baseMileage = 56000;
      const targetMileage = Number(mileageVal) || 63500;
      const milDelta = Math.max(-8.0, minPrice > 0 ? ((baseMileage - targetMileage) / 10000.0) * 1.3 : 0);
      const accScoreDelta = -3.0; // 외판 단순교환/수리 2판 기준
      const calcScore = mappedCars.length > 0 ? Math.round((100.0 + milDelta + accScoreDelta) * 10) / 10 : 0;
      const preciseIndividualPrice = mappedCars.length > 0 && avgPrice > 0 ? Math.round(avgPrice * (calcScore / 100)) : 0;
      const preciseMinPrice = minPrice > 0 ? minPrice : 0;
      const preciseMaxPrice = maxPrice > 0 ? maxPrice : 0;
      const bubbleGap = avgPrice > 0 && preciseIndividualPrice > 0 ? avgPrice - preciseIndividualPrice : 0;
      const bubblePct = preciseIndividualPrice > 0 ? Math.round((bubbleGap / preciseIndividualPrice) * 1000) / 10 : 0;

      logEvent('ENCAR_IN', `Found ${mappedCars.length} Encar comparable cars (avg: ${avgPrice}만, preciseValuation: ${preciseIndividualPrice}만)`);

      return res.json({
        success: mappedCars.length > 0,
        message: mappedCars.length === 0 ? '엔카 실시간 매물을 불러오지 못했습니다.' : undefined,
        count: filteredComparableCount || mappedCars.length,
        totalModelCount: totalModelCount,
        filteredCount: filteredComparableCount,
        filterStats: filterStats,
        items: mappedCars,
        directSearchUrl: directSearchUrl || activeQueryCondition,
        stats: {
          count: mappedCars.length,
          totalModelCount: totalModelCount,
          filteredCount: filteredComparableCount,
          excludedByBadge: filterStats.excludedByBadge,
          excludedByDuplicate: filterStats.excludedByDuplicate,
          excludedByOutlier: filterStats.excludedByOutlier,
          targetBadge: filterStats.targetBadge,
          min: minPrice,
          max: maxPrice,
          avg: avgPrice
        },
        valuation: {
          hasData: mappedCars.length > 0,
          individualPrice: preciseIndividualPrice,
          minPrice: preciseMinPrice,
          maxPrice: preciseMaxPrice,
          score: calcScore,
          bubbleGap: bubbleGap,
          bubblePct: bubblePct,
          safeCeiling: 0,
          baseMileage: baseMileage
        }
      });
    } catch (err: any) {
      console.error('엔카 실시간 시세 조회 실패:', err);
      logEvent('ENCAR_ERR', `Encar Search Failed: ${err.message} | Stack: ${err.stack}`);
      return res.status(500).json({
        success: false,
        error: err.message,
        message: '엔카 실시간 매물을 불러오지 못했습니다.',
        items: [],
        stats: { count: 0, min: 0, max: 0, avg: 0 }
      });
    }
  });

  // 5-0. 엔카 판매완료(완판) 소진 속도 및 실거래 시세 분석 API (로컬 Python 백엔드 연동)
  app.all('/api/encar/soldout', async (req, res) => {
    try {
      const carIds = req.body?.carIds || req.query.carIds || [];
      const targetYear = req.body?.targetYear || req.query.targetYear || '';
      const expectedModel = req.body?.expectedModel || req.query.expectedModel || '';

      const pyRes = await fetch('http://127.0.0.1:8000/api/encar/soldout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          carIds: Array.isArray(carIds) ? carIds : [carIds],
          targetYear: String(targetYear),
          expectedModel: String(expectedModel)
        }),
        signal: AbortSignal.timeout(10000)
      });
      if (pyRes.ok) {
        const data = await pyRes.json();
        return res.json(data);
      }
      return res.status(pyRes.status).json({ success: false, message: 'Python API 반환 실패' });
    } catch (err: any) {
      console.warn('엔카 판매완료 API 연동 실패:', err.message);
      return res.json({
        success: true,
        data: {
          has_data: false,
          total_sold_count: 0,
          count_30d: 0,
          daily_rate: 0,
          velocity_badge: '보통 출고',
          velocity_color: '#38bdf8',
          avg_mileage: 0,
          latest_sold_date: '-',
          matched_hits: 0,
          sold_avg_price: 0,
          sold_avg_days: 0,
          enriched_cars: []
        }
      });
    }
  });

  // 5-1. 엔카 특정 매물 성능점검표 상세 조회 API
  app.get('/api/encar/inspection/:carId', async (req, res) => {
    const { carId } = req.params;
    // [1순위] Python FastAPI 실시간 엔카 검증 엔진 호출
    try {
      const pyRes = await fetch(`http://127.0.0.1:8000/api/encar/inspection/${carId}`, {
        signal: AbortSignal.timeout(6000)
      });
      if (pyRes.ok) {
        const pyData = await pyRes.json();
        if (pyData?.success && pyData?.data) {
          return res.json(pyData);
        }
      }
    } catch (e: any) {
      logEvent('INSPECT_WARN', `Python inspection API 실패, Express fallback 전환: ${e.message}`);
    }

    try {
      // 1. 차량 기본 제원 조회 (vehicleId, 실제 색상, 실제 옵션 확보)
      let vehicleId = carId;
      let vehicleData: any = null;
      try {
        const vRes = await fetch(`https://api.encar.com/v1/readside/vehicle/${carId}`, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': `https://fem.encar.com/cars/detail/${carId}`,
            'Accept': 'application/json'
          }
        });
        if (vRes.ok) {
          vehicleData = await vRes.json();
          if (vehicleData?.vehicleId) {
            vehicleId = String(vehicleData.vehicleId);
          }
        }
      } catch (e) {
        console.warn('엔카 차량 제원 조회 예외:', e);
      }

      // 2. 성능점검표 상세 조회 (vehicleId 기준)
      let inspectData: any = null;
      try {
        const inspectRes = await fetch(`https://api.encar.com/v1/readside/inspection/vehicle/${vehicleId}`, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': `https://fem.encar.com/cars/detail/${carId}`,
            'Accept': 'application/json'
          }
        });
        if (inspectRes.ok) {
          inspectData = await inspectRes.json();
        } else if (vehicleId !== carId) {
          const inspectRes2 = await fetch(`https://api.encar.com/v1/readside/inspection/vehicle/${carId}`, {
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
              'Referer': `https://fem.encar.com/cars/detail/${carId}`,
              'Accept': 'application/json'
            }
          });
          if (inspectRes2.ok) {
            inspectData = await inspectRes2.json();
          }
        }
      } catch (e) {
        console.warn('엔카 성능점검 조회 예외:', e);
      }

      if (!inspectData && !vehicleData) {
        return res.json({ success: false, message: '엔카 성능점검 및 제원 데이터 없음' });
      }

      // 실측 색상
      const color = vehicleData?.spec?.colorName || '미확인';

      // 실측 성능점검일자 및 등록일자 분리
      let inspectionDate = '-';
      let registrationDate = '-';
      let accidentType = '미확인';
      const parsedReplaces: string[] = [];
      const parsedRepairs: string[] = [];
      const replaceNames: string[] = [];
      const repairNames: string[] = [];

      if (inspectData?.master) {
        const rawIssueDate = inspectData.master.detail?.issueDate;
        if (rawIssueDate && String(rawIssueDate).length >= 8) {
          const s = String(rawIssueDate).replace(/[^\d]/g, '');
          inspectionDate = `${s.slice(2, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
        }
        const rawRegDate = inspectData.master.registrationDate || vehicleData?.manage?.registDateTime;
        if (rawRegDate) {
          const d = new Date(rawRegDate);
          if (!isNaN(d.getTime())) {
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            registrationDate = `${String(y).slice(2, 4)}-${m}-${day}`;
          }
        }

        const outers = (inspectData.outers || []).concat(inspectData.master.outers || []);
        const inners = (inspectData.inners || []).concat(inspectData.master.inners || []);
        const allInspectionParts = [...outers, ...inners];

        for (const o of allInspectionParts) {
          const title = String(o.type?.title || o.name || '').trim();
          const stList = (o.statusTypes || []).map((s: any) => String(s.code || '').toUpperCase());
          let mappedPart = '';
          if (title.includes('후드') || title.includes('본넷')) mappedPart = 'HOOD';
          else if (title.includes('앞휀더(좌)') || title.includes('프론트 휀더(좌)') || title.includes('프론트휀더(좌)')) mappedPart = 'F_FENDER_L';
          else if (title.includes('앞휀더(우)') || title.includes('프론트 휀더(우)') || title.includes('프론트휀더(우)')) mappedPart = 'F_FENDER_R';
          else if (title.includes('앞도어(좌)') || title.includes('프론트 도어(좌)') || title.includes('프론트도어(좌)')) mappedPart = 'FRONT_DOOR_L';
          else if (title.includes('앞도어(우)') || title.includes('프론트 도어(우)') || title.includes('프론트도어(우)')) mappedPart = 'FRONT_DOOR_R';
          else if (title.includes('뒤도어(좌)') || title.includes('리어 도어(좌)') || title.includes('리어도어(좌)')) mappedPart = 'REAR_DOOR_L';
          else if (title.includes('뒤도어(우)') || title.includes('리어 도어(우)') || title.includes('리어도어(우)')) mappedPart = 'REAR_DOOR_R';
          else if (title.includes('트렁크')) mappedPart = 'TRUNK';
          else if (title.includes('쿼터') && title.includes('우')) mappedPart = 'QUARTER_R';
          else if (title.includes('쿼터') && title.includes('좌')) mappedPart = 'QUARTER_L';
          else if (title.includes('루프')) mappedPart = 'ROOF';
          else if (title.includes('사이드실') && title.includes('좌')) mappedPart = 'SIDE_SILL_L';
          else if (title.includes('사이드실') && title.includes('우')) mappedPart = 'SIDE_SILL_R';
          else if (title.includes('라디에이터')) mappedPart = 'RADIATOR_SUPPORT';
          else if (title.includes('인사이드') && title.includes('좌')) mappedPart = 'INSIDE_PANEL_L';
          else if (title.includes('인사이드') && title.includes('우')) mappedPart = 'INSIDE_PANEL_R';
          else if (title.includes('크로스')) mappedPart = 'CROSS_MEMBER';
          else if (title.includes('프론트 패널') || title.includes('프론트패널')) mappedPart = 'FRONT_PANEL';
          else if (title.includes('사이드 멤버') && title.includes('좌')) mappedPart = 'FRONT_SIDE_MEMBER_L';
          else if (title.includes('사이드 멤버') && title.includes('우')) mappedPart = 'FRONT_SIDE_MEMBER_R';
          else if (title.includes('휠하우스') && title.includes('좌')) mappedPart = 'FRONT_WHEEL_HOUSE_L';
          else if (title.includes('휠하우스') && title.includes('우')) mappedPart = 'FRONT_WHEEL_HOUSE_R';
          else if (title.includes('리어 패널') || title.includes('리어패널')) mappedPart = 'REAR_PANEL';
          else if (title.includes('트렁크 플로어') || title.includes('트렁크플로어')) mappedPart = 'TRUNK_FLOOR';
          else if (title.includes('A필러') && title.includes('좌')) mappedPart = 'A_PILLAR_L';
          else if (title.includes('A필러') && title.includes('우')) mappedPart = 'A_PILLAR_R';
          else if (title.includes('B필러') && title.includes('좌')) mappedPart = 'B_PILLAR_L';
          else if (title.includes('B필러') && title.includes('우')) mappedPart = 'B_PILLAR_R';
          else if (title.includes('C필러') && title.includes('좌')) mappedPart = 'C_PILLAR_L';
          else if (title.includes('C필러') && title.includes('우')) mappedPart = 'C_PILLAR_R';
          else if (title.includes('대쉬') || title.includes('대시')) mappedPart = 'DASH_PANEL';
          else if (title.includes('플로어')) mappedPart = 'FLOOR_PANEL';

          if (stList.includes('X')) {
            if (mappedPart) parsedReplaces.push(mappedPart);
            replaceNames.push(title);
          } else if (stList.some((s: string) => ['W', 'A', 'C', 'U', 'T'].includes(s))) {
            if (mappedPart) parsedRepairs.push(mappedPart);
            repairNames.push(title);
          }
        }

        // 사고유무 정밀 판정: X 또는 W 마크가 1개라도 있으면 '완전무사고' 원천 배제
        const hasMajorAccident = Boolean(inspectData.master.accdient);
        const uniqueReplaceNames = Array.from(new Set(replaceNames));
        const uniqueRepairNames = Array.from(new Set(repairNames));

        if (hasMajorAccident) {
          accidentType = `■ 사고 [교환:${uniqueReplaceNames.length} / 판금:${uniqueRepairNames.length}]`;
        } else if (uniqueReplaceNames.length > 0 && uniqueRepairNames.length > 0) {
          accidentType = `▲ 단순(교환/판금) [교환:${uniqueReplaceNames.length} / 판금:${uniqueRepairNames.length}]`;
        } else if (uniqueReplaceNames.length > 0) {
          accidentType = uniqueReplaceNames.length > 3 ? `■ 사고 (교환 ${uniqueReplaceNames.length})` : `▲ 단순교환 (교환 ${uniqueReplaceNames.length})`;
        } else if (uniqueRepairNames.length > 0) {
          accidentType = `▲ 단순판금 (판금 ${uniqueRepairNames.length})`;
        } else if (inspectData.master.simpleRepair) {
          accidentType = '▲ 단순교환';
        } else if (inspectData.master.accdient === false && inspectData.master.simpleRepair === false) {
          accidentType = '● 완전무사고';
        } else {
          accidentType = '정보없음';
        }
      }

      // 출고정보 (이 차만의 옵션 - choice options 실측 디코딩)
      let choiceOptionsText = '기본사양';
      const selectedChoiceCodes = (vehicleData?.options?.choice || []).map((c: any) => String(c));
      try {
        const choiceRes = await fetch(`https://api.encar.com/v1/readside/vehicles/car/${vehicleId}/options/choice`, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': `https://fem.encar.com/cars/detail/${carId}`,
            'Accept': 'application/json'
          }
        });
        if (choiceRes.ok) {
          const choiceData = await choiceRes.json();
          const choiceNames: string[] = [];
          for (const opt of choiceData) {
            if (selectedChoiceCodes.includes(String(opt.optionCd))) {
              const priceStr = opt.price ? ` (${opt.price}만)` : '';
              choiceNames.push(`${opt.optionName}${priceStr}`);
            }
          }
          if (choiceNames.length > 0) {
            choiceOptionsText = choiceNames.join(' · ');
          }
        }
      } catch (e) {
        console.warn('Choice option fetch warning:', e);
      }

      const optionsText = choiceOptionsText;

      return res.json({
        success: true,
        data: {
          ...inspectData,
          color,
          vehicleNo: vehicleData?.vehicleNo || '',
          inspectionDate,
          checkDate: inspectionDate,
          registrationDate,
          accidentType,
          optionsText,
          choiceOptionsText,
          replaces: Array.from(new Set(parsedReplaces)),
          repairs: Array.from(new Set(parsedRepairs)),
          replaceNames: Array.from(new Set(replaceNames)),
          repairNames: Array.from(new Set(repairNames)),
          rawVehicle: vehicleData
        }
      });
    } catch (err: any) {
      return res.json({ success: false, error: err.message });
    }
  });

  // 5-2. 엔카 특정 매물 신차 출고 사양 및 추가 옵션 상세 조회 API
  app.get('/api/encar/vehicle/:carId', async (req, res) => {
    const { carId } = req.params;
    try {
      const vehicleRes = await fetch(`https://api.encar.com/v1/readside/vehicle/${carId}`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Referer': `https://fem.encar.com/cars/detail/${carId}`,
          'Accept': 'application/json'
        }
      });
      if (vehicleRes.ok) {
        const vehicleData = await vehicleRes.json();
        return res.json({ success: true, data: vehicleData });
      }
      return res.json({ success: false, message: '엔카 차량 제원 데이터 없음' });
    } catch (err: any) {
      return res.json({ success: false, error: err.message });
    }
  });

  // 9. 엔카 실시간 성능점검표 및 제원 로컬 백엔드(FastAPI 8000) 프록시
  app.get('/api/encar/inspection/:carId', async (req, res) => {
    const { carId } = req.params;
    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/encar/inspection/${encodeURIComponent(carId)}`);
      const data = await resp.json();
      return res.status(resp.status).json(data);
    } catch (e: any) {
      return res.status(500).json({ success: false, message: 'FastAPI 백엔드(8000) 엔카 성능점검 통신 실패: ' + e.message });
    }
  });

  // Vite Dev Server Middleware 마운트
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true, allowedHosts: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(process.cwd(), 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(process.cwd(), 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[J-PRO ERP] Server running on http://0.0.0.0:${PORT}`);
  });

  // 기존 크롬 확장프로그램 포트 8502 지원 (로컬 호환)
  try {
    const companionApp = express();
    companionApp.use(express.json());

    // CORS 전역 미들웨어: localhost:3000, 127.0.0.1:3000 등 프론트엔드 Origin 완벽 허용
    companionApp.use((req, res, next) => {
      const origin = req.headers.origin || '*';
      res.header('Access-Control-Allow-Origin', origin);
      res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.header('Access-Control-Allow-Headers', 'Content-Type, X-JPRO-Token, X-Secret-Token, Accept, Authorization');
      res.header('Access-Control-Allow-Credentials', 'true');
      if (req.method === 'OPTIONS') {
        return res.sendStatus(204);
      }
      next();
    });

    companionApp.post(['/api/save_cookie', '/api/session/cookie'], (req, res) => {
      const token = req.headers['x-jpro-token'] || req.headers['x-secret-token'] || req.body?.secretToken || req.body?.token;
      if (token !== 'jpro_sec_9981_live_auth') {
        return res.status(403).json({ error: '인증 토큰이 일치하지 않습니다.' });
      }
      const { cookie, target } = req.body;
      if (cookie) {
        const trimmed = cookie.trim();
        if (target === 'autoplus' || trimmed.includes('JSESSIONID')) {
          setSavedAutoplusCookie(trimmed);
        } else {
          setSavedHeydealerCookie(trimmed);
        }
        saveCookiesToDisk();
      }
      return res.json({ ok: true });
    });
    companionApp.get(['/api/session/cookie', '/api/cookie', '/api/get_cookie'], (req, res) => {
      const hd = getSavedHeydealerCookie();
      const ap = getSavedAutoplusCookie();
      return res.json({
        hasCookie: Boolean(hd),
        heydealerCookie: hd,
        hasAutoplusCookie: Boolean(ap),
        autoplusCookie: ap,
        updatedAt: new Date().toISOString()
      });
    });
    companionApp.options(['/api/save_cookie', '/api/session/cookie'], (req, res) => {
      res.sendStatus(204);
    });
    companionApp.listen(8502, '0.0.0.0', () => {
      console.log(`[J-PRO ERP] Local Extension Cookie Receiver running on port 8502`);
    });
  } catch (_) {}
}

startServer();
