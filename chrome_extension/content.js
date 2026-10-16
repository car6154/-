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
    console.log('[J-PRO AutoSync] high A+ 매입 데이터 실시간 감지 엔진 활성화');
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

            // 1차: 실측 오토플러스 SPPOL10001 전용 26개 컬럼 고정 그리드 매핑 (100% 정확도)
            if (cells.length >= 20 && carMatch) {
              // [4]: "224버2800\n(224버2800)\nKLYDC487DMC214608"
              // [5]: "쉐보레(대우)\n더 뉴스파크 LT"
              // [6]: "2021"
              // [9]: "현물"
              // [14]: "김재현"
              // [15]: "2026-10-16"
              // [16]: "4,850,000" (최종매입가)
              // [20]: "C26101600062" (PID)
              if (!carName && cells[5]) carName = (cells[5].innerText || "").replace(/\n+/g, ' ').trim();
              if (!modelYear && cells[6]) modelYear = (cells[6].innerText || "").trim();
              if (!purchaseType && cells[9]) purchaseType = (cells[9].innerText || "").trim();
              if (!transferDate && cells[15]) transferDate = (cells[15].innerText || "").trim();
              if (cells[20]) pid = (cells[20].innerText || "").trim();

              if (cells[16]) {
                const pStr = (cells[16].innerText || "").replace(/[^\d]/g, '');
                if (pStr) buyPrice = parseInt(pStr, 10);
              }
            }

            // 2차: 동적 헤더 컬럼 인덱스 매칭 기반 추출
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
                if (val > 0 && val < 50000000) {
                  etcFee = val > 5000 ? val : val * 10000;
                }
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

            // 3차: Fallback 패턴 매칭 (비정형 그리드 대응)
            cells.forEach((cell, idx) => {
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
              if (/폐자원/.test(txt) || (idx === 16 && /^\d{1,3}(,\d{3})+$/.test(txt))) {
                const num = parseInt(txt.replace(/,/g, ''), 10);
                if (num > 0) scrapDeduction = num;
              }
            });

            let manager = "";
            if (rowText.includes("김재현") || (cells[14] && cells[14].innerText.includes("김재현"))) {
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

        // B) 매입등록(일반) 단건 상세 화면 및 폼 입력 요소 정밀 스캔
        const bodyText = document.body.innerText || "";
        const allCarMatches = bodyText.match(new RegExp(CAR_NO_REGEX, 'g')) || [];
        for (const rawCarMatch of allCarMatches) {
          const sCarNo = rawCarMatch.replace(/\s+/g, '');
          let formBuyPrice = 0;
          let formEtcFee = 0;
          let formOuterRepairs = 0;

          // 1. input 요소 직접 전수 탐색 (name, id, title, 부모 텍스트 기반)
          const allInputs = document.querySelectorAll('input');
          allInputs.forEach(inp => {
            const valClean = (inp.value || "").replace(/[^\d]/g, '');
            if (!valClean) return;
            const valNum = parseInt(valClean, 10);

            // 주변 부모나 형제 요소 텍스트
            const pText = (inp.closest('tr, td, div, dl')?.innerText || "").replace(/\s+/g, '');

            // 기타비용 (545,000 등 소개/낙찰수수료)
            if (/기타비용|소개수수료|낙찰수수료/.test(pText) || /etc|fee/.test(inp.name || inp.id)) {
              if (valNum >= 10000 && valNum <= 50000000) {
                formEtcFee = valNum;
              }
            }

            // 최종매입가
            if (/최종매입가|실매입가/.test(pText) || /buy|pur/.test(inp.name || inp.id)) {
              if (valNum >= 1000000 && valNum <= 500000000) {
                formBuyPrice = valNum;
              }
            }
          });

          // 2. 텍스트 정규식 fallback
          if (formEtcFee === 0) {
            const mEtc = bodyText.match(/(?:기타비용|낙찰\/소개수수료)[^\d]*([\d,]{4,})/);
            if (mEtc) formEtcFee = parseInt(mEtc[1].replace(/,/g, ''), 10) || 0;
          }
          if (formBuyPrice === 0) {
            const mBuy = bodyText.match(/최종매입가[^\d]*([\d,]{6,})/);
            if (mBuy) formBuyPrice = parseInt(mBuy[1].replace(/,/g, ''), 10) || 0;
          }

          // 3. 외판 판수
          const outerInput = document.querySelector('input[name*="out"], input[id*="out"], input[name*="pan"]');
          if (outerInput && outerInput.value) {
            formOuterRepairs = parseInt(outerInput.value.replace(/[^\d]/g, ''), 10) || 0;
          } else {
            const mOut = bodyText.match(/외판[^\d]*(\d{1,2})/);
            if (mOut) formOuterRepairs = parseInt(mOut[1], 10) || 0;
          }

          // 목록에서 찾은 차량과 병합하거나 신규 추가
          const targetCar = foundCars.find(c => c.carNumber === sCarNo);
          if (targetCar) {
            if (formBuyPrice > 0) targetCar.buyPrice = formBuyPrice;
            if (formEtcFee > 0) targetCar.etcFee = formEtcFee;
            if (formOuterRepairs > 0) targetCar.outerRepairs = formOuterRepairs;
          } else if (formBuyPrice > 0 || formEtcFee > 0 || formOuterRepairs > 0) {
            foundCars.push({
              carNumber: sCarNo,
              buyPrice: formBuyPrice,
              etcFee: formEtcFee,
              outerRepairs: formOuterRepairs
            });
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


