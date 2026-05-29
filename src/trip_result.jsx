import React, { useState } from 'react';

// 負責顯示可折疊的路線名稱組件
function RoutePathDisplay({ pathNames }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!pathNames || pathNames.length === 0) return null;

  // 如果只有不到3站，直接全部顯示
  if (pathNames.length <= 3) {
    return (
      <li className="text-xs font-mono bg-gray-200 p-2 rounded inline-block mt-1 whitespace-normal break-words">
        路線: {pathNames.join(' → ')}
      </li>
    );
  }

  // 摺疊時的顯示：起點 → ... (N站) ... → 終點
  const collapsedText = `${pathNames[0]} → ... (共 ${pathNames.length} 站) ... → ${pathNames[pathNames.length - 1]}`;

  return (
    <li className="text-xs bg-gray-200 p-2 rounded block mt-1 hover:bg-gray-300 transition-colors cursor-pointer select-none" onClick={() => setIsExpanded(!isExpanded)}>
      <div className="flex items-center text-gray-700 font-mono">
        <span className="font-semibold text-blue-600 mr-2">{isExpanded ? '▼ 收起路線' : '▶ 展開路線'}</span>
        <span className="flex-1 whitespace-normal break-words">
          {isExpanded ? pathNames.join(' → ') : collapsedText}
        </span>
      </div>
    </li>
  );
}

export default function TripResult({ resultData }) {
  // 防呆：如果沒有資料則不渲染
  if (!resultData || (resultData.status !== 'optimal' && resultData.status !== 'optimal_with_violation')) return null;

  const { totals, legs, ordered_attraction_names, constraints } = resultData;

  // 輔助函式：將分鐘數轉為 "X 小時 Y 分"
  const formatTime = (mins) => {
    const h = Math.floor(mins / 60);
    const m = Math.round(mins % 60);
    return h > 0 ? `${h} 小時 ${m} 分鐘` : `${m} 分鐘`;
  };

  return (
    <div className="max-w-3xl mx-auto p-6 bg-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">最佳行程排定結果</h2>

      {/* 如果違反時間或預算限制，顯示警告 */}
      {constraints && !constraints.feasible && (
        <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <h3 className="text-md font-bold text-red-800 mb-1">⚠️ 行程限制提醒</h3>
          <p className="text-sm text-red-700">
            您設定的時間或預算可能不足以跑完所有行程！
            {constraints.binding.includes('time') && ` (目前排定需 ${Math.round(totals.total_time_min)} 分鐘，超過設定的 ${constraints.time_budget_min} 分鐘)`}
            {constraints.binding.includes('budget') && ` (目前排定需 ${totals.total_fare_yen} 日圓，超過預算的 ${constraints.budget_yen} 日圓)`}
          </p>
        </div>
      )}

      {resultData.reasoning && (
        <div className="mb-8 p-5 bg-yellow-50 rounded-lg border border-yellow-200">
          <h3 className="text-lg font-bold text-yellow-800 mb-2">💡 推薦原因與系統取捨</h3>
          <p className="text-gray-700 leading-relaxed">{resultData.reasoning}</p>
        </div>
      )}

      {/* 總結面板 (Dashboard) */}
      <div className="grid grid-cols-3 gap-4 mb-8 bg-blue-50 p-4 rounded-lg border border-blue-100">
        <div className="text-center">
          <p className="text-sm text-gray-500">總花費時間</p>
          <p className="text-xl font-bold text-blue-700">{formatTime(totals.total_time_min)}</p>
        </div>
        <div className="text-center border-l border-r border-blue-200">
          <p className="text-sm text-gray-500">交通預估</p>
          <p className="text-xl font-bold text-blue-700">¥ {totals.total_fare_yen}</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-gray-500">景點停留</p>
          <p className="text-xl font-bold text-blue-700">{formatTime(totals.stay_time_min)}</p>
        </div>
      </div>

      {/* 行程時間軸 (Timeline) */}
      <div className="relative border-l-2 border-gray-200 ml-4 space-y-8">
        {legs.map((leg, index) => {
          const isFirst = leg.from === '__start__';
          const isLast = leg.to === '__end__';
          const attractionName = !isLast ? ordered_attraction_names[index] : '行程結束';

          return (
            <div key={index} className="relative pl-6">
              {/* 交通段 (Transit) */}
              <div className="mb-6">
                <div className="absolute -left-[9px] top-2 w-4 h-4 rounded-full bg-gray-300 border-2 border-white"></div>
                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-sm">
                  <div className="flex items-center text-gray-600 mb-2">
                    <span className="material-icons text-base mr-1">directions_subway</span>
                    <span className="font-medium mr-4">交通移動 ({formatTime(leg.total_leg_time_min)})</span>
                    <span>車資: ¥{leg.fare_yen}</span>
                  </div>
                  <ul className="list-disc list-inside text-gray-500 ml-1 space-y-1">
                    <li>地鐵: {formatTime(leg.metro_time_min)} | 步行: {formatTime(leg.walk_time_min)}</li>
                    {leg.transfer_count > 0 && <li>轉乘次數: {leg.transfer_count} 次</li>}
                    {/* 若有下雨懲罰，動態顯示警告 */}
                    {leg.rain_penalty_min > 0 && (
                      <li className="text-orange-500">雨天戶外延遲風險: +{Math.round(leg.rain_penalty_min)} 分鐘</li>
                    )}
                    
                    {/* 使用折疊站名組件 */}
                    {leg.route_path_names ? (
                      <RoutePathDisplay pathNames={leg.route_path_names} />
                    ) : (
                      <li className="text-xs font-mono bg-gray-200 p-1 rounded inline-block mt-1">
                        路線: {leg.route_path}
                      </li>
                    )}
                  </ul>
                </div>
              </div>

              {/* 景點段 (Attraction) - 最後一個結束節點不顯示景點卡片 */}
              {!isLast && (
                <div className="relative">
                  <div className="absolute -left-[11px] top-5 w-5 h-5 rounded-full bg-blue-500 border-4 border-white shadow"></div>
                  <div className="bg-white p-4 rounded-lg border-2 border-blue-100 shadow-sm hover:border-blue-300 transition-colors">
                    <h3 className="text-lg font-bold text-gray-800">
                      <span className="text-blue-500 mr-2">{index + 1}.</span> 
                      {attractionName}
                    </h3>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}