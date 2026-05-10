/**
 * 富邦證券成交回報 → 投資助理自動匯入
 * 使用方式：
 * 1. 到 script.google.com 建立 Apps Script 專案
 * 2. 貼上此檔內容
 * 3. 修改 RENDER_URL、IMPORT_TOKEN、FUBON_SENDER
 * 4. 先執行 syncFubonExecutionReports() 授權與測試
 * 5. 成功後執行 createFiveMinuteTrigger()，之後每 5 分鐘自動檢查一次
 */

const RENDER_URL = 'https://你的-render-service.onrender.com';
const IMPORT_TOKEN = '請貼上和 Render EMAIL_IMPORT_TOKEN 一樣的字串';

// 請改成富邦證券成交回報的實際寄件者 email 或網域片段。
// 例：'notice@fubon.com' 或 'fubon'
const FUBON_SENDER = '請改成實際寄件者';

// 限制只搜尋特定寄件者 + 證券成交回報，且排除已匯入的信件。
const IMPORTED_LABEL = 'InvestLog_已匯入';
const SEARCH_DAYS = 30;
const MAX_THREADS_EACH_RUN = 20;

function getOrCreateLabel_(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}

function buildSearchQuery_() {
  // 如果你想更嚴格，也可以改成：from:(xxx@xxx.com) subject:(證券成交回報)
  return `from:(${FUBON_SENDER}) subject:(證券成交回報) newer_than:${SEARCH_DAYS}d -label:${IMPORTED_LABEL}`;
}

function syncFubonExecutionReports() {
  if (!RENDER_URL || RENDER_URL.includes('你的-render-service')) throw new Error('請先設定 RENDER_URL');
  if (!IMPORT_TOKEN || IMPORT_TOKEN.includes('請貼上')) throw new Error('請先設定 IMPORT_TOKEN');
  if (!FUBON_SENDER || FUBON_SENDER.includes('請改成')) throw new Error('請先設定 FUBON_SENDER');

  const label = getOrCreateLabel_(IMPORTED_LABEL);
  const query = buildSearchQuery_();
  const threads = GmailApp.search(query, 0, MAX_THREADS_EACH_RUN);
  let importedMessages = 0;
  let skippedMessages = 0;

  for (const thread of threads) {
    const messages = thread.getMessages();
    let threadOk = false;

    for (const msg of messages) {
      const payload = {
        messageId: msg.getId(),
        from: msg.getFrom(),
        subject: msg.getSubject(),
        date: msg.getDate().toISOString(),
        plainBody: msg.getPlainBody(),
        htmlBody: msg.getBody()
      };

      const url = `${RENDER_URL.replace(/\/$/, '')}/api/gmail/import?token=${encodeURIComponent(IMPORT_TOKEN)}`;
      const resp = UrlFetchApp.fetch(url, {
        method: 'post',
        contentType: 'application/json; charset=utf-8',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      const status = resp.getResponseCode();
      const text = resp.getContentText();
      let data = {};
      try { data = JSON.parse(text); } catch (e) {}

      if (status >= 200 && status < 300 && data.ok) {
        importedMessages += Number(data.imported || 0);
        skippedMessages += Number(data.skipped || 0);
        threadOk = true;
      } else {
        console.log(`匯入失敗 message=${msg.getId()} status=${status} response=${text}`);
      }
    }

    if (threadOk) label.addToThread(thread);
  }

  console.log(`完成。匯入 ${importedMessages} 筆，略過重複 ${skippedMessages} 筆，搜尋條件：${query}`);
}

function createFiveMinuteTrigger() {
  // 避免重複建立同樣 trigger
  for (const t of ScriptApp.getProjectTriggers()) {
    if (t.getHandlerFunction() === 'syncFubonExecutionReports') {
      ScriptApp.deleteTrigger(t);
    }
  }
  ScriptApp.newTrigger('syncFubonExecutionReports')
    .timeBased()
    .everyMinutes(5)
    .create();
  console.log('已建立每 5 分鐘自動檢查 Gmail 的 trigger');
}

function deleteImportTriggers() {
  for (const t of ScriptApp.getProjectTriggers()) {
    if (t.getHandlerFunction() === 'syncFubonExecutionReports') {
      ScriptApp.deleteTrigger(t);
    }
  }
  console.log('已刪除自動匯入 trigger');
}
