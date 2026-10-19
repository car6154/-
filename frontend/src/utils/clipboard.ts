/**
 * 클립보드 복사 유틸리티 (HTTP/HTTPS/iframe 환경 완벽 지원 fallback)
 * 1. navigator.clipboard.writeText 시도 (HTTPS / Secure Context)
 * 2. 실패 시 document.execCommand('copy') textarea fallback 시도
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false;

  // 1차 시도: 최신 navigator.clipboard API
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('[Clipboard] navigator.clipboard.writeText failed, falling back:', err);
    }
  }

  // 2차 시도: 레거시 execCommand fallback (HTTP 환경, 권한 차단 환경 등)
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    // 화면에 보이지 않도록 스타일링하되 포커스 가능하도록 처리
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.width = '2em';
    textArea.style.height = '2em';
    textArea.style.padding = '0';
    textArea.style.border = 'none';
    textArea.style.outline = 'none';
    textArea.style.boxShadow = 'none';
    textArea.style.background = 'transparent';
    textArea.style.opacity = '0';
    textArea.setAttribute('readonly', '');

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, text.length);

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    if (successful) {
      return true;
    }
  } catch (err) {
    console.error('[Clipboard] document.execCommand fallback failed:', err);
  }

  return false;
}
