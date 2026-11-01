import React, { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { EncarSoldItem } from '@/components/BiddingCockpit/types';

export interface SoldListingsV2SectionProps {
  encarSoldList: EncarSoldItem[];
  matchedAutoplusList: any[];
  matchedAuctionList: any[];
  carName?: string;
  detailModel?: string;
  yearModel?: number;
  liveMarketStats?: any;
  biddingVerdict?: any;
  defaultTabMode?: 'encar' | 'autoplus' | 'wholesale' | 'none';
}

export const SoldListingsV2Section: React.FC<SoldListingsV2SectionProps> = ({
  encarSoldList = [],
  matchedAutoplusList = [],
  matchedAuctionList = [],
  carName = '',
  detailModel = '',
  yearModel,
  liveMarketStats,
  biddingVerdict,
  defaultTabMode = 'none',
}) => {
  const [soldTabMode, setSoldTabMode] = useState<'encar' | 'autoplus' | 'wholesale' | 'none'>(defaultTabMode);

  // 자사 소매 평균가 및 평균 경과일수
  const avgSellPrice = Number(liveMarketStats?.avg_sell_price || 0);
  const avgDays = Number(liveMarketStats?.avg_days || 0);

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-3 space-y-2 shadow-sm">
      {/* 1. 상단 브리핑 줄 & 우측 완판 평균가·평균 경과일수 지표 행 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-1">
        {/* 좌측: 훅의 biddingVerdict.mainText 브리핑 문장 줄 */}
        <div className="min-w-0 flex-1 text-xs text-zinc-300 flex items-center gap-1.5">
          {biddingVerdict?.mainText ? (
            <span
              className="text-zinc-300 [&>b]:text-white [&>b]:font-bold"
              dangerouslySetInnerHTML={{ __html: biddingVerdict.mainText }}
            />
          ) : (
            <span className="text-zinc-500">시장 완판 데이터 분석 대기 중</span>
          )}
        </div>

        {/* 우측 상단: 자사 소매 평균가 · 평균 경과일수 */}
        <div className="shrink-0 flex items-center gap-1.5 text-[11px] font-mono">
          {avgSellPrice > 0 || avgDays > 0 ? (
            <>
              {avgSellPrice > 0 && (
                <span className="px-2 py-0.5 rounded bg-[#1a1d2b] border border-[#2b3044] text-zinc-300">
                  완판 평균 <strong className="text-amber-300 font-bold">{avgSellPrice.toLocaleString()}만</strong>
                </span>
              )}
              {avgDays > 0 && (
                <span className="px-2 py-0.5 rounded bg-[#1a1d2b] border border-[#2b3044] text-zinc-300">
                  평균 경과일수 <strong className="text-emerald-400 font-bold">{avgDays}일</strong>
                </span>
              )}
            </>
          ) : (
            <span className="px-2 py-0.5 rounded bg-[#161822] border border-[#262938] text-zinc-400">
              완판 데이터 0건
            </span>
          )}
        </div>
      </div>

      {/* 2. 슬림 스트립 3개 서브탭 버튼 바 (기존 탭처럼 border-t 구분선과 슬림 여백) */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none text-xs pt-1.5 border-t border-[#1e2029]">
        <button
          type="button"
          onClick={() => setSoldTabMode(soldTabMode === 'encar' ? 'none' : 'encar')}
          className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
            soldTabMode === 'encar'
              ? 'bg-blue-500/25 text-blue-200 border border-blue-500/40'
              : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
          }`}
        >
          <span>🚗 엔카 팔린매물 ({encarSoldList.length}건) {soldTabMode === 'encar' ? '▲' : '▼'}</span>
        </button>

        <button
          type="button"
          onClick={() => setSoldTabMode(soldTabMode === 'autoplus' ? 'none' : 'autoplus')}
          className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
            soldTabMode === 'autoplus'
              ? 'bg-emerald-500/25 text-emerald-200 border border-emerald-500/40'
              : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
          }`}
        >
          <span>🏢 자사 소매 실적 ({matchedAutoplusList.length}대) {soldTabMode === 'autoplus' ? '▲' : '▼'}</span>
        </button>

        <button
          type="button"
          onClick={() => setSoldTabMode(soldTabMode === 'wholesale' ? 'none' : 'wholesale')}
          className={`px-3 py-1.5 rounded-lg font-bold transition cursor-pointer flex items-center gap-1.5 ${
            soldTabMode === 'wholesale'
              ? 'bg-amber-500/25 text-amber-200 border border-amber-500/40'
              : 'text-zinc-300 hover:text-white hover:bg-[#181a24] border border-transparent'
          }`}
        >
          <span>📦 자사 도매 실적 ({matchedAuctionList.length}대) {soldTabMode === 'wholesale' ? '▲' : '▼'}</span>
        </button>
      </div>

      {/* 3. 탭 본문 영역 */}
      {/* 3-1. 엔카 팔린매물 탭 */}
      {soldTabMode === 'encar' && (
        <div className="space-y-2 pt-2 border-t border-[#1e2029]">
          <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
            <span>엔카 최근 판매완료(광고종료) 기록 (<strong className="text-blue-400 font-bold">{encarSoldList.length}건</strong>)</span>
            <span className="text-xs text-amber-300 font-medium">※ 실측 스냅샷 기반</span>
          </div>
          {encarSoldList.length > 0 ? (
            <div className="overflow-x-auto max-h-72 overflow-y-auto border border-[#262833] rounded-xl">
              <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                  <tr>
                    <th className="p-2.5">차량정보</th>
                    <th className="p-2.5 text-center">연식(년/월)</th>
                    <th className="p-2.5 text-right">주행거리</th>
                    <th className="p-2.5 text-center">판매구분</th>
                    <th className="p-2.5 text-right">소매 판매가</th>
                    <th className="p-2.5 text-right">판매일</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                  {encarSoldList.map((s) => (
                    <tr key={s.id} className="hover:bg-[#14151c] transition">
                      <td className="p-2.5 text-white font-bold text-xs sm:text-sm">
                        {s.encarUrl ? (
                          <a
                            href={s.encarUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-blue-400 hover:underline inline-flex items-center gap-1.5"
                            title="엔카 원본 상세페이지 보기"
                          >
                            <span>{s.carName || s.subModel || '차량정보 없음'}</span>
                            <ExternalLink className="w-3 h-3 text-zinc-500 hover:text-blue-400 shrink-0 inline" />
                          </a>
                        ) : (
                          <span>{s.carName || s.subModel || '차량정보 없음'}</span>
                        )}
                      </td>
                      <td className="p-2.5 text-center text-xs text-blue-400 font-mono">
                        {s.year ? (s.year.includes('식') || s.year.includes('년') ? s.year : `${s.year}년`) : '-'}
                      </td>
                      <td className="p-2.5 text-right text-xs text-white font-mono">
                        {s.mileage > 0 ? `${s.mileage.toLocaleString()}km` : '-'}
                      </td>
                      <td className="p-2.5 text-center text-xs text-zinc-400 font-mono">
                        {s.saleType || '-'}
                      </td>
                      <td className="p-2.5 text-right font-bold text-emerald-400 font-mono">
                        {s.finalPrice > 0 ? `${s.finalPrice.toLocaleString()}만` : '-'}
                      </td>
                      <td className="p-2.5 text-right text-xs text-zinc-400 font-mono">
                        {s.soldDate || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm text-zinc-400 font-medium">
              💡 최근 90일 내 매칭된 엔카 판매완료(광고종료) 스냅샷 이력이 없습니다.
            </div>
          )}
        </div>
      )}

      {/* 3-2. 자사 소매 실적 탭 */}
      {soldTabMode === 'autoplus' && (
        <div className="space-y-2 pt-2 border-t border-[#1e2029]">
          <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
            <span>자사 소매 실적 DB 매물 (<strong className="text-emerald-400 font-bold">{matchedAutoplusList.length}대</strong>)</span>
            <span className="text-xs text-zinc-400">엔카 광고 집행 순수 소매 완판 데이터</span>
          </div>

          {/* 자사 DB 필터 조건 투명 공개 박스 */}
          <div className="bg-[#12131b] border border-[#232634] rounded-xl p-3 text-xs space-y-2">
            <div className="flex items-center justify-between text-zinc-300 border-b border-[#202230] pb-2">
              <div className="flex items-center gap-1.5 font-bold text-emerald-400">
                <span>🔍</span>
                <span>자사 원장(2,964건) 매칭 필터 기준</span>
              </div>
              <span className="text-[11px] text-zinc-400">
                매칭 결과: <strong className={matchedAutoplusList.length > 0 ? "text-emerald-400" : "text-amber-400"}>{matchedAutoplusList.length}대</strong>
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-zinc-300">
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">조회 차종</div>
                <div className="font-bold text-white truncate" title={carName}>{carName || '-'}</div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">세부 모델/트림</div>
                <div className="font-bold text-emerald-400 truncate" title={detailModel}>{detailModel || '기본형 (전체)'}</div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">연식 대역 (±1년)</div>
                <div className="font-bold text-blue-400 font-mono">
                  {yearModel ? `${Number(yearModel) - 1}년 ~ ${Number(yearModel) + 1}년` : '연식 전체'}
                </div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">매칭 판정</div>
                <div className="font-bold text-amber-300 truncate font-mono">
                  {liveMarketStats?.matched_tier || (matchedAutoplusList.length > 0 ? '정밀 매칭' : '매칭 실적 없음')}
                </div>
              </div>
            </div>
            {liveMarketStats?.year_diff_note && (
              <div className="text-[11px] text-amber-300 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                ℹ️ {liveMarketStats.year_diff_note}
              </div>
            )}
          </div>

          {matchedAutoplusList.length > 0 ? (
            <div className="overflow-x-auto max-h-64 overflow-y-auto border border-[#262833] rounded-xl">
              <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                  <tr>
                    <th className="p-2.5">판매일자</th>
                    <th className="p-2.5">차량번호</th>
                    <th className="p-2.5">세부모델</th>
                    <th className="p-2.5">연식</th>
                    <th className="p-2.5 text-right">주행거리</th>
                    <th className="p-2.5 text-right">매입가</th>
                    <th className="p-2.5 text-right">소매 판매가</th>
                    <th className="p-2.5 text-center">경과일수</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                  {matchedAutoplusList.map((item: any, idx: number) => {
                    const rawBuy = Number(item.buyPrice);
                    const buyMan = rawBuy ? (rawBuy >= 100000 ? Math.round(rawBuy / 10000) : Math.round(rawBuy)) : null;
                    
                    const rawSell = Number(item.sellPrice);
                    const sellMan = rawSell ? (rawSell >= 100000 ? Math.round(rawSell / 10000) : Math.round(rawSell)) : null;

                    return (
                      <tr key={item.id || idx} className="hover:bg-[#14151c]">
                        <td className="p-2.5 text-xs text-zinc-400 font-mono">{item.soldDate || item.regDate || '-'}</td>
                        <td className="p-2.5 font-mono text-white font-bold">{item.carNumber || item.plate || '-'}</td>
                        <td className="p-2.5 text-white font-semibold text-xs sm:text-sm">{item.subModel || item.carName || '-'}</td>
                        <td className="p-2.5 text-xs text-blue-400 font-mono">{item.year ? `${item.year}년` : '-'}</td>
                        <td className="p-2.5 text-right text-xs text-white font-mono">{item.mileage > 0 ? `${Number(item.mileage).toLocaleString()}km` : '-'}</td>
                        <td className="p-2.5 text-right text-zinc-300 font-mono">
                          {buyMan !== null ? `${buyMan.toLocaleString()}만` : '-'}
                        </td>
                        <td className="p-2.5 text-right text-emerald-400 font-bold font-mono">
                          {sellMan !== null ? `${sellMan.toLocaleString()}만` : '-'}
                        </td>
                        <td className="p-2.5 text-center font-mono text-xs">{item.stockDays ? `${item.stockDays}일` : '0일'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm space-y-1.5">
              <div className="text-amber-400 font-bold flex items-center justify-center gap-1.5">
                <span>⚠️</span>
                <span>자사 소매 실적 0건 (필터 조건 매칭 매물 없음)</span>
              </div>
              <div className="text-zinc-400 text-xs leading-relaxed max-w-lg mx-auto">
                자사 전체 정산 원장(2,964건) 중 차종 <strong className="text-zinc-200">[{carName}]</strong>, 
                세부모델 <strong className="text-zinc-200">[{detailModel || '기본형'}]</strong>, 
                연식 대역 <strong className="text-zinc-200">[{yearModel ? `${Number(yearModel) - 1}~${Number(yearModel) + 1}년` : '전체'}]</strong> 
                조건과 100% 일치하는 소매 완판 매물이 없습니다.
              </div>
              <div className="text-[11px] text-zinc-500 pt-1">
                💡 팁: 해당 세부모델의 과거 자사 소매 실적이 없으므로, 상단 <strong className="text-blue-400">엔카 팔린매물 ({encarSoldList.length}건)</strong>의 시장 실거래 시세를 표준으로 참고하세요.
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3-3. 자사 도매 실적 탭 */}
      {soldTabMode === 'wholesale' && (
        <div className="space-y-2 pt-2 border-t border-[#1e2029]">
          <div className="flex justify-between items-center text-xs sm:text-sm text-zinc-300">
            <span>자사 도매 실적 DB 매물 (<strong className="text-amber-400 font-bold">{matchedAuctionList.length}대</strong>)</span>
            <span className="text-xs text-zinc-400">도매/경매 낙찰 출고 데이터 (도매 바닥 시세)</span>
          </div>

          {/* 자사 도매 필터 조건 투명 공개 박스 */}
          <div className="bg-[#12131b] border border-[#232634] rounded-xl p-3 text-xs space-y-2">
            <div className="flex items-center justify-between text-zinc-300 border-b border-[#202230] pb-2">
              <div className="flex items-center gap-1.5 font-bold text-amber-400">
                <span>🔍</span>
                <span>자사 경매/도매 원장 매칭 필터 기준</span>
              </div>
              <span className="text-[11px] text-zinc-400">
                매칭 결과: <strong className={matchedAuctionList.length > 0 ? "text-emerald-400" : "text-amber-400"}>{matchedAuctionList.length}대</strong>
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-zinc-300">
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">조회 차종</div>
                <div className="font-bold text-white truncate" title={carName}>{carName || '-'}</div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">세부 모델/트림</div>
                <div className="font-bold text-amber-400 truncate" title={detailModel}>{detailModel || '기본형 (전체)'}</div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">연식 대역 (±1년)</div>
                <div className="font-bold text-blue-400 font-mono">
                  {yearModel ? `${Number(yearModel) - 1}년 ~ ${Number(yearModel) + 1}년` : '연식 전체'}
                </div>
              </div>
              <div className="bg-[#0b0c10] p-2 rounded-lg border border-[#1d202d]">
                <div className="text-[10px] text-zinc-500">매칭 판정</div>
                <div className="font-bold text-amber-300 truncate font-mono">
                  {liveMarketStats?.matched_tier || (matchedAuctionList.length > 0 ? '정밀 매칭' : '매칭 실적 없음')}
                </div>
              </div>
            </div>
          </div>

          {matchedAuctionList.length > 0 ? (
            <div className="overflow-x-auto max-h-64 overflow-y-auto border border-[#262833] rounded-xl">
              <table className="w-full text-left text-xs sm:text-sm text-zinc-200">
                <thead className="bg-[#14151b] text-xs text-zinc-400 sticky top-0 uppercase border-b border-[#262833]">
                  <tr>
                    <th className="p-2.5">판매일자</th>
                    <th className="p-2.5">차량번호</th>
                    <th className="p-2.5">세부모델</th>
                    <th className="p-2.5">연식</th>
                    <th className="p-2.5 text-right">주행거리</th>
                    <th className="p-2.5 text-right">매입가</th>
                    <th className="p-2.5 text-right">도매 낙찰가</th>
                    <th className="p-2.5 text-center">경과일수</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232634] bg-[#0a0b0e]">
                  {matchedAuctionList.map((item: any, idx: number) => {
                    const rawBuy = Number(item.buyPrice);
                    const buyMan = rawBuy ? (rawBuy >= 100000 ? Math.round(rawBuy / 10000) : Math.round(rawBuy)) : null;
                    
                    const rawSell = Number(item.sellPrice);
                    const sellMan = rawSell ? (rawSell >= 100000 ? Math.round(rawSell / 10000) : Math.round(rawSell)) : null;

                    return (
                      <tr key={item.id || idx} className="hover:bg-[#14151c]">
                        <td className="p-2.5 text-xs text-zinc-400 font-mono">{item.soldDate || item.regDate || '-'}</td>
                        <td className="p-2.5 font-mono text-white font-bold">{item.carNumber || item.plate || '-'}</td>
                        <td className="p-2.5 text-white font-semibold text-xs sm:text-sm">{item.subModel || item.carName || '-'}</td>
                        <td className="p-2.5 text-xs text-blue-400 font-mono">{item.year ? `${item.year}년` : '-'}</td>
                        <td className="p-2.5 text-right text-xs text-white font-mono">{item.mileage > 0 ? `${Number(item.mileage).toLocaleString()}km` : '-'}</td>
                        <td className="p-2.5 text-right text-zinc-300 font-mono">
                          {buyMan !== null ? `${buyMan.toLocaleString()}만` : '-'}
                        </td>
                        <td className="p-2.5 text-right text-amber-400 font-bold font-mono">
                          {sellMan !== null ? `${sellMan.toLocaleString()}만` : '-'}
                        </td>
                        <td className="p-2.5 text-center font-mono text-xs">{item.stockDays ? `${item.stockDays}일` : '0일'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-4 text-center bg-[#0a0b0e] rounded-xl border border-[#262833] text-xs sm:text-sm space-y-1.5">
              <div className="text-amber-400 font-bold flex items-center justify-center gap-1.5">
                <span>⚠️</span>
                <span>자사 도매 실적 0건 (필터 조건 매칭 매물 없음)</span>
              </div>
              <div className="text-zinc-400 text-xs leading-relaxed max-w-lg mx-auto">
                자사 경매/도매 원장 중 차종 <strong className="text-zinc-200">[{carName}]</strong>, 
                세부모델 <strong className="text-zinc-200">[{detailModel || '기본형'}]</strong>, 
                연식 대역 <strong className="text-zinc-200">[{yearModel ? `${Number(yearModel) - 1}~${Number(yearModel) + 1}년` : '전체'}]</strong> 
                조건의 출고 이력이 없습니다.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
