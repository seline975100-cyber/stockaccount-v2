已取消 Gmail 富邦證券成交回報自動匯入功能

這個版本保留：
- 雲端同步交易紀錄（PostgreSQL/Supabase）
- 原先持股可編輯
- 可編輯/複製/刪除交易紀錄
- 手機快速新增交易
- AI 股票分析與明日操作計畫

這個版本移除：
- /api/gmail/import 後端匯入端點
- Gmail Apps Script 自動匯入檔案
- EMAIL_IMPORT_TOKEN / GMAIL_ALLOWED_SENDER 的程式使用

部署後建議：
1. Render Environment Variables 可刪除 EMAIL_IMPORT_TOKEN 與 GMAIL_ALLOWED_SENDER。
2. 到 Google Apps Script 刪除 trigger 或整個專案，避免它繼續嘗試呼叫舊 API。
3. 原本已經匯入到資料庫的交易紀錄不會自動刪除；若不需要，請在網站交易紀錄中手動刪除。
