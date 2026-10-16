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
        const DATE_REGEX = /\b202\d[-.]\d{1,2}[-.]\d{1,2}\b/;

        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
          let buyPriceColIdx = -1;
          let etcFeeColIdx = -1;
          let carNoColIdx = -1;
          let carNameColIdx = -1;
          let yearColIdx = -1;
          let scrapColIdx = -1;
          let typeColIdx = -1;
          let mgrColIdx = -1;

          const headerRows = table.querySelectorAll('thead tr, tr');
          for (const hRow of headerRows) {
            const ths = hRow.querySelectorAll('th, td');
            if (ths.length >= 5) {
              ths.forEach((th, idx) => {
                const title = (th.innerText || "").replace(/\s+/g, '');
                if (/^(매입가|실매입가|매입금액|낙찰가|취득가|최종매입가)$/.test(title)) buyPriceColIdx = idx;
                else if (buyPriceColIdx === -1 && /(매입가|실매입|낙찰가)/.test(title)) buyPriceColIdx = idx;

                if (/^(수수료|기타비용|낙찰수수료|헤딜수수료|플랫폼수수료|부대비용)$/.test(title)) etcFeeColIdx = idx;
                else if (etcFeeColIdx === -1 && /(기타비용|수수료|부대비)/.test(title)) etcFeeColIdx = idx;

                if (/(차량번호|차번)/.test(title)) carNoColIdx = idx;
                if (/(차량명|차종|모델명)/.test(title)) carNameColIdx = idx;
                if (/^(연식|년식)$/.test(title)) yearColIdx = idx;
                if (/폐자원/.test(title)) scrapColIdx = idx;
                if (/(매입구분|매입유형|구분)/.test(title)) typeColIdx = idx;
                if (/(담당자|매니저|담당)/.test(title)) mgrColIdx = idx;
              });
              if (buyPriceColIdx !== -1 || carNoColIdx !== -1) break;
            }
          }

          const rows = table.querySelectorAll('tbody tr, tr');
          rows.forEach(tr => {
            // 하위 테이블을 감싼 외부 레이아웃 tr은 제외
            if (tr.querySelector('table')) return;

            const cells = Array.from(tr.querySelectorAll('td'));
            if (cells.length < 5) return;

            const rowText = tr.innerText || "";
            const carMatch = rowText.match(CAR_NO_REGEX);
            if (!carMatch) return;

            const carNo = carMatch[0].replace(/\s+/g, '');
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

            const dateMatches = rowText.match(new RegExp(DATE_REGEX, 'g')) || [];
            if (dateMatches.length > 0) {
              transferDate = dateMatches[dateMatches.length - 1];
            }

            // 1차: 실측 오토플러스 SPPOL10001 전용 고정 그리드 매핑
            if (cells.length >= 20) {
              if (cells[5]) carName = (cells[5].innerText || "").replace(/\n+/g, ' ').trim();
              if (cells[6]) modelYear = (cells[6].innerText || "").trim();
              if (cells[9]) purchaseType = (cells[9].innerText || "").trim();
              if (cells[15]) transferDate = (cells[15].innerText || "").trim();
              if (cells[20]) pid = (cells[20].innerText || "").trim();

              if (cells[16]) {
                const pStr = (cells[16].innerText || "").replace(/[^\d]/g, '');
                if (pStr) buyPrice = parseInt(pStr, 10);
              }
            }

            // 2차: 동적 헤더 컬럼 인덱스 기반 추출
            if (buyPrice === 0 && buyPriceColIdx !== -1 && cells[buyPriceColIdx]) {
              const numStr = (cells[buyPriceColIdx].innerText || "").replace(/[^\d]/g, '');
              if (numStr) {
                const val = parseInt(numStr, 10);
                if (val >= 1000000 && val <= 500000000) buyPrice = val;
                else if (val > 0 && val <= 50000) buyPrice = val * 10000;
              }
            }

            if (etcFeeColIdx !== -1 && cells[etcFeeColIdx]) {
              const numStr = (cells[etcFeeColIdx].innerText || "").replace(/[^\d]/g, '');
              if (numStr) {
                const val = parseInt(numStr, 10);
                if (val > 0 && val < 50000000) etcFee = val > 5000 ? val : val * 10000;
              }
            }

            if (carNameColIdx !== -1 && cells[carNameColIdx] && !carName) {
              carName = (cells[carNameColIdx].innerText || "").replace(/\n+/g, ' ').trim();
            }
            if (yearColIdx !== -1 && cells[yearColIdx] && !modelYear) {
              const yMatch = (cells[yearColIdx].innerText || "").match(/(201\d|202\d)/);
              if (yMatch) modelYear = yMatch[1];
            }
            if (typeColIdx !== -1 && cells[typeColIdx] && !purchaseType) {
              purchaseType = (cells[typeColIdx].innerText || "").trim();
            }
            if (scrapColIdx !== -1 && cells[scrapColIdx] && !scrapDeduction) {
              const sNum = (cells[scrapColIdx].innerText || "").replace(/[^\d]/g, '');
              if (sNum) scrapDeduction = parseInt(sNum, 10) || 0;
            }

            // 3차: Fallback 패턴 매칭 (수정: idx === 16을 scrapDeduction으로 오인하던 버그 제거)
            cells.forEach((cell) => {
              const txt = (cell.innerText || "").trim();
              if (!modelYear && /^(201\d|202\d)$/.test(txt)) modelYear = txt;
              if (!carName && /(현대|기아|제네시스|쉐보레|르노|쌍용|KGM|BMW|벤츠|아우디|볼보|폭스바겐|포르쉐|렉서스|토요타|미니|랜드로버|테슬라)/.test(txt)) {
                carName = txt.replace(/\n+/g, ' ');
              }
              if (!purchaseType && /(헤이딜러|엔카|KB|플랫폼|현물|공판|대행)/.test(txt)) purchaseType = txt;

              const cleanNumStr = txt.replace(/[^\d]/g, '');
              if (buyPrice === 0 && cleanNumStr.length >= 7 && cleanNumStr.length <= 9) {
                const num = parseInt(cleanNumStr, 10);
                if (num >= 1000000 && num <= 500000000) buyPrice = num;
              }
              if (etcFee === 0 && /(수수료|기타비용|낙찰수수료)/.test(txt)) {
                const feeNum = parseInt(cleanNumStr, 10);
                if (feeNum >= 10000 && feeNum <= 5000000) etcFee = feeNum;
              }
              if (!scrapDeduction && /폐자원/.test(txt)) {
                const num = parseInt(cleanNumStr, 10);
                if (num > 0) scrapDeduction = num;
              }
            });

            let manager = "";
            if (rowText.includes("김재현") || (cells[14] && cells[14].innerText.includes("김재현"))) {
              manager = "김재현";
            } else if (mgrColIdx !== -1 && cells[mgrColIdx]) {
              manager = (cells[mgrColIdx].innerText || "").trim();
            }

            let poId = "";
            const poInp = tr.querySelector('input[name*="poId"]');
            if (poInp && poInp.value) {
              poId = poInp.value.trim();
            } else {
              const mPo = (tr.innerHTML || "").match(/poId=(\d+)/);
              if (mPo) poId = mPo[1];
            }

            if (carNo) {
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
                manager
              });
            }
          });
        });

        const foundCars = Array.from(carMap.values());

        async function enrichCarDetails(cars) {
          if (!cars.length) return;
          for (const car of cars) {
            if (car.poId && (!car.etcFee || car.etcFee === 0)) {
              try {
                const detailUrl = `https://admin.autoplus.co.kr/spot/syspo/SPPOR20001?poId=${car.poId}&vw=1&showGbn=H`;
                const resp = await fetch(detailUrl, { credentials: 'include' });
                if (resp.ok) {
                  const html = await resp.text();
                  const parsedFee = extractEtcFeeFromHtml(html);
                  if (parsedFee > 0) car.etcFee = parsedFee;
                }
              } catch (e) {}
            }
          }

          const sig = JSON.stringify(cars);
          if (sig !== lastScanSignature && isContextAlive()) {
            chrome.runtime.sendMessage(
              { action: 'sync_highplus_buy_data', data: cars },
              (response) => {
                // 중요: 백엔드 전송이 실제로 성공했을 때만 서명을 잠금
                if (!chrome.runtime.lastError && response && response.synced) {
                  lastScanSignature = sig;
                  console.log(`[J-PRO AutoSync] high A+ 매입 데이터 ${cars.length}대 백엔드 동기화 성공`);
                } else {
                  console.warn('[J-PRO AutoSync] 백엔드 전송 미완료 - 다음 주기에 재시도합니다.');
                }
              }
            );
          }
        }

        enrichCarDetails(foundCars);
      } catch (err) {}
    }

    setTimeout(scanHighplusBuyData, 800);
    window.__jproAutoplusScanTimer = setInterval(scanHighplusBuyData, 5000);
  }
})();


