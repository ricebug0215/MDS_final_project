import React, { useState } from 'react';

// 接收從 App.jsx 傳進來的 props
export default function TripPlanner({ setResultData, setIsLoading, isLoading }) {
  const [attractionList, setAttractionList] = useState([{ name: '', stayMinutes: 60 }]);
  const [startPoint, setStartPoint] = useState('上野');
  const [endPoint, setEndPoint] = useState('新宿');
  const [startTime, setStartTime] = useState('10:00');
  const [endTime, setEndTime] = useState('19:00');
  const [budget, setBudget] = useState(2500);
  const [draggedItemIndex, setDraggedItemIndex] = useState(null);
  
  // 偏好設定
  const [prefs, setPrefs] = useState({
    avoidCrowd: false,
    shortestTime: false,
    lowestCost: false,
    fewTransfers: false,
    rainyDayPreferred: false
  });

  const handlePrefChange = (e) => {
    const { name, checked } = e.target;
    setPrefs(prev => ({ ...prev, [name]: checked }));
  };

  const handleAttractionChange = (index, field, value) => {
    const newList = [...attractionList];
    newList[index][field] = value;
    setAttractionList(newList);
  };

  const addAttraction = () => {
    setAttractionList([...attractionList, { name: '', stayMinutes: 60 }]);
  };

  const removeAttraction = (index) => {
    const newList = attractionList.filter((_, i) => i !== index);
    setAttractionList(newList);
  };

  const handleDragStart = (index, e) => {
    setDraggedItemIndex(index);
    // 讓拖曳效果看起來順暢一點
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnter = (index, e) => {
    e.preventDefault();
    if (draggedItemIndex === null || draggedItemIndex === index) return;
    
    // 交換位置
    const newList = [...attractionList];
    const item = newList[draggedItemIndex];
    newList.splice(draggedItemIndex, 1);
    newList.splice(index, 0, item);
    
    setDraggedItemIndex(index);
    setAttractionList(newList);
  };

  const handleDragEnd = () => {
    setDraggedItemIndex(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);      // 開始 Loading
    setResultData(null);     // 清除舊的結果

    // 過濾掉未輸入名稱的景點
    const validAttractions = attractionList.filter(a => a.name.trim() !== '');

    const payload = {
      start_point: startPoint,
      end_point: endPoint,
      start_time: startTime,
      end_time: endTime,
      places: validAttractions.map(a => ({
        name: a.name.trim(),
        stay_minutes: parseInt(a.stayMinutes, 10)
      })),
      preferences: {
        avoid_crowd: prefs.avoidCrowd,
        shortest_time: prefs.shortestTime,
        lowest_cost: prefs.lowestCost,
        few_transfers: prefs.fewTransfers,
        rainy_day: prefs.rainyDayPreferred
      },
      budget_yen: parseInt(budget, 10)
    };

    try {
      // 2. 將這裡換成你朋友後端 API 的真實網址 (例如 http://127.0.0.1:8000/api/plan)
      const apiUrl = '/api/plan'; 

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      // 檢查 HTTP 狀態碼是否為 200 OK
      if (!response.ok) {
        throw new Error(`伺服器錯誤: ${response.status}`);
      }

      // 3. 解析後端回傳的 JSON (也就是你上一題貼給我的那份最佳化結果)
      const data = await response.json();
      
      // 4. 將拿到的資料存入 App.jsx 的狀態中，畫面就會自動渲染！
      setResultData(data);

    } catch (error) {
      console.error("API 連線失敗:", error);
      alert("連線失敗！請打開 F12 開發者工具查看 Console 錯誤訊息。");
    } finally {
      setIsLoading(false); // 結束 Loading
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-4">
      <h2 className="text-3xl font-bold mb-6 text-gray-800 text-center">開始規劃您的東京之旅</h2>
      
      <form onSubmit={handleSubmit} className="mb-2 flex flex-col items-center">
        
        {/* 起迄點與時間設定 */}
        <div className="w-full max-w-2xl mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block mb-2 font-medium text-gray-700">出發起點</label>
            <input type="text" value={startPoint} onChange={e => setStartPoint(e.target.value)} placeholder="如: 上野" className="w-full bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 text-gray-700 font-mono" required />
          </div>
          <div className="flex-1">
            <label className="block mb-2 font-medium text-gray-700">結束終點</label>
            <input type="text" value={endPoint} onChange={e => setEndPoint(e.target.value)} placeholder="如: 新宿" className="w-full bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 text-gray-700 font-mono" required />
          </div>
        </div>

        <div className="w-full max-w-2xl mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block mb-2 font-medium text-gray-700">出發時間</label>
            <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} className="w-full bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 text-gray-700" required />
          </div>
          <div className="flex-1">
            <label className="block mb-2 font-medium text-gray-700">結束時間</label>
            <input type="time" value={endTime} onChange={e => setEndTime(e.target.value)} className="w-full bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 text-gray-700" required />
          </div>
        </div>

        <label className="block mb-4 font-medium text-gray-700 text-center text-lg">
          你想去哪些景點與停留時間？
        </label>
        
        <div className="w-full max-w-2xl mb-6 flex flex-col gap-4">
          {attractionList.map((attraction, index) => (
            <div 
              key={index} 
              draggable
              onDragStart={(e) => handleDragStart(index, e)}
              onDragEnter={(e) => handleDragEnter(index, e)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => e.preventDefault()}
              className={`flex gap-2 items-center bg-white/50 p-3 rounded-2xl shadow-sm border ${draggedItemIndex === index ? 'border-blue-500 opacity-50' : 'border-gray-200'} transition-all cursor-move`}
            >
              <input 
                type="text" 
                value={attraction.name}
                onChange={(e) => handleAttractionChange(index, 'name', e.target.value)}
                placeholder="景點名稱 (例: Shibuya...)"
                className="flex-grow bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 focus:outline-none transition-all text-gray-700 font-mono"
                required={index === 0}
              />
              <div className="flex items-center gap-2">
                <input 
                  type="number" 
                  value={attraction.stayMinutes}
                  onChange={(e) => handleAttractionChange(index, 'stayMinutes', e.target.value)}
                  min="10"
                  step="5"
                  className="w-24 bg-white border border-gray-300 p-3 rounded-xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 focus:outline-none transition-all text-gray-700 text-center"
                  required
                />
                <span className="text-gray-600 font-medium whitespace-nowrap">分鐘</span>
              </div>
              {attractionList.length > 1 && (
                <button 
                  type="button" 
                  onClick={() => removeAttraction(index)}
                  className="p-3 text-red-500 hover:bg-red-50 rounded-xl transition-colors font-medium"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
          <button 
            type="button" 
            onClick={addAttraction}
            className="w-full py-3 border-2 border-dashed border-gray-300 text-gray-500 rounded-2xl hover:border-blue-500 hover:text-blue-500 transition-colors font-medium"
          >
            + 新增景點
          </button>
        </div>
        
        <div className="w-full max-w-2xl mb-8 flex flex-col gap-6">
            <div className="flex flex-col items-center">
                <label className="block mb-2 font-medium text-gray-700 text-center">
                  交通預算上限 (日圓)
                </label>
                <input 
                    type="number" 
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                    min="100"
                    step="100"
                    placeholder="2500"
                    className="w-full sm:w-1/2 bg-white/70 border border-gray-300 p-3 rounded-full focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 focus:outline-none transition-all shadow-sm text-gray-700 text-center"
                    required
                />
            </div>

            <div className="bg-white/50 p-6 rounded-2xl shadow-sm border border-gray-200">
              <label className="block mb-4 font-medium text-gray-700 text-lg">個人偏好設定</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="avoidCrowd" checked={prefs.avoidCrowd} onChange={handlePrefChange} className="w-5 h-5 text-blue-600 rounded" />
                  <span className="text-gray-700">避開擁擠車站</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="shortestTime" checked={prefs.shortestTime} onChange={handlePrefChange} className="w-5 h-5 text-blue-600 rounded" />
                  <span className="text-gray-700">最短交通時間優先</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="lowestCost" checked={prefs.lowestCost} onChange={handlePrefChange} className="w-5 h-5 text-blue-600 rounded" />
                  <span className="text-gray-700">降低交通費用優先</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="fewTransfers" checked={prefs.fewTransfers} onChange={handlePrefChange} className="w-5 h-5 text-blue-600 rounded" />
                  <span className="text-gray-700">減少轉乘次數</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" name="rainyDayPreferred" checked={prefs.rainyDayPreferred} onChange={handlePrefChange} className="w-5 h-5 text-blue-600 rounded" />
                  <span className="text-gray-700">雨天模式 (減少戶外步行)</span>
                </label>
              </div>
            </div>
        </div>

        <button 
          type="submit" 
          disabled={isLoading}
          className="w-full max-w-sm bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold px-8 py-4 rounded-full hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed shadow-md hover:shadow-lg transition-all active:scale-[0.98] text-lg"
        >
          {isLoading ? '演算中...' : '產生最佳行程'}
        </button>
      </form>
    </div>
  );
}