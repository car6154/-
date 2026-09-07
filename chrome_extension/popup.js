document.getElementById('syncBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncBtn');
  
  btn.disabled = true;
  statusDiv.textContent = '쿠키 추출 중...';
  statusDiv.className = '';

  try {
    // heydealer.com 관련 모든 쿠키 수집 (url 방식 및 domain 방식 모두 병합)
    const [cUrl1, cUrl2, cUrl3, cDom1, cDom2, cDom3] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://dealer.heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://api.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'heydealer.com' }),
      chrome.cookies.getAll({ domain: '.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'dealer.heydealer.com' })
    ]);

    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cDom1, ...cDom2, ...cDom3].forEach(c => {
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 헤이딜러 쿠키를 찾지 못했습니다. 헤이딜러 창을 열고 로그인해주세요!';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');

    // 로컬 수신 서버로 전송
    statusDiv.textContent = 'J-PRO 프로그램으로 전송 중...';
    try {
      const response = await fetch('http://localhost:8502/api/save_cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookie: cookieStr })
      });

      if (response.ok) {
        statusDiv.textContent = '✅ 쿠키 연동 완료! J-PRO 화면을 새로고침합니다...';
        statusDiv.className = 'success';
        
        // 열려있는 J-PRO(Streamlit) 탭 자동 새로고침
        if (chrome.tabs) {
          chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
              if (tab.url && (tab.url.includes('localhost:8501') || tab.url.includes('127.0.0.1:8501'))) {
                chrome.tabs.reload(tab.id);
              }
            });
          });
        }
        return;
      }
    } catch (netErr) {
      // 서버 전송 실패 시 클립보드 복사로 자동 폴백
      await navigator.clipboard.writeText(cookieStr);
      statusDiv.textContent = '📋 쿠키가 복사되었습니다! (입력창에 붙여넣기하세요)';
      statusDiv.className = 'success';
      return;
    }
    statusDiv.textContent = '⚠️ 전송 실패: 수신 서버 상태를 확인해주세요.';
    statusDiv.className = 'error';
  } catch (err) {
    statusDiv.textContent = '❌ 오류: ' + err.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('copyBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  try {
    const [cUrl1, cUrl2, cUrl3, cDom1, cDom2, cDom3] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://dealer.heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://heydealer.com' }),
      chrome.cookies.getAll({ url: 'https://api.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'heydealer.com' }),
      chrome.cookies.getAll({ domain: '.heydealer.com' }),
      chrome.cookies.getAll({ domain: 'dealer.heydealer.com' })
    ]);
    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cDom1, ...cDom2, ...cDom3].forEach(c => {
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 헤이딜러 쿠키가 없습니다.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    statusDiv.textContent = '📋 클립보드 복사 완료! (Ctrl+V로 붙여넣기)';
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});
