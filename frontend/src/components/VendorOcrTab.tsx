import React, { useState, useRef, useEffect } from 'react';
import {
  Upload,
  Camera,
  Copy,
  Check,
  Download,
  AlertCircle,
  FileText,
  Building,
  User,
  Car,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Clock,
  ShieldCheck,
} from 'lucide-react';

interface OCRResult {
  document_type: 'BIZ' | 'SEAL' | 'CAR' | 'UNKNOWN';
  document_label: string;
  vendor_type: 'business' | 'individual';
  fields: {
    // 사업자등록증
    business_number?: string;
    company_name?: string;
    representative_name?: string;
    business_type?: string;
    business_item?: string;
    // 인감증명서 / 자동차등록증 공통
    name?: string;
    owner_name?: string;
    resident_number?: string;
    // 주소
    address?: string;
    base_address?: string;
    detail_address?: string;
    // 자동차등록증
    car_number?: string;
    car_name?: string;
    vin?: string;
  };
  elapsed_sec: number;
  raw_texts: string[];
}

export const VendorOcrTab: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<'IDLE' | 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'>('IDLE');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [elapsedTimer, setElapsedTimer] = useState<number>(0);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [showRawTexts, setShowRawTexts] = useState<boolean>(false);

  // 파싱 결과 및 편집 가능한 필드 상태
  const [vendorType, setVendorType] = useState<'business' | 'individual'>('business');
  const [docLabel, setDocLabel] = useState<string>('');
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [rawTexts, setRawTexts] = useState<string[]>([]);
  const [actualElapsed, setActualElapsed] = useState<number | null>(null);

  const [formFields, setFormFields] = useState<{ [key: string]: string }>({
    business_number: '',
    company_name: '',
    representative_name: '',
    business_type: '',
    business_item: '',
    name: '',
    resident_number: '',
    base_address: '',
    detail_address: '',
    car_number: '',
    car_name: '',
    vin: '',
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<any>(null);

  // 경과 시간 타이머
  useEffect(() => {
    if (status === 'PROCESSING' || status === 'UPLOADING') {
      timerRef.current = setInterval(() => {
        setElapsedTimer((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status]);

  // 상태 폴링 (작업 진행 중일 때 1.5초마다 조회)
  useEffect(() => {
    if (!taskId || status !== 'PROCESSING') return;

    let isSubscribed = true;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/ocr/status/${taskId}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();

        if (!isSubscribed) return;

        if (data.status === 'COMPLETED') {
          setStatus('COMPLETED');
          const result: OCRResult = data.data;
          setDocLabel(result.document_label || '미분류 서류');
          setVendorType(result.vendor_type || 'business');
          setDownloadUrl(data.download_url || null);
          setRawTexts(result.raw_texts || []);
          setActualElapsed(result.elapsed_sec || null);

          // 필드 채우기
          const f = result.fields || {};
          setFormFields({
            business_number: f.business_number || '',
            company_name: f.company_name || '',
            representative_name: f.representative_name || f.name || f.owner_name || '',
            business_type: f.business_type || '',
            business_item: f.business_item || '',
            name: f.name || f.owner_name || f.representative_name || '',
            resident_number: f.resident_number || '',
            base_address: f.base_address || '',
            detail_address: f.detail_address || '',
            car_number: f.car_number || '',
            car_name: f.car_name || '',
            vin: f.vin || '',
          });
        } else if (data.status === 'FAILED') {
          setStatus('FAILED');
          setErrorMsg(data.error || 'OCR 분석 중 오류가 발생했습니다.');
        }
      } catch (err: any) {
        console.error('OCR polling error:', err);
      }
    }, 1500);

    return () => {
      isSubscribed = false;
      clearInterval(interval);
    };
  }, [taskId, status]);

  // 파일 선택 및 업로드 핸들러
  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);
    setPreviewUrl(URL.createObjectURL(selectedFile));
    setStatus('UPLOADING');
    setErrorMsg(null);
    setElapsedTimer(0);
    setTaskId(null);
    setDownloadUrl(null);
    setRawTexts([]);
    setDocLabel('');
    setActualElapsed(null);
    // 새 업로드 시작 시 이전 결과 필드 전부 초기화
    setFormFields({
      business_number: '',
      company_name: '',
      representative_name: '',
      business_type: '',
      business_item: '',
      name: '',
      resident_number: '',
      base_address: '',
      detail_address: '',
      car_number: '',
      car_name: '',
      vin: '',
    });

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch('/api/ocr/vendor', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `업로드 실패 (${res.status})`);
      }

      const data = await res.json();
      setTaskId(data.task_id);
      setStatus('PROCESSING');
    } catch (err: any) {
      setStatus('FAILED');
      setErrorMsg(err.message || '파일 업로드 중 오류가 발생했습니다.');
    }
  };

  // 단일 필드 복사
  const handleCopyField = (key: string, value: string) => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  // 전체 복사 (인트라넷 기입용 요약 텍스트)
  const handleCopyAll = () => {
    let summary = '';
    if (vendorType === 'business') {
      summary = [
        `[거래처구분] 사업자`,
        `[사업자등록번호] ${formFields.business_number}`,
        `[상호명] ${formFields.company_name}`,
        `[대표자명] ${formFields.representative_name}`,
        `[기본주소] ${formFields.base_address}`,
        `[상세주소] ${formFields.detail_address}`,
        `[업태] ${formFields.business_type}`,
        `[종목] ${formFields.business_item}`,
      ].join('\n');
    } else {
      summary = [
        `[거래처구분] 개인`,
        `[성명] ${formFields.name}`,
        `[주민등록번호] ${formFields.resident_number}`,
        `[기본주소] ${formFields.base_address}`,
        `[상세주소] ${formFields.detail_address}`,
        formFields.car_number ? `[차량번호] ${formFields.car_number}` : '',
        formFields.car_name ? `[차명] ${formFields.car_name}` : '',
        formFields.vin ? `[차대번호] ${formFields.vin}` : '',
      ]
        .filter(Boolean)
        .join('\n');
    }

    navigator.clipboard.writeText(summary);
    setCopiedKey('ALL');
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const handleFieldChange = (key: string, value: string) => {
    setFormFields((prev) => ({ ...prev, [key]: value }));
  };

  const resetAll = () => {
    setFile(null);
    setPreviewUrl(null);
    setTaskId(null);
    setStatus('IDLE');
    setErrorMsg(null);
    setElapsedTimer(0);
    setDocLabel('');
    setDownloadUrl(null);
    setRawTexts([]);
    setActualElapsed(null);
    setFormFields({
      business_number: '',
      company_name: '',
      representative_name: '',
      business_type: '',
      business_item: '',
      name: '',
      resident_number: '',
      base_address: '',
      detail_address: '',
      car_number: '',
      car_name: '',
      vin: '',
    });
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* 1. 상단 안내 헤더 */}
      <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">📄</span>
            <h1 className="text-lg font-bold text-white">현장 서류 거래처 OCR 자동 추출</h1>
            <span className="text-[11px] font-semibold bg-[#221c17] text-[#cc9166] border border-[#442c1d] px-2 py-0.5 rounded-full">
              RapidOCR OpenVINO 상주 파이프라인
            </span>
          </div>
          <p className="text-xs text-[#9194a1]">
            사업자등록증·인감증명서·자동차등록증 사진을 업로드하면 핵심 필드를 즉시 추출하여 인트라넷에 1클릭 복사할 수 있습니다.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#6e717e] bg-[#14151a] px-3 py-2 rounded-lg border border-[#23242c]">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>개인정보 보호: 분석 완료 즉시 원본 서류 영구 삭제 (사업자등록증만 첨부용 임시 다운로드 지원)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 2. 좌측: 서류 업로드 및 미리보기 영역 (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg space-y-4">
            <h2 className="text-sm font-semibold text-white flex items-center justify-between">
              <span>서류 사진 업로드</span>
              {status !== 'IDLE' && (
                <button
                  onClick={resetAll}
                  className="text-xs text-[#9194a1] hover:text-white flex items-center gap-1 transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  다시 올리기
                </button>
              )}
            </h2>

            {/* 드롭존 / 업로드 박스 */}
            {!previewUrl ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) handleFileSelect(e.dataTransfer.files[0]);
                }}
                className="border-2 border-dashed border-[#2a2b34] hover:border-[#cc9166] rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition bg-[#121318]/50 hover:bg-[#121318]"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="w-12 h-12 rounded-full bg-[#1c1d24] flex items-center justify-center text-[#cc9166] mb-3">
                  <Upload className="w-6 h-6" />
                </div>
                <p className="text-sm font-medium text-white mb-1">사진 파일을 여기로 끌어오거나 클릭</p>
                <p className="text-xs text-[#6e717e] mb-4">사업자등록증, 인감증명서, 자동차등록증 (JPG, PNG, WEBP)</p>

                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-3.5 py-1.5 bg-[#1f2029] hover:bg-[#282935] text-white text-xs font-medium rounded-lg border border-[#333544] transition flex items-center gap-1.5"
                  >
                    <FileText className="w-3.5 h-3.5 text-[#cc9166]" />
                    파일 선택
                  </button>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="px-3.5 py-1.5 bg-[#cc9166] hover:bg-[#b87f54] text-black text-xs font-bold rounded-lg transition flex items-center gap-1.5 shadow"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    현장 촬영
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative rounded-lg overflow-hidden border border-[#23242c] bg-black max-h-[360px] flex items-center justify-center">
                  <img src={previewUrl} alt="서류 미리보기" className="max-h-[360px] w-auto object-contain" />

                  {/* 처리 중 오버레이 */}
                  {status === 'PROCESSING' && (
                    <div className="absolute inset-0 bg-black/75 backdrop-blur-sm flex flex-col items-center justify-center p-4 text-center">
                      <RefreshCw className="w-8 h-8 text-[#cc9166] animate-spin mb-3" />
                      <p className="text-sm font-bold text-white mb-1">거래처 서류 정밀 분석 진행 중</p>
                      <p className="text-xs text-[#9194a1] max-w-[240px]">
                        RapidOCR OpenVINO 초고속 추론 중...
                      </p>
                      <div className="mt-3 flex items-center gap-1.5 text-xs text-[#cc9166] font-mono bg-[#1c140d] px-3 py-1 rounded-full border border-[#442c1d]">
                        <Clock className="w-3.5 h-3.5" />
                        <span>경과 시간: {elapsedTimer}초</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-[#9194a1] px-1">
                  <span className="truncate max-w-[200px]">{file?.name}</span>
                  {actualElapsed && (
                    <span className="text-emerald-400 font-medium">실측 완료: {actualElapsed}초</span>
                  )}
                </div>
              </div>
            )}

            {/* 히든 인풋 */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) handleFileSelect(e.target.files[0]);
              }}
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) handleFileSelect(e.target.files[0]);
              }}
            />

            {/* 에러 메시지 표시 */}
            {status === 'FAILED' && (
              <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-lg flex items-start gap-2 text-xs text-red-300">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold mb-0.5">분석 실패</p>
                  <p className="text-red-400/90">{errorMsg}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 3. 우측: 추출 필드 및 1클릭 복사 폼 (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg space-y-5">
            {/* 상단 액션바: 문서 판별 뱃지 + 개인/사업자 토글 + 전체 복사 + 첨부 다운로드 */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#1c1d22]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#9194a1]">문서 구분:</span>
                {docLabel ? (
                  <span
                    className={`text-xs font-bold px-2.5 py-1 rounded-md border ${
                      docLabel === '사업자등록증'
                        ? 'bg-emerald-950/50 text-emerald-400 border-emerald-800'
                        : docLabel === '자동차등록증'
                        ? 'bg-blue-950/50 text-blue-400 border-blue-800'
                        : 'bg-purple-950/50 text-purple-400 border-purple-800'
                    }`}
                  >
                    {docLabel}
                  </span>
                ) : (
                  <span className="text-xs text-[#6e717e] italic">서류 대기 중</span>
                )}

                {/* 개인 / 사업자 수동 전환 스위치 */}
                <div className="flex items-center bg-[#15161c] p-0.5 rounded-lg border border-[#23242c] ml-1">
                  <button
                    type="button"
                    onClick={() => setVendorType('business')}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition flex items-center gap-1 ${
                      vendorType === 'business'
                        ? 'bg-[#cc9166] text-black font-bold shadow'
                        : 'text-[#9194a1] hover:text-white'
                    }`}
                  >
                    <Building className="w-3 h-3" />
                    사업자
                  </button>
                  <button
                    type="button"
                    onClick={() => setVendorType('individual')}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition flex items-center gap-1 ${
                      vendorType === 'individual'
                        ? 'bg-[#cc9166] text-black font-bold shadow'
                        : 'text-[#9194a1] hover:text-white'
                    }`}
                  >
                    <User className="w-3 h-3" />
                    개인
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* 원본 파일 다운로드 (사업자등록증 인트라넷 첨부용) */}
                {downloadUrl && (
                  <a
                    href={downloadUrl}
                    download
                    className="px-3 py-1.5 bg-[#181a22] hover:bg-[#20232e] text-[#4ade80] text-xs font-medium rounded-lg border border-[#22543d] transition flex items-center gap-1.5"
                    title="인트라넷 첨부용 원본 사진 다운로드"
                  >
                    <Download className="w-3.5 h-3.5" />
                    서류 첨부 다운로드
                  </a>
                )}

                {/* 전체 복사 버튼 */}
                <button
                  type="button"
                  onClick={handleCopyAll}
                  disabled={status !== 'COMPLETED'}
                  className="px-3 py-1.5 bg-[#1f2029] hover:bg-[#282935] disabled:opacity-40 disabled:pointer-events-none text-white text-xs font-medium rounded-lg border border-[#333544] transition flex items-center gap-1.5"
                >
                  {copiedKey === 'ALL' ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400 font-semibold">전체 복사됨!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-[#cc9166]" />
                      <span>전체 복사</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* 필드 입력 및 1클릭 복사 폼 (인트라넷 등록 폼 순서) */}
            <div className="space-y-3.5">
              {vendorType === 'business' ? (
                /* 4-A. 사업자 거래처등록 폼 필드 */
                <>
                  <FieldRow
                    label="사업자등록번호"
                    badge="10자리"
                    value={formFields.business_number}
                    onChange={(v) => handleFieldChange('business_number', v)}
                    onCopy={() => handleCopyField('business_number', formFields.business_number)}
                    isCopied={copiedKey === 'business_number'}
                    placeholder="예: 123-45-67890"
                    highlight
                  />
                  <FieldRow
                    label="상호명"
                    value={formFields.company_name}
                    onChange={(v) => handleFieldChange('company_name', v)}
                    onCopy={() => handleCopyField('company_name', formFields.company_name)}
                    isCopied={copiedKey === 'company_name'}
                    placeholder="상호명 입력"
                  />
                  <FieldRow
                    label="대표자명"
                    value={formFields.representative_name}
                    onChange={(v) => handleFieldChange('representative_name', v)}
                    onCopy={() => handleCopyField('representative_name', formFields.representative_name)}
                    isCopied={copiedKey === 'representative_name'}
                    placeholder="대표자 성명"
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <FieldRow
                      label="업태"
                      value={formFields.business_type}
                      onChange={(v) => handleFieldChange('business_type', v)}
                      onCopy={() => handleCopyField('business_type', formFields.business_type)}
                      isCopied={copiedKey === 'business_type'}
                      placeholder="예: 음식점업, 도소매업"
                    />
                    <FieldRow
                      label="종목"
                      value={formFields.business_item}
                      onChange={(v) => handleFieldChange('business_item', v)}
                      onCopy={() => handleCopyField('business_item', formFields.business_item)}
                      isCopied={copiedKey === 'business_item'}
                      placeholder="예: 한식 음식점업, 중고차매매"
                    />
                  </div>
                  <FieldRow
                    label="기본주소 (도로명/건물번호)"
                    value={formFields.base_address}
                    onChange={(v) => handleFieldChange('base_address', v)}
                    onCopy={() => handleCopyField('base_address', formFields.base_address)}
                    isCopied={copiedKey === 'base_address'}
                    placeholder="예: 서울특별시 강남구 테헤란로 123"
                  />
                  <FieldRow
                    label="상세주소 (동/호/층)"
                    value={formFields.detail_address}
                    onChange={(v) => handleFieldChange('detail_address', v)}
                    onCopy={() => handleCopyField('detail_address', formFields.detail_address)}
                    isCopied={copiedKey === 'detail_address'}
                    placeholder="예: 101동 101호"
                  />
                </>
              ) : (
                /* 4-B. 개인 거래처등록 폼 필드 */
                <>
                  <FieldRow
                    label="성명 / 소유자명"
                    value={formFields.name}
                    onChange={(v) => handleFieldChange('name', v)}
                    onCopy={() => handleCopyField('name', formFields.name)}
                    isCopied={copiedKey === 'name'}
                    placeholder="예: 홍길동"
                  />
                  <FieldRow
                    label="주민등록번호"
                    badge="13자리"
                    value={formFields.resident_number}
                    onChange={(v) => handleFieldChange('resident_number', v)}
                    onCopy={() => handleCopyField('resident_number', formFields.resident_number)}
                    isCopied={copiedKey === 'resident_number'}
                    placeholder="예: 900101-1******"
                    highlight
                  />
                  <FieldRow
                    label="기본주소 (도로명/건물번호)"
                    value={formFields.base_address}
                    onChange={(v) => handleFieldChange('base_address', v)}
                    onCopy={() => handleCopyField('base_address', formFields.base_address)}
                    isCopied={copiedKey === 'base_address'}
                    placeholder="예: 서울특별시 강남구 테헤란로 123"
                  />
                  <FieldRow
                    label="상세주소 (동/호/층)"
                    value={formFields.detail_address}
                    onChange={(v) => handleFieldChange('detail_address', v)}
                    onCopy={() => handleCopyField('detail_address', formFields.detail_address)}
                    isCopied={copiedKey === 'detail_address'}
                    placeholder="예: 101동 101호"
                  />

                  {/* 자동차등록증인 경우 차량 정보 표시 */}
                  {(docLabel === '자동차등록증' || formFields.car_number || formFields.vin) && (
                    <div className="pt-2 border-t border-[#1c1d22] space-y-3">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-400">
                        <Car className="w-3.5 h-3.5" />
                        <span>자동차등록증 부가 정보</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <FieldRow
                          label="자동차등록번호"
                          value={formFields.car_number}
                          onChange={(v) => handleFieldChange('car_number', v)}
                          onCopy={() => handleCopyField('car_number', formFields.car_number)}
                          isCopied={copiedKey === 'car_number'}
                          placeholder="예: 123가4567"
                        />
                        <FieldRow
                          label="차명"
                          value={formFields.car_name}
                          onChange={(v) => handleFieldChange('car_name', v)}
                          onCopy={() => handleCopyField('car_name', formFields.car_name)}
                          isCopied={copiedKey === 'car_name'}
                          placeholder="예: 스파크 1.0"
                        />
                      </div>
                      <FieldRow
                        label="차대번호"
                        badge="17자리"
                        value={formFields.vin}
                        onChange={(v) => handleFieldChange('vin', v)}
                        onCopy={() => handleCopyField('vin', formFields.vin)}
                        isCopied={copiedKey === 'vin'}
                        placeholder="예: KMHET41BP0A000001"
                      />
                    </div>
                  )}
                </>
              )}
            </div>

            {/* 5. 하단: OCR 원문 전체 보기 아코디언 */}
            {rawTexts.length > 0 && (
              <div className="pt-3 border-t border-[#1c1d22]">
                <button
                  type="button"
                  onClick={() => setShowRawTexts((prev) => !prev)}
                  className="w-full flex items-center justify-between text-xs text-[#9194a1] hover:text-white py-1 transition"
                >
                  <span className="flex items-center gap-1.5 font-medium">
                    <FileText className="w-3.5 h-3.5 text-[#cc9166]" />
                    OCR 원문 전체 텍스트 대조 ({rawTexts.length}개 라인)
                  </span>
                  {showRawTexts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showRawTexts && (
                  <div className="mt-2.5 p-3 bg-[#08090b] rounded-lg border border-[#1f2027] max-h-48 overflow-y-auto font-mono text-[11px] text-[#a0a3b1] space-y-1">
                    {rawTexts.map((line, idx) => (
                      <div key={idx} className="flex gap-2 hover:bg-[#121318] px-1 py-0.5 rounded">
                        <span className="text-[#555866] select-none w-6 text-right">{idx + 1}</span>
                        <span className="select-all">{line}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// 개별 필드 입력 및 복사 행 컴포넌트
interface FieldRowProps {
  label: string;
  badge?: string;
  value: string;
  onChange: (v: string) => void;
  onCopy: () => void;
  isCopied: boolean;
  placeholder?: string;
  highlight?: boolean;
}

const FieldRow: React.FC<FieldRowProps> = ({
  label,
  badge,
  value,
  onChange,
  onCopy,
  isCopied,
  placeholder,
  highlight,
}) => {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-[11px] font-semibold text-[#a5a8b6] flex items-center gap-1.5">
          <span>{label}</span>
          {badge && (
            <span className="text-[9px] font-bold bg-[#1e2029] text-[#cc9166] border border-[#373949] px-1.5 py-0.2 rounded">
              {badge}
            </span>
          )}
        </label>
        {isCopied && <span className="text-[10px] text-emerald-400 font-bold animate-pulse">복사됨!</span>}
      </div>

      <div className="relative flex items-center">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full bg-[#13141a] text-white text-xs font-medium rounded-lg pl-3 pr-9 py-2 border transition outline-none ${
            highlight
              ? 'border-[#442c1d] focus:border-[#cc9166] text-[#ffdcb3]'
              : 'border-[#22232c] focus:border-[#4a4d60]'
          }`}
        />
        <button
          type="button"
          onClick={onCopy}
          disabled={!value}
          title="클립보드에 복사"
          className="absolute right-1.5 p-1.5 text-[#9194a1] hover:text-white disabled:opacity-30 disabled:pointer-events-none rounded hover:bg-[#20222b] transition"
        >
          {isCopied ? (
            <Check className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Copy className="w-3.5 h-3.5 text-[#cc9166]" />
          )}
        </button>
      </div>
    </div>
  );
};
