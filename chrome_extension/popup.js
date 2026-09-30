// 헤이딜러 쿠키 전송
document.getElementById('syncBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncBtn');
  
  btn.disabled = true;
  statusDiv.textContent = '헤이딜러 쿠키 추출 중...';
  statusDiv.className = '';

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
      if (c && c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 헤이딜러 쿠키를 찾지 못했습니다.<br><a href="https://dealer.heydealer.com" target="_blank" style="color:#38bdf8;">헤이딜러 로그인 열기</a>';
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
        body: JSON.stringify({ cookie: cookieStr, target: 'heydealer' })
      });

      if (response.ok) {
        statusDiv.textContent = '✅ 헤이딜러 쿠키 연동 완료! J-PRO 화면을 새로고침합니다...';
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
      statusDiv.textContent = '📋 쿠키가 복사되었습니다! (상단 🔑설정에 붙여넣기하세요)';
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

// 헤이딜러 쿠키 복사 버튼
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

// 차얼마(오토플러스) 쿠키 수동 동기화 버튼
document.getElementById('syncApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncApBtn');
  btn.disabled = true;
  statusDiv.textContent = '차얼마 쿠키 추출 중...';
  statusDiv.className = '';

  try {
    const [cUrl1, cUrl2, cUrl3, cUrl4, cDom1, cDom2, cDom3, cDom4] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'http://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/purchase/PCVP010001' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/login/login.do' }),
      chrome.cookies.getAll({ domain: 'purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.autoplus.co.kr' })
    ]);

    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cUrl4, ...cDom1, ...cDom2, ...cDom3, ...cDom4].forEach(c => {
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });

    if (allMap.size === 0) {
      statusDiv.innerHTML = '❌ 차얼마 로그인 쿠키를 찾지 못했습니다.<br><a href="https://purchase.autoplus.co.kr/login/login.do" target="_blank" style="color:#38bdf8;">차얼마 로그인 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    // 로그인 세션 쿠키(JSESSIONID 또는 remember-me) 필수 체크
    const hasSession = Array.from(allMap.keys()).some(k => {
      const u = k.toUpperCase();
      return u === 'JSESSIONID' || u === 'REMEMBER-ME';
    });

    if (!hasSession) {
      statusDiv.innerHTML = '⚠️ <b>로그인 세션이 없습니다!</b><br>차얼마(purchase.autoplus.co.kr)에 먼저 로그인해주세요.<br><a href="https://purchase.autoplus.co.kr/login/login.do" target="_blank" style="color:#38bdf8; text-decoration:underline; font-size:12px; display:inline-block; margin-top:4px;">🔗 차얼마 로그인 창 열기</a>';
      statusDiv.className = 'error';
      btn.disabled = false;
      return;
    }

    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    
    // 클립보드에도 자동 복사해둠
    try { await navigator.clipboard.writeText(cookieStr); } catch (_) {}

    try {
      const res = await fetch('http://localhost:8502/api/save_cookie', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookie: cookieStr, target: 'autoplus' })
      });

      if (res.ok) {
        statusDiv.textContent = '✅ 차얼마 쿠키 연동 성공! J-PRO 화면을 새로고침합니다...';
        statusDiv.className = 'success';
        
        // 열려있는 J-PRO 탭 자동 새로고침
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
      statusDiv.textContent = '📋 쿠키가 복사되었습니다! (상단 🔑설정에 붙여넣기하세요)';
      statusDiv.className = 'success';
      return;
    }

    statusDiv.textContent = '⚠️ 전송 실패 (J-PRO 실행 여부 확인)';
    statusDiv.className = 'error';
  } catch (e) {
    statusDiv.textContent = '❌ 오류: ' + e.message;
    statusDiv.className = 'error';
  } finally {
    btn.disabled = false;
  }
});

// 차얼마 쿠키 복사 버튼
document.getElementById('copyApBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  try {
    const [cUrl1, cUrl2, cUrl3, cUrl4, cDom1, cDom2, cDom3, cDom4] = await Promise.all([
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'http://purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/purchase/PCVP010001' }),
      chrome.cookies.getAll({ url: 'https://purchase.autoplus.co.kr/login/login.do' }),
      chrome.cookies.getAll({ domain: 'purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.purchase.autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: 'autoplus.co.kr' }),
      chrome.cookies.getAll({ domain: '.autoplus.co.kr' })
    ]);
    const allMap = new Map();
    [...cUrl1, ...cUrl2, ...cUrl3, ...cUrl4, ...cDom1, ...cDom2, ...cDom3, ...cDom4].forEach(c => {
      if (c && c.name && c.value) allMap.set(c.name, c.value);
    });
    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 차얼마 쿠키를 찾지 못했습니다.';
      statusDiv.className = 'error';
      return;
    }
    const hasSession = Array.from(allMap.keys()).some(k => {
      const u = k.toUpperCase();
      return u === 'JSESSIONID' || u === 'REMEMBER-ME';
    });
    if (!hasSession) {
      statusDiv.innerHTML = '⚠️ <b>로그인 세션이 없습니다!</b> 차얼마에 먼저 로그인해주세요.';
      statusDiv.className = 'error';
      return;
    }
    const cookieStr = Array.from(allMap.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
    await navigator.clipboard.writeText(cookieStr);
    statusDiv.textContent = '📋 차얼마 쿠키 복사 완료! (상단 🔑설정에 붙여넣기)';
    statusDiv.className = 'success';
  } catch (e) {
    statusDiv.textContent = '❌ 복사 실패: ' + e.message;
    statusDiv.className = 'error';
  }
});


