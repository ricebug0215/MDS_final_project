import React, { useState } from 'react'
import TripPlanner from './trip_planner'
import TripResult from './trip_result'

function App() {
  // 狀態 1：儲存 OR 模型的真實計算結果 (初始為空)
  const [resultData, setResultData] = useState(null);
  // 狀態 2：控制 Loading 動畫
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 via-white to-purple-100 relative">
      {/* 左上角的標題 */}
      <div className="absolute top-6 left-8 text-left">
        <h1 className="text-3xl font-extrabold text-blue-800 drop-shadow-sm">
          Tokyo Tourism
        </h1>
        <p className="text-sm text-blue-600 mt-1 font-medium tracking-wide">
          Intelligence Itinerary Planner
        </p>
      </div>

      <div className="pt-24 pb-10">
        {/* 將改變狀態的函數 (setResultData, setIsLoading) 當作 props 傳給表單元件 */}
        <TripPlanner 
          setResultData={setResultData} 
          setIsLoading={setIsLoading} 
          isLoading={isLoading} 
        />
        
        {/* 如果正在載入，顯示提示文字 */}
        {isLoading && (
          <div className="text-center mt-8 text-blue-600 font-bold animate-pulse">
            AI 正在為您計算最佳路線，請稍候...
          </div>
        )}

        {/* 如果有資料且沒有在載入，才顯示結果 */}
        {!isLoading && resultData && (
          <div className="mt-8">
            <TripResult resultData={resultData} />
          </div>
        )}
      </div>
    </div>
  )
}

export default App