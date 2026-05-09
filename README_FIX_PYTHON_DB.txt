修正內容：Render PostgreSQL / Supabase 連線錯誤

你遇到的錯誤：
psycopg2/_psycopg... undefined symbol: _PyInterpreterState_Get

原因：Render 這次用 Python 3.14 建置，舊版 psycopg2-binary 在這個 Python 版本上不相容。

此版本已修正：
1. requirements.txt 改成 psycopg[binary]，使用新版 psycopg v3。
2. app.py 改成優先 import psycopg；如果本機沒有 psycopg，才 fallback psycopg2。
3. 新增 .python-version = 3.11.9。
4. 保留 runtime.txt = python-3.11.9。

Render 必做：
1. 把這份 zip 解壓後，上傳/覆蓋到 GitHub repo。
2. 到 Render Web Service → Environment。
3. 確認有：
   DATABASE_URL = 你的 Supabase / PostgreSQL connection string
4. 建議再新增一個：
   PYTHON_VERSION = 3.11.9
5. 到 Manual Deploy → Clear build cache & deploy。
   注意：一定要 Clear build cache，避免 Render 沿用舊的 Python 3.14 venv。

部署後測試：
打開 https://你的網站.onrender.com/health

成功時 storage 應顯示：
"ok": true,
"backend": "postgres"

如果 storage backend 是 postgres 但 ok=false，請檢查 DATABASE_URL 或 Supabase 密碼。
