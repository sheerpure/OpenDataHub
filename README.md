# FinTechHub | 分散式安全財務帳本系統

本專案為一套基於 **FastAPI** 與 **PostgreSQL** 構建的後端帳務系統。核心設計目標在於確保財務數據的 **絕對私密性** 與 **高並發環境下的數據一致性**，並透過 Service Layer 模式實現業務邏輯與 API 介面的完全解耦。

## 🛠️ 核心架構與技術實作

### 1. 欄位級數據加密 (Field-Level Encryption)
為了保障使用者隱私，本系統針對敏感財務欄位（如 Transaction Amount）實作了 **AES-256-CBC** 對稱加密。
- **機制**：數據在進入持久層（Persistence Layer）前由 `auth.py` 進行加密，讀取後再行動態解密。
- **優勢**：即使資料庫層級發生非授權存取，攻擊者亦無法取得真實財務明細。

### 2. 並發控制與死鎖防止 (Concurrency & Deadlock Prevention)
在處理帳戶轉帳等涉及多行更新的操作時，本系統採用了嚴謹的鎖定策略：
- **行級鎖定 (Row-level Locking)**：利用 SQLAlchemy 的 `with_for_update()` 確保計算期間餘額不被篡改。
- **排序鎖定機制**：系統會自動對多個帳戶 ID 進行排序並依序請求鎖定，從根本上消除了循環等待造成的 **資料庫死鎖 (Deadlock)**。

### 3. 事務原子性 (Transactional Atomicity)
所有帳務操作皆封裝於單一資料庫事務（Transaction）中。
- **特性**：遵循 ACID 原則，確保轉帳操作的 **不可分割性**。若任一環節出錯，系統將執行自動回滾（Rollback），防止產生帳實不符的壞帳。

### 4. 模組化前端與狀態持久化
- **關注點分離 (SoC)**：前端採用 HTML/CSS/JS 物理隔離架構，提升代碼維護性與瀏覽器快取效率。
- **UI 狀態同步**：優化了異步請求後的組件渲染邏輯，解決了 CRUD 操作後過濾器狀態（Filter State）重置的 UI 缺陷。

## 🧪 自動化測試 (Testing)

專案內置 `test_main.py` 整合測試腳本，覆蓋以下核心路徑：
- JWT 鑑權與身分隔離
- 帳戶生命週期管理
- 高並發下的轉帳數據完整性驗證

```bash
# 執行測試
pytest test_main.py
