 
# M&A 平台後端 API

## 🚀 快速開始

### 1. 環境準備

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安裝依賴
pip install -r requirements-dev.txt
```

### 2. 環境變數設定

```bash
# 複製環境變數範例
cp .env.example .env

# 編輯 .env 檔案，設定你的 MongoDB 連接字串
# MONGODB_URL=mongodb://localhost:27017
```

### 3. 測試基礎設定

```bash
# 測試基礎配置和資料庫連接
python test_startup.py
```

### 4. 啟動開發伺服器

```bash
# 啟動 FastAPI 開發伺服器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 訪問 API 文檔

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康檢查: http://localhost:8000/health

## 🛠️ 開發工具

### 生成測試資料

```bash
# 生成用戶測試資料
python scripts/generate_dummy_users.py
```

### 執行測試

```bash
# 執行所有測試
pytest

# 執行測試並顯示覆蓋率
pytest --cov=app --cov-report=html
```

### 代碼格式化

```bash
# 格式化代碼
black app/
isort app/

# 檢查代碼風格
flake8 app/
```

## 📁 專案結構

```
backend/
├── app/                    # 主應用程式
│   ├── core/              # 核心配置
│   ├── models/            # 資料模型
│   ├── schemas/           # Pydantic 模型
│   ├── api/               # API 路由
│   ├── services/          # 業務邏輯
│   ├── utils/             # 工具函數
│   └── middleware/        # 中介軟體
├── tests/                 # 測試檔案
├── scripts/               # 工具腳本
└── uploads/               # 檔案上傳目錄
```

## 🧪 測試帳號

當執行 Dummy Data 腳本後，可以使用以下測試帳號：

- **管理員**: admin@ma-platform.com / admin123
- **管理員**: manager@ma-platform.com / manager123
- **買方**: buyer1@example.com / buyer123
- **提案方**: seller1@example.com / seller123

## 📝 開發狀態

### Phase 1 進度 (Day 1-2 專案初始化)

- [x] FastAPI 專案架構建立
- [x] MongoDB 連接配置
- [x] 基礎中介軟體設定
- [x] 環境變數管理
- [x] 開發工具配置
- [ ] 用戶認證系統開發

### 下一步

- 完成用戶模型和認證 API (Day 3-5)
- 生成完整用戶測試資料 (Day 6)

## 🔧 疑難排解

### MongoDB 連接問題

1. 確認 MongoDB 已安裝並啟動
2. 檢查 `.env` 檔案中的 `MONGODB_URL` 設定
3. 如果使用 MongoDB Atlas，確認網路存取權限

### 依賴安裝問題

```bash
# 更新 pip
pip install --upgrade pip

# 清除快取重新安裝
pip cache purge
pip install -r requirements-dev.txt
```