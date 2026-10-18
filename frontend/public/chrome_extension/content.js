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
        const CAR_NO_REGEX = /\d{2,3}[가-힣]\s*\d{4}/;
        const PID_REGEX = /\bC\d{11}\b/;
        const DATE_REGEX = /\b202\d[-/.]\d{1,2}[-/.]\d{1,2}\b/g;

        // 1차 최우선 스캔: 화면 내 전체 행(tr)에서 매입 차량 1:1 직접 매칭
        const allRows = Array.from(document.querySelectorAll('tr'));
        for (const tr of allRows) {
          const rowText = tr.innerText || "";
          const carMatch = rowText.match(CAR_NO_REGEX);
          if (!carMatch) continue;

          // 헤더/라벨 행 제외 (차량번호 텍스트 자체인 경우)
          if (rowText.includes("차량번호") && !/\d{4}/.test(carMatch[0])) continue;

          const carNo = carMatch[0].replace(/\s+/g, '');
          const cells = Array.from(tr.querySelectorAll('td, th'));

          let carName = "";
          let modelYear = "";
          let buyPrice = 0;
          let etcFee;
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

          // Fallback: 차량명 추출
          if (!carName) {
            for (const cell of cells) {
              const txt = (cell.innerText || "").replace(/\n+/g, ' ').trim();
              if (/(현대|기아|제네시스|쉐보레|르노|쌍용|KGM|BMW|벤츠|아우디|볼보|폭스바겐|포르쉐|렉서스|카니발|아반떼|투싼|캐스퍼|쏘렌토|그랜저|스포티지|레이|모닝|스파크)/.test(txt)) {
                carName = txt;
                break;
              }
            }
          }

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
          const poInp = tr.querySelector('input[name*="poId"], input[name*="poIdList"], input[name*="chk"], input[type="checkbox"]');
          if (poInp && poInp.value && /^\d+$/.test(poInp.value.trim())) {
            poId = poInp.value.trim();
          } else {
            const mPo = (tr.innerHTML || "").match(/poId[=:\s'"]+(\d+)/i) ||
                        (tr.innerHTML || "").match(/poIdList[=:\s'"]+(\d+)/i) ||
                        (tr.innerHTML || "").match(/fn_detail\(['"]?(\d+)/i) ||
                        (tr.innerHTML || "").match(/goDetail\(['"]?(\d+)/i);
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
        console.log(`[J-PRO Scan] 감지된 차량: ${foundCars.length}대`, foundCars.map(c => c.carNumber));
        if (!foundCars.length) return;

        // 300ms 디바운스 일괄 전송 (getSysPo.do 수수료 추출과 함께 7대 1회 전송)
        let etcFeeSuccessCount = 0;
        let pendingFetches = 0;
        let debounceTimer = null;

        function scheduleDebouncedBatchSync(delay = 300) {
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            if (isContextAlive()) {
              const currentCars = Array.from(carMap.values());
              console.log(`[J-PRO AutoSync] 300ms 디바운스 완료 -> 매입 데이터 ${currentCars.length}대 1회 일괄 전송`);
              chrome.runtime.sendMessage({ action: 'sync_highplus_buy_data', data: currentCars });
            }
          }, delay);
        }

        // 기본 디바운스 예약 (fetch 지연되더라도 1회 전송 보장)
        scheduleDebouncedBatchSync(500);

        for (const car of foundCars) {
          const carNo = car.carNumber;
          if (!car.poId) {
            console.warn(`[J-PRO etcFee] 차량번호: ${carNo} | poId 없음 (추출 실패)`);
            continue;
          }

          if (car.etcFee !== undefined && car.etcFee > 0) {
            etcFeeSuccessCount++;
            continue;
          }

          pendingFetches++;
          fetch('https://admin.autoplus.co.kr/spot/syspo/getSysPo.do', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
              'X-Ajax-call': 'true'
            },
            body: `poId=${encodeURIComponent(car.poId)}`,
            credentials: 'include'
          })
            .then(async (r) => {
              const responseStatus = r.status;
              const rawText = await r.text();
              let parsedFee = 0;
              let parseDetail = "";

              // 1. JSON 응답 파싱 시도 (poAddExt 필드)
              try {
                const res = JSON.parse(rawText);
                if (res && res.data) {
                  const ext = res.data.poAddExt;
                  if (ext !== null && ext !== undefined && String(ext).trim() !== '') {
                    parsedFee = parseInt(String(ext).replace(/[^\d]/g, ''), 10) || 0;
                    parseDetail = `JSON(poAddExt=${ext})`;
                  } else {
                    parseDetail = "JSON(poAddExt 비어있음)";
                  }
                } else {
                  parseDetail = "JSON(res.data 없음)";
                }
              } catch (_) {
                // 2. HTML 응답 Fallback 파싱 시도
                parsedFee = extractEtcFeeFromHtml(rawText);
                parseDetail = parsedFee > 0 ? "HTML Fallback 파싱" : "HTML 파싱 실패";
              }

              console.log('[J-PRO etcFee] 차량번호:', carNo, '응답:', responseStatus, 'etcFee:', parsedFee, `(${parseDetail}, poId: ${car.poId})`);

              if (parsedFee > 0) {
                etcFeeSuccessCount++;
                if (car.etcFee !== parsedFee) {
                  car.etcFee = parsedFee;
                  scheduleDebouncedBatchSync(300);
                }
              }
            })
            .catch((err) => {
              console.error('[J-PRO etcFee] 차량번호:', carNo, '호출 실패:', err.message);
            })
            .finally(() => {
              pendingFetches--;
              if (pendingFetches === 0) {
                console.log(`[J-PRO etcFee] 기타비용 추출 집계: 성공 ${etcFeeSuccessCount}대 / 전체 ${foundCars.length}대`);
                if (etcFeeSuccessCount > 0) {
                  scheduleDebouncedBatchSync(50);
                }
              }
            });
        }
      } catch (err) {}
    }

    // ── 8. SPPOL10001 자동 검색 & 스마트 스캔 로직 ──
    function isAlreadySearched() {
      const CAR_NO_REGEX = /\d{2,3}[가-힣]\s*\d{4}/;
      const rows = Array.from(document.querySelectorAll('tr')).filter(tr => {
        const txt = tr.innerText || "";
        return CAR_NO_REGEX.test(txt) && !txt.includes("차량번호");
      });
      const mgrInput = document.querySelector('#searchPurManagerNm, input[name="searchPurManagerNm"]');
      const isMgrMatch = mgrInput ? mgrInput.value.includes('김재현') : true;
      return rows.length >= 1 && isMgrMatch;
    }

    function executeAutoSearchAndScan() {
      // 3. 이미 검색된 상태(차량 목록 표시 중)면 검색을 건너뛰고 바로 스캔
      if (isAlreadySearched()) {
        console.log('[J-PRO AutoSearch] 이미 검색 결과가 로드되어 있습니다. 검색 생략 후 즉시 스캔 실행');
        scanHighplusBuyData();
        return;
      }

      const dtInput = document.querySelector('#searchReturnDtSt, input[name="searchReturnDtSt"]');
      const mgrInput = document.querySelector('#searchPurManagerNm, input[name="searchPurManagerNm"]');

      if (dtInput) {
        dtInput.value = '2026-09-01';
        dtInput.dispatchEvent(new Event('input', { bubbles: true }));
        dtInput.dispatchEvent(new Event('change', { bubbles: true }));
      }

      if (mgrInput) {
        mgrInput.value = '김재현';
        mgrInput.dispatchEvent(new Event('input', { bubbles: true }));
        mgrInput.dispatchEvent(new Event('change', { bubbles: true }));
      }

      // 검색(조회) 버튼 탐색
      const searchBtn = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]')).find(el => {
        const txt = (el.innerText || el.value || '').trim();
        const onclick = el.getAttribute('onclick') || '';
        return (txt === '조회' || txt === '검색') || /search|조회|검색/i.test(onclick) || (el.id && el.id.toLowerCase().includes('search'));
      });

      // 무한 클릭 방지 sessionStorage 플래그 저장
      sessionStorage.setItem('jpro_auto_searched', 'true');

      if (searchBtn) {
        console.log('[J-PRO AutoSearch] 검색조건(2026-09-01, 김재현) 자동 입력 완료 -> 검색 버튼 자동 클릭');
        searchBtn.click();
      } else {
        const form = document.querySelector('form[name*="search"], form[action*="SPPOL10001"], form');
        if (form) {
          console.log('[J-PRO AutoSearch] 검색 버튼 미발견 -> form.submit() 실행');
          form.submit();
        } else {
          console.warn('[J-PRO AutoSearch] 검색 버튼/폼 미발견 -> 1초 대기 후 직접 스캔');
          setTimeout(scanHighplusBuyData, 1000);
          return;
        }
      }

      // AJAX 페이지 업데이트(리로드 없는 경우) 대비 DOM 관찰
      let ajaxTriggered = false;
      const observer = new MutationObserver(() => {
        if (!ajaxTriggered && isAlreadySearched()) {
          ajaxTriggered = true;
          observer.disconnect();
          console.log('[J-PRO AutoSearch] AJAX 검색 결과 로드 감지 -> 자동 스캔 실행');
          setTimeout(scanHighplusBuyData, 600);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
      setTimeout(() => observer.disconnect(), 6000);
    }

    // ── 9. 페이지 로드/새로고침 시 플래그 확인 (자동 검색으로 리로드된 경우 자동 스캔 1회 실행) ──
    if (sessionStorage.getItem('jpro_auto_searched') === 'true') {
      sessionStorage.removeItem('jpro_auto_searched'); // 1회성 소진
      console.log('[J-PRO AutoSearch] 자동 검색 후 결과 페이지 로드 감지 -> 결과 자동 스캔 실행');
      setTimeout(scanHighplusBuyData, 800);
    }

    // ── 10. [매입연동] 버튼 클릭 신호(triggerActiveAutoplusTabScan) 수신 시 실행 ──
    if (chrome && chrome.runtime && chrome.runtime.onMessage) {
      chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
        if (msg && (msg.action === 'triggerActiveAutoplusTabScan' || msg.action === 'trigger_scan')) {
          console.log('[J-PRO Scan] [매입연동] 버튼 신호 수신 -> 스마트 검색 & 스캔 파이프라인 가동');
          executeAutoSearchAndScan();
          sendResponse({ status: 'ok' });
        }
      });
    }

    // ── 일반 페이지 로드 시 무조건 자동 스캔은 영구 비활성화 ──
    // setTimeout(scanHighplusBuyData, 800);
    // window.__jproAutoplusScanTimer = setInterval(scanHighplusBuyData, 5000);
  }
})();


