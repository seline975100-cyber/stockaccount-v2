# Gmail 證券成交回報自動匯入設定說明

這版已新增後端 API：

POST /api/gmail/import?token=你的EMAIL_IMPORT_TOKEN

目的：當 Gmail 收到「富邦證券成交回報」時，透過 Google Apps Script 把信件內容送到 Render 後端，後端解析成交回報表格後，自動新增交易紀錄到 Supabase/PostgreSQL。

## 一、Render 要新增的環境變數

到 Render Web Service → Environment → Add Environment Variable：

1. EMAIL_IMPORT_TOKEN
   - 自己設定一串長一點的密碼，例如：
     investlog_fubon_2026_請自己改成更長隨機字串
   - 這串也要貼到 Apps Script 的 IMPORT_TOKEN。

2. GMAIL_ALLOWED_SENDER（建議設定）
   - 填富邦證券成交回報的實際寄件者 email 或網域片段。
   - 例如：fubon 或 notice@xxx.fubon.com
   - 後端會檢查 payload.from 是否包含這段文字。

保留原本的：
- DATABASE_URL
- PYTHON_VERSION = 3.11.9

設定完成後，Render 重新部署。

## 二、Google Apps Script 設定

1. 到 https://script.google.com
2. 新增專案
3. 把 google_apps_script_fubon_import.gs 的內容貼上
4. 修改檔案最上方三個變數：

const RENDER_URL = 'https://你的-render-service.onrender.com';
const IMPORT_TOKEN = '和 Render EMAIL_IMPORT_TOKEN 一樣';
const FUBON_SENDER = '富邦成交回報實際寄件者';

5. 先手動執行 syncFubonExecutionReports()
6. Google 會要求授權 Gmail 與外部連線，按授權
7. 執行成功後，回網站重新整理，確認交易紀錄是否自動新增
8. 確認成功後，執行 createFiveMinuteTrigger()

之後 Apps Script 會每 5 分鐘檢查一次 Gmail。

## 三、如何限制只讀特定寄件者

Apps Script 的搜尋條件是：

from:(FUBON_SENDER) subject:(證券成交回報) newer_than:30d -label:InvestLog_已匯入

也就是只讀：
- 特定寄件者
- 主旨包含「證券成交回報」
- 近 30 天
- 尚未匯入的信件

成功匯入後，系統會幫該信件加上 Gmail 標籤：
InvestLog_已匯入

避免重複匯入。

## 四、支援解析的欄位

從信件表格解析：
- 股票名稱，例如 2308台達電
- 交易類別，例如 現買 / 現賣
- 成交股數
- 成交單價
- 成交價金
- 委託書編號
- 成交時間
- 成交日期

會自動轉成網站交易紀錄：
- 現買 → 買進
- 現賣 → 賣出
- 手續費依網站設定 feeRate 自動估算
- 賣出證交稅依 0.3% 自動估算
- 備註會保留成交時間與委託書編號

## 五、測試方式

部署後可先打開：
https://你的-render-service.onrender.com/health

如果有看到：
"gmail_import":{"token_configured":true,...}

代表 Render 已設定 EMAIL_IMPORT_TOKEN。

再到 Apps Script 手動執行 syncFubonExecutionReports()。

## 六、注意事項

1. 這不是讓網站直接登入你的 Gmail；Gmail 權限留在你自己的 Google Apps Script 裡。
2. 網站只接受 Apps Script 送來的成交回報資料。
3. 只要 EMAIL_IMPORT_TOKEN 不外洩，外部使用者不能隨便寫入交易紀錄。
4. 請不要把 EMAIL_IMPORT_TOKEN、DATABASE_URL 截圖或上傳到 GitHub。
