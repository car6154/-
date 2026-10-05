import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  onAuthStateChanged,
  User,
  signOut,
} from 'firebase/auth';
import firebaseConfig from '../../firebase-applet-config.json';

const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

const provider = new GoogleAuthProvider();
provider.addScope('https://www.googleapis.com/auth/drive.file');

let cachedAccessToken: string | null = null;
let isSigningIn = false;

export const initAuth = (
  onAuthSuccess?: (user: User, token: string) => void,
  onAuthFailure?: () => void
) => {
  return onAuthStateChanged(auth, async (user: User | null) => {
    if (user) {
      if (cachedAccessToken) {
        if (onAuthSuccess) onAuthSuccess(user, cachedAccessToken);
      } else if (!isSigningIn) {
        cachedAccessToken = null;
        if (onAuthFailure) onAuthFailure();
      }
    } else {
      cachedAccessToken = null;
      if (onAuthFailure) onAuthFailure();
    }
  });
};

export const googleSignIn = async (): Promise<{ user: User; accessToken: string } | null> => {
  try {
    isSigningIn = true;
    const result = await signInWithPopup(auth, provider);
    const credential = GoogleAuthProvider.credentialFromResult(result);
    if (!credential?.accessToken) {
      throw new Error('Google OAuth 액세스 토큰을 발급받지 못했습니다.');
    }
    cachedAccessToken = credential.accessToken;
    return { user: result.user, accessToken: cachedAccessToken };
  } catch (error: any) {
    console.error('Google 로그인 에러:', error);
    throw error;
  } finally {
    isSigningIn = false;
  }
};

export const getAccessToken = async (): Promise<string | null> => {
  return cachedAccessToken;
};

export const logout = async () => {
  await signOut(auth);
  cachedAccessToken = null;
};

/**
 * Upload a text file (e.g. Markdown or CSV) to Google Drive via multipart upload.
 */
export async function uploadFileToDrive(
  fileName: string,
  content: string,
  mimeType: string = 'text/markdown'
): Promise<{ id: string; name: string; webViewLink?: string }> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error('Google 로그인이 필요합니다. 먼저 로그인해 주세요.');
  }

  const metadata = {
    name: fileName,
    mimeType: mimeType,
    description: 'J-PRO 제이 대표님 13년 중고차 도메인 실무 기록 및 아키텍처 문서',
  };

  const boundary = '-------314159265358979323846';
  const delimiter = `\r\n--${boundary}\r\n`;
  const closeDelimiter = `\r\n--${boundary}--`;

  const multipartRequestBody =
    delimiter +
    'Content-Type: application/json; charset=UTF-8\r\n\r\n' +
    JSON.stringify(metadata) +
    delimiter +
    `Content-Type: ${mimeType}; charset=UTF-8\r\n\r\n` +
    content +
    closeDelimiter;

  const response = await fetch(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink',
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': `multipart/related; boundary=${boundary}`,
      },
      body: multipartRequestBody,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Google Drive 업로드 실패 (${response.status}): ${errorText}`);
  }

  return await response.json();
}

/**
 * Convert CarLedgerItem list into Jay's exact 10-column Google Sheet CSV format
 */
export function formatCarsToGoogleSheetCSV(cars: any[]): string {
  const headers = [
    '등록일', '차량번호', '제조사', '차량명', '세부모델', '연식', '주행거리', '매입가', '판매가', '특이사항'
  ];

  const rows = cars.map(c => [
    c.regDate || '',
    c.carNumber || '',
    c.manufacturer || '',
    c.carName || '',
    c.detailModel || '',
    c.year || '',
    `"${(c.mileage || '').replace(/"/g, '""')}"`,
    c.buyPrice ?? '',
    c.sellPrice ?? '',
    `"${(c.memo || '').replace(/"/g, '""')}"`
  ].join(','));

  return '\uFEFF' + [headers.join(','), ...rows].join('\n');
}

/**
 * Upload CSV content to Google Drive and convert directly into a native Google Sheets spreadsheet
 */
export async function uploadGoogleSheetToDrive(
  sheetTitle: string,
  csvContent: string
): Promise<{ id: string; name: string; webViewLink?: string }> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error('Google 로그인이 필요합니다. 먼저 로그인해 주세요.');
  }

  const metadata = {
    name: sheetTitle,
    mimeType: 'application/vnd.google-apps.spreadsheet',
    description: 'J-PRO 제이 대표님 전용 10컬럼 차량 원장 구글 스프레드시트 백업',
  };

  const boundary = '-------314159265358979323846';
  const delimiter = `\r\n--${boundary}\r\n`;
  const closeDelimiter = `\r\n--${boundary}--`;

  const multipartRequestBody =
    delimiter +
    'Content-Type: application/json; charset=UTF-8\r\n\r\n' +
    JSON.stringify(metadata) +
    delimiter +
    'Content-Type: text/csv; charset=UTF-8\r\n\r\n' +
    csvContent +
    closeDelimiter;

  const response = await fetch(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink',
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': `multipart/related; boundary=${boundary}`,
      },
      body: multipartRequestBody,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Google 스프레드시트 생성 실패 (${response.status}): ${errorText}`);
  }

  return await response.json();
}
