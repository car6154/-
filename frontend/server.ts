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

  // 4. 엔카 실시간 동급 매물 및 시세 검색 API (Python 백엔드 8000 직결 프록시)
  app.all('/api/encar/search', async (req, res) => {
    const startTime = Date.now();
    try {
      const payload = {
        url: (req.body?.url || req.query.url) as string || '',
        carName: (req.body?.carName || req.body?.keyword || req.query.keyword || req.body?.model || req.query.model) as string || '',
        detailModel: (req.body?.detailModel || req.query.detailModel) as string || '',
        gradeName: (req.body?.gradeName || req.query.gradeName) as string || '',
        gradeDetailName: (req.body?.gradeDetailName || req.query.gradeDetailName) as string || '',
        manufacturer: (req.body?.manufacturer || req.query.manufacturer) as string || '',
        year: Number(req.body?.year || req.query.year) || 0,
        mileage: Number(req.body?.mileage || req.query.mileage) || 0,
        carNumber: (req.body?.carNumber || req.query.carNumber) as string || '',
        targetAccident: (req.body?.targetAccident || req.query.targetAccident) as string || '',
        skipDetail: req.body?.skipDetail !== undefined ? Boolean(req.body.skipDetail) : true
      };

      const pyRes = await fetch('http://127.0.0.1:8000/api/encar/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(45000)
      });

      const data = await pyRes.json();
      const duration = Date.now() - startTime;
      const itemsCount = Array.isArray(data?.items) ? data.items.length : 0;
      console.info(`[EncProxy] POST /api/encar/search -> 8000, status=${pyRes.status}, items=${itemsCount}, time=${duration}ms`);
      logEvent('ENCAR_PROXY', `POST /api/encar/search -> 8000, status=${pyRes.status}, items=${itemsCount}`);

      return res.status(pyRes.status).json(data);
    } catch (e: any) {
      const duration = Date.now() - startTime;
      console.error(`[EncProxy] POST /api/encar/search -> 8000 FAILED, time=${duration}ms:`, e.message);
      logEvent('ENCAR_PROXY_ERR', `POST /api/encar/search failed: ${e.message}`);
      return res.status(502).json({
        success: false,
        error: `Python 백엔드(8000) 연결 또는 응답 실패: ${e.message}`,
        items: []
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

  // 5-0-1. K-Car 직영 매물 검색 및 실시간 소매 시세 분석 API (로컬 Python 백엔드 연동)
  app.all('/api/kcar/market', async (req, res) => {
    try {
      const carName = (req.body?.carName || req.query.carName || '') as string;
      const detailModel = (req.body?.detailModel || req.query.detailModel || '') as string;
      const gradeName = (req.body?.gradeName || req.query.gradeName || '') as string;
      const gradeDetailName = (req.body?.gradeDetailName || req.query.gradeDetailName || '') as string;
      const manufacturer = (req.body?.manufacturer || req.query.manufacturer || '') as string;
      const year = Number(req.body?.year || req.query.year || 0);
      const mileage = Number(req.body?.mileage || req.query.mileage || 0);

      const pyRes = await fetch('http://127.0.0.1:8000/api/kcar/market', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          carName,
          detailModel,
          gradeName,
          gradeDetailName,
          manufacturer,
          year,
          mileage
        }),
        signal: AbortSignal.timeout(10000)
      });
      if (pyRes.ok) {
        const data = await pyRes.json();
        return res.json(data);
      }
      return res.status(pyRes.status).json({ success: false, message: 'Python K-Car API 반환 실패' });
    } catch (err: any) {
      console.warn('K-Car 시세 API 연동 실패:', err.message);
      return res.json({
        success: false,
        count: 0,
        min: 0,
        max: 0,
        avg: 0,
        median: 0,
        yearStats: [],
        priceBins: [],
        cars: [],
        message: err.message
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

      let choiceOptionsText = '기본사양';
      let totalOptionPrice = 0;
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
              if (typeof opt.price === 'number' && opt.price > 0) {
                totalOptionPrice += opt.price;
              }
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
      const originPrice = Number(vehicleData?.category?.originPrice) || 0;
      const newCarPrice = originPrice > 0 ? originPrice + totalOptionPrice : 0;

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
          rawVehicle: vehicleData,
          originPrice,
          optionPrice: totalOptionPrice,
          newCarPrice
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
