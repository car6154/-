import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  Cloud, 
  Download, 
  CheckCircle, 
  AlertTriangle, 
  ExternalLink, 
  FileText, 
  Database,
  Upload,
  FileSpreadsheet,
  ShieldCheck,
  Check
} from 'lucide-react';
import { 
  initAuth, 
  googleSignIn, 
  logout, 
  uploadFileToDrive, 
  uploadGoogleSheetToDrive,
  formatCarsToGoogleSheetCSV 
} from '../services/driveService';
import type { User } from 'firebase/auth';
import { CarLedgerItem, InventorySettlementItem } from '@/types';

interface DriveModalProps {
  isOpen: boolean;
  onClose: () => void;
  cars?: CarLedgerItem[];
  settlementItems?: InventorySettlementItem[];
  onRestoreLedger?: (restoredCars: CarLedgerItem[], restoredSettlement?: InventorySettlementItem[]) => void;
}

const INTERVIEW_CONTENT = `# [J-PRO] 제이 대표님 13년 중고차 실무 도메인 인터뷰 & 설계 철학 기록

## 1. 개요 및 인물 소개
- 대상자: 제이 대표 (오토플러스 / 리본카 13년차 베테랑 매입 딜러 & 프로덕트 총괄)
- 개발 배경:
  - 코딩 언어를 직접 작성하지 못하나, 생성형 AI(Gemini Pro/Flash, Antigravity IDE)를 실무 PM처럼 직접 지휘하여 J-PRO 시스템을 자체 개발.
  - 기존 로컬 Python/Streamlit 환경에서 16,000줄 규모로 비대화되면서 발생한 토큰 소모 및 PC 종속성 문제를 해결하고, 24시간 안정적인 프로덕션 클라우드 환경으로 전환.

## 2. 13년 현장 도메인 핵심 알고리즘 및 노하우
### 1) 4대 앵커 가격 산출 매트릭스
1. 헤이딜러 20대 낙찰가 데이터: 실시간 경매 낙찰 표본을 추출하여 도매 바닥가 파악.
2. 엔카 실시간 소매 매물 13대 분석: 허위/미끼 및 과장 호가를 배제하고 실시간 등록 매물 수집.
3. 1차 다항식 회귀선 (np.polyfit) 산점도: 주행거리(X축)와 소매가격(Y축)의 회귀 추세선을 도출하여 진짜 적정 소매가를 수치화.
4. 오토플러스 6,170건 내수 완판 실적 DB: 자사 실현 평균 마진(100만원) 및 평균 재고 회전일수(18일) 데이터를 앵커로 대조 검증.

### 2) 20(21)년식 형식년도 감가 갭 보정
- 등록일자와 형식년도가 불일치할 때 발생하는 소매 호가 감가 왜곡을 사전 보정.
- 90일 이상 장기재고 감가 갭 자동 반영.

### 3) 2D 외판/골격 실비 감가 엔진
- 외판 판당 도색/판금: 판당 130,000원
- 문콕/덴트: 개당 50,000원
- 휠 스크래치 복원: 개당 50,000원
- 골격/사고 감가: 인사이드 패널, 사이드멤버, 하우스 등 주요 골격 사고 시 50~150만원 감가 가산.

## 3. 6대 라이프사이클 워룸 구성
1. [시세 분석]: 헤이딜러 URL 파싱, 4대 앵커 시세 산출, 1차 다항식 산점도, 2D 외판 도면 감가, 안전 매입 상한선 계산.
2. [매입 장부]: 125대 규모의 실시간 매입 진행 장부 (매입원가, 탁송비, 부대비용, 목표 판매가).
3. [재고 및 정산]: 보유 일수(Aging) 트래킹, 90일 장기재고 위험 알림, 재고 금융 이자 반영.
4. [판매완료 정산]: 최종 실현 마진, 부대비용 및 상사비 정산, 실현 ROI 분석.
5. [자사 판매 실적]: 오토플러스 6,170건 실적 DB 필터 및 검색 (차종별 최적 회전율 분석).
6. [자사 보유 재고]: 오토플러스 실시간 자사 재고 현황 및 가격 포지셔닝.
`;

export const DriveModal: React.FC<DriveModalProps> = ({ 
  isOpen, 
  onClose,
  cars = [],
  settlementItems = [],
  onRestoreLedger
}) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccessLink, setUploadSuccessLink] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sheet' | 'interview'>('sheet');
  const [restoreSuccessMsg, setRestoreSuccessMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const unsubscribe = initAuth(
      (user) => setCurrentUser(user),
      () => setCurrentUser(null)
    );
    return () => unsubscribe();
  }, []);

  if (!isOpen) return null;

  const handleLogin = async () => {
    setIsLoggingIn(true);
    setErrorMsg(null);
    try {
      const res = await googleSignIn();
      if (res) {
        setCurrentUser(res.user);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Google 로그인에 실패했습니다.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setCurrentUser(null);
    setUploadSuccessLink(null);
  };

  // Google Drive에 진짜 구글 스프레드시트(.gsheet) 문서로 백업 업로드
  const handleUploadGoogleSheet = async () => {
    setIsUploading(true);
    setErrorMsg(null);
    setUploadSuccessLink(null);

    try {
      const todayStr = new Date().toISOString().slice(0, 10);
      const sheetTitle = `JPRO_차량원장_구글스프레드시트_${todayStr}`;
      const csvContent = formatCarsToGoogleSheetCSV(cars);

      const res = await uploadGoogleSheetToDrive(sheetTitle, csvContent);
      setUploadSuccessLink(res.webViewLink || `https://drive.google.com/file/d/${res.id}/view`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Google 스프레드시트 생성 중 오류가 발생했습니다.');
    } finally {
      setIsUploading(false);
    }
  };

  // Google Drive에 전체 원장 JSON 백업 파일 업로드
  const handleUploadLedgerJsonToDrive = async () => {
    setIsUploading(true);
    setErrorMsg(null);
    setUploadSuccessLink(null);

    try {
      const todayStr = new Date().toISOString().slice(0, 10);
      const fileName = `JPRO_차량원장_정산_백업_${todayStr}.json`;
      const backupPayload = JSON.stringify({
        version: '3.0',
        exportedAt: new Date().toISOString(),
        totalCars: cars.length,
        totalSettlement: settlementItems.length,
        cars,
        settlementItems
      }, null, 2);

      const res = await uploadFileToDrive(fileName, backupPayload, 'application/json');
      setUploadSuccessLink(res.webViewLink || `https://drive.google.com/file/d/${res.id}/view`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Google Drive 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsUploading(false);
    }
  };

  // 내 PC로 제이 대표님 전용 10컬럼 구글 시트 규격 CSV 다운로드
  const handleDownloadSheetCSV = () => {
    const todayStr = new Date().toISOString().slice(0, 10);
    const csvContent = formatCarsToGoogleSheetCSV(cars);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `JPRO_차량원장_구글시트규격_${todayStr}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 내 PC로 원장 JSON 전체 백업 다운로드
  const handleDownloadLedgerJSON = () => {
    const todayStr = new Date().toISOString().slice(0, 10);
    const backupPayload = JSON.stringify({
      version: '3.0',
      exportedAt: new Date().toISOString(),
      totalCars: cars.length,
      totalSettlement: settlementItems.length,
      cars,
      settlementItems
    }, null, 2);

    const blob = new Blob([backupPayload], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `JPRO_차량원장_전체백업_${todayStr}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 백업 파일(CSV 또는 JSON) 업로드로 원장 복원
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;

        // 1. JSON 형식인 경우
        if (file.name.endsWith('.json')) {
          const data = JSON.parse(text);
          if (Array.isArray(data)) {
            if (confirm(`백업 파일에서 ${data.length}대의 차량 데이터를 복원하시겠습니까?`)) {
              if (onRestoreLedger) onRestoreLedger(data);
              setRestoreSuccessMsg(`성공적으로 ${data.length}대의 차량 데이터를 복원했습니다.`);
            }
          } else if (data.cars && Array.isArray(data.cars)) {
            const carCount = data.cars.length;
            const settCount = Array.isArray(data.settlementItems) ? data.settlementItems.length : 0;
            if (confirm(`백업 파일에서 차량 ${carCount}대, 정산 ${settCount}건을 복원하시겠습니까?`)) {
              if (onRestoreLedger) onRestoreLedger(data.cars, data.settlementItems);
              setRestoreSuccessMsg(`성공적으로 차량 ${carCount}대와 정산 데이터를 복원했습니다.`);
            }
          }
          return;
        }

        // 2. CSV 형식인 경우 (대표님의 10컬럼 규격)
        const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
        if (lines.length <= 1) {
          alert('CSV 데이터가 비어 있습니다.');
          return;
        }

        const parsedCars: CarLedgerItem[] = [];
        // Header 확인 (lines[0])
        for (let i = 1; i < lines.length; i++) {
          const line = lines[i];
          // 간단한 CSV 파싱 (따옴표 고려)
          const parts = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || line.split(',');
          if (parts.length >= 7) {
            const clean = (val: string) => (val || '').replace(/^"|"$/g, '').trim();
            const regDate = clean(parts[0]);
            const carNumber = clean(parts[1]);
            const manufacturer = clean(parts[2]);
            const carName = clean(parts[3]);
            const detailModel = clean(parts[4]);
            const year = clean(parts[5]);
            const mileage = clean(parts[6]);
            const buyPrice = Number(clean(parts[7])) || 0;
            const sellPrice = Number(clean(parts[8])) || 0;
            const memo = clean(parts[9] || '');

            parsedCars.push({
              id: `car_csv_${Date.now()}_${i}_${carNumber}`,
              regDate,
              carNumber,
              manufacturer,
              carName,
              detailModel,
              year,
              mileage,
              options: '',
              buyPrice,
              sellPrice,
              outerRepairs: 0,
              repairCost: 0,
              heydealerFee: 25.0,
              memo,
              status: '장부저장'
            });
          }
        }

        if (parsedCars.length > 0) {
          if (confirm(`구글 시트 CSV 파일에서 총 ${parsedCars.length}대의 차량을 원장에 복원/적용하시겠습니까?`)) {
            if (onRestoreLedger) onRestoreLedger(parsedCars);
            setRestoreSuccessMsg(`성공적으로 ${parsedCars.length}대의 구글 시트 원장 데이터를 복원했습니다.`);
          }
        } else {
          alert('CSV 데이터를 파싱하지 못했습니다. 형식을 확인해 주세요.');
        }

      } catch (err) {
        alert('백업 파일을 파싱하는 데 실패했습니다. 파일 내용을 확인해 주세요.');
      }
    };
    reader.readAsText(file, 'utf-8');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#12161F] border border-slate-700/80 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                Google Sheets & 원장 백업 보관함
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  10컬럼 시트 표준 규격
                </span>
              </h2>
              <p className="text-xs text-slate-400">제이 대표님 전용 구글 시트 자동 변환 및 클라우드 영구 백업</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 text-xs px-6 pt-2">
          <button
            onClick={() => setActiveTab('sheet')}
            className={`pb-2.5 px-3 font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'sheet'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>구글 스프레드시트 실시간 백업</span>
          </button>
          <button
            onClick={() => setActiveTab('interview')}
            className={`pb-2.5 px-3 font-semibold border-b-2 flex items-center gap-2 transition ${
              activeTab === 'interview'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>도메인 인터뷰 & 설계 기록</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm">
          
          {/* TAB 1: 구글 스프레드시트 백업 */}
          {activeTab === 'sheet' && (
            <div className="space-y-4">
              
              {/* 10-Column Standard Preview Box */}
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-emerald-900/40 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                    <Check className="w-3.5 h-3.5" />
                    <span>대표님 구글 스프레드시트 10개 표준 컬럼 일치</span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    현재 {cars.length}대 차량 보관 중
                  </span>
                </div>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[10.5px] font-mono text-slate-300 overflow-x-auto whitespace-nowrap leading-relaxed">
                  등록일 | 차량번호 | 제조사 | 차량명 | 세부모델 | 연식 | 주행거리 | 매입가 | 판매가 | 특이사항
                </div>
              </div>

              {/* Restore Alert */}
              {restoreSuccessMsg && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2 text-emerald-400 text-xs">
                  <CheckCircle className="w-4 h-4 shrink-0" />
                  <span>{restoreSuccessMsg}</span>
                </div>
              )}

              {/* Google Drive Sheet Upload */}
              <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cloud className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-white">Google Drive에 "구글 시트(스프레드시트)"로 즉시 생성</span>
                  </div>
                  {currentUser && (
                    <span className="text-[11px] text-slate-400">{currentUser.email}</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  구글 드라이브에 파일을 올리면 단순 파일이 아니라 **더블클릭해 바로 웹에서 열고 수정할 수 있는 정식 구글 스프레드시트(녹색 아이콘)** 문서로 자동 생성됩니다.
                </p>

                {!currentUser ? (
                  <button
                    onClick={handleLogin}
                    disabled={isLoggingIn}
                    className="w-full inline-flex items-center justify-center gap-2.5 py-2.5 rounded-lg bg-white hover:bg-slate-100 text-slate-800 font-semibold text-xs shadow-md transition disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 48 48">
                      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                    </svg>
                    {isLoggingIn ? '구글 연결 중...' : 'Google 로그인하고 구글 시트 연동'}
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={handleUploadGoogleSheet}
                      disabled={isUploading}
                      className="flex-1 py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 transition disabled:opacity-50"
                    >
                      <FileSpreadsheet className="w-4 h-4" />
                      {isUploading ? '구글 시트 생성 중...' : 'Google 스프레드시트로 지금 백업'}
                    </button>
                    <button
                      onClick={handleLogout}
                      className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
                    >
                      로그아웃
                    </button>
                  </div>
                )}
              </div>

              {/* Action 2: PC Local CSV & JSON Backup */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-white">
                  <Download className="w-4 h-4 text-[#cc9166]" />
                  <span>내 PC로 파일 즉시 저장</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleDownloadSheetCSV}
                    className="p-2.5 rounded-lg bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-xs font-medium text-slate-200 flex items-center justify-center gap-2 transition"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                    <span>구글시트 규격 CSV 다운로드</span>
                  </button>
                  <button
                    onClick={handleDownloadLedgerJSON}
                    className="p-2.5 rounded-lg bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-xs font-medium text-slate-200 flex items-center justify-center gap-2 transition"
                  >
                    <Database className="w-4 h-4 text-blue-400" />
                    <span>전체 백업본(JSON) 저장</span>
                  </button>
                </div>
              </div>

              {/* Action 3: Restore from File (CSV or JSON) */}
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-white">
                    <Upload className="w-4 h-4 text-amber-400" />
                    <span>구글 시트 CSV 또는 JSON 백업 파일로 원장 복원</span>
                  </div>
                  <span className="text-[10px] text-slate-400">CSV/JSON 지원</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  대표님께서 갖고 계신 구글 시트 백업 CSV 파일이나 JSON 파일을 선택하면 장부에 즉시 복원 적용됩니다.
                </p>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".csv,.json"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs flex items-center justify-center gap-2 border border-slate-700 transition"
                >
                  <Upload className="w-4 h-4 text-amber-400" />
                  <span>백업 파일(CSV/JSON) 선택하여 원장 복원하기</span>
                </button>
              </div>

            </div>
          )}

          {/* TAB 2: 도메인 인터뷰 & 설계 기록 */}
          {activeTab === 'interview' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-200 text-sm">
                        J-PRO_제이대표님_도메인_인터뷰_설계기록.md
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        4대 앵커 시세, 1차 다항식 회귀선, 125대 장부, 클린 아키텍처 원칙
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] px-2 py-1 rounded bg-slate-800 text-slate-300 font-mono">
                    Markdown
                  </span>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                  <span className="text-slate-400">문서 크기: 약 3.8 KB (전문 보존)</span>
                  <button
                    onClick={() => {
                      const blob = new Blob([INTERVIEW_CONTENT], { type: 'text/markdown;charset=utf-8' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `J-PRO_제이대표님_도메인_인터뷰_기록_${new Date().toISOString().slice(0, 10)}.md`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                    }}
                    className="text-blue-400 hover:text-blue-300 flex items-center gap-1.5 font-medium hover:underline"
                  >
                    <Download className="w-3.5 h-3.5" />
                    PC로 다운로드
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Upload Success Link */}
          {uploadSuccessLink && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3 text-emerald-400">
              <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-semibold text-xs">Google 스프레드시트 생성이 완료되었습니다!</p>
                <p className="text-[11px] text-slate-300">내 구글 드라이브에 안전하게 새 시트가 생성되었습니다.</p>
                <a
                  href={uploadSuccessLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-300 underline hover:text-emerald-200 mt-1"
                >
                  새 탭에서 Google 스프레드시트 바로 열기
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-400 text-xs">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>제이 대표님 10컬럼 구글 시트 백업 포맷 100% 호환</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
};
