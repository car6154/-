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
    setTimeout(() => notifySync('window_load'), 200);
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

  // ── 6. high A+ (admin.autoplus.co.kr) 매입 데이터 실시간 자동 감지 & 백엔드 전송 ──
  if (window.location.hostname.includes('admin.autoplus.co.kr')) {
    let lastScanSignature = "";

    function scanHighplusBuyData() {
      try {
        const foundCars = [];
        const CAR_NO_REGEX = /\b\d{2,3}[가-힣]\s*\d{4}\b/;
        const PID_REGEX = /\bC26\d{9}\b/;
        const DATE_REGEX = /\b202\d[-.]\d{1,2}[-.]\d{1,2}\b/;

        // A) 매입조회 (SPPOL10001) 목록 테이블 스캔
        // 1. 테이블별 헤더 매핑 (매입가, 수수료/기타비용, 차명, 연식, 매니저, 폐자원 등 컬럼 위치 동적 파악)
        const tables = document.querySelectorAll('table, .grid');
        tables.forEach(table => {
          let buyPriceColIdx = -1;
          let etcFeeColIdx = -1;
          let carNoColIdx = -1;
          let carNameColIdx = -1;
          let yearColIdx = -1;
          let scrapColIdx = -1;
          let typeColIdx = -1;
          let mgrColIdx = -1;

          // thead 또는 첫 번째 tr에서 헤더 감지
          const headerRows = table.querySelectorAll('thead tr, tr');
          for (const hRow of headerRows) {
            const ths = hRow.querySelectorAll('th, td');
            if (ths.length >= 5) {
              ths.forEach((th, idx) => {
                const title = (th.innerText || "").replace(/\s+/g, '');
                if (/^(매입가|실매입가|매입금액|낙찰가|취득가)$/.test(title)) buyPriceColIdx = idx;
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

          const rows = table.querySelectorAll('tr');
          rows.forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('td, th'));
            if (cells.length < 5) return;

            const rowText = tr.innerText || "";
            const carMatch = rowText.match(CAR_NO_REGEX);
            if (!carMatch) return;

            const carNo = (carNoColIdx !== -1 && cells[carNoColIdx] ? cells[carNoColIdx].innerText.replace(/\s+/g, '') : carMatch[0].replace(/\s+/g, ''));
            
            // 각 셀 텍스트 분석
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
              transferDate = dateMatches[dateMatches.length - 1]; // 마지막 날짜가 보통 이전일자
            }

            // 1차: 헤더 컬럼 인덱스 매칭 기반 정확한 값 추출
            if (buyPriceColIdx !== -1 && cells[buyPriceColIdx]) {
              const numStr = (cells[buyPriceColIdx].innerText || "").replace(/[^\d]/g, '');
              if (numStr) {
                const val = parseInt(numStr, 10);
                if (val >= 1000000 && val <= 500000000) buyPrice = val;
                else if (val > 0 && val <= 50000) buyPrice = val * 10000; // 만원 단위 표기인 경우
              }
            }

            if (etcFeeColIdx !== -1 && cells[etcFeeColIdx]) {
              const numStr = (cells[etcFeeColIdx].innerText || "").replace(/[^\d]/g, '');
              if (numStr) {
                const val = parseInt(numStr, 10);
                if (val > 0 && val < 50000000) {
                  etcFee = val > 5000 ? val : val * 10000;
                }
              }
            }

            if (carNameColIdx !== -1 && cells[carNameColIdx]) {
              carName = (cells[carNameColIdx].innerText || "").replace(/\n+/g, ' ').trim();
            }

            if (yearColIdx !== -1 && cells[yearColIdx]) {
              const yMatch = (cells[yearColIdx].innerText || "").match(/(201\d|202\d)/);
              if (yMatch) modelYear = yMatch[1];
            }

            if (typeColIdx !== -1 && cells[typeColIdx]) {
              purchaseType = (cells[typeColIdx].innerText || "").trim();
            }

            if (scrapColIdx !== -1 && cells[scrapColIdx]) {
              const sNum = (cells[scrapColIdx].innerText || "").replace(/[^\d]/g, '');
              if (sNum) scrapDeduction = parseInt(sNum, 10) || 0;
            }

            // 2차: Fallback 패턴 매칭 (헤더 인덱스가 없거나 파싱 실패 시)
            cells.forEach((cell, idx) => {
              const txt = (cell.innerText || "").trim();
              // 연식 (2015~2027)
              if (!modelYear && /^(201\d|202\d)$/.test(txt)) {
                modelYear = txt;
              }
              // 차명 (현대, 기아, 제네시스, 쉐보레, 르노, 쌍용, BMW, 벤츠 등이 포함된 셀)
              if (!carName && /(현대|기아|제네시스|쉐보레|르노|쌍용|KGM|BMW|벤츠|아우디|볼보|폭스바겐|포르쉐|렉서스|토요타|미니|랜드로버|테슬라)/.test(txt)) {
                carName = txt.replace(/\n+/g, ' ');
              }
              // 매입유형 (헤이딜러, 경매, 플랫폼 등)
              if (!purchaseType && /(헤이딜러|엔카|KB|플랫폼|현물|공판|대행)/.test(txt)) {
                purchaseType = txt;
              }
              // 금액 (백만 원 이상: 1,000,000 ~ 500,000,000)
              const cleanNumStr = txt.replace(/[^\d]/g, '');
              if (buyPrice === 0 && cleanNumStr.length >= 7 && cleanNumStr.length <= 9) {
                const num = parseInt(cleanNumStr, 10);
                if (num >= 1000000 && num <= 500000000) {
                  buyPrice = num;
                }
              }
              // 수수료 / 기타비용 fallback (1만 ~ 200만 원 사이 수수료 후보 셀 감지)
              if (etcFee === 0 && /(수수료|기타비용|낙찰수수료)/.test(txt)) {
                const feeNum = parseInt(cleanNumStr, 10);
                if (feeNum >= 10000 && feeNum <= 5000000) etcFee = feeNum;
              }
              // 폐자원공제액 (십만~수백만 원 단위 공제액)
              if (/폐자원/.test(txt) || (idx === 16 && /^\d{1,3}(,\d{3})+$/.test(txt))) {
                const num = parseInt(txt.replace(/,/g, ''), 10);
                if (num > 0) scrapDeduction = num;
              }
            });

            let manager = "";
            if (rowText.includes("김재현")) {
              manager = "김재현";
            } else if (mgrColIdx !== -1 && cells[mgrColIdx]) {
              manager = (cells[mgrColIdx].innerText || "").trim();
            } else {
              for (const cell of cells) {
                const txt = (cell.innerText || "").trim();
                if (/^[가-힣]{2,4}$/.test(txt) && !/(조회|수정|완료|진행|대기|현물|공판|대행|법인|개인|과세|면세|간이|승인|반려|결재|취소|경매|일반)/.test(txt)) {
                  manager = txt;
                  break;
                }
              }
              if (!manager) {
                const mgrInput = document.querySelector('input[name*="Charge"], input[name*="Emp"], input[name*="User"], input[id*="Charge"], input[id*="Emp"], input[id*="User"]');
                if (mgrInput && mgrInput.value) {
                  manager = mgrInput.value.trim();
                }
              }
            }

            if (carNo) {
              foundCars.push({
                carNumber: carNo,
                carName: carName,
                modelYear: modelYear,
                buyPrice: buyPrice,
                etcFee: etcFee,
                transferDate: transferDate,
                purchaseType: purchaseType,
                pid: pid,
                scrapDeduction: scrapDeduction,
                manager: manager
              });
            }
          });
        });

        // B) 매입등록(일반) 단건 상세 화면 스캔 (외판 판수 및 기타비용 545,000 등)
        const bodyText = document.body.innerText || "";
        const singleCarMatch = bodyText.match(CAR_NO_REGEX);
        if (singleCarMatch) {
          const sCarNo = singleCarMatch[0].replace(/\s+/g, '');
          let etcFee = 0;
          let outerRepairs = 0;
          let repairCost = 0;

          // 기타비용 (낙찰/소개수수료)
          const etcFeeInput = document.querySelector('input[name*="etc"], input[id*="etc"], input[name*="fee"]');
          if (etcFeeInput && etcFeeInput.value) {
            etcFee = parseInt(etcFeeInput.value.replace(/[^\d]/g, ''), 10) || 0;
          } else {
            const mEtc = bodyText.match(/기타비용[^\d]*([\d,]{4,})/);
            if (mEtc) etcFee = parseInt(mEtc[1].replace(/,/g, ''), 10) || 0;
          }

          // 외판 판수
          const outerInput = document.querySelector('input[name*="out"], input[id*="out"], input[name*="pan"]');
          if (outerInput && outerInput.value) {
            outerRepairs = parseInt(outerInput.value.replace(/[^\d]/g, ''), 10) || 0;
          } else {
            const mOut = bodyText.match(/외판[^\d]*(\d{1,2})/);
            if (mOut) outerRepairs = parseInt(mOut[1], 10) || 0;
          }

          if (etcFee > 0 || outerRepairs > 0) {
            const existing = foundCars.find(c => c.carNumber === sCarNo);
            if (existing) {
              if (etcFee > 0) existing.etcFee = etcFee;
              if (outerRepairs > 0) existing.outerRepairs = outerRepairs;
            } else {
              foundCars.push({
                carNumber: sCarNo,
                etcFee: etcFee,
                outerRepairs: outerRepairs
              });
            }
          }
        }

        if (foundCars.length > 0) {
          const sig = JSON.stringify(foundCars);
          if (sig !== lastScanSignature) {
            lastScanSignature = sig;
            chrome.runtime.sendMessage({
              action: 'sync_highplus_buy_data',
              data: foundCars
            }, (res) => {
              if (res && res.status === 'ok') {
                console.log(`[J-PRO AutoSync] high A+ 매입 데이터 ${foundCars.length}대 자동 전송 완료`);
              }
            });
          }
        }
      } catch (err) {
        // 무시
      }
    }

    // 1초 뒤 1차 스캔, DOM 변경 시 재스캔
    setTimeout(scanHighplusBuyData, 1200);
    setInterval(scanHighplusBuyData, 5000);
  }

  // 제이프로 웹앱에서 [매입연동] 버튼 클릭 시 백그라운드 수집 즉시 실행 브릿지
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'JPRO_TRIGGER_HIGHPLUS_BUY_SYNC') {
      try {
        chrome.runtime.sendMessage({ action: 'trigger_highplus_buy_sync' });
      } catch (e) {}
    }
  });
})();


