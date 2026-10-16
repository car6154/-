// content.js - 헤이딜러 및 오토플러스 페이지 진입/포커스/로드 시 실시간 동기화 트리거
(function() {
  function notifySync(reason) {
    try {
      if (chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ 
          action: 'trigger_sync', 
          reason: reason, 
          url: window.location.href 
        }, () => {
          // 응답 무시 (에러 방지)
          if (chrome.runtime.lastError) {}
        });
      }
    } catch (e) {}
  }

  // 1. 페이지 시작 즉시 트리거 (새 창/새 탭 열리자마자 1차 동기화)
  notifySync('page_start');

  // 2. DOM 로드 완료 시 (서버 Set-Cookie 및 토큰 반영 시점)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      notifySync('dom_ready');
    });
  } else {
    notifySync('dom_ready');
  }

  // 3. 페이지 완전 로딩 후 (비동기 API 요청 완료 후 쿠키 안정화 시점)
  window.addEventListener('load', () => {
    setTimeout(() => {
      notifySync('window_load');
    }, 200);
  });

  // 4. 창/탭 포커스 시 (다른 창에서 이 창으로 돌아올 때 즉시 동기화)
  window.addEventListener('focus', () => {
    notifySync('window_focus');
  });

  // 5. 사용자가 화면을 클릭하거나 키를 누를 때 1회 동기화 (최신 활성 세션 보장)
  let userInteracted = false;
  window.addEventListener('click', () => {
    if (!userInteracted) {
      userInteracted = true;
      notifySync('user_interaction');
    }
  }, { once: true, passive: true });

  // ── 6. J-PRO 웹앱(jpro:3000 등)에서 [매입연동] 클릭 시 postMessage를 받아 background.js로 전달 ──
  if (
    window.location.hostname === 'jpro' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '100.95.238.123'
  ) {
    window.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'JPRO_TRIGGER_HIGHPLUS_BUY_SYNC') {
        try {
          if (chrome?.runtime?.id) {
            chrome.runtime.sendMessage({ action: 'trigger_highplus_buy_sync_from_tab' });
          }
        } catch (e) {}
      }
    });
  }

  // ── 7. 오토플러스 어드민 (admin.autoplus.co.kr) 매입 데이터 실시간 스캔 & 백엔드 전송 ──
  if (window.location.hostname.includes('admin.autoplus.co.kr')) {
    // 중복 타이머 방지 (executeScript로 재주입될 때 기존 타이머 정리)
    if (window.__jproAutoplusScanTimer) {
      clearInterval(window.__jproAutoplusScanTimer);
    }
    let lastScanSignature = "";

    function isContextAlive() {
      try { return !!(chrome && chrome.runtime && chrome.runtime.id); } catch (e) { return false; }
    }

    function extractEtcFeeFromHtml(html) {
      try {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const elements = Array.from(doc.querySelectorAll('th, td, label, span'));
        for (let i = 0; i < elements.length; i++) {
          const txt = (elements[i].textContent || '').replace(/\s+/g, '');
          if (txt.includes('기타비용')) {
            // 인접 셀(nextElementSibling) 또는 내부 input value 확인
            const nextEl = elements[i].nextElementSibling || elements[i].parentElement;
            if (nextEl) {
              const inp = nextEl.querySelector('input');
              const rawVal = inp ? inp.value : nextEl.textContent;
              const num = parseInt((rawVal || '').replace(/[^\d]/g, ''), 10);
              if (num > 0) return num;
            }
          }
        }
        // Fallback: HTML 태그를 모두 제거한 순수 텍스트에서 정규식 매칭 (속성값 숫자 간섭 배제)
        const textOnly = html.replace(/<[^>]+>/g, ' ');
        const mEtc = textOnly.match(/기타비용[^\d]*([\d,]{4,})/);
        if (mEtc) {
          const parsedFee = parseInt(mEtc[1].replace(/,/g, ''), 10);
          if (parsedFee > 0) return parsedFee;
        }
      } catch (e) {}
      return 0;
    }

    function scanHighplusBuyData() {
      if (!isContextAlive()) {
        if (window.__jproAutoplusScanTimer) clearInterval(window.__jproAutoplusScanTimer);
        return;
      }
      try {
        const carMap = new Map(); // 차량번호 기준 중복 방지
        const CAR_NO_REGEX = /\b\d{2,3}[가-힣]\s*\d{4}\b/;
        const PID_REGEX = /\bC26\d{9}\b/;
        const DATE_REGEX = /\b202\d[-.]\d{1,2}[-.]\d{1,2}\b/g;

        // 1차 최우선 스캔: 화면 내 전체 행(tr)에서 김재현 매입 차량 1:1 직접 매칭
        const allRows = Array.from(document.querySelectorAll('tr'));
        for (const tr of allRows) {
          const rowText = tr.innerText || "";
          const carMatch = rowText.match(CAR_NO_REGEX);
          if (!carMatch) continue;

          // 김재현 담당자 우선 필터
          const isKim = rowText.includes("김재현");
          if (!isKim) continue;

          const carNo = carMatch[0].replace(/\s+/g, '');
          const cells = Array.from(tr.querySelectorAll('td, th'));

          let carName = "";
          let modelYear = "";
          let buyPrice = 0;
          let etcFee = 0;
          let transferDate = "";
          let purchaseType = "";
          let pid = "";
          let scrapDeduction = 0;

          const pidMatch = rowText.match(PID_REGEX);
          if (pidMatch) pid = pidMatch[0];

          const dateMatches = rowText.match(DATE_REGEX) || [];
          if (dateMatches.length > 0) {
            transferDate = dateMatches[dateMatches.length - 1];
          }

          // 오토플러스 SPPOL10001 컬럼 매핑
          if (cells[5]) carName = (cells[5].innerText || "").replace(/\n+/g, ' ').trim();
          if (cells[6]) modelYear = (cells[6].innerText || "").trim();
          if (cells[9]) purchaseType = (cells[9].innerText || "").trim();
          if (cells[15] && !transferDate) transferDate = (cells[15].innerText || "").trim();
          if (cells[20] && !pid) pid = (cells[20].innerText || "").trim();

          if (cells[16]) {
            const pStr = (cells[16].innerText || "").replace(/[^\d]/g, '');
            if (pStr) {
              const pVal = parseInt(pStr, 10);
              if (pVal >= 1000000 && pVal <= 500000000) buyPrice = pVal;
            }
          }

          // Fallback: 금액 추출
          if (buyPrice === 0) {
            const numMatches = rowText.match(/\b\d{1,3}(?:,\d{3}){2,}\b/g) || [];
            for (const nm of numMatches) {
              const val = parseInt(nm.replace(/,/g, ''), 10);
              if (val >= 1000000 && val <= 500000000) {
                buyPrice = val;
                break;
              }
            }
          }

          let poId = "";
          const poInp = tr.querySelector('input[name*="poId"]');
          if (poInp && poInp.value) {
            poId = poInp.value.trim();
          } else {
            const mPo = (tr.innerHTML || "").match(/poId=(\d+)/);
            if (mPo) poId = mPo[1];
          }

          carMap.set(carNo, {
            carNumber: carNo,
            carName,
            modelYear,
            buyPrice,
            etcFee,
            transferDate,
            purchaseType,
            pid,
            poId,
            scrapDeduction,
            manager: "김재현"
          });
        }

        const foundCars = Array.from(carMap.values());
        if (!foundCars.length) return;

        // 서명 검사: 데이터 변경 시 백엔드 즉시 전송
        const sig = JSON.stringify(foundCars.map(c => ({ no: c.carNumber, p: c.buyPrice, d: c.transferDate })));
        if (sig !== lastScanSignature && isContextAlive()) {
          chrome.runtime.sendMessage(
            { action: 'sync_highplus_buy_data', data: foundCars },
            (response) => {
              if (!chrome.runtime.lastError && response && response.synced) {
                lastScanSignature = sig;
                console.log(`[J-PRO AutoSync] high A+ 매입 데이터 ${foundCars.length}대 백엔드 무인 동기화 성공`);
              }
            }
          );
        }

        // 백그라운드 세부 기타비용 fetch (오토플러스 getSysPo.do poAddExt 실측치)
        for (const car of foundCars) {
          if (car.poId && car.etcFee === undefined) {
            fetch('https://admin.autoplus.co.kr/spot/syspo/getSysPo.do', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Ajax-call': 'true'
              },
              body: `poId=${encodeURIComponent(car.poId)}`,
              credentials: 'include'
            })
              .then(r => r.ok ? r.json() : null)
              .then(res => {
                if (!res || !res.data) return;
                const ext = res.data.poAddExt;
                const parsedFee = (ext !== null && ext !== undefined && String(ext).trim() !== '') ? parseInt(String(ext).replace(/[^\d]/g, ''), 10) : 0;
                if (car.etcFee !== parsedFee) {
                  car.etcFee = parsedFee;
                  if (isContextAlive()) {
                    chrome.runtime.sendMessage({ action: 'sync_highplus_buy_data', data: [car] });
                  }
                }
              })
              .catch(() => {});
          }
        }
      } catch (err) {}
    }

    setTimeout(scanHighplusBuyData, 800);
    window.__jproAutoplusScanTimer = setInterval(scanHighplusBuyData, 5000);
  }
})();


