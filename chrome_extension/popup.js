document.getElementById('syncBtn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  const btn = document.getElementById('syncBtn');
  
  btn.disabled = true;
  statusDiv.textContent = '쿠키 추출 중...';
  statusDiv.className = '';

  try {
    // heydealer.com 관련 모든 쿠키 수집
    const cookies1 = await chrome.cookies.getAll({ domain: 'heydealer.com' });
    const cookies2 = await chrome.cookies.getAll({ domain: 'api.heydealer.com' });
    const cookies3 = await chrome.cookies.getAll({ domain: 'dealer.heydealer.com' });

    const allMap = new Map();
    [...cookies1, ...cookies2, ...cookies3].forEach(c => {
      if (c.name && c.value) {
        allMap.set(c.name, c.value);
      }
    });

    if (allMap.size === 0) {
      statusDiv.textContent = '❌ 헤이딜러 쿠키가 없습니다. 먼저 헤이딜러에 로그인해주세요!';
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
        statusDiv.textContent = '✅ 쿠키 연동 완료! 프로그램에 자동 적용되었습니다.';
        statusDiv.className = 'success';
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
    const cookies = await chrome.cookies.getAll({ domain: 'heydealer.com' });
    const allMap = new Map();
    cookies.forEach(c => { if (c.name && c.value) allMap.set(c.name, c.value); });
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
