# 東京觀光行程最佳化系統 (Tokyo Trip Optimization System)

這是一個結合了 **React 前端** 與 **FastAPI / OR (作業研究) 後端** 的東京觀光行程最佳化系統。
使用者可以透過網頁輸入想去的本京景點與時間等條件，系統會自動在背景計算最佳的拜訪順序，並將路線、轉乘次數、預估成本視覺化呈現。

## 系統需求
- Node.js (建議 v18 以上)
- Python 3.9+ 

## 🚀 如何啟動專案

本專案分為「前端網站」與「後端 API 伺服器」，需要**開啟兩個終端機 (Terminal) 視窗**分別執行。

### 步驟一：啟動後端 API 伺服器 (FastAPI)

1. 開啟第一個終端機，並進入後端程式資料夾：
   ```bash
   cd MDS_final_project
   ```
2. (強烈建議) 建立並啟動 Python 虛擬環境：
   ```bash
   # macOS / Linux:
   python3 -m venv venv
   source venv/bin/activate
   
   # Windows:
   python -m venv venv
   venv\Scripts\activate
   ```
3. 安裝後端所需套件：
   ```bash
   pip install -r requirements.txt
   ```
4. 啟動 FastAPI 服務：
   ```bash
   uvicorn server:app --reload
   ```
   *(啟動成功後，伺服器預設會運行在 `http://127.0.0.1:8000`)*

---

### 步驟二：啟動前端網站 (React + Vite)

1. 開啟**第二個終端機**，並確保你在專案的**根目錄** (有 `package.json` 的那層目錄)。
2. 安裝前端所需套件：
   ```bash
   npm install
   ```
3. 啟動 Vite 開發伺服器：
   ```bash
   npm run dev
   ```
4. 🎉 **開始使用**：開啟您的瀏覽器，前往終端機顯示的網址（預設通常為 `http://localhost:5173`），即可馬上體驗本系統！

---

## 專案結構簡介
- `/src` 與 `/public`: 前端 React UI 元件與畫面樣式。
- `/MDS_final_project`: 後端 Python 伺服器與最佳化演算法核心。
  - `/data/OR_data/`: 系統所需的靜態資料庫 (包含車站、景點、天氣等資料集)。
  - `/or_model/`: 成本矩陣 (Cost Matrix) 計算與 Open TSP 最佳化演算法實作。
  - `server.py`: FastAPI 啟動檔 (處理前後端溝通)。
