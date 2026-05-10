個人投資復盤助理｜雲端同步版

這一版已經改成：
1. 前端網站仍然是一個頁面。
2. 股價由 Render 後端 /api/prices 抓取，避免瀏覽器 CORS 問題。
3. 新增交易、刪除交易、清除資料、設定手續費，都會同步到後端 /api/state。
4. 後端會把資料存進 PostgreSQL；只要手機和電腦打開同一個 Render 網址，就會看到同一份交易紀錄。
5. 原先持股仍是內建基礎持股，清除所有資料時不會被刪掉。

重要：一定要設定 DATABASE_URL
--------------------------------
如果沒有設定 DATABASE_URL，網站仍可以本機測試，但只會使用 JSON 檔案備援；部署到 Render 後不保證長期保存，也不適合跨裝置同步。

建議方法 A：使用 Render PostgreSQL
1. 在 Render 建立 PostgreSQL 資料庫。
2. 複製資料庫的 External Database URL 或 Internal Database URL。
3. 到你的 Web Service > Environment。
4. 新增環境變數：
   Key: DATABASE_URL
   Value: 貼上 PostgreSQL connection string
5. 重新部署 Web Service。

建議方法 B：使用 Supabase PostgreSQL
1. 到 Supabase 建立 Project。
2. 到 Project > Connect，複製 Postgres connection string。
3. 建議使用 Session pooler / Transaction pooler 連線字串，並確認包含 sslmode=require。
4. 到 Render Web Service > Environment。
5. 新增環境變數：
   Key: DATABASE_URL
   Value: 貼上 Supabase connection string
6. 重新部署 Web Service。

部署到 GitHub + Render
--------------------------------
1. 解壓縮這個資料夾。
2. 把裡面的檔案上傳到 GitHub repo 根目錄。
3. Render 建立 New Web Service，連到這個 GitHub repo。
4. Build Command: pip install -r requirements.txt
5. Start Command: python app.py
6. 加上 DATABASE_URL 環境變數。
7. Deploy。

測試方式
--------------------------------
部署完成後打開：
https://你的-render網址/health

如果 storage 顯示 backend: postgres，代表雲端資料庫已成功連接。
如果顯示 backend: json-file，代表你還沒有設定 DATABASE_URL。

再打開主頁，新增一筆交易後，用手機打開同一網址，應該會看到同一筆交易。

資料格式說明
--------------------------------
後端只建立一張資料表 investlog_state，將整份交易資料存在單一 JSONB 欄位中。
這樣比較簡單，適合個人使用與作業展示。

注意
--------------------------------
如果兩台裝置同時新增資料，最後一次儲存會覆蓋前一次。個人使用通常沒問題；如果之後要多人共同使用，建議改成逐筆交易資料表。


=== 本版新增 ===
- 左側新增「AI 股票分析」頁面。
- 新增後端 API：/api/analyze?date=YYYY-MM-DD&refresh=1。
- 預設分析 0050、2303、2308、2330、2454。
- 保留原本 Supabase/PostgreSQL 雲端同步與側邊欄伸縮功能。

---

## Gmail 成交回報自動匯入

本版新增 /api/gmail/import，可搭配 google_apps_script_fubon_import.gs 使用。

Render Environment Variables 請額外新增：

EMAIL_IMPORT_TOKEN = 自己設定一串長隨機密碼
GMAIL_ALLOWED_SENDER = 富邦證券成交回報寄件者或網域片段，例如 fubon

詳細步驟請看 README_GMAIL_IMPORT.txt。
