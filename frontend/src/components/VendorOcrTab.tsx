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
  CreditCard,
  PlusCircle,
  Trash2,
  FileCheck,
} from 'lucide-react';

export type RegistrationType = 'individual' | 'business';
export type DocType = 'BIZ' | 'CAR' | 'SEAL' | 'FACT' | 'UNKNOWN';

export const DOC_TYPE_OPTIONS: { value: DocType; label: string }[] = [
  { value: 'BIZ', label: '사업자등록증' },
  { value: 'CAR', label: '자동차등록증' },
  { value: 'SEAL', label: '인감증명서' },
  { value: 'FACT', label: '비사업용사실확인서' },
  { value: 'UNKNOWN', label: '기타 서류' },
];

export interface UploadItem {
  id: string;
  file: File;
  previewUrl: string;
  status: 'WAITING' | 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  errorMsg?: string;
  taskId?: string;
  docType: DocType;
  docLabel: string;
  downloadUrl?: string;
  elapsed?: number;
  savedToServer: boolean;
  rawTexts?: string[];
}

export const VendorOcrTab: React.FC = () => {
  // 1. 거래처 등록 기준 (제이 선택: 개인 vs 사업자)
  const [registrationType, setRegistrationType] = useState<RegistrationType>('individual');

  // 2. 다중 업로드 파일 큐
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isProcessingQueue, setIsProcessingQueue] = useState<boolean>(false);
  const [selectedPreviewItem, setSelectedPreviewItem] = useState<UploadItem | null>(null);

  // 3. 계좌 텍스트 및 계좌 정보 상태
  const [accountText, setAccountText] = useState<string>('');
  const [accountFields, setAccountFields] = useState<{
    bank_name: string;
    bank_code: string;
    account_no: string;
    holder: string;
  }>({
    bank_name: '',
    bank_code: '',
    account_no: '',
    holder: '',
  });
  const [accountSaveStatus, setAccountSaveStatus] = useState<'IDLE' | 'SAVING' | 'SAVED' | 'ERROR'>('IDLE');

  // 4. 주 서류 거래처 추출 필드 상태
  const [vendorType, setVendorType] = useState<'business' | 'individual'>('individual');
  const [docLabel, setDocLabel] = useState<string>('');
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [rawTexts, setRawTexts] = useState<string[]>([]);
  const [showRawTexts, setShowRawTexts] = useState<boolean>(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

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

  // 등록 기준 변경 시 거래처 구분 연동
  useEffect(() => {
    setVendorType(registrationType);
  }, [registrationType]);

  // "새 건 시작" 초기화
  const handleResetSession = async () => {
    if (!window.confirm('새 건을 시작하시겠습니까? 현재 보관된 모든 서류 파일과 추출 데이터가 초기화됩니다.')) {
      return;
    }
    try {
      await fetch('/api/ocr/latest/reset', { method: 'POST' });
    } catch (e) {
      console.error('Reset error:', e);
    }
    setItems([]);
    setSelectedPreviewItem(null);
    setAccountText('');
    setAccountFields({ bank_name: '', bank_code: '', account_no: '', holder: '' });
    setAccountSaveStatus('IDLE');
    setDocLabel('');
    setDownloadUrl(null);
    setRawTexts([]);
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

  // 파일 선택 수신 (다중 지원)
  const handleFilesSelect = (fileList: FileList | File[]) => {
    const newItems: UploadItem[] = [];

    Array.from(fileList).forEach((f) => {
      const lower = (f.name || '').toLowerCase();
      let preview = '';
      try {
        preview = URL.createObjectURL(f);
      } catch {
        preview = '';
      }

      if (lower.endsWith('.heic') || lower.endsWith('.heif')) {
        // HEIC 파일은 인트라넷 미지원이므로 즉시 실패 처리 후 안내
        newItems.push({
          id: Math.random().toString(36).substring(2, 9),
          file: f,
          previewUrl: preview,
          status: 'FAILED',
          errorMsg: 'HEIC는 인트라넷 첨부도 지원되지 않으니 JPG로 올려 주세요.',
          docType: 'UNKNOWN',
          docLabel: '미지원 포맷',
          savedToServer: false,
        });
      } else {
        newItems.push({
          id: Math.random().toString(36).substring(2, 9),
          file: f,
          previewUrl: preview,
          status: 'WAITING',
          docType: 'UNKNOWN',
          docLabel: '분석 대기',
          savedToServer: false,
        });
      }
    });

    if (newItems.length > 0) {
      setItems((prev) => [...prev, ...newItems]);
      if (!selectedPreviewItem && newItems[0].previewUrl) {
        setSelectedPreviewItem(newItems[0]);
      }
    }
  };

  // 순차 처리 큐 워커
  useEffect(() => {
    if (isProcessingQueue) return;

    const nextItem = items.find((it) => it.status === 'WAITING');
    if (!nextItem) return;

    processSingleItem(nextItem.id);
  }, [items, isProcessingQueue, registrationType, accountText]);

  const processSingleItem = async (itemId: string) => {
    setIsProcessingQueue(true);

    setItems((prev) =>
      prev.map((it) => (it.id === itemId ? { ...it, status: 'UPLOADING', errorMsg: undefined } : it))
    );

    const target = items.find((it) => it.id === itemId);
    if (!target) {
      setIsProcessingQueue(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', target.file);
      formData.append('registration_type', registrationType);
      if (accountText.trim()) {
        formData.append('account_text', accountText.trim());
      }
      if (target.docType === 'FACT') {
        formData.append('manual_doc_type', 'FACT');
      }

      const res = await fetch('/api/ocr/vendor', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `업로드 실패 (${res.status})`);
      }

      const data = await res.json();
      const taskId = data.task_id;

      setItems((prev) =>
        prev.map((it) => (it.id === itemId ? { ...it, status: 'PROCESSING', taskId } : it))
      );

      // 계좌 정보가 처음 수신되면 계좌 필드에 즉시 탑재
      if (data.account && (data.account.bank_name || data.account.account_no)) {
        setAccountFields({
          bank_name: data.account.bank_name || '',
          bank_code: data.account.bank_code || '',
          account_no: data.account.account_no || '',
          holder: data.account.holder || '',
        });
      }

      // 상태 폴링
      await pollTaskUntilDone(itemId, taskId);
    } catch (err: any) {
      setItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? { ...it, status: 'FAILED', errorMsg: err.message || '분석 중 오류 발생' }
            : it
        )
      );
    } finally {
      setIsProcessingQueue(false);
    }
  };

  const pollTaskUntilDone = (itemId: string, taskId: string): Promise<void> => {
    return new Promise((resolve) => {
      const startTime = Date.now();
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/ocr/status/${taskId}`);
          if (!res.ok) throw new Error(`HTTP error ${res.status}`);
          const data = await res.json();

          if (data.status === 'COMPLETED') {
            clearInterval(interval);
            const elapsed = Math.round((Date.now() - startTime) / 100) / 10;
            const parsed = data.data || {};
            const docType = (parsed.document_type || 'UNKNOWN') as DocType;
            const docLabel = parsed.document_label || '기타 서류';

            setItems((prev) =>
              prev.map((it) =>
                it.id === itemId
                  ? {
                      ...it,
                      status: 'COMPLETED',
                      docType,
                      docLabel,
                      downloadUrl: data.download_url,
                      elapsed: parsed.elapsed_sec || elapsed,
                      savedToServer: true,
                      rawTexts: parsed.raw_texts || [],
                    }
                  : it
              )
            );

            // 주 서류 우선 원칙에 따른 거래처 폼 필드 갱신
            applyMainDocumentFields(docType, parsed);
            resolve();
          } else if (data.status === 'FAILED') {
            clearInterval(interval);
            setItems((prev) =>
              prev.map((it) =>
                it.id === itemId
                  ? {
                      ...it,
                      status: 'FAILED',
                      errorMsg: data.error || 'OCR 분석 실패',
                    }
                  : it
              )
            );
            resolve();
          }
        } catch (e: any) {
          // 일시 네트워크 오류 시 계속 폴링 (최대 40초)
          if (Date.now() - startTime > 40000) {
            clearInterval(interval);
            setItems((prev) =>
              prev.map((it) =>
                it.id === itemId ? { ...it, status: 'FAILED', errorMsg: '분석 시간 초과 (40초)' } : it
              )
            );
            resolve();
          }
        }
      }, 1500);
    });
  };

  // 주 서류 필드 반영 (제이 원칙: 개인=등록증/인감, 사업자=사업자등록증 우선)
  const applyMainDocumentFields = (docType: DocType, parsed: any) => {
    const f = parsed.fields || {};

    if (registrationType === 'business') {
      // 사업자 기준: BIZ가 들어오면 무조건 주 서류로 확정
      if (docType === 'BIZ') {
        setDocLabel(parsed.document_label || '사업자등록증');
        setDownloadUrl(`/api/ocr/latest/file?doc_type=BIZ`);
        setRawTexts(parsed.raw_texts || []);
        setFormFields((prev) => ({
          ...prev,
          business_number: f.business_number || prev.business_number || '',
          company_name: f.company_name || prev.company_name || '',
          representative_name: f.representative_name || prev.representative_name || '',
          business_type: f.business_type || prev.business_type || '',
          business_item: f.business_item || prev.business_item || '',
          base_address: f.base_address || prev.base_address || '',
          detail_address: f.detail_address || prev.detail_address || '',
        }));
      } else if (!formFields.business_number) {
        // 아직 BIZ가 없는 경우 임시로 다른 서류 필드 반영
        setDocLabel(parsed.document_label || '');
        setRawTexts(parsed.raw_texts || []);
        setFormFields((prev) => ({
          ...prev,
          name: f.name || f.owner_name || prev.name || '',
          resident_number: f.resident_number || prev.resident_number || '',
          base_address: f.base_address || prev.base_address || '',
          detail_address: f.detail_address || prev.detail_address || '',
          car_number: f.car_number || prev.car_number || '',
          car_name: f.car_name || prev.car_name || '',
          vin: f.vin || prev.vin || '',
        }));
      }
    } else {
      // 개인 기준: SEAL 또는 CAR가 들어오면 개인 정보 확정 (BIZ가 늦게 와도 덮어쓰지 않음)
      if (docType === 'SEAL' || docType === 'CAR') {
        setDocLabel(parsed.document_label || (docType === 'SEAL' ? '인감증명서' : '자동차등록증'));
        setDownloadUrl(`/api/ocr/latest/file?doc_type=${docType}`);
        setRawTexts(parsed.raw_texts || []);
        setFormFields((prev) => ({
          ...prev,
          name: f.name || f.owner_name || prev.name || '',
          resident_number: f.resident_number || prev.resident_number || '',
          base_address: f.base_address || prev.base_address || '',
          detail_address: f.detail_address || prev.detail_address || '',
          car_number: f.car_number || prev.car_number || '',
          car_name: f.car_name || prev.car_name || '',
          vin: f.vin || prev.vin || '',
        }));
      }
    }

    if (parsed.account && (parsed.account.bank_name || parsed.account.account_no)) {
      setAccountFields({
        bank_name: parsed.account.bank_name || '',
        bank_code: parsed.account.bank_code || '',
        account_no: parsed.account.account_no || '',
        holder: parsed.account.holder || '',
      });
    }
  };

  // 사용자가 카드에서 서류 종류 직접 변경
  const handleChangeDocType = async (item: UploadItem, newType: DocType) => {
    const oldType = item.docType;
    const opt = DOC_TYPE_OPTIONS.find((o) => o.value === newType);
    const newLabel = opt ? opt.label : newType;

    setItems((prev) =>
      prev.map((it) => (it.id === item.id ? { ...it, docType: newType, docLabel: newLabel } : it))
    );

    if (item.savedToServer && oldType !== newType) {
      try {
        await fetch('/api/ocr/latest/file-type', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ old_doc_type: oldType, new_doc_type: newType }),
        });
      } catch (e) {
        console.error('File type patch error:', e);
      }
    }
  };

  // [계좌만 저장] 단독 전송
  const handleSaveAccountOnly = async () => {
    const trimmed = accountText.trim();
    if (!trimmed) {
      alert('저장할 계좌 문자열을 입력해 주세요.');
      return;
    }
    setAccountSaveStatus('SAVING');
    try {
      const res = await fetch('/api/ocr/latest/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_text: trimmed }),
      });
      if (!res.ok) throw new Error('계좌 저장 실패');
      const data = await res.json();
      if (data.account) {
        setAccountFields({
          bank_name: data.account.bank_name || '',
          bank_code: data.account.bank_code || '',
          account_no: data.account.account_no || '',
          holder: data.account.holder || '',
        });
      }
      setAccountSaveStatus('SAVED');
      setTimeout(() => setAccountSaveStatus('IDLE'), 3000);
    } catch (e) {
      setAccountSaveStatus('ERROR');
      setTimeout(() => setAccountSaveStatus('IDLE'), 3000);
    }
  };

  // 계좌 필드 직접 수정 시 서버 동기화
  const handleSyncAccount = async (updated: typeof accountFields) => {
    setAccountFields(updated);
    setAccountSaveStatus('SAVING');
    try {
      const res = await fetch('/api/ocr/latest', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      if (res.ok) {
        setAccountSaveStatus('SAVED');
        setTimeout(() => setAccountSaveStatus('IDLE'), 3000);
      } else {
        setAccountSaveStatus('ERROR');
      }
    } catch {
      setAccountSaveStatus('ERROR');
    }
  };

  const handleCopyField = (key: string, value: string) => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const handleCopyAll = () => {
    let summary = '';
    if (registrationType === 'business') {
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

    if (accountFields.bank_name || accountFields.account_no) {
      summary += `\n[계좌] ${accountFields.bank_name} ${accountFields.account_no} (예금주: ${accountFields.holder})`;
    }

    navigator.clipboard.writeText(summary);
    setCopiedKey('ALL');
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const handleFieldChange = (key: string, value: string) => {
    setFormFields((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      {/* 1. 상단 안내 헤더 & 등록 기준 선택 & 새 건 시작 */}
      <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">📄</span>
              <h1 className="text-lg font-bold text-white">현장 서류 거래처 OCR 자동 추출</h1>
              <span className="text-[11px] font-semibold bg-[#221c17] text-[#cc9166] border border-[#442c1d] px-2 py-0.5 rounded-full">
                건 단위 세션 관리
              </span>
            </div>
            <p className="text-xs text-[#9194a1]">
              여러 서류(사업자·등록증·인감·사실확인서)를 한 번에 올려도 각각 판정·보관되며, 선택한 등록 기준(개인/사업자)에 맞춰 주 서류가 고정됩니다.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleResetSession}
              className="px-3.5 py-1.5 bg-[#1b1c24] hover:bg-[#262835] text-amber-300 hover:text-amber-200 text-xs font-bold rounded-lg border border-amber-900/60 transition flex items-center gap-1.5 shadow"
            >
              <PlusCircle className="w-4 h-4 text-amber-400" />
              새 건 시작 (보관함 초기화)
            </button>
          </div>
        </div>

        {/* 거래처 등록 기준 선택 바 */}
        <div className="pt-3 border-t border-[#1c1d22] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[#cc9166]">거래처 등록 기준:</span>
            <div className="inline-flex rounded-lg border border-[#2c2d38] bg-[#14151b] p-0.5">
              <button
                type="button"
                onClick={() => setRegistrationType('individual')}
                className={`px-3 py-1 text-xs font-bold rounded-md transition flex items-center gap-1.5 ${
                  registrationType === 'individual'
                    ? 'bg-[#cc9166] text-black shadow'
                    : 'text-[#9194a1] hover:text-white'
                }`}
              >
                <User className="w-3.5 h-3.5" />
                개인 (등록증·인감 기준)
              </button>
              <button
                type="button"
                onClick={() => setRegistrationType('business')}
                className={`px-3 py-1 text-xs font-bold rounded-md transition flex items-center gap-1.5 ${
                  registrationType === 'business'
                    ? 'bg-[#cc9166] text-black shadow'
                    : 'text-[#9194a1] hover:text-white'
                }`}
              >
                <Building className="w-3.5 h-3.5" />
                사업자 (사업자등록증 기준)
              </button>
            </div>
            <span className="text-[11px] text-[#6e717e] ml-2">
              ※ 사업자등록증이 있어도 '개인'을 선택하면 인감/등록증이 주 서류가 되고, 사업자 서류는 매입등록 첨부용으로 자동 보관됩니다.
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 2. 좌측: 다중 서류 업로드 및 파일별 상태 리스트 (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg space-y-4">
            <h2 className="text-sm font-semibold text-white flex items-center justify-between">
              <span>서류 사진 다중 업로드 (순차 분석)</span>
              {items.length > 0 && (
                <span className="text-xs text-[#9194a1] font-mono">
                  총 {items.length}건 (완료: {items.filter((i) => i.status === 'COMPLETED').length})
                </span>
              )}
            </h2>

            {/* 드롭존 (multiple) */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files?.length) handleFilesSelect(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-[#2a2b34] hover:border-[#cc9166] rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition bg-[#121318]/50 hover:bg-[#121318]"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="w-10 h-10 rounded-full bg-[#1c1d24] flex items-center justify-center text-[#cc9166] mb-2">
                <Upload className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-white mb-0.5">여러 장의 사진을 한 번에 끌어오거나 클릭</p>
              <p className="text-[11px] text-[#6e717e] mb-3">사업자·인감·자동차등록증·사실확인서 (JPG, PNG, WEBP)</p>

              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 bg-[#1f2029] hover:bg-[#282935] text-white text-xs font-medium rounded-lg border border-[#333544] transition flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5 text-[#cc9166]" />
                  파일 여러 장 선택
                </button>
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="px-3 py-1.5 bg-[#cc9166] hover:bg-[#b87f54] text-black text-xs font-bold rounded-lg transition flex items-center gap-1.5 shadow"
                >
                  <Camera className="w-3.5 h-3.5" />
                  현장 촬영
                </button>
              </div>
            </div>

            {/* 히든 인풋 (multiple) */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) handleFilesSelect(e.target.files);
              }}
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) handleFilesSelect(e.target.files);
              }}
            />

            {/* 파일별 상태 카드 리스트 */}
            {items.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-[#1c1d22] max-h-[380px] overflow-y-auto pr-1">
                <div className="text-[11px] font-semibold text-[#9194a1] flex items-center justify-between">
                  <span>업로드 서류 목록</span>
                  <span className="text-[10px] text-[#6e717e]">클릭 시 우측 미리보기</span>
                </div>
                {items.map((it) => (
                  <div
                    key={it.id}
                    onClick={() => setSelectedPreviewItem(it)}
                    className={`p-3 rounded-lg border text-xs transition cursor-pointer flex flex-col gap-2 ${
                      selectedPreviewItem?.id === it.id
                        ? 'bg-[#181922] border-[#cc9166]'
                        : 'bg-[#111217] border-[#22232c] hover:border-[#333544]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 truncate max-w-[200px]">
                        <FileText className="w-3.5 h-3.5 text-[#cc9166] shrink-0" />
                        <span className="font-medium text-white truncate">{it.file.name}</span>
                      </div>
                      {/* 상태 배지 */}
                      {it.status === 'WAITING' && (
                        <span className="text-[10px] bg-[#22232a] text-[#9194a1] px-2 py-0.5 rounded font-mono">
                          대기 중
                        </span>
                      )}
                      {it.status === 'UPLOADING' && (
                        <span className="text-[10px] bg-blue-950/60 text-blue-400 border border-blue-800 px-2 py-0.5 rounded animate-pulse">
                          업로드 중...
                        </span>
                      )}
                      {it.status === 'PROCESSING' && (
                        <span className="text-[10px] bg-amber-950/60 text-amber-400 border border-amber-800 px-2 py-0.5 rounded flex items-center gap-1">
                          <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                          분석 중...
                        </span>
                      )}
                      {it.status === 'COMPLETED' && (
                        <span className="text-[10px] bg-emerald-950/60 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          완료 ({it.elapsed}초)
                        </span>
                      )}
                      {it.status === 'FAILED' && (
                        <span className="text-[10px] bg-red-950/60 text-red-400 border border-red-800 px-2 py-0.5 rounded">
                          실패
                        </span>
                      )}
                    </div>

                    {/* 서류 판정 드롭다운 및 서버 보관 배지 */}
                    <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#1a1b22]">
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <span className="text-[11px] text-[#6e717e]">분류:</span>
                        <select
                          value={it.docType}
                          onChange={(e) => handleChangeDocType(it, e.target.value as DocType)}
                          className="bg-[#0a0b0e] text-[#cc9166] border border-[#2e303d] rounded px-1.5 py-0.5 text-[11px] font-semibold outline-none focus:border-[#cc9166]"
                        >
                          {DOC_TYPE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value} className="bg-[#121318] text-white">
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {it.savedToServer ? (
                        <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1 bg-emerald-950/40 border border-emerald-900 px-1.5 py-0.5 rounded">
                          <ShieldCheck className="w-3 h-3 text-emerald-400" />
                          서버 보관 완료
                        </span>
                      ) : it.status === 'FAILED' ? (
                        <span className="text-[10px] text-red-300 truncate max-w-[150px]">{it.errorMsg}</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 계좌 정보 입력칸 + [계좌만 저장] 버튼 */}
            <div className="bg-[#121318] border border-[#23242c] rounded-xl p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <CreditCard className="w-3.5 h-3.5 text-[#cc9166]" />
                  <span>계좌 정보 (문자·카톡 텍스트)</span>
                </label>
                <div className="flex items-center gap-2">
                  {accountText && (
                    <button
                      type="button"
                      onClick={() => setAccountText('')}
                      className="text-[11px] text-[#9194a1] hover:text-white transition"
                    >
                      지우기
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleSaveAccountOnly}
                    disabled={!accountText.trim() || accountSaveStatus === 'SAVING'}
                    className="px-2.5 py-1 bg-[#1c1d27] hover:bg-[#252735] disabled:opacity-40 text-amber-300 text-xs font-bold rounded-md border border-amber-800/60 transition flex items-center gap-1"
                  >
                    <CreditCard className="w-3 h-3" />
                    계좌만 저장
                  </button>
                </div>
              </div>
              <textarea
                value={accountText}
                onChange={(e) => setAccountText(e.target.value)}
                placeholder="예: 국민은행 123456-78-901234 홍길동&#10;(사진 없이 이 버튼만 눌러도 은행·계좌·예금주가 분리되어 최신 보관분에 저장됩니다)"
                rows={3}
                className="w-full bg-[#0a0b0e] text-white text-xs rounded-lg p-2.5 border border-[#262833] focus:border-[#cc9166] outline-none resize-none transition placeholder:text-[#555866]"
              />
              <div className="flex items-center justify-between text-[11px] text-[#6e717e]">
                <span>사진 업로드 시 함께 전송되거나, 우측 [계좌만 저장]으로 단독 반영됩니다.</span>
                {accountSaveStatus === 'SAVED' && (
                  <span className="text-emerald-400 font-semibold flex items-center gap-0.5">
                    <Check className="w-3 h-3" /> 계좌 보관 완료
                  </span>
                )}
                {accountSaveStatus === 'SAVING' && (
                  <span className="text-amber-400 animate-pulse">저장 중...</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 3. 우측: 주 서류 추출 필드 및 1클릭 복사 폼 (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-[#0e0f12] border border-[#1c1d22] rounded-xl p-5 shadow-lg space-y-5">
            {/* 상단 액션바: 주 서류 판정 라벨 + 등록 기준 안내 + 전체 복사 */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#1c1d22]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#9194a1]">주 서류:</span>
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
                <span className="text-[11px] text-[#cc9166] bg-[#221c17] px-2 py-0.5 rounded border border-[#442c1d]">
                  {registrationType === 'business' ? '사업자 거래처 기준' : '개인 거래처 기준'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {downloadUrl && (
                  <a
                    href={downloadUrl}
                    download
                    className="px-3 py-1.5 bg-[#181a22] hover:bg-[#20232e] text-[#4ade80] text-xs font-medium rounded-lg border border-[#22543d] transition flex items-center gap-1.5"
                    title="인트라넷 첨부용 원본 사진 다운로드"
                  >
                    <Download className="w-3.5 h-3.5" />
                    주 서류 다운로드
                  </a>
                )}

                {/* 전체 복사 버튼 */}
                <button
                  type="button"
                  onClick={handleCopyAll}
                  className="px-3 py-1.5 bg-[#1f2029] hover:bg-[#282935] text-white text-xs font-medium rounded-lg border border-[#333544] transition flex items-center gap-1.5"
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

            {/* 필드 입력 및 1클릭 복사 폼 (선택한 등록 기준에 맞춰 렌더링) */}
            <div className="space-y-3.5">
              {registrationType === 'business' ? (
                /* 사업자 거래처등록 폼 필드 */
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
                /* 개인 거래처등록 폼 필드 */
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
                  {(formFields.car_number || formFields.vin) && (
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

            {/* 계좌 정보 섹션 (분리 결과 및 실시간 동기화) */}
            <div className="pt-4 border-t border-[#1c1d22] space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                  <CreditCard className="w-3.5 h-3.5" />
                  <span>계좌 정보 (거래처등록 & 송금정보용)</span>
                  {accountFields.bank_code && (
                    <span className="text-[10px] font-mono bg-[#241d13] text-[#f59e0b] border border-[#53381a] px-1.5 py-0.2 rounded">
                      코드: {accountFields.bank_code}
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <FieldRow
                  label="은행명"
                  value={accountFields.bank_name}
                  onChange={(v) => handleSyncAccount({ ...accountFields, bank_name: v })}
                  onCopy={() => handleCopyField('bank_name', accountFields.bank_name)}
                  isCopied={copiedKey === 'bank_name'}
                  placeholder="예: 국민은행"
                />
                <FieldRow
                  label="계좌번호"
                  value={accountFields.account_no}
                  onChange={(v) => handleSyncAccount({ ...accountFields, account_no: v })}
                  onCopy={() => handleCopyField('account_no', accountFields.account_no)}
                  isCopied={copiedKey === 'account_no'}
                  placeholder="예: 123456-78-901234"
                  highlight
                />
                <FieldRow
                  label="예금주"
                  value={accountFields.holder}
                  onChange={(v) => handleSyncAccount({ ...accountFields, holder: v })}
                  onCopy={() => handleCopyField('holder', accountFields.holder)}
                  isCopied={copiedKey === 'holder'}
                  placeholder="예: 홍길동"
                />
              </div>
            </div>

            {/* 하단: OCR 원문 텍스트 아코디언 */}
            {rawTexts.length > 0 && (
              <div className="pt-3 border-t border-[#1c1d22]">
                <button
                  type="button"
                  onClick={() => setShowRawTexts(!showRawTexts)}
                  className="w-full flex items-center justify-between text-xs text-[#9194a1] hover:text-white py-1 transition"
                >
                  <span>인식된 텍스트 원문 ({rawTexts.length}행)</span>
                  {showRawTexts ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showRawTexts && (
                  <div className="mt-2 p-3 bg-[#0a0b0e] border border-[#1f2029] rounded-lg max-h-48 overflow-y-auto space-y-1 font-mono text-[11px] text-[#808394]">
                    {rawTexts.map((txt, idx) => (
                      <div key={idx} className="flex gap-2">
                        <span className="text-[#454754] select-none w-6 text-right">{idx + 1}</span>
                        <span className="select-text">{txt}</span>
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

// 재사용 가능한 입력 필드 행 컴포넌트
interface FieldRowProps {
  label: string;
  badge?: string;
  value: string;
  onChange: (val: string) => void;
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
        <label className="text-[11px] font-semibold text-[#9194a1] flex items-center gap-1.5">
          <span>{label}</span>
          {badge && (
            <span className="text-[10px] text-[#cc9166] bg-[#221c17] border border-[#442c1d] px-1 py-0.2 rounded">
              {badge}
            </span>
          )}
        </label>
      </div>
      <div className="relative flex items-center">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full bg-[#121318] text-white text-xs rounded-lg px-3 py-2 pr-10 border transition outline-none ${
            highlight
              ? 'border-[#442c1d] focus:border-[#cc9166] text-amber-200 font-medium'
              : 'border-[#23242c] focus:border-[#cc9166]'
          } placeholder:text-[#555866]`}
        />
        <button
          type="button"
          onClick={onCopy}
          disabled={!value}
          title={`${label} 복사`}
          className="absolute right-1.5 p-1.5 text-[#9194a1] hover:text-white disabled:opacity-30 disabled:pointer-events-none transition rounded hover:bg-[#1f2029]"
        >
          {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
};
