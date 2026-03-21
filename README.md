# 💰 FinTech Hub - 個人資產管理系統 (加密安全版)

這是一個基於 **FastAPI** 與 **PostgreSQL** 構建的現代化個人帳本。開發初衷是在提供流暢 UI 的同時，導入金融級的資料安全保護機制，確保每一筆收支紀錄都受到嚴格保護

---

## 🚀 專案與技術細節

### 1. 🛡️ 資料防禦與加密 (Security First)
* **AES-256 欄位加密**：使用 Fernet (對稱加密) 對敏感的交易描述進行加密。即使資料庫遭劫，攻擊者也無法直接讀取原始消費明細
* **JWT 身份驗證**：實作完整的註冊與登入流程，透過密鑰簽發 Token，確保資料存取權限
* **防禦性編程 (Defensive Coding)**：前後端同步驗證金額數值，杜絕負數或非法字串進入資料庫，確保資料完整性 (Data Integrity)

### 2. ⚡ 高性能後端架構
* **FastAPI & Python 3.11**：利用非同步 (Asynchronous) 特性確保 API 高併發下的響應速度
* **SQLAlchemy 2.0**：控制資料庫關聯，支援「級聯刪除 (Cascade Delete)」。當使用者刪除帳戶時，系統會自動清理所有關聯交易紀錄

### 3. 🛠️ 部署實戰紀錄
在部署至 Render 雲端平台時，克服了環境隱性差異
* **相容性修復**：解決了 Python 3.14 與 `passlib/bcrypt` 庫不相容導致的 500 錯誤，最終透過鎖定 `bcrypt==4.0.1` 成功上線
* **雲端配置優化**：實現程式碼與密鑰分離，透過 Render 環境變數安全管理 `ENCRYPTION_KEY`

---

## 📸 功能展示

### ✨ 登入與註冊流程
> (screenshots/register.png)

### ✨ 個人資產總覽 (Dashboard)
>  ![Dashboard Overview](screenshots/dashboard.png)

### ✨ 嚴謹的輸入驗證
>  ![Validation UI](screenshots/validation.png)

### ✨ 帳戶管理功能
> ![Account Management](screenshots/delete_account.png)

---

## 🛠️ 技術棧 (Tech Stack)
* **Backend**: FastAPI, SQLAlchemy, Pydantic, Passlib (BCrypt)
* **Frontend**: Tailwind CSS, Pure JavaScript, Chart.js
* **Database**: PostgreSQL (Render Managed)
* **DevOps**: Render PaaS, Git/GitHub

