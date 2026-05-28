# 東京觀光行程最佳化（OR）— 期末專案

本專案實作一個**東京觀光行程最佳化模組**。使用者輸入起點、終點、想去的景點、出發時間、結束時間、預算與偏好後，系統會使用 **OR 模型**計算景點**造訪順序**，並輸出每段移動時間、票價、轉乘次數、擁擠程度與天氣影響等資訊。

**本系統不是景點推薦系統**（不從 800+ 景點中幫你「挑哪些值得去」），而是**景點排序最佳化模組**：在**使用者已選定**的景點集合中，找出整體移動成本較低的拜訪順序與捷運路線摘要。

```
期末專案/
├── README.md                   ← 本文件
├── data/OR_data/               ← 靜態參考 CSV
├── or_model/                   ← 成本矩陣 + Open TSP 求解
├── schemas/trip_request.json   ← UI → OR 請求格式
├── run_or_demo.py              ← 本地 demo
└── output_or_demo.json         ← demo 輸出（執行後產生）
```

---

## Problem Statement

旅遊者在規劃東京一日行程時，往往需要同時考慮：

- 景點**順序**（先去哪、後去哪）
- 捷運**移動時間**與**轉乘次數**
- **交通費**
- 車站**擁擠程度**
- **天氣**與戶外景點的不便
- 總行程**時間窗**與**預算**上限

若只靠直覺或地圖上的直線距離排序，容易忽略「繞路、轉乘、等車、雨天步行」等整體成本，導致實際旅途更累、更貴或更擠。

因此本專案將問題建模為：

| 項目 | 說明 |
|------|------|
| 輸入 | 使用者**已選定**的景點清單 + 起訖站 + 時間窗 + 預算 + 偏好權重 |
| OR 的任務 | 決定景點**拜訪順序**（Open TSP） |
| 不做的事 | 不從全庫景點中自動篩選子集；不產生自然語言導覽 |
| 目標 | 降低**加權移動成本**（時間、票價、擁擠、下雨懲罰的折衷） |

OR 模組**不是**依直線距離或地圖直覺排序，而是先建立 **pairwise cost matrix `c_ij`**，再在所有可能的拜訪順序中求解**組合最佳化**（Open TSP）。

---

## 系統架構與分工

```
使用者（UI）
    │  POST JSON（景點、預算、偏好）
    ▼
OR 模組（or_model/）          ← 算最佳順序 + 每段捷運 leg
    │  JSON 結果
    ▼
AI 說明層                     ← 解釋 OR 輸出（不應改順序）
    ▼
使用者
```

| Layer | Responsibility | Not Responsible For |
|-------|----------------|---------------------|
| UI | 選景點、收集起訖站、時間、預算、偏好 | 不計算路線或排序 |
| OR | 最佳化造訪順序、計算每段 leg 的時間/票價/路線 | 不產生自然語言 |
| AI | 依 OR 結果向使用者解釋「為何此順序」 | 不修改 `ordered_attraction_ids` |

---

## OR Formulation

本問題為 **Open TSP（開放式旅行推銷員問題）**：路徑從指定起點站出發，造訪每個選定景點恰好一次，最後抵達指定終點站；**不需要**回到起點（與傳統 closed TSP 不同）。

若 `start_station_id` 與 `end_station_id` 為**同一實體車站**（例如皆為 `G16` 上野），輸出可能最後回到同一站——這是因為**使用者指定相同終點**，不是模型要求 **closed tour**（環状回路）。

> 公式以 `text` 程式碼區塊撰寫，在 GitHub / Cursor Preview 均可正常顯示。

### Sets / Nodes

節點集合 `V = {0, 1, …, n−1}`，其中 `n = |選定景點| + 2`：

| 節點 | 類型 | 說明 |
|------|------|------|
| `0` | Start node | 使用者指定起點站 `start_station_id` |
| `1, …, n−2` | Attraction nodes | 使用者選定的景點 |
| `n−1` | End node | 使用者指定終點站 `end_station_id` |

### Decision Variable

```text
x_ij = 1   if the route directly travels from node i to node j
x_ij = 0   otherwise

∀ i, j ∈ V,  i ≠ j
```

中文：`x_ij = 1` 代表路線中**存在**「從 i 直接走到 j」這一段弧；否則為 0。

（實作上未建立 MILP 的 `x_ij` 變數，而以 TSP 演算法求等價路徑；見 [求解器設計]。）

### Objective Function

```text
minimize    Σ_{i∈V} Σ_{j∈V, j≠i}  c_ij · x_ij
```

模型選出一組弧，使整條路徑的**加權總成本**最小。每一段 `c_ij` 為單段移動的綜合成本（見下）。

### Arc Cost

對每一對節點 `(i, j)`，預先計算：

```text
c_ij = w_time × T_ij + w_fare × fare_ij + w_crowd × crowd_ij × 60 + rain_penalty_ij
```

**`T_ij` 是什麼？**  
`T_ij` 表示從節點 i 走到節點 j 這一段的**移動時間（分鐘）**，會乘上 `w_time` 進入目標函數，也會在求解後加總成 `travel_time_min`。它不是票價或擁擠分數本身，而是「這一段路上大概要花多久」的估計。

**`T_ij` 由四部分加總：**

| 項 | 內容 |
|----|------|
| `walk_ij` | 景點與最近捷運站之間的步行（下雨時會放大） |
| `metro_ij` | 捷運車上 + 轉乘時間，以及下方的**超轉乘軟懲罰** |
| `wait_ij` | 依時段估計的等車時間（`train_frequency_by_time`） |
| `outdoor_ij` | 雨天且目的地為戶外景點時的額外分鐘（目前約 15 分） |

**什麼是「超轉乘軟懲罰」？**

- `tc_ij`：該段捷運路線的轉乘次數（來自 `station_pair_routes.transfer_count`）
- `K`：使用者設定的 `max_transfers`（例如 3，代表「希望不要轉太多趟」）

若實際轉乘次數 **超過** `K`，程式**不會**禁止這條路（那是硬限制），而是在 `metro_ij` 上**多加時間**：

```text
額外分鐘 = 12 × max(0, tc_ij − K)
```

| 情況 | 額外懲罰 |
|------|----------|
| `tc_ij ≤ K` | 0 分鐘 |
| `tc_ij = 4`, `K = 3` | 12 分鐘 |
| `tc_ij = 5`, `K = 3` | 24 分鐘 |

這稱為 **軟性（soft）** 限制：路仍可走，但 `T_ij` 變大 → `c_ij` 變高 → TSP 傾向選轉乘較少的順序。`12` 為實作常數（非官方轉乘時間），見 `or_model/cost_matrix.py`。

其中 `T_ij` 再分解為：

```text
T_ij = walk_ij + metro_ij + wait_ij + outdoor_ij

metro_ij = train_ij + transfer_ij + 12 × max(0, tc_ij − K)    ← 超轉乘軟懲罰
```

| 符號 | 意義 | 單位 / 範圍 |
|------|------|-------------|
| `T_ij` | 從 i 到 j 的總移動時間（含步行、捷運、等車、戶外懲罰、轉乘軟懲罰） | 分鐘 |
| `fare_ij` | 該段捷運票價 | 日圓 |
| `crowd_ij` | 起迄站平均擁擠分數（proxy） | 0～1 |
| `rain_penalty_ij` | 雨天額外懲罰（`avoid_rain` 時） | 加在 `c_ij` |
| `w_time, w_fare, w_crowd` | 使用者偏好權重 | `preferences` |
| `tc_ij` | 該段轉乘次數 | 整數 |
| `K` | `max_transfers` 偏好上限 | 整數 |

**Preference weights（`w_time`, `w_fare`, `w_crowd`）**  
這些係數是 **composite cost function** 的權重，**不是**嚴格意義上的百分比分配。因為 time（分鐘）、fare（日圓）、crowd（0～1）的**單位與尺度不同**，權重效果必須與 scaling 一併解讀。例如 `crowd_ij × 60` 是為了讓擁擠項在數值上接近「分鐘」量級，便於與 `T_ij` 一起加權；建議將 `w_time + w_fare + w_crowd` 設為接近 1，但並非硬性約束。

**Rain-related terms（雨天相關項）**

| 類型 | 項 | 說明 |
|------|-----|------|
| 時間型雨天影響 | `walk_ij` 的 **walking multiplier**（`rain_mult`） | 放大步行分鐘數，計入 `T_ij` |
| 時間型雨天影響 | `outdoor_ij` | 雨天抵達戶外景點時的額外分鐘，計入 `T_ij` |
| 非時間型不便懲罰 | `rain_penalty_ij` | 直接加在 `c_ij` 上，不經 `w_time × T_ij` |

目前程式在 `avoid_rain: true` 時**同時**實作兩類：`rain_mult` 與 `outdoor_ij` 進入 `T_ij`，另以 `rain_penalty_ij` 對步行不便再加一項（見 `cost_matrix.py`）。設計上 `rain_penalty_ij` 代表「主觀不便」的額外成本；若僅希望**時間型**雨天影響，理論上應令 `rain_penalty_ij = 0` 以避免與已放大的 `walk_ij` 重複計價（double counting）。**現版尚未開關分離兩者**，報告時應說明此為簡化建模，屬未來可改進項目。

`T_ij` includes walking time, metro time, waiting time, transfer soft penalty, and outdoor rain penalty when applicable.

`c_ij` 由**時間、票價、擁擠、下雨**四類成本加權加總而成；TSP 比較的是這個單一數值，而非單獨最小化時間或票價。

**不可行弧（infeasible arcs）**  
若 `(i, j)` 在資料中無可行捷運路徑（或為異常零時間零票價 OD），該弧可能不建立，或於矩陣中以 **large cost（如 `1e6`）** 近似「極不偏好」。TSP 仍可能選到高成本弧；僅當路徑上**必經**的弧無法建立（`leg is None`）時，才回傳 `status: infeasible`。目前實作**尚未明確區分**「高成本但仍可走」與「真正不可行」兩類弧的語意，屬 **future improvement**。

### Route Constraints（路徑結構）

概念上需滿足：

- 每個景點節點**恰好造訪一次**
- 每個景點有一條**進入弧**與一條**離開弧**
- 起點只有**離開弧**（不在路徑中間被進入）
- 終點只有**進入弧**（不在路徑中間被離開）
- **Open TSP**：起點 ≠ 終點時，不要求回到起點

形式化（與程式一致）：

```text
(1)  Σ_j x_0j = 1                         （自起點出發一次）
(2)  Σ_i x_i,n-1 = 1                      （進入終點一次）
(3)  Σ_j x_ij = Σ_k x_ki = 1              ∀ 景點 i ∈ {1,…,n−2}
(4)  x_ij ∈ {0, 1}
```

### Post-Solve Feasibility（時間與預算）

**目前總行程時間與總預算不是 TSP 求解器內部的硬限制（hard constraint）**，而是求解完成後的 **post-solve feasibility check**：

1. 先求出使 `Σ c_ij x_ij` 最小的景點順序  
2. 再加總實際 `t_ij`（移動時間）、各景點停留 `d_k`、總票價 `fare_ij`  
3. 檢查是否超過使用者設定的 time window（`end_time − start_time`）與 `budget_yen`

下列不等式**目前不是** TSP 求解器內部強制加入的 constraints，而是求解後的 **diagnostic checks**（僅用於標記是否超過使用者設定，不改變已求出的順序）：

```text
(5)  Σ_{i,j} t_ij x_ij + Σ_{k∈A} d_k  ≤  T_max    （總移動 + 停留）
(6)  Σ_{i,j} fare_ij x_ij  ≤  B                   （總票價）
```

若違反 (5) 或 (6)：

- 系統**仍回傳**該加權成本最低的排序  
- `status` 標記為 `optimal_with_violation`  
- `constraints.binding` 列出 `"time"` 和/或 `"budget"`（違反項目）

**請勿理解為「模型保證不超時、不超預算」。**

### 程式對應

| 數學 | 程式 |
|------|------|
| `c_ij`, `t_ij`, `fare_ij` | `or_model/cost_matrix.py` → `build_problem()` |
| `min Σ c_ij x_ij` | `or_model/tsp_solver.py` → `solve_tsp()` |
| Post-solve (5)(6) | `or_model/optimizer.py` → `optimize_trip()` |

---

## Modeling Assumptions

以下為目前模型的明確假設與限制，供報告與評分參考：

- Each attraction is connected to its **nearest station** only, via `attraction_station_access.csv`（hub-and-spoke）.
- Walking speed is assumed to be approximately **1 m/s**（`access_walk_time_min = distance_m / 60`）.
- Station-to-station travel time is **static**（`station_pair_routes.csv`），不隨行程推進逐段更新。
- Waiting time is estimated from `train_frequency_by_time.csv` using the **request `start_time`** mapped to one `time_slot`；**不會**在每段 leg 後動態更新時段。
- Crowd score is a **proxy**（official heatmap 1–6 正規化），not real-time passenger count；缺值視為 0。
- Weather is **daily**（`weather_daily.csv`），not hourly；rain mainly affects walking multiplier and outdoor attraction penalty.
- Transfer limit `max_transfers` is a **soft penalty**（每超過 1 次轉乘 +12 分鐘），not a hard ban on arcs.
- **All selected attractions must be visited**；the model does not skip attractions or choose a subset.
- No integration with **real-time transit API** or **real-time weather API**.
- Some OD rows or fare entries are simplified or precomputed offline for demonstration.
- Output order is optimal **only under the current cost function**；opening hours, meals, fatigue, attraction-type pairing, and narrative flow are not modeled.

---

## Data Sources and Processing

靜態資料目錄：`data/OR_data/`。詳細品質說明見 `data/OR_data/data_quality_report.md`。

### 資料類型

| 類型 | 檔案 | 說明 |
|------|------|------|
| 靜態參考 | `attractions.csv` | 景點基本資料（~801 筆候選） |
| 靜態參考 | `attraction_station_access.csv` | 景點與最近車站、步行時間、壓力分數 |
| 靜態參考 | `station_info.csv` | 車站基本資料（Tokyo Metro 為主） |
| 加工矩陣 | `station_pair_routes.csv` | 站對站最短路：時間、轉乘、`route_path`（84,390 列） |
| 加工矩陣 | `station_pair_fares.csv` | 站對站票價（與 routes 對齊） |
| Proxy / 時段 | `train_frequency_by_time.csv` | 各時段等車時間估計 |
| Proxy / 時段 | `station_crowd_by_time.csv` | 各時段車站擁擠分數（非實際人流） |
| 情境 / 每日 | `weather_daily.csv` | 每日雨量、炎熱等（非逐時 API） |
| 進階 | `station_graph_edges.csv` | 鄰接圖（相鄰站 + 轉乘邊） |

- **Static reference**：景點、車站、接入距離。  
- **Precomputed pairwise matrices**：`station_pair_routes` / `station_pair_fares` 供 OR 直接查表建 `c_ij`。  
- **Proxy / simplified**：擁擠 heatmap、等車估計、部分票價為規則計算。  
- **Not used in runtime**：無即時大眾運輸或即時天氣 API。

Some datasets are **prepared, simplified, or approximated** for course-project demonstration purposes. The model demonstrates the **optimization pipeline** and should **not** be interpreted as a replacement for real-time navigation (e.g. Google Maps or Tokyo Metro live routing).

Some data fields are simplified or approximated for modeling and demonstration purposes. Therefore, the output should be interpreted as a **planning aid** rather than an exact real-time navigation result.

### 資料注意事項

| 項目 | 說明 |
|------|------|
| 路網規模 | `station_pair_routes` 含 **291 站**；`station_info` 約 186 站，以 routes 為準 |
| 同站移動 | `G16→G16` 等不在 routes 表；程式視為零捷運、僅步行 |
| 擁擠覆蓋 | 僅部分車站有 crowd 資料 |
| 異常 OD | 少數 `in_train=0` 且 `fare=0` 列視為不可行 |

---

## 求解器設計（Solver Design）

雖然本問題可以用二元變數 `x_ij` 建成 **MILP** 並交給 **Gurobi** 或 **OR-Tools** 求解，目前實作採**兩階段**設計：

1. **Cost construction**：`cost_matrix.py` 建立 pairwise `c_ij`  
2. **Route optimization**：`tsp_solver.py` 解 Open TSP  

| 選定景點數 | 方法 | 說明 |
|------------|------|------|
| ≤ 8（中間節點） | 精確枚舉 | `itertools.permutations`，保證該規模下最優 |
| > 8 | 啟發式 | 最近鄰 + 2-opt |

這是完整的 **OR formulation**，只是 solver implementation 較輕量。流程為：**先建立 pairwise cost matrix，再解組合最佳化**——不是單純依距離排序。若課程或專案要求，可將同一 formulation 改寫為 Gurobi MILP，輸入輸出介面（`trip_request` JSON）可沿用。

**未使用 Gurobi / CPLEX / OR-Tools**（目前依賴 `numpy`、`pandas` 即可執行 demo）。

---

## 如何執行（How to Run）

### 環境

```bash
cd 期末專案
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # numpy, pandas
```

### Demo

```bash
python run_or_demo.py
```

輸出寫入 `output_or_demo.json`。

### 程式內呼叫

```python
from or_model import optimize_trip

result = optimize_trip({
    "trip_date": "2024-06-15",
    "day_type": "holiday",
    "start_time": "09:00",
    "end_time": "18:00",
    "start_station_id": "G16",
    "end_station_id": "G16",
    "attractions": [
        {"attraction_id": "P0001", "stay_minutes": 90},
        {"attraction_id": "P0003", "stay_minutes": 60},
    ],
    "budget_yen": 2500,
    "preferences": {
        "time_weight": 0.5,
        "fare_weight": 0.2,
        "crowd_weight": 0.3,
        "avoid_rain": True,
        "max_transfers": 3,
    },
})
```

| 步驟 | 檔案 | 函數 |
|------|------|------|
| 載入 CSV | `or_model/data_loader.py` | `ORDataStore.load()` |
| 建 `c_ij` | `or_model/cost_matrix.py` | `build_problem()` |
| 解 TSP | `or_model/tsp_solver.py` | `solve_tsp()` |
| 輸出與檢查 | `or_model/optimizer.py` | `optimize_trip()` |

---

## Demo Output Interpretation

執行 `python run_or_demo.py` 後，JSON 主要欄位：

| 欄位 | 意義 |
|------|------|
| `ordered_attraction_ids` | 建議造訪順序（景點 ID） |
| `ordered_attraction_names` | 建議造訪順序（名稱） |
| `legs` | 每一段移動（起訖、步行/捷運/等車、票價、路線） |
| `totals.travel_time_min` | 實際估計**移動**時間加總 |
| `totals.total_fare_yen` | **交通費**加總 |
| `totals.objective_cost` | 目標函數 `Σ c_ij`（加權成本） |
| `totals.total_time_min` | 移動 + 各景點**停留**時間 |
| `status` | `optimal` / `optimal_with_violation` / `infeasible` |
| `constraints.binding` | 違反項目：`"time"` 和/或 `"budget"` |

### 範例解讀

若輸出：

```json
"ordered_attraction_names": [
  "Shibuya Scramble Crossing",
  "Kabukicho / Shinjuku Entertainment District",
  "Ueno Zoological Gardens"
]
```

代表模型建議依序造訪：**澀谷 → 新宿歌舞伎町 → 上野動物園**。

這個順序**不是**因為這三個景點「本身最推薦」，而是在給定起點（如 `G16` 上野）、終點、票價、等車、擁擠與雨天懲罰下，**加權移動成本 `Σ c_ij` 較低**的排序。

- **`legs`**：逐段列出從 `__start__` → 第一個景點 → … → `__end__` 的捷運與步行細節。  
- **`totals.objective_cost`**：TSP 最小化的目標值（加權）。  
- **`totals.travel_time_min`**：與使用者感受較接近的「路上時間」。  
- **`status: optimal_with_violation`**：有最佳排序，但總時間或總預算超過設定；請看 `constraints.binding`。

輸出順序僅代表在**目前成本函數**下的最佳解，尚未納入：景點營業時間、用餐安排、使用者疲勞、景點類型搭配、行程敘事流暢度等。

---

## Validation and Testing

目前以 `run_or_demo.py` 驗證下列流程可端到端執行：

- [x] 靜態資料載入（`ORDataStore.load()`）
- [x] Pairwise cost matrix `c_ij` 建立
- [x] Open TSP 求解與景點順序輸出
- [x] JSON 輸出（`legs`、`totals`、`constraints`）

**尚未**進行：

- 與真實旅客路徑選擇的對照實驗
- 與 **Google Maps** 或 **Tokyo Metro 即時路線** 的系統性誤差比較
- 大規模壓力測試或單元測試套件（`pytest`）

---

## 與前端串接

### 請求格式

`schemas/trip_request.json`（JSON Schema + 範例）。

必填摘要：`trip_date`, `day_type`, `start_time`, `end_time`, `start_station_id`, `end_station_id`, `attractions[]`, `budget_yen`, `preferences`。

### 建議 API（尚未實作）

```http
POST /api/v1/itinerary/optimize
Content-Type: application/json
```

Body：同上 `trip_request`；Response：見下方 schema 範例。

目前可：表單 → JSON → 本機 `optimize_trip()`；或由後端包 FastAPI。

### 回應格式（OR → UI / AI）

```json
{
  "status": "optimal",
  "ordered_attraction_ids": ["P0003", "P0008", "P0001"],
  "ordered_attraction_names": ["...", "...", "..."],
  "legs": [{ "from": "__start__", "to": "P0003", "metro_time_min": 55.9, "fare_yen": 296, "route_path": "..." }],
  "totals": {
    "travel_time_min": 244.54,
    "stay_time_min": 210,
    "total_time_min": 454.54,
    "total_fare_yen": 770,
    "objective_cost": 319.8
  },
  "constraints": {
    "time_budget_min": 540,
    "budget_yen": 2500,
    "binding": [],
    "feasible": true
  }
}
```

| `status` | 意義 |
|----------|------|
| `optimal` | 有排序，且 post-solve 時間/預算皆通過 |
| `optimal_with_violation` | 有排序，但超過時間或預算 |
| `infeasible` | 無法建立必要弧（路徑上某段 `leg` 缺失）；非僅因弧成本為 `1e6` |

### AI 層建議

Prompt 應要求：**解釋 OR 輸出的順序，不要自行改寫 `ordered_attraction_ids`**，除非 `infeasible` 並建議使用者調整輸入。

---

## Current Status

### Implemented

- [x] Load static Tokyo tourism and transit datasets（`data/OR_data/`）
- [x] Build pairwise leg cost matrix `c_ij`
- [x] Solve **Open TSP** for user-selected attractions
- [x] Output ordered itinerary and leg-level details（時間、票價、轉乘、路徑）
- [x] User preference weights：`time_weight`, `fare_weight`, `crowd_weight`
- [x] Rain-related penalty when `avoid_rain` is enabled
- [x] Post-solve feasibility checks for total time and budget
- [x] Local demo：`run_or_demo.py`

### Not Implemented Yet / Future Work

- [ ] Web API endpoint（e.g. FastAPI）
- [ ] Frontend integration
- [ ] Dynamic time-slot update after each leg
- [ ] Real-time transit API
- [ ] Real-time weather API
- [ ] Attraction selection from full catalog or skipping attractions
- [ ] Formal MILP solver（Gurobi / OR-Tools）with `x_ij` variables
- [ ] `schemas/trip_response.json`
- [ ] More realistic walking and transfer modeling；configurable transfer penalty

---

## 常見問題（FAQ）

**Q: 為什麼 `station_info` 186 站，`station_pair_routes` 卻 291 站？**  
A: Routes 涵蓋較大路網；站碼能否路由以 **routes 表** 為準。

**Q: `max_transfers` 的 +12 分鐘是什麼？**  
A: 超過偏好轉乘次數時的**軟性懲罰**（啟發常數，非官方轉乘時間）。

**Q: 會隨行程更新等車/擁擠的時段嗎？**  
A: 目前否；全程使用 `start_time` 對應的單一 `time_slot`。

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `數據說明/data_explain.txt` | 各 CSV 欄位中文說明 |
| `data/OR_data/data_quality_report.md` | 資料來源、NA、proxy |
| `schemas/trip_request.json` | UI → OR 請求 Schema |
