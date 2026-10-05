/**
 * J-PRO 실시간 구글 스프레드시트 웹훅 연동 서비스
 * 대표님 전용 Google Apps Script Webhook:
 * https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec
 */

export const JPRO_GOOGLE_SHEET_WEBHOOK_URL = 
  "https://script.google.com/macros/s/AKfycbyFTXuPkC0R9y-UftHOFmJfgBwxycMwqOabhxKVT4bcsBK9gfsscQtGCTohzFiccq71/exec";

export interface GoogleSheetCarPayload {
  차량번호: string;
  제조사?: string;
  차량명?: string;
  세부모델?: string;
  연식?: string;
  주행거리?: string;
  옵션?: string;
  매입가?: number | string;
  판매가?: number | string;
  외판수리?: number;
  외판수리비?: number;
  헤딜수수료?: number;
  특이사항?: string;
  상태?: string;
  등록일?: string;
  [key: string]: any;
}

/**
 * 장부 차량 데이터를 구글 스프레드시트 웹훅으로 실시간 자동 전송
 */
export async function sendCarToGoogleSheet(payload: GoogleSheetCarPayload): Promise<{ success: boolean; message: string }> {
  try {
    // navigator.sendBeacon 또는 no-cors fetch로 Google Apps Script CORS 우회 전송
    const response = await fetch(JPRO_GOOGLE_SHEET_WEBHOOK_URL, {
      method: "POST",
      mode: "no-cors", // Google Apps Script Webhook은 302 리다이렉트되므로 no-cors가 표준
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    return {
      success: true,
      message: `[${payload.차량번호}] 구글 스프레드시트에 실시간 행 추가 완료!`
    };
  } catch (error: any) {
    console.error("[GoogleSheetService] 웹훅 전송 실패:", error);
    return {
      success: false,
      message: `구글 시트 전송 중 오류 발생: ${error?.message || error}`
    };
  }
}
