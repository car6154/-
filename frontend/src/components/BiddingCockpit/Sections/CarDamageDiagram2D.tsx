import React from 'react';

export interface CarDamageDiagram2DProps {
  selectedEncar: any;
}

export const CarDamageDiagram2D: React.FC<CarDamageDiagram2DProps> = ({ selectedEncar }) => {
  if (!selectedEncar) return null;

  const checkStatus = (keywords: string[], code?: string) => {
    const dData = selectedEncar?.damageData || {};
    const rep = (selectedEncar?.replaces || []) as string[];
    const fix = (selectedEncar?.repairs || []) as string[];
    const repNames = (selectedEncar?.replaceNames || []) as string[];
    const fixNames = (selectedEncar?.repairNames || []) as string[];

    const normCode = (code || '').toUpperCase().replace(/[\s_\-()]/g, '');
    const lowerKw = keywords.map(k => k.toLowerCase().replace(/[\s_\-()]/g, ''));

    // 1. 코드 직접 대조
    if (normCode) {
      if (rep.some(r => String(r).toUpperCase().replace(/[\s_\-()]/g, '') === normCode)) return '#ef4444';
      if (fix.some(f => String(f).toUpperCase().replace(/[\s_\-()]/g, '') === normCode)) return '#f59e0b';
    }

    // 2. 교환 부위 (replaces 코드 / 한글명 replaceNames) 대조
    for (const r of [...rep, ...repNames]) {
      const rNorm = String(r).toLowerCase().replace(/[\s_\-()]/g, '');
      if (lowerKw.some(k => rNorm.includes(k) || k.includes(rNorm))) return '#ef4444';
    }

    // 3. 판금/수리 부위 (repairs 코드 / 한글명 repairNames) 대조
    for (const f of [...fix, ...fixNames]) {
      const fNorm = String(f).toLowerCase().replace(/[\s_\-()]/g, '');
      if (lowerKw.some(k => fNorm.includes(k) || k.includes(fNorm))) return '#f59e0b';
    }

    // 4. damageData 객체 검사
    for (const [pName, st] of Object.entries(dData)) {
      const norm = pName.toLowerCase().replace(/[\s_\-()]/g, '').replace(/프론트/g, '앞').replace(/리어/g, '뒤').replace(/도어/g, '문').replace(/펜더/g, '휀더').replace(/보닛/g, '후드');
      if (lowerKw.some(k => norm.includes(k) || pName.toLowerCase().includes(k) || k.includes(norm))) {
        if (st === '교환') return '#ef4444';
        if (st === '판금' || st === '용접') return '#f59e0b';
      }
    }

    return '#1e293b';
  };

  const outerParts = [
    { code: 'HOOD', kw: ['후드', '보닛', '본넷', 'hood'], x: 55, y: 20, w: 110, h: 55, label: '후드', full: '후드(보닛)' },
    { code: 'F_FENDER_L', kw: ['앞휀더(좌)', '앞휀더좌', '프론트휀더(좌)', '프론트 휀더(좌)', 'front_fender_left', 'f_fender_l'], x: 15, y: 25, w: 35, h: 65, label: 'F휀', full: '프론트 휀더(좌)' },
    { code: 'F_FENDER_R', kw: ['앞휀더(우)', '앞휀더우', '프론트휀더(우)', '프론트 휀더(우)', 'front_fender_right', 'f_fender_r'], x: 170, y: 25, w: 35, h: 65, label: 'F휀', full: '프론트 휀더(우)' },
    { code: 'SIDE_SILL_L', kw: ['사이드실(좌)', '사이드실좌', '사이드실패널(좌)', '사이드실 패널(좌)', 'side_sill_left', 'side_sill_l'], x: 3, y: 98, w: 9, h: 128, label: '실', full: '사이드실 패널(좌)' },
    { code: 'FRONT_DOOR_L', kw: ['앞문(좌)', '앞문좌', '앞도어(좌)', 'front_door_left', 'front_door_l'], x: 14, y: 100, w: 38, h: 60, label: 'F도', full: '프론트 도어(좌)' },
    { code: 'FRONT_DOOR_R', kw: ['앞문(우)', '앞문우', '앞도어(우)', 'front_door_right', 'front_door_r'], x: 168, y: 100, w: 38, h: 60, label: 'F도', full: '프론트 도어(우)' },
    { code: 'SIDE_SILL_R', kw: ['사이드실(우)', '사이드실우', '사이드실패널(우)', '사이드실 패널(우)', 'side_sill_right', 'side_sill_r'], x: 208, y: 98, w: 9, h: 128, label: '실', full: '사이드실 패널(우)' },
    { code: 'REAR_DOOR_L', kw: ['뒤문(좌)', '뒷문(좌)', '뒤문좌', '뒷문좌', '뒤도어(좌)', 'rear_door_left', 'rear_door_l'], x: 14, y: 165, w: 38, h: 60, label: 'R도', full: '리어 도어(좌)' },
    { code: 'REAR_DOOR_R', kw: ['뒤문(우)', '뒷문(우)', '뒤문우', '뒷문우', '뒤도어(우)', 'rear_door_right', 'rear_door_r'], x: 168, y: 165, w: 38, h: 60, label: 'R도', full: '리어 도어(우)' },
    { code: 'QUARTER_L', kw: ['쿼터(좌)', '뒤휀더(좌)', '쿼터패널(좌)', 'quarter_panel_left', 'quarter_l'], x: 10, y: 230, w: 40, h: 60, label: '쿼터', full: '쿼터 패널(좌)' },
    { code: 'QUARTER_R', kw: ['쿼터(우)', '뒤휀더(우)', '쿼터패널(우)', 'quarter_panel_right', 'quarter_r'], x: 170, y: 230, w: 40, h: 60, label: '쿼터', full: '쿼터 패널(우)' },
    { code: 'ROOF', kw: ['루프', 'roof'], x: 55, y: 80, w: 110, h: 145, label: '루프', full: '루프 패널' },
    { code: 'TRUNK', kw: ['트렁크', '트렁크리드', 'trunk'], x: 55, y: 230, w: 110, h: 60, label: 'TR', full: '트렁크리드' }
  ];

  const innerParts = [
    { code: 'SIDE_MEMBER_FRONT_L', kw: ['사이드멤버(좌)', 'side_member_front_left', 'side_member_front_l'], x: 10, y: 30, w: 40, h: 55, label: 'F멤', full: '프론트 사이드멤버(좌)' },
    { code: 'SIDE_MEMBER_FRONT_R', kw: ['사이드멤버(우)', 'side_member_front_right', 'side_member_front_r'], x: 170, y: 30, w: 40, h: 55, label: 'F멤', full: '프론트 사이드멤버(우)' },
    { code: 'RADIATOR_SUPPORT', kw: ['라디에이터', 'radiator_support', 'radiator'], x: 55, y: 30, w: 110, h: 30, label: 'R.S', full: '라디에이터 서포트' },
    { code: 'CROSS_MEMBER', kw: ['크로스멤버', 'cross_member'], x: 55, y: 65, w: 110, h: 30, label: '크로스', full: '크로스멤버' },
    { code: 'INSIDE_PANEL_L', kw: ['인사이드(좌)', 'inside_panel_left', 'inside_panel_l'], x: 10, y: 100, w: 40, h: 120, label: 'I패', full: '인사이드 패널(좌)' },
    { code: 'INSIDE_PANEL_R', kw: ['인사이드(우)', 'inside_panel_right', 'inside_panel_r'], x: 170, y: 100, w: 40, h: 120, label: 'I패', full: '인사이드 패널(우)' },
    { code: 'SIDE_MEMBER_REAR_L', kw: ['리어사이드멤버(좌)', 'side_member_rear_left', 'side_member_rear_l'], x: 10, y: 230, w: 40, h: 60, label: 'R멤', full: '리어 사이드멤버(좌)' },
    { code: 'SIDE_MEMBER_REAR_R', kw: ['리어사이드멤버(우)', 'side_member_rear_right', 'side_member_rear_r'], x: 170, y: 230, w: 40, h: 60, label: 'R멤', full: '리어 사이드멤버(우)' },
    { code: 'TRUNK_FLOOR', kw: ['트렁크플로어', 'trunk_floor'], x: 55, y: 230, w: 110, h: 60, label: 'T플', full: '트렁크 플로어' },
    { code: 'REAR_PANEL', kw: ['리어패널', 'rear_panel'], x: 55, y: 290, w: 110, h: 20, label: 'R패', full: '리어 패널' }
  ];

  const hasReplaces = (selectedEncar?.replaces?.length > 0) || (selectedEncar?.replaceNames?.length > 0);
  const hasRepairs = (selectedEncar?.repairs?.length > 0) || (selectedEncar?.repairNames?.length > 0);

  return (
    <div className="space-y-2 pt-2 border-t border-[#262833]">
      <div className="flex justify-between items-center text-xs sm:text-sm">
        <span className="font-bold text-white">외판 및 주요골격 상태도</span>
        <div className="flex items-center gap-2.5 text-xs">
          <span className="flex items-center gap-1 text-rose-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block" /> 교환
          </span>
          <span className="flex items-center gap-1 text-amber-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block" /> 판금/용접
          </span>
          <span className="flex items-center gap-1 text-zinc-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-[#1e293b] inline-block border border-slate-700" /> 정상
          </span>
        </div>
      </div>

      {/* Dual SVG Container (외판 + 주요골격 2개 나란히 배치) */}
      <div className="p-3 bg-[#0b1120] rounded-xl border border-[#1e293b] flex flex-col gap-2.5">
        <div className="flex justify-around items-center w-full gap-3">
          {/* Outer Panel SVG */}
          <div className="text-center flex-1">
            <div className="text-xs font-bold text-zinc-400 mb-1">외판</div>
            <svg viewBox="0 0 220 340" className="w-full max-w-[150px] mx-auto">
              <rect x="15" y="10" width="190" height="320" rx="18" fill="#0f172a" stroke="#334155" strokeWidth="1.2" />
              {outerParts.map((p, i) => {
                const fill = checkStatus(p.kw, p.code);
                return (
                  <g key={i}>
                    <title>{p.full}</title>
                    <rect x={p.x} y={p.y} width={p.w} height={p.h} rx="6" fill={fill} stroke="#334155" strokeWidth="1.2" />
                    <text x={p.x + p.w / 2} y={p.y + p.h / 2} textAnchor="middle" dominantBaseline="middle" fontSize={p.w < 15 ? 7.5 : 10} fontWeight="bold" fill="#ffffff">
                      {p.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Inner Structure SVG */}
          <div className="text-center flex-1">
            <div className="text-xs font-bold text-zinc-400 mb-1">주요골격</div>
            <svg viewBox="0 0 220 340" className="w-full max-w-[150px] mx-auto">
              <rect x="15" y="10" width="190" height="320" rx="18" fill="#0f172a" stroke="#334155" strokeWidth="1.2" />
              {innerParts.map((p, i) => {
                const fill = checkStatus(p.kw, p.code);
                return (
                  <g key={i}>
                    <title>{p.full}</title>
                    <rect x={p.x} y={p.y} width={p.w} height={p.h} rx="6" fill={fill} stroke="#334155" strokeWidth="1.2" />
                    <text x={p.x + p.w / 2} y={p.y + p.h / 2} textAnchor="middle" dominantBaseline="middle" fontSize="9" fontWeight="bold" fill="#ffffff">
                      {p.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Accident Details Text List */}
        <div className="pt-2 text-xs border-t border-[#1e293b] flex flex-col gap-1 px-1">
          {hasReplaces && (
            <div className="text-rose-400 font-medium flex items-start gap-1">
              <span className="font-bold shrink-0">🔴 교환:</span>
              <span>
                {(selectedEncar?.replaceNames?.length > 0
                  ? selectedEncar.replaceNames
                  : selectedEncar.replaces
                ).join(', ')}
              </span>
            </div>
          )}
          {hasRepairs && (
            <div className="text-amber-400 font-medium flex items-start gap-1">
              <span className="font-bold shrink-0">🟡 판금/용접:</span>
              <span>
                {(selectedEncar?.repairNames?.length > 0
                  ? selectedEncar.repairNames
                  : selectedEncar.repairs
                ).join(', ')}
              </span>
            </div>
          )}
          {!hasReplaces && !hasRepairs && (
            <div className="text-emerald-400 font-medium flex items-center gap-1">
              <span>🟢 교환/판금 없는 완전무사고 매물입니다.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
