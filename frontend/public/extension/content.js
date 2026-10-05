// J-PRO Content Script for HeyDealer Dealer Web
(function () {
  console.log('[J-PRO Extension] HeyDealer Content Script 활성화');

  const SECRET_TOKEN = 'jpro_sec_9981_live_auth';
  const SERVER_URL = 'https://ais-dev-2br46rkotrokqfzdwk6oxg-839480298953.asia-east1.run.app';

  // 1. LocalStorage & Session 동기화
  function syncTokens() {
    try {
      const authData = localStorage.getItem('heydealer-dealer-web:auth');
      const allKeys = Object.keys(localStorage);
      const storageDump = {};
      allKeys.forEach(k => {
        storageDump[k] = localStorage.getItem(k);
      });

      chrome.runtime.sendMessage({
        action: 'STORAGE_DUMP',
        data: { authData, storageDump }
      });
    } catch (e) {
      console.warn('[J-PRO] 스토리지 추출 실패:', e);
    }
  }

  syncTokens();

  // 2. 헤이딜러 차량 페이지에 [J-PRO ERP 1초 전송] 플로팅 버튼 생성
  function injectFloatingButton() {
    if (document.getElementById('jpro-quick-btn')) return;
    if (!window.location.pathname.includes('/cars/')) return;

    const btn = document.createElement('div');
    btn.id = 'jpro-quick-btn';
    btn.innerHTML = `
      <div style="
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 999999;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 14px 20px;
        border-radius: 9999px;
        box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', sans-serif;
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: transform 0.2s, box-shadow 0.2s;
      ">
        <span style="font-size: 18px;">⚡</span>
        <span>J-PRO ERP로 가져오기</span>
      </div>
    `;

    btn.addEventListener('mouseenter', () => {
      btn.firstElementChild.style.transform = 'translateY(-2px) scale(1.03)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.firstElementChild.style.transform = 'translateY(0) scale(1)';
    });

    btn.addEventListener('click', async () => {
      const hashId = window.location.pathname.split('/cars/')[1]?.replace('/', '');
      btn.firstElementChild.innerHTML = '<span>⏳ 분석 및 전송 중...</span>';

      // 페이지 데이터 추출
      const titleEl = document.querySelector('h1') || document.querySelector('[class*="title"]') || document.querySelector('[class*="carName"]');
      const carTitle = titleEl ? titleEl.innerText : document.title;

      // 새 탭으로 J-PRO 열기 (URL 파라미터로 즉시 열기)
      const targetUrl = `${SERVER_URL}/?hashId=${hashId || ''}&title=${encodeURIComponent(carTitle)}`;
      window.open(targetUrl, '_blank');
      btn.firstElementChild.innerHTML = '<span>⚡ J-PRO ERP로 가져오기</span>';
    });

    document.body.appendChild(btn);
  }

  // DOM 로드 및 URL 변경 감지
  setInterval(injectFloatingButton, 1000);
})();
