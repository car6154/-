const syncBtn = document.getElementById('syncBtn');
const statusDiv = document.getElementById('status');

syncBtn.addEventListener('click', () => {
  statusDiv.innerHTML = '동기화 진행 중...';
  chrome.runtime.sendMessage({ action: 'SYNC_NOW' }, (response) => {
    if (response && response.success) {
      statusDiv.innerHTML = `<span class="success">✅ 세션 ${response.count}개 전송 완료!</span>`;
    } else {
      statusDiv.innerHTML = `<span class="error">❌ 전송 실패: ${response ? response.message : '알 수 없는 오류'}</span>`;
    }
  });
});
