# -*- coding: utf-8 -*-
"""
個人投資復盤助理｜Render 後端股價版
- 首頁 HTML/CSS/JS 內嵌於 app.py，不需要 static 資料夾
- 前端呼叫 /api/prices，後端用 Python 連外抓取股價，避免瀏覽器 CORS 擋住
- 本機啟動：python app.py
- 本機網址：http://127.0.0.1:5000
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Any, Dict, List, Tuple

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
TW_TZ = timezone(timedelta(hours=8))
APP_VERSION = "investment-tracker-cloud-sync-v1"

EMBEDDED_INDEX_HTML = '<!DOCTYPE html>\n<html lang="zh-TW">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>個人投資復盤助理</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">\n<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>\n<style>\n*{box-sizing:border-box;margin:0;padding:0}\n:root{\n  --bg:#0f1117;--bg2:#161b27;--bg3:#1e2535;\n  --border:#2a3348;--text:#e8eaf2;--text2:#8892a4;--text3:#4a5568;\n  --accent:#3b82f6;--accent2:#1d4ed8;\n  --green:#10b981;--red:#ef4444;--yellow:#f59e0b;\n  --radius:10px;--radius-lg:14px;\n}\nbody{font-family:\'Noto Sans TC\',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px;line-height:1.6}\n.app{display:flex;height:100vh;overflow:hidden}\n.sidebar{width:220px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}\n.logo{padding:20px 18px 16px;border-bottom:1px solid var(--border)}\n.logo-text{font-family:\'Space Mono\',monospace;font-size:13px;font-weight:700;color:var(--accent);letter-spacing:.05em}\n.logo-sub{font-size:11px;color:var(--text2);margin-top:2px}\n.nav{padding:12px 8px;flex:1}\n.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;color:var(--text2);font-size:13px;font-weight:500;transition:all .15s;margin-bottom:2px}\n.nav-item:hover{background:var(--bg3);color:var(--text)}\n.nav-item.active{background:rgba(59,130,246,.15);color:var(--accent)}\n.nav-item i{font-size:17px}\n.sidebar-bottom{padding:12px 8px;border-top:1px solid var(--border)}\n.main{flex:1;overflow-y:auto;background:var(--bg)}\n.page{display:none;padding:28px 32px}\n.page.active{display:block}\n.page-header{margin-bottom:24px;display:flex;align-items:flex-start;justify-content:space-between}\n.page-header-left .page-title{font-size:20px;font-weight:700;letter-spacing:-.3px}\n.page-header-left .page-sub{font-size:13px;color:var(--text2);margin-top:4px}\n.header-actions{display:flex;gap:10px;align-items:center}\n.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}\n.metric-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:18px 20px}\n.metric-label{font-size:11px;color:var(--text2);font-weight:500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}\n.metric-val{font-family:\'Space Mono\',monospace;font-size:22px;font-weight:700}\n.metric-val.pos{color:var(--green)}.metric-val.neg{color:var(--red)}\n.metric-sub{font-size:11px;color:var(--text2);margin-top:4px}\n.metric-sub.pos{color:var(--green)}.metric-sub.neg{color:var(--red)}\n.section{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);margin-bottom:20px;overflow:hidden}\n.section-head{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}\n.section-title{font-size:14px;font-weight:600}\ntable{width:100%;border-collapse:collapse}\nth{padding:10px 16px;text-align:left;font-size:11px;font-weight:500;color:var(--text2);text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--border);background:var(--bg3)}\ntd{padding:12px 16px;font-size:13px;border-bottom:1px solid var(--border)}\ntr:last-child td{border-bottom:none}\ntr:hover td{background:rgba(255,255,255,.02)}\n.badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}\n.badge.profit{background:rgba(16,185,129,.15);color:var(--green)}\n.badge.loss{background:rgba(239,68,68,.15);color:var(--red)}\n.badge.hold{background:rgba(245,158,11,.12);color:var(--yellow)}\n.badge.near-stop{background:rgba(239,68,68,.25);color:#fca5a5}\n.badge.buy{background:rgba(59,130,246,.15);color:var(--accent)}\n.mono{font-family:\'Space Mono\',monospace;font-size:13px}\n.pos{color:var(--green)}.neg{color:var(--red)}\n.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:24px}\n.form-group{display:flex;flex-direction:column;gap:6px}\n.form-group.full{grid-column:1/-1}\nlabel{font-size:12px;font-weight:500;color:var(--text2)}\ninput,select,textarea{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border .15s;outline:none;width:100%}\ninput:focus,select:focus,textarea:focus{border-color:var(--accent)}\nselect option{background:var(--bg3)}\ntextarea{resize:vertical;min-height:70px}\n.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;font-family:inherit;transition:all .15s;white-space:nowrap}\n.btn-primary{background:var(--accent);color:#fff}\n.btn-primary:hover{background:var(--accent2)}\n.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}\n.btn-ghost:hover{background:var(--bg3);color:var(--text)}\n.btn-green{background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3)}\n.btn-green:hover{background:rgba(16,185,129,.25)}\n.btn-row{display:flex;gap:10px;justify-content:flex-end;padding:0 24px 24px}\n.tab-row{display:flex;gap:2px;padding:14px 20px 0;border-bottom:1px solid var(--border)}\n.tab{padding:8px 16px;font-size:13px;font-weight:500;color:var(--text2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .15s}\n.tab.active{color:var(--accent);border-color:var(--accent)}\n.chart-wrap{padding:20px}\n.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}\n.progress-bar{height:6px;background:var(--bg3);border-radius:3px;overflow:hidden;margin-top:6px}\n.progress-fill{height:100%;border-radius:3px}\n.review-item{padding:18px 20px;border-bottom:1px solid var(--border)}\n.review-item:last-child{border-bottom:none}\n.review-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}\n.review-stock{font-weight:700;font-size:15px}\n.review-meta{font-size:12px;color:var(--text2);margin-bottom:8px}\n.review-note{font-size:13px;background:var(--bg3);border-radius:8px;padding:10px 14px;line-height:1.7;margin-bottom:8px}\n.review-note.ai{border-left:3px solid var(--accent);color:var(--text2)}\n.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;margin-right:5px;margin-bottom:4px}\n.tag.tech{background:rgba(59,130,246,.15);color:var(--accent)}\n.tag.short{background:rgba(245,158,11,.12);color:var(--yellow)}\n.tag.long{background:rgba(16,185,129,.12);color:var(--green)}\n\n/* 即時股價 */\n.price-updating{animation:pulse 1.2s ease-in-out infinite}\n@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}\n.price-cell{display:flex;align-items:center;gap:6px}\n.price-dot{width:6px;height:6px;border-radius:50%;background:var(--green);flex-shrink:0}\n.price-dot.updating{background:var(--yellow);animation:pulse 1s infinite}\n.price-dot.error{background:var(--red)}\n.price-badge{font-size:10px;padding:1px 6px;border-radius:4px;background:rgba(16,185,129,.12);color:var(--green);font-weight:600}\n.price-badge.neg{background:rgba(239,68,68,.12);color:var(--red)}\n.refresh-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;background:rgba(59,130,246,.12);color:var(--accent);border:1px solid rgba(59,130,246,.25);font-family:inherit;transition:all .15s}\n.refresh-btn:hover{background:rgba(59,130,246,.2)}\n.refresh-btn.spinning i{animation:spin .8s linear infinite}\n@keyframes spin{to{transform:rotate(360deg)}}\n.price-note{font-size:11px;color:var(--text3);padding:8px 20px 14px;text-align:center}\n\n/* 匯出 */\n.export-panel{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;margin-bottom:20px}\n.export-title{font-size:14px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px}\n.export-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}\n.export-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;cursor:pointer;transition:all .15s;text-align:center}\n.export-card:hover{border-color:var(--accent);background:rgba(59,130,246,.05)}\n.export-card i{font-size:28px;display:block;margin-bottom:8px;color:var(--accent)}\n.export-card-title{font-size:13px;font-weight:600;margin-bottom:4px}\n.export-card-sub{font-size:11px;color:var(--text2)}\n\n/* toast */\n.toast{position:fixed;bottom:28px;right:28px;background:#1e2535;border:1px solid var(--border);border-radius:10px;padding:12px 18px;font-size:13px;display:flex;align-items:center;gap:10px;z-index:999;transform:translateY(80px);opacity:0;transition:all .3s}\n.toast.show{transform:translateY(0);opacity:1}\n.toast i{font-size:18px}\n.toast.success i{color:var(--green)}\n.toast.info i{color:var(--accent)}\n\n/* modal */\n.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;display:none;align-items:center;justify-content:center}\n.modal-overlay.show{display:flex}\n.modal{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;width:480px;max-width:95vw}\n.modal-title{font-size:16px;font-weight:700;margin-bottom:16px}\n.modal-close{float:right;cursor:pointer;color:var(--text2);font-size:20px;line-height:1}\n\n\n/* 側邊目錄伸縮 / 手機抽屜 */\n.app{position:relative}\n.sidebar{transition:width .22s ease, transform .22s ease;z-index:30}\n.logo{position:relative}\n.logo-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}\n.logo-title-wrap{min-width:0}\n.sidebar-toggle,.mobile-menu-btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);background:var(--bg3);color:var(--text2);border-radius:8px;cursor:pointer;transition:all .15s}\n.sidebar-toggle{width:32px;height:32px;padding:0;flex-shrink:0}\n.sidebar-toggle:hover,.mobile-menu-btn:hover{color:var(--text);border-color:rgba(59,130,246,.5);background:rgba(59,130,246,.12)}\n.mobile-menu-btn{display:none;position:fixed;top:12px;left:12px;width:38px;height:38px;z-index:80;box-shadow:0 10px 24px rgba(0,0,0,.22)}\n.sidebar-backdrop{display:none}\n.nav-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.app.sidebar-collapsed .sidebar{width:68px}\n.app.sidebar-collapsed .logo{padding:14px 10px}\n.app.sidebar-collapsed .logo-row{justify-content:center}\n.app.sidebar-collapsed .logo-title-wrap{display:none}\n.app.sidebar-collapsed .sidebar-toggle i{transform:rotate(180deg)}\n.app.sidebar-collapsed .nav{padding:12px 8px}\n.app.sidebar-collapsed .nav-item{justify-content:center;gap:0;padding:12px 0}\n.app.sidebar-collapsed .nav-label{display:none}\n.app.sidebar-collapsed .nav-item i{font-size:20px}\n.app.sidebar-collapsed .sidebar-bottom{padding:12px 8px}\n\n@media (max-width: 820px){\n  .app{height:100vh;overflow:hidden}\n  .mobile-menu-btn{display:inline-flex}\n  .sidebar{position:fixed;left:0;top:0;bottom:0;width:240px;max-width:82vw;transform:translateX(-105%);box-shadow:18px 0 38px rgba(0,0,0,.38)}\n  .app.sidebar-open .sidebar{transform:translateX(0)}\n  .app.sidebar-collapsed .sidebar{width:240px;max-width:82vw}\n  .app.sidebar-collapsed .logo{padding:20px 18px 16px}\n  .app.sidebar-collapsed .logo-row{justify-content:space-between}\n  .app.sidebar-collapsed .logo-title-wrap{display:block}\n  .app.sidebar-collapsed .nav-item{justify-content:flex-start;gap:10px;padding:9px 12px}\n  .app.sidebar-collapsed .nav-label{display:inline}\n  .app.sidebar-collapsed .nav-item i{font-size:17px}\n  .app.sidebar-open .sidebar-backdrop{display:block;position:fixed;inset:0;background:rgba(0,0,0,.56);z-index:20}\n  .main{width:100%;padding-top:48px}\n  .page{padding:18px 14px 28px}\n  .page-header{gap:12px;flex-direction:column}\n  .header-actions{width:100%;flex-wrap:wrap}\n  .metric-grid{grid-template-columns:repeat(2, minmax(0,1fr));gap:10px}\n  .metric-card{padding:14px}\n  .metric-val{font-size:18px}\n  .two-col{grid-template-columns:1fr}\n  .form-grid{grid-template-columns:1fr;padding:18px}\n  .export-grid{grid-template-columns:1fr}\n  table{min-width:720px}\n  .section{overflow:auto}\n}\n@media (max-width: 520px){\n  .metric-grid{grid-template-columns:1fr}\n  .page-title{padding-left:2px}\n}\n\n</style>\n</head>\n<body>\n\n<div class="toast" id="toast">\n  <i class="ti ti-check"></i>\n  <span id="toast-msg">已完成</span>\n</div>\n\n<div class="modal-overlay" id="import-modal">\n  <div class="modal">\n    <div class="modal-title">匯入 CSV 交易紀錄 <span class="modal-close" onclick="closeImportModal()">✕</span></div>\n    <div style="margin-bottom:14px;font-size:13px;color:var(--text2);line-height:1.8">\n      CSV 格式需包含以下欄位（第一行為標題）：<br>\n      <code style="background:var(--bg3);padding:8px 12px;border-radius:6px;display:block;margin:8px 0;font-size:12px;color:var(--accent)">日期,股票代號,股票名稱,動作,股數,價格,手續費,進場理由,備注</code>\n      動作填「買進」或「賣出」\n    </div>\n    <div class="form-group" style="margin-bottom:16px">\n      <label>選擇 CSV 檔案</label>\n      <input type="file" accept=".csv" id="csv-file-input" style="padding:8px">\n    </div>\n    <div id="import-preview" style="display:none;margin-bottom:16px">\n      <div style="font-size:12px;color:var(--text2);margin-bottom:6px">預覽（前3筆）：</div>\n      <div id="import-preview-content" style="background:var(--bg3);border-radius:8px;padding:10px 12px;font-size:12px;color:var(--text);font-family:monospace;max-height:120px;overflow-y:auto"></div>\n    </div>\n    <div style="display:flex;gap:10px;justify-content:flex-end">\n      <button class="btn btn-ghost" onclick="closeImportModal()">取消</button>\n      <button class="btn btn-primary" onclick="confirmImport()"><i class="ti ti-upload"></i> 匯入</button>\n    </div>\n  </div>\n</div>\n\n<button class="mobile-menu-btn" type="button" onclick="toggleSidebar()" aria-label="開啟目錄"><i class="ti ti-menu-2"></i></button>\n<div class="app" id="app-shell">\n<div class="sidebar-backdrop" onclick="closeSidebarOnMobile()"></div>\n<aside class="sidebar">\n  <div class="logo">\n    <div class="logo-row">\n      <div class="logo-title-wrap">\n        <div class="logo-text">INVEST LOG</div>\n        <div class="logo-sub">個人投資復盤助理</div>\n      </div>\n      <button class="sidebar-toggle" type="button" onclick="toggleSidebar()" aria-label="收合或展開目錄" title="收合/展開目錄"><i class="ti ti-layout-sidebar-left-collapse"></i></button>\n    </div>\n  </div>\n  <nav class="nav">\n    <div class="nav-item active" onclick="showPage(\'overview\')"><i class="ti ti-layout-dashboard"></i><span class="nav-label">持股總覽</span></div>\n    <div class="nav-item" onclick="showPage(\'add\')"><i class="ti ti-plus"></i><span class="nav-label">新增交易</span></div>\n    <div class="nav-item" onclick="showPage(\'pnl\')"><i class="ti ti-chart-bar"></i><span class="nav-label">損益分析</span></div>\n    <div class="nav-item" onclick="showPage(\'review\')"><i class="ti ti-notebook"></i><span class="nav-label">投資復盤</span></div>\n    <div class="nav-item" onclick="showPage(\'export\')"><i class="ti ti-database-export"></i><span class="nav-label">匯出 / 匯入</span></div>\n  </nav>\n  <div class="sidebar-bottom">\n    <div class="nav-item" onclick="showPage(\'settings\')"><i class="ti ti-settings"></i><span class="nav-label">設定</span></div>\n  </div>\n</aside>\n\n<main class="main">\n\n<!-- ═══ 持股總覽 ═══ -->\n<div class="page active" id="page-overview">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">持股總覽</div>\n      <div class="page-sub" id="last-update-text">Render 後端股價服務載入中...</div>\n    </div>\n    <div class="header-actions">\n      <button class="refresh-btn" id="refresh-btn" onclick="refreshPrices()">\n        <i class="ti ti-refresh"></i> 更新股價\n      </button>\n    </div>\n  </div>\n\n  <div class="metric-grid">\n    <div class="metric-card">\n      <div class="metric-label">總投入成本</div>\n      <div class="metric-val mono" id="m-cost">$567,490</div>\n      <div class="metric-sub">含手續費</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">目前市值</div>\n      <div class="metric-val mono" id="m-value">$601,230</div>\n      <div class="metric-sub">以現價計算</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">未實現損益</div>\n      <div class="metric-val mono pos" id="m-unrealized">+$33,740</div>\n      <div class="metric-sub pos" id="m-unrealized-pct">+5.95%</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">已實現損益</div>\n      <div class="metric-val mono" id="m-realized">$0</div>\n      <div class="metric-sub">歷史交易統計</div>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">目前持股</span>\n      <div style="display:flex;gap:8px;align-items:center">\n        <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)">\n          <span class="price-dot" id="dot-status"></span>\n          <span id="price-status-text">尚未更新</span>\n        </div>\n        <button class="btn btn-ghost" style="padding:5px 11px;font-size:12px" onclick="showPage(\'add\')">\n          <i class="ti ti-plus"></i> 新增\n        </button>\n      </div>\n    </div>\n    <table>\n      <thead>\n        <tr>\n          <th>股票</th>\n          <th>持有股數</th>\n          <th>平均成本</th>\n          <th>現價</th>\n          <th>漲跌</th>\n          <th>未實現損益</th>\n          <th>報酬率</th>\n          <th>狀態</th>\n        </tr>\n      </thead>\n      <tbody id="holdings-tbody"></tbody>\n    </table>\n    <div class="price-note" id="price-note">\n      ⚠ 股價會優先抓盤中即時資料；若瀏覽器擋住或休市，會改用最新收盤價。僅供參考，不構成投資建議。\n    </div>\n  </div>\n\n  <div class="two-col">\n    <div class="section">\n      <div class="section-head"><span class="section-title">持股比例</span></div>\n      <div class="chart-wrap" style="height:230px;position:relative">\n        <canvas id="pieChart" role="img" aria-label="持股比例圓餅圖">持股比例圖</canvas>\n      </div>\n    </div>\n    <div class="section">\n      <div class="section-head"><span class="section-title">個股損益比較</span></div>\n      <div class="chart-wrap" style="height:230px;position:relative">\n        <canvas id="barChart" role="img" aria-label="個股損益長條圖">個股損益比較</canvas>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 新增交易 ═══ -->\n<div class="page" id="page-add">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">新增交易紀錄</div>\n      <div class="page-sub">記錄每筆買賣，建立完整投資日誌</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="tab-row">\n      <div class="tab active" id="tab-buy" onclick="switchTab(\'buy\')">買進</div>\n      <div class="tab" id="tab-sell" onclick="switchTab(\'sell\')">賣出</div>\n    </div>\n    <div class="form-grid">\n      <div class="form-group">\n        <label>股票代號</label>\n        <input type="text" placeholder="例：2330" id="f-code" oninput="autoFillName()">\n      </div>\n      <div class="form-group">\n        <label>股票名稱</label>\n        <input type="text" placeholder="例：台積電" id="f-name">\n      </div>\n      <div class="form-group">\n        <label>交易日期</label>\n        <input type="date" id="f-date">\n      </div>\n      <div class="form-group">\n        <label>股數</label>\n        <input type="number" placeholder="例：10" id="f-qty" oninput="calcFee()">\n      </div>\n      <div class="form-group">\n        <label>價格（元）</label>\n        <input type="number" placeholder="例：800" id="f-price" oninput="calcFee()">\n      </div>\n      <div class="form-group">\n        <label>手續費（元）</label>\n        <input type="number" placeholder="自動計算" id="f-fee">\n      </div>\n      <div class="form-group" id="sell-tax-group" style="display:none">\n        <label>證交稅（元）</label>\n        <input type="number" placeholder="自動計算 0.3%" id="f-tax">\n      </div>\n      <div class="form-group">\n        <label>操作方向</label>\n        <select id="f-direction">\n          <option>短線（1週內）</option>\n          <option>波段（1-3個月）</option>\n          <option selected>中期（3-6個月）</option>\n          <option>長期（6個月以上）</option>\n        </select>\n      </div>\n      <div class="form-group full">\n        <label>進場理由</label>\n        <select id="f-reason">\n          <option>技術面突破（量增價漲）</option>\n          <option>財報優於預期</option>\n          <option>產業題材/新聞</option>\n          <option>試水溫/分批佈局</option>\n          <option>均線支撐買入</option>\n          <option>跌深反彈</option>\n          <option>其他</option>\n        </select>\n      </div>\n      <div class="form-group">\n        <label>停損價</label>\n        <input type="number" placeholder="停損觸發價" id="f-stop">\n      </div>\n      <div class="form-group">\n        <label>停利價</label>\n        <input type="number" placeholder="停利目標價" id="f-target">\n      </div>\n      <div class="form-group full">\n        <label>當時判斷 / 備注</label>\n        <textarea placeholder="記錄當時技術面判斷、新聞背景、心理狀態等..." id="f-note"></textarea>\n      </div>\n    </div>\n    <div class="btn-row">\n      <button class="btn btn-ghost" onclick="clearForm()"><i class="ti ti-x"></i> 清除</button>\n      <button class="btn btn-primary" onclick="saveRecord()"><i class="ti ti-check"></i> 儲存紀錄</button>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">交易紀錄</span>\n      <button class="btn btn-ghost" style="padding:5px 11px;font-size:12px" onclick="exportCSV(\'records\')">\n        <i class="ti ti-download"></i> 匯出此表\n      </button>\n    </div>\n    <table>\n      <thead>\n        <tr><th>日期</th><th>股票</th><th>動作</th><th>股數</th><th>價格</th><th>進場理由</th><th>備注</th><th></th></tr>\n      </thead>\n      <tbody id="records-tbody"></tbody>\n    </table>\n  </div>\n</div>\n\n<!-- ═══ 損益分析 ═══ -->\n<div class="page" id="page-pnl">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">損益分析</div>\n      <div class="page-sub">整體投資績效報告</div>\n    </div>\n    <div class="header-actions">\n      <button class="btn btn-ghost" onclick="exportCSV(\'pnl\')"><i class="ti ti-download"></i> 匯出損益表</button>\n    </div>\n  </div>\n  <div class="metric-grid">\n    <div class="metric-card">\n      <div class="metric-label">交易勝率</div>\n      <div class="metric-val mono" id="p-winrate">—</div>\n      <div class="metric-sub" id="p-winrate-sub">—</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">平均持有天數</div>\n      <div class="metric-val mono" id="p-avgdays">—</div>\n      <div class="metric-sub">已實現交易</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">最大單筆獲利</div>\n      <div class="metric-val mono pos" id="p-maxwin">—</div>\n      <div class="metric-sub" id="p-maxwin-sub">—</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">最大單筆虧損</div>\n      <div class="metric-val mono neg" id="p-maxloss">—</div>\n      <div class="metric-sub" id="p-maxloss-sub">—</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="section-head"><span class="section-title">進場理由勝率分析</span></div>\n    <div style="padding:16px 20px" id="reason-pnl">\n      <div style="color:var(--text2);font-size:13px">新增交易紀錄後，勝率分析將自動出現。</div>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 投資復盤 ═══ -->\n<div class="page" id="page-review">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">投資復盤</div>\n      <div class="page-sub">逐筆回顧操作決策</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="section-head"><span class="section-title">交易復盤清單</span></div>\n    <div id="review-list">\n      <div style="padding:40px;text-align:center;color:var(--text2)">\n        <i class="ti ti-notebook" style="font-size:36px;display:block;margin-bottom:12px;color:var(--text3)"></i>\n        尚無交易紀錄，請先在「新增交易」頁面新增紀錄。\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 匯出 / 匯入 ═══ -->\n<div class="page" id="page-export">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">匯出 / 匯入</div>\n      <div class="page-sub">備份資料或匯入歷史紀錄</div>\n    </div>\n  </div>\n\n  <div class="export-panel">\n    <div class="export-title"><i class="ti ti-download" style="font-size:18px;color:var(--accent)"></i> 匯出 CSV</div>\n    <div class="export-grid">\n      <div class="export-card" onclick="exportCSV(\'all\')">\n        <i class="ti ti-file-spreadsheet"></i>\n        <div class="export-card-title">完整交易紀錄</div>\n        <div class="export-card-sub">所有買賣紀錄，含備注</div>\n      </div>\n      <div class="export-card" onclick="exportCSV(\'holdings\')">\n        <i class="ti ti-chart-pie"></i>\n        <div class="export-card-title">目前持股清單</div>\n        <div class="export-card-sub">現有持股與成本</div>\n      </div>\n      <div class="export-card" onclick="exportCSV(\'pnl\')">\n        <i class="ti ti-report-money"></i>\n        <div class="export-card-title">損益分析表</div>\n        <div class="export-card-sub">已實現損益統計</div>\n      </div>\n    </div>\n  </div>\n\n  <div class="export-panel">\n    <div class="export-title"><i class="ti ti-upload" style="font-size:18px;color:var(--green)"></i> 匯入 CSV</div>\n    <div style="font-size:13px;color:var(--text2);margin-bottom:16px;line-height:1.8">\n      支援從 Excel 或其他工具匯出的 CSV 格式，系統自動解析並加入交易紀錄。<br>\n      <strong style="color:var(--text)">格式：</strong>\n      <code style="background:var(--bg2);padding:4px 8px;border-radius:5px;font-size:12px;color:var(--accent)">\n        日期, 股票代號, 股票名稱, 動作, 股數, 價格, 手續費, 進場理由, 備注\n      </code>\n    </div>\n    <div style="display:flex;gap:12px;align-items:center">\n      <button class="btn btn-green" onclick="openImportModal()"><i class="ti ti-upload"></i> 選擇 CSV 檔案</button>\n      <button class="btn btn-ghost" onclick="downloadTemplate()"><i class="ti ti-template"></i> 下載範本</button>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">資料管理</span>\n    </div>\n    <div style="padding:20px;display:flex;gap:12px;align-items:center">\n      <button class="btn btn-ghost" onclick="exportCSV(\'backup\')">\n        <i class="ti ti-database-export"></i> 完整備份（JSON）\n      </button>\n      <button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" onclick="clearAllData()">\n        <i class="ti ti-trash"></i> 清除所有資料\n      </button>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 設定 ═══ -->\n<div class="page" id="page-settings">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">設定</div>\n      <div class="page-sub">個人化你的投資助理</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="section-head"><span class="section-title">交易參數</span></div>\n    <div class="form-grid">\n      <div class="form-group">\n        <label>手續費率（%）</label>\n        <input type="number" value="0.1425" step="0.001" id="s-fee-rate">\n      </div>\n      <div class="form-group">\n        <label>總資金（元）</label>\n        <input type="number" placeholder="600000" id="s-capital">\n      </div>\n      <div class="form-group full">\n        <label>停損警示門檻</label>\n        <select id="s-stop-threshold">\n          <option>距停損價 5%</option>\n          <option selected>距停損價 3%</option>\n          <option>距停損價 1%</option>\n        </select>\n      </div>\n    </div>\n    <div class="btn-row">\n      <button class="btn btn-primary" onclick="saveSettings()"><i class="ti ti-check"></i> 儲存設定</button>\n    </div>\n  </div>\n</div>\n\n</main>\n</div>\n\n<script>\n// ═══════════════════════════════════════════\n// 資料層 — 雲端同步（Render 後端 + PostgreSQL / Supabase）\n// ═══════════════════════════════════════════\nconst STORE_KEY = \'investlog_v2_base_holdings\';\nconst OLD_STORE_KEY = \'investlog_v1\';\n\n// 使用者指定的原先持股：這些是固定基礎部位，按「清除所有資料」也會保留。\nconst BASE_HOLDINGS = [\n  { code:\'0050\', name:\'元大台灣50\', qty:307, avgCost:76.95, totalCost:23624 },\n  { code:\'2303\', name:\'聯電\', qty:150, avgCost:72.37, totalCost:10855 },\n  { code:\'2308\', name:\'台達電\', qty:35, avgCost:2008.66, totalCost:70303 },\n  { code:\'2330\', name:\'台積電\', qty:60, avgCost:1956.02, totalCost:117361 },\n  { code:\'2454\', name:\'聯發科\', qty:5, avgCost:3414.8, totalCost:17074 }\n];\n\nfunction emptyData() {\n  return { records: [], prices: {}, priceType: {}, priceSource: {}, settings: { feeRate: 0.1425 } };\n}\n\nfunction isOldSampleRecord(r) {\n  const key = `${r?.date}|${r?.code}|${r?.action}|${r?.qty}|${r?.price}`;\n  return [\n    \'2025-04-01|2330|buy|10|800\',\n    \'2025-04-05|2303|buy|100|48\',\n    \'2025-04-10|5190|buy|1|5190\',\n    \'2025-04-20|2454|buy|5|1200\'\n  ].includes(key);\n}\n\nfunction normalizeData(d) {\n  return Object.assign(emptyData(), d || {}, {\n    records: Array.isArray(d?.records) ? d.records : [],\n    prices: d?.prices || {},\n    priceType: d?.priceType || {},\n    priceSource: d?.priceSource || {},\n    settings: d?.settings || { feeRate: 0.1425 }\n  });\n}\n\nfunction loadLocalBackup() {\n  try {\n    const saved = JSON.parse(localStorage.getItem(STORE_KEY));\n    if (saved && Array.isArray(saved.records)) return normalizeData(saved);\n  } catch(e) {}\n  try {\n    const old = JSON.parse(localStorage.getItem(OLD_STORE_KEY));\n    if (old && Array.isArray(old.records)) {\n      const migrated = emptyData();\n      migrated.records = old.records.filter(r => !isOldSampleRecord(r));\n      migrated.prices = old.prices || {};\n      migrated.priceType = old.priceType || {};\n      migrated.priceSource = old.priceSource || {};\n      migrated.settings = old.settings || { feeRate: 0.1425 };\n      return migrated;\n    }\n  } catch(e) {}\n  return emptyData();\n}\n\nlet db = emptyData();\nlet cloudReady = false;\nlet saveTimer = null;\n\nasync function loadCloudData() {\n  try {\n    const res = await fetch(\'/api/state\', { cache: \'no-store\' });\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    const payload = await res.json();\n    db = normalizeData(payload.data);\n    cloudReady = true;\n    localStorage.setItem(STORE_KEY, JSON.stringify(db));\n    setDot(\'ok\', \'雲端資料已載入\');\n    return true;\n  } catch (err) {\n    console.warn(\'cloud load failed:\', err);\n    db = loadLocalBackup();\n    cloudReady = false;\n    setDot(\'error\', \'雲端載入失敗，暫用本機備份\');\n    showToast(\'雲端資料載入失敗，請確認 Render 後端與 DATABASE_URL\', \'info\');\n    return false;\n  }\n}\n\nfunction saveData(d) {\n  const normalized = normalizeData(d);\n  localStorage.setItem(STORE_KEY, JSON.stringify(normalized));\n  db = normalized;\n  queueCloudSave(normalized);\n}\n\nfunction queueCloudSave(d) {\n  clearTimeout(saveTimer);\n  saveTimer = setTimeout(() => syncCloudData(d), 450);\n}\n\nasync function syncCloudData(d) {\n  try {\n    const res = await fetch(\'/api/state\', {\n      method: \'PUT\',\n      headers: { \'Content-Type\': \'application/json\' },\n      body: JSON.stringify(d)\n    });\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    cloudReady = true;\n    const text = document.getElementById(\'last-update-text\');\n    if (text) text.textContent = `雲端已同步 · ${new Date().toLocaleString(\'zh-TW\')} · 台股`;\n  } catch (err) {\n    cloudReady = false;\n    console.warn(\'cloud save failed:\', err);\n    const text = document.getElementById(\'last-update-text\');\n    if (text) text.textContent = `雲端同步失敗，已暫存本機 · ${new Date().toLocaleString(\'zh-TW\')}`;\n  }\n}\n\n// ═══════════════════════════════════════════\n// 股價更新 — Render 後端代理版\n// 這版不再讓瀏覽器直接連外部股價 API，而是呼叫同網域 /api/prices。\n// 部署到 Render 後：前端 → Render app.py → 外部股價來源 → 回傳前端。\n// ═══════════════════════════════════════════\nlet priceCharts = {};\n\nfunction isTradingHours() {\n  const now = new Date();\n  const day = now.getDay();\n  if (day === 0 || day === 6) return false;\n  const h = now.getHours(), m = now.getMinutes();\n  const mins = h * 60 + m;\n  return mins >= 9 * 60 && mins <= 13 * 60 + 30;\n}\n\nfunction normalizeStockCode(code) {\n  return String(code || \'\')\n    .trim()\n    .toUpperCase()\n    .replace(/\\.TW$|\\.TWO$/i, \'\')\n    .replace(/^TSE_|^OTC_/i, \'\')\n    .replace(/\\.tw$/i, \'\');\n}\n\nasync function refreshPrices() {\n  const holdings = calcHoldings();\n  const codes = [...new Set(holdings.map(h => normalizeStockCode(h.code)))].filter(Boolean);\n  if (!codes.length) { showToast(\'尚無持股，請先新增交易紀錄\', \'info\'); return; }\n\n  const btn = document.getElementById(\'refresh-btn\');\n  if (btn) {\n    btn.classList.add(\'spinning\');\n    btn.innerHTML = \'<i class="ti ti-refresh"></i> 更新中...\';\n  }\n  setDot(\'updating\', \'Render 後端抓取中...\');\n\n  try {\n    const res = await fetch(`/api/prices?codes=${encodeURIComponent(codes.join(\',\'))}&_=${Date.now()}`, { cache: \'no-store\' });\n    const payload = await res.json();\n    if (!res.ok || !payload.ok) {\n      throw new Error(payload.error || \'後端股價 API 回傳失敗\');\n    }\n\n    const priceMap = payload.prices || {};\n    const successCodes = Object.keys(priceMap).filter(code => priceMap[code] && Number(priceMap[code].price) > 0);\n\n    if (!successCodes.length) {\n      throw new Error((payload.attempts || []).join(\'；\') || \'沒有取得任何股價\');\n    }\n\n    for (const code of successCodes) {\n      const q = priceMap[code];\n      db.prices[code] = Number(q.price);\n      db.priceType = db.priceType || {};\n      db.priceSource = db.priceSource || {};\n      db.priceType[code] = q.type || \'price\';\n      db.priceSource[code] = q.source || \'Render 後端\';\n\n      if (q.name) {\n        db.records = db.records.map(r => {\n          const rc = normalizeStockCode(r.code);\n          if (rc === code && (!r.name || r.name === r.code)) return { ...r, name: q.name };\n          return r;\n        });\n      }\n    }\n\n    saveData(db);\n    renderAll();\n\n    const now = new Date();\n    const timeStr = now.toLocaleTimeString(\'zh-TW\', {hour:\'2-digit\', minute:\'2-digit\'});\n    const trading = isTradingHours();\n    const allLive = successCodes.every(c => (priceMap[c].type || \'\').includes(\'live\'));\n    const note = allLive && trading\n      ? `盤中即時報價 · ${timeStr} 更新`\n      : `最新可用價格／收盤價 · ${timeStr} 更新`;\n    document.getElementById(\'last-update-text\').textContent = note;\n\n    const failCount = codes.length - successCodes.length;\n    setDot(\'ok\', failCount ? `成功 ${successCodes.length}/${codes.length}，部分使用快取` : `成功 ${successCodes.length}/${codes.length}`);\n    showToast(`股價更新成功（${successCodes.length}/${codes.length} 支）`, \'success\');\n    console.log(\'[Render 後端股價更新成功]\', payload);\n  } catch (e) {\n    setDot(\'error\', \'抓取失敗，使用快取\');\n    showToast(\'無法抓取股價；請確認 Render 網址已正常部署，或稍後重試。\', \'info\');\n    console.error(\'[Render 後端股價抓取失敗]\', e);\n  }\n\n  if (btn) {\n    btn.classList.remove(\'spinning\');\n    btn.innerHTML = \'<i class="ti ti-refresh"></i> 更新股價\';\n  }\n}\n\nfunction setDot(state, text) {\n  const dot = document.getElementById(\'dot-status\');\n  const txt = document.getElementById(\'price-status-text\');\n  if (!dot || !txt) return;\n  dot.className = \'price-dot\';\n  if (state === \'ok\') { dot.style.background = \'var(--green)\'; }\n  else if (state === \'updating\') { dot.className = \'price-dot updating\'; dot.style.background = \'\'; }\n  else if (state === \'error\') { dot.style.background = \'var(--red)\'; }\n  txt.textContent = text;\n}\n\n// ═══════════════════════════════════════════\n// 計算持股\n// ═══════════════════════════════════════════\nfunction calcHoldings() {\n  const holdings = {};\n\n  // 先放入固定原先持股，確保「清除所有資料」也不會刪掉這些部位。\n  for (const b of BASE_HOLDINGS) {\n    const k = normalizeStockCode(b.code);\n    holdings[k] = {\n      code: k,\n      name: b.name,\n      qty: Number(b.qty) || 0,\n      totalCost: Number(b.totalCost) || (Number(b.qty) || 0) * (Number(b.avgCost) || 0),\n      stop: 0,\n      target: 0,\n      isBase: true\n    };\n  }\n\n  // 再疊加使用者後續新增的買賣紀錄。\n  for (const r of db.records) {\n    const k = normalizeStockCode(r.code);\n    if (!k) continue;\n    if (!holdings[k]) holdings[k] = { code:k, name:r.name, qty:0, totalCost:0, stop:r.stop, target:r.target, isBase:false };\n    if (r.name && (!holdings[k].name || holdings[k].name === k)) holdings[k].name = r.name;\n    if (r.stop) holdings[k].stop = r.stop;\n    if (r.target) holdings[k].target = r.target;\n\n    const qty = parseFloat(r.qty) || 0;\n    const price = parseFloat(r.price) || 0;\n    const fee = parseFloat(r.fee) || 0;\n\n    if (r.action === \'buy\') {\n      holdings[k].qty += qty;\n      holdings[k].totalCost += qty * price + fee;\n    } else {\n      const beforeQty = holdings[k].qty;\n      const avgCost = beforeQty > 0 ? holdings[k].totalCost / beforeQty : 0;\n      const matchedQty = Math.min(qty, Math.max(beforeQty, 0));\n      holdings[k].qty -= qty;\n      holdings[k].totalCost -= avgCost * matchedQty;\n      if (holdings[k].qty <= 0) {\n        holdings[k].qty = 0;\n        holdings[k].totalCost = 0;\n      }\n    }\n  }\n  return Object.values(holdings).filter(h => h.qty > 0);\n}\nfunction getStatus(pnlPct, price, stop) {\n  if (stop && price <= stop * 1.01) return [\'near-stop\',\'接近停損\'];\n  if (pnlPct >= 10) return [\'profit\',\'獲利中\'];\n  if (pnlPct >= 3) return [\'profit\',\'穩定持有\'];\n  if (pnlPct >= -2) return [\'hold\',\'成本附近\'];\n  if (pnlPct >= -8) return [\'hold\',\'小虧觀察\'];\n  return [\'near-stop\',\'停損觀察\'];\n}\n\nfunction renderHoldings() {\n  const holdings = calcHoldings();\n  const tbody = document.getElementById(\'holdings-tbody\');\n  tbody.innerHTML = \'\';\n  for (const h of holdings) {\n    const avgCost = h.totalCost / h.qty;\n    const price = db.prices[h.code] || avgCost;\n    const pnl = (price - avgCost) * h.qty;\n    const pnlPct = ((price - avgCost) / avgCost * 100);\n    const [sc, label] = getStatus(pnlPct, price, h.stop);\n    // price change vs yesterday (simulate from cache delta)\n    const chg = pnlPct.toFixed(2);\n    const pt = db.priceType?.[h.code];\n    const labelText = pt === \'live\' ? \'盤中\' : pt === \'prev\' ? \'昨收\' : pt === \'close\' ? \'收盤\' : pt === \'fallback\' ? \'參考\' : \'\';\n    const labelColor = pt === \'live\' ? \'var(--green)\' : \'var(--text2)\';\n    const priceLabel = db.prices[h.code] && labelText\n      ? `<span style="font-size:10px;color:${labelColor};margin-left:4px">${labelText}</span>` : \'\';\n    tbody.innerHTML += `<tr>\n      <td><strong>${h.code}</strong><br><span style="color:var(--text2);font-size:11px">${h.name}</span>${h.isBase ? \'<br><span style="color:var(--accent);font-size:10px">原先持股</span>\' : \'\'}</td>\n      <td class="mono">${h.qty}</td>\n      <td class="mono">${Math.round(avgCost).toLocaleString()}</td>\n      <td>\n        <div class="price-cell">\n          <span class="mono">${Math.round(price).toLocaleString()}</span>\n          ${priceLabel}\n          ${db.prices[h.code] ? \'<span class="price-dot" style="background:var(--green)"></span>\' : \'\'}\n        </div>\n      </td>\n      <td><span class="price-badge ${pnlPct<0?\'neg\':\'\'}">${pnlPct>=0?\'+\':\'\'}${chg}%</span></td>\n      <td class="mono ${pnl>=0?\'pos\':\'neg\'}">${pnl>=0?\'+\':\'\'}${Math.round(pnl).toLocaleString()}</td>\n      <td class="mono ${pnlPct>=0?\'pos\':\'neg\'}">${pnlPct>=0?\'+\':\'\'}${pnlPct.toFixed(2)}%</td>\n      <td><span class="badge ${sc}">${label}</span></td>\n    </tr>`;\n  }\n  if (!holdings.length) {\n    tbody.innerHTML = \'<tr><td colspan="8" style="text-align:center;color:var(--text2);padding:32px">尚無持股</td></tr>\';\n  }\n}\n\nfunction calcRealizedPnl() {\n  const positions = {};\n  for (const b of BASE_HOLDINGS) {\n    const k = normalizeStockCode(b.code);\n    positions[k] = {\n      qty: Number(b.qty) || 0,\n      cost: Number(b.totalCost) || (Number(b.qty) || 0) * (Number(b.avgCost) || 0)\n    };\n  }\n  let realized = 0;\n  const sorted = [...db.records].sort((a, b) => {\n    const dateCompare = String(a.date || \'\').localeCompare(String(b.date || \'\'));\n    if (dateCompare !== 0) return dateCompare;\n    return (a.ts || a.id || 0) - (b.ts || b.id || 0);\n  });\n\n  for (const r of sorted) {\n    const code = normalizeStockCode(r.code);\n    if (!code) continue;\n    if (!positions[code]) positions[code] = { qty: 0, cost: 0 };\n\n    const qty = parseFloat(r.qty) || 0;\n    const price = parseFloat(r.price) || 0;\n    const fee = parseFloat(r.fee) || 0;\n    const tax = parseFloat(r.tax) || 0;\n    const amount = qty * price;\n\n    if (r.action === \'buy\') {\n      positions[code].qty += qty;\n      positions[code].cost += amount + fee;\n    } else if (r.action === \'sell\') {\n      const pos = positions[code];\n      const avgCost = pos.qty > 0 ? pos.cost / pos.qty : 0;\n      const matchedQty = Math.min(qty, Math.max(pos.qty, 0));\n      const costRemoved = avgCost * matchedQty;\n      const proceeds = amount - fee - tax;\n      realized += proceeds - costRemoved;\n\n      pos.qty -= qty;\n      pos.cost -= costRemoved;\n      if (pos.qty <= 0) {\n        pos.qty = 0;\n        pos.cost = 0;\n      }\n    }\n  }\n\n  return realized;\n}\n\nfunction updateMetrics() {\n  const holdings = calcHoldings();\n  let totalCost = 0, totalValue = 0;\n  for (const h of holdings) {\n    totalCost += h.totalCost;\n    totalValue += (db.prices[h.code] || h.totalCost / h.qty) * h.qty;\n  }\n  const unreal = totalValue - totalCost;\n  const unrealPct = totalCost ? (unreal / totalCost * 100) : 0;\n  document.getElementById(\'m-cost\').textContent = \'$\' + Math.round(totalCost).toLocaleString();\n  document.getElementById(\'m-value\').textContent = \'$\' + Math.round(totalValue).toLocaleString();\n  const uEl = document.getElementById(\'m-unrealized\');\n  uEl.textContent = (unreal>=0?\'+\':\'\') + \'$\' + Math.round(unreal).toLocaleString();\n  uEl.className = \'metric-val mono \' + (unreal>=0?\'pos\':\'neg\');\n  document.getElementById(\'m-unrealized-pct\').textContent = (unrealPct>=0?\'+\':\'\') + unrealPct.toFixed(2) + \'%\';\n  document.getElementById(\'m-unrealized-pct\').className = \'metric-sub \' + (unrealPct>=0?\'pos\':\'neg\');\n\n  const realized = calcRealizedPnl();\n  const rEl = document.getElementById(\'m-realized\');\n  if (rEl) {\n    rEl.textContent = (realized >= 0 ? \'+\' : \'-\') + \'$\' + Math.abs(Math.round(realized)).toLocaleString();\n    if (Math.round(realized) === 0) rEl.textContent = \'$0\';\n    rEl.className = \'metric-val mono \' + (realized > 0 ? \'pos\' : realized < 0 ? \'neg\' : \'\');\n  }\n}\n\n// ═══════════════════════════════════════════\n// 圖表\n// ═══════════════════════════════════════════\nfunction updateCharts() {\n  const holdings = calcHoldings();\n  const labels = holdings.map(h => h.name || h.code);\n  const pnlData = holdings.map(h => {\n    const avgCost = h.totalCost / h.qty;\n    const price = db.prices[h.code] || avgCost;\n    return Math.round((price - avgCost) * h.qty);\n  });\n  const weights = holdings.map(h => (db.prices[h.code] || h.totalCost/h.qty) * h.qty);\n\n  const colors = [\'#3b82f6\',\'#10b981\',\'#f59e0b\',\'#ef4444\',\'#a855f7\',\'#ec4899\'];\n\n  if (priceCharts.pie) { priceCharts.pie.destroy(); }\n  const pieCtx = document.getElementById(\'pieChart\');\n  if (pieCtx && weights.some(w=>w>0)) {\n    priceCharts.pie = new Chart(pieCtx, {\n      type: \'doughnut\',\n      data: { labels, datasets: [{ data: weights, backgroundColor: colors.slice(0, labels.length), borderWidth: 0, hoverOffset: 4 }] },\n      options: { responsive:true, maintainAspectRatio:false, cutout:\'68%\',\n        plugins: { legend:{display:false}, tooltip:{callbacks:{label:ctx=>`${ctx.label}: ${(ctx.parsed/weights.reduce((a,b)=>a+b,0)*100).toFixed(1)}%`}} } }\n    });\n  }\n\n  if (priceCharts.bar) { priceCharts.bar.destroy(); }\n  const barCtx = document.getElementById(\'barChart\');\n  if (barCtx && pnlData.length) {\n    priceCharts.bar = new Chart(barCtx, {\n      type: \'bar\',\n      data: { labels, datasets: [{ label:\'未實現損益\', data:pnlData, backgroundColor: pnlData.map(v=>v>=0?\'#10b981\':\'#ef4444\'), borderRadius:5 }] },\n      options: { responsive:true, maintainAspectRatio:false,\n        plugins: { legend:{display:false} },\n        scales: { y:{ grid:{color:\'rgba(255,255,255,0.05)\'}, ticks:{color:\'#8892a4\',font:{size:11}} }, x:{ grid:{display:false}, ticks:{color:\'#8892a4\',font:{size:11}} } } }\n    });\n  }\n}\n\n// ═══════════════════════════════════════════\n// 新增交易\n// ═══════════════════════════════════════════\nlet currentTab = \'buy\';\nfunction switchTab(t) {\n  currentTab = t;\n  document.getElementById(\'tab-buy\').classList.toggle(\'active\', t===\'buy\');\n  document.getElementById(\'tab-sell\').classList.toggle(\'active\', t===\'sell\');\n  document.getElementById(\'sell-tax-group\').style.display = t===\'sell\'?\'flex\':\'none\';\n}\n\nconst stockNames = {\'0050\':\'元大台灣50\',\'2308\':\'台達電\',\'2330\':\'台積電\',\'2303\':\'聯電\',\'2454\':\'聯發科\',\'5190\':\'旺矽\',\'2317\':\'鴻海\',\'2002\':\'中鋼\',\'1301\':\'台塑\',\'2881\':\'富邦金\',\'3008\':\'大立光\',\'2379\':\'瑞昱\'};\nfunction autoFillName() {\n  const c = document.getElementById(\'f-code\').value.trim();\n  if (stockNames[c]) document.getElementById(\'f-name\').value = stockNames[c];\n}\nfunction calcFee() {\n  const qty = parseFloat(document.getElementById(\'f-qty\').value)||0;\n  const price = parseFloat(document.getElementById(\'f-price\').value)||0;\n  const rate = db.settings?.feeRate || 0.1425;\n  const fee = Math.round(qty * price * rate / 100);\n  if (fee) document.getElementById(\'f-fee\').value = fee;\n  if (currentTab===\'sell\') {\n    const tax = Math.round(qty * price * 0.3 / 100);\n    document.getElementById(\'f-tax\').value = tax;\n  }\n}\n\nfunction saveRecord() {\n  const code = document.getElementById(\'f-code\').value.trim();\n  const name = document.getElementById(\'f-name\').value.trim();\n  const qty = parseFloat(document.getElementById(\'f-qty\').value);\n  const price = parseFloat(document.getElementById(\'f-price\').value);\n  const date = document.getElementById(\'f-date\').value;\n  if (!code || !qty || !price || !date) { showToast(\'請填寫股票代號、日期、股數與價格\', \'info\'); return; }\n\n  const record = {\n    id: Date.now(),\n    date, code, name: name||code,\n    action: currentTab,\n    qty, price,\n    fee: parseFloat(document.getElementById(\'f-fee\').value)||0,\n    tax: parseFloat(document.getElementById(\'f-tax\').value)||0,\n    direction: document.getElementById(\'f-direction\').value,\n    reason: document.getElementById(\'f-reason\').value,\n    stop: parseFloat(document.getElementById(\'f-stop\').value)||0,\n    target: parseFloat(document.getElementById(\'f-target\').value)||0,\n    note: document.getElementById(\'f-note\').value.trim(),\n    ts: Date.now()\n  };\n\n  db.records.push(record);\n  saveData(db);\n  renderRecords();\n  renderHoldings();\n  updateMetrics();\n  updateCharts();\n  renderReview();\n  updatePnlPage();\n  clearForm();\n  showToast(\'交易紀錄已儲存並同步到雲端！\', \'success\');\n}\n\nfunction renderRecords() {\n  const tbody = document.getElementById(\'records-tbody\');\n  tbody.innerHTML = \'\';\n  const sorted = [...db.records].reverse();\n  for (const r of sorted) {\n    tbody.innerHTML += `<tr>\n      <td>${r.date}</td>\n      <td><strong>${r.code}</strong> ${r.name}</td>\n      <td><span class="badge ${r.action===\'buy\'?\'buy\':\'loss\'}">${r.action===\'buy\'?\'買進\':\'賣出\'}</span></td>\n      <td class="mono">${r.qty}</td>\n      <td class="mono">${r.price.toLocaleString()}</td>\n      <td><span class="tag tech">${r.reason.split(\'（\')[0]}</span></td>\n      <td style="color:var(--text2);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.note||\'—\'}</td>\n      <td><button onclick="deleteRecord(${r.id})" style="background:none;border:none;cursor:pointer;color:var(--text3);font-size:15px;padding:2px 6px" title="刪除">✕</button></td>\n    </tr>`;\n  }\n  if (!sorted.length) {\n    tbody.innerHTML = \'<tr><td colspan="8" style="text-align:center;color:var(--text2);padding:28px">尚無紀錄</td></tr>\';\n  }\n}\n\nfunction deleteRecord(id) {\n  if (!confirm(\'確定刪除此筆紀錄？\')) return;\n  db.records = db.records.filter(r => r.id !== id);\n  saveData(db);\n  renderAll();\n  showToast(\'已刪除\', \'info\');\n}\n\nfunction clearForm() {\n  [\'f-code\',\'f-name\',\'f-qty\',\'f-price\',\'f-fee\',\'f-tax\',\'f-stop\',\'f-target\',\'f-note\'].forEach(id=>{\n    const el=document.getElementById(id); if(el) el.value=\'\';\n  });\n  document.getElementById(\'f-date\').value = new Date().toISOString().split(\'T\')[0];\n}\n\n// ═══════════════════════════════════════════\n// 損益分析頁\n// ═══════════════════════════════════════════\nfunction updatePnlPage() {\n  const buys = db.records.filter(r=>r.action===\'buy\');\n  const sells = db.records.filter(r=>r.action===\'sell\');\n  const total = buys.length + sells.length;\n  const winCount = sells.filter(r => {\n    const matchBuy = db.records.find(b=>b.code===r.code && b.action===\'buy\');\n    return matchBuy && r.price > matchBuy.price;\n  }).length;\n  const wr = total > 0 ? Math.round(winCount/sells.length*100)||0 : 0;\n  document.getElementById(\'p-winrate\').textContent = sells.length ? wr+\'%\' : \'—\';\n  document.getElementById(\'p-winrate-sub\').textContent = sells.length ? `${sells.length}筆已實現交易` : \'尚無已實現交易\';\n\n  // reason breakdown\n  const reasonMap = {};\n  for (const r of db.records) {\n    const key = r.reason.split(\'（\')[0];\n    if (!reasonMap[key]) reasonMap[key] = { win:0, total:0 };\n    reasonMap[key].total++;\n  }\n  const rEl = document.getElementById(\'reason-pnl\');\n  const entries = Object.entries(reasonMap);\n  if (!entries.length) { rEl.innerHTML=\'<div style="color:var(--text2);font-size:13px">新增交易紀錄後，分析將自動出現。</div>\'; return; }\n  rEl.innerHTML = entries.map(([k,v])=>{\n    const pct = Math.round(v.win/v.total*100)||50;\n    const col = pct>=60?\'var(--green)\':pct>=40?\'var(--yellow)\':\'var(--red)\';\n    return `<div style="margin-bottom:14px">\n      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">\n        <span>${k}</span><span class="mono" style="color:${col}">${v.total}筆</span>\n      </div>\n      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${col}"></div></div>\n    </div>`;\n  }).join(\'\');\n}\n\n// ═══════════════════════════════════════════\n// 投資復盤\n// ═══════════════════════════════════════════\nfunction renderReview() {\n  const el = document.getElementById(\'review-list\');\n  const sorted = [...db.records].reverse();\n  if (!sorted.length) {\n    el.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text2)">\n      <i class="ti ti-notebook" style="font-size:36px;display:block;margin-bottom:12px;color:var(--text3)"></i>\n      尚無交易紀錄\n    </div>`;\n    return;\n  }\n  el.innerHTML = sorted.map(r => {\n    const price = db.prices[r.code] || r.price;\n    const pnlPct = ((price - r.price)/r.price*100);\n    const [sc, label] = getStatus(pnlPct, price, r.stop);\n    return `<div class="review-item">\n      <div class="review-header">\n        <div>\n          <span class="review-stock">${r.code} ${r.name}</span>\n          <div class="review-meta">${r.action===\'buy\'?\'買進\':\'賣出\'} ${r.date} · ${r.qty}股 · ${r.price.toLocaleString()}元 · ${r.direction}</div>\n        </div>\n        <span class="badge ${sc}">${label}</span>\n      </div>\n      <div style="margin-bottom:8px"><span class="tag tech">${r.reason.split(\'（\')[0]}</span></div>\n      ${r.note ? `<div class="review-note">${r.note}</div>` : \'\'}\n      ${r.stop||r.target ? `<div style="font-size:12px;color:var(--text2);margin-top:6px">\n        ${r.stop?`⬇ 停損：${r.stop.toLocaleString()} 元`:\'\'}\n        ${r.target?`\u3000⬆ 停利：${r.target.toLocaleString()} 元`:\'\'}\n      </div>`:\'\'}\n    </div>`;\n  }).join(\'\');\n}\n\n// ═══════════════════════════════════════════\n// CSV 匯出\n// ═══════════════════════════════════════════\nfunction exportCSV(type) {\n  let rows = [], filename = \'\';\n\n  if (type === \'all\' || type === \'records\') {\n    filename = `交易紀錄_${today()}.csv`;\n    rows.push([\'日期\',\'股票代號\',\'股票名稱\',\'動作\',\'股數\',\'價格\',\'手續費\',\'稅\',\'進場理由\',\'操作方向\',\'停損\',\'停利\',\'備注\']);\n    for (const r of db.records) {\n      rows.push([r.date, r.code, r.name, r.action===\'buy\'?\'買進\':\'賣出\', r.qty, r.price, r.fee, r.tax, r.reason, r.direction, r.stop||\'\', r.target||\'\', r.note||\'\']);\n    }\n  } else if (type === \'holdings\') {\n    filename = `持股清單_${today()}.csv`;\n    rows.push([\'股票代號\',\'股票名稱\',\'持有股數\',\'平均成本\',\'現價\',\'未實現損益\',\'報酬率%\']);\n    for (const h of calcHoldings()) {\n      const avgCost = h.totalCost / h.qty;\n      const price = db.prices[h.code] || avgCost;\n      const pnl = Math.round((price - avgCost) * h.qty);\n      const pct = ((price - avgCost)/avgCost*100).toFixed(2);\n      rows.push([h.code, h.name, h.qty, Math.round(avgCost), Math.round(price), pnl, pct]);\n    }\n  } else if (type === \'pnl\') {\n    filename = `損益分析_${today()}.csv`;\n    rows.push([\'股票代號\',\'股票名稱\',\'買進日期\',\'買進價\',\'現價/賣出價\',\'股數\',\'未實現損益\',\'報酬率%\']);\n    for (const r of db.records.filter(r=>r.action===\'buy\')) {\n      const price = db.prices[r.code] || r.price;\n      const pnl = Math.round((price - r.price) * r.qty);\n      const pct = ((price - r.price)/r.price*100).toFixed(2);\n      rows.push([r.code, r.name, r.date, r.price, Math.round(price), r.qty, pnl, pct]);\n    }\n  } else if (type === \'backup\') {\n    const blob = new Blob([JSON.stringify(db, null, 2)], { type: \'application/json\' });\n    const a = document.createElement(\'a\');\n    a.href = URL.createObjectURL(blob);\n    a.download = `投資助理備份_${today()}.json`;\n    a.click();\n    showToast(\'JSON 備份已下載\', \'success\');\n    return;\n  }\n\n  const bom = \'\\uFEFF\'; // UTF-8 BOM for Excel\n  const csv = bom + rows.map(r => r.map(cell => `"${String(cell).replace(/"/g,\'""\')}"`).join(\',\')).join(\'\\n\');\n  const blob = new Blob([csv], { type: \'text/csv;charset=utf-8\' });\n  const a = document.createElement(\'a\');\n  a.href = URL.createObjectURL(blob);\n  a.download = filename;\n  a.click();\n  showToast(`已匯出 ${filename}`, \'success\');\n}\n\nfunction downloadTemplate() {\n  const bom = \'\\uFEFF\';\n  const rows = [\n    [\'日期\',\'股票代號\',\'股票名稱\',\'動作\',\'股數\',\'價格\',\'手續費\',\'進場理由\',\'備注\'],\n    [\'2025-04-01\',\'2330\',\'台積電\',\'買進\',\'10\',\'800\',\'114\',\'技術面突破（量增價漲）\',\'站上800元整數關卡\'],\n    [\'2025-04-10\',\'2303\',\'聯電\',\'賣出\',\'50\',\'52\',\'74\',\'\',\'獲利了結\']\n  ];\n  const csv = bom + rows.map(r => r.map(c=>`"${c}"`).join(\',\')).join(\'\\n\');\n  const blob = new Blob([csv], {type:\'text/csv;charset=utf-8\'});\n  const a = document.createElement(\'a\'); a.href=URL.createObjectURL(blob); a.download=\'交易紀錄範本.csv\'; a.click();\n  showToast(\'範本已下載，請用 Excel 開啟填寫\', \'success\');\n}\n\n// ═══════════════════════════════════════════\n// CSV 匯入\n// ═══════════════════════════════════════════\nlet importedRows = [];\n\nfunction openImportModal() {\n  document.getElementById(\'import-modal\').classList.add(\'show\');\n}\nfunction closeImportModal() {\n  document.getElementById(\'import-modal\').classList.remove(\'show\');\n  document.getElementById(\'csv-file-input\').value = \'\';\n  document.getElementById(\'import-preview\').style.display = \'none\';\n  importedRows = [];\n}\n\ndocument.addEventListener(\'DOMContentLoaded\', () => {\n  const fileInput = document.getElementById(\'csv-file-input\');\n  if (fileInput) {\n    fileInput.addEventListener(\'change\', e => {\n      const file = e.target.files[0];\n      if (!file) return;\n      const reader = new FileReader();\n      reader.onload = ev => {\n        const text = ev.target.result.replace(/^\\uFEFF/,\'\'); // strip BOM\n        const lines = text.trim().split(\'\\n\');\n        const headers = lines[0].split(\',\').map(h=>h.replace(/"/g,\'\').trim());\n        importedRows = [];\n        for (let i = 1; i < lines.length; i++) {\n          const vals = lines[i].split(\',\').map(v=>v.replace(/"/g,\'\').trim());\n          if (vals.length < 5) continue;\n          importedRows.push({\n            id: Date.now() + i,\n            date: vals[0]||\'\', code: vals[1]||\'\', name: vals[2]||vals[1]||\'\',\n            action: vals[3]===\'賣出\'?\'sell\':\'buy\',\n            qty: parseFloat(vals[4])||0, price: parseFloat(vals[5])||0,\n            fee: parseFloat(vals[6])||0, tax: 0,\n            direction: \'中期（3-6個月）\',\n            reason: vals[7]||\'其他\', stop: 0, target: 0,\n            note: vals[8]||\'\', ts: Date.now()\n          });\n        }\n        const preview = importedRows.slice(0,3).map(r=>`${r.date} ${r.code} ${r.name} ${r.action===\'buy\'?\'買進\':\'賣出\'} ${r.qty}股 @${r.price}`).join(\'\\n\');\n        document.getElementById(\'import-preview-content\').textContent = preview || \'（無法解析）\';\n        document.getElementById(\'import-preview\').style.display = \'block\';\n      };\n      reader.readAsText(file, \'UTF-8\');\n    });\n  }\n});\n\nfunction confirmImport() {\n  if (!importedRows.length) { showToast(\'沒有可匯入的資料\', \'info\'); return; }\n  db.records.push(...importedRows);\n  saveData(db);\n  renderAll();\n  closeImportModal();\n  showToast(`已匯入 ${importedRows.length} 筆交易紀錄`, \'success\');\n}\n\n// ═══════════════════════════════════════════\n// 工具\n// ═══════════════════════════════════════════\nfunction today() {\n  return new Date().toISOString().split(\'T\')[0].replace(/-/g,\'\');\n}\n\nfunction showToast(msg, type=\'success\') {\n  const t = document.getElementById(\'toast\');\n  const icon = t.querySelector(\'i\');\n  document.getElementById(\'toast-msg\').textContent = msg;\n  icon.className = type===\'success\' ? \'ti ti-check\' : \'ti ti-info-circle\';\n  t.className = `toast ${type} show`;\n  setTimeout(()=>t.className=`toast ${type}`,2800);\n}\n\nfunction clearAllData() {\n  if (!confirm(\'確定清除所有新增交易、股價快取與設定？原先持股會保留。\')) return;\n  db = emptyData();\n  saveData(db);\n  renderAll();\n  showToast(\'已清除新增資料並同步雲端；原先持股已保留\', \'info\');\n  refreshPrices();\n}\n\nfunction saveSettings() {\n  const rate = parseFloat(document.getElementById(\'s-fee-rate\').value);\n  if (!db.settings) db.settings = {};\n  db.settings.feeRate = rate || 0.1425;\n  saveData(db);\n  showToast(\'設定已儲存並同步雲端\', \'success\');\n}\n\n\nfunction isMobileSidebar() {\n  return window.matchMedia(\'(max-width: 820px)\').matches;\n}\n\nfunction closeSidebarOnMobile() {\n  const app = document.getElementById(\'app-shell\');\n  if (app) app.classList.remove(\'sidebar-open\');\n}\n\nfunction toggleSidebar() {\n  const app = document.getElementById(\'app-shell\');\n  if (!app) return;\n  if (isMobileSidebar()) {\n    app.classList.toggle(\'sidebar-open\');\n    return;\n  }\n  const collapsed = app.classList.toggle(\'sidebar-collapsed\');\n  localStorage.setItem(\'investlog_sidebar_collapsed\', collapsed ? \'1\' : \'0\');\n}\n\nfunction initSidebarState() {\n  const app = document.getElementById(\'app-shell\');\n  if (!app) return;\n  if (!isMobileSidebar() && localStorage.getItem(\'investlog_sidebar_collapsed\') === \'1\') {\n    app.classList.add(\'sidebar-collapsed\');\n  }\n  window.addEventListener(\'resize\', () => {\n    if (!isMobileSidebar()) app.classList.remove(\'sidebar-open\');\n  });\n}\n\nfunction showPage(id) {\n  document.querySelectorAll(\'.page\').forEach(p=>p.classList.remove(\'active\'));\n  document.querySelectorAll(\'.nav-item\').forEach(n=>n.classList.remove(\'active\'));\n  document.getElementById(\'page-\'+id).classList.add(\'active\');\n  const map = { overview:0, add:1, pnl:2, review:3, export:4, settings:5 };\n  const items = document.querySelectorAll(\'.nav-item\');\n  if (map[id]!==undefined && items[map[id]]) items[map[id]].classList.add(\'active\');\n  closeSidebarOnMobile();\n}\n\nfunction renderAll() {\n  renderRecords();\n  renderHoldings();\n  updateMetrics();\n  updateCharts();\n  renderReview();\n  updatePnlPage();\n}\n\n// ═══════════════════════════════════════════\n// 啟動\n// ═══════════════════════════════════════════\ndocument.addEventListener(\'DOMContentLoaded\', async () => {\n  initSidebarState();\n  document.getElementById(\'f-date\').value = new Date().toISOString().split(\'T\')[0];\n  document.getElementById(\'last-update-text\').textContent = \'正在載入雲端資料...\';\n  setDot(\'updating\', \'載入雲端資料...\');\n  await loadCloudData();\n  renderAll();\n  refreshPrices();\n});\n</script>\n</body>\n</html>\n'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

NAME_MAP = {
    "0050": "元大台灣50",
    "2303": "聯電",
    "2308": "台達電",
    "2330": "台積電",
    "2454": "聯發科",
}

_cache: Dict[str, Tuple[float, Any]] = {}
CACHE_SECONDS = 45


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
STATE_FILE = os.environ.get("STATE_FILE", "investlog_state.json")
STATE_ROW_ID = 1

DEFAULT_CLOUD_STATE: Dict[str, Any] = {
    "records": [],
    "prices": {},
    "priceType": {},
    "priceSource": {},
    "settings": {"feeRate": 0.1425},
}


def normalize_state(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    out = dict(DEFAULT_CLOUD_STATE)
    out.update(data)
    out["records"] = out.get("records") if isinstance(out.get("records"), list) else []
    out["prices"] = out.get("prices") if isinstance(out.get("prices"), dict) else {}
    out["priceType"] = out.get("priceType") if isinstance(out.get("priceType"), dict) else {}
    out["priceSource"] = out.get("priceSource") if isinstance(out.get("priceSource"), dict) else {}
    out["settings"] = out.get("settings") if isinstance(out.get("settings"), dict) else {"feeRate": 0.1425}
    return out


def _connect_postgres():
    # Import inside the function so local preview can still run with JSON fallback if DATABASE_URL is not set.
    # Prefer psycopg v3 because psycopg2-binary can break on newer Render Python runtimes.
    kwargs = {}
    # Supabase / many managed Postgres providers require SSL. If the URL already has sslmode, the driver will use it.
    if "sslmode=" not in DATABASE_URL and any(host in DATABASE_URL.lower() for host in ("supabase", "neon", "railway")):
        kwargs["sslmode"] = "require"

    try:
        import psycopg  # type: ignore
        return psycopg.connect(DATABASE_URL, **kwargs)
    except ImportError:
        import psycopg2  # type: ignore
        return psycopg2.connect(DATABASE_URL, **kwargs)


def init_storage() -> Dict[str, Any]:
    if DATABASE_URL:
        try:
            with _connect_postgres() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS investlog_state (
                            id INTEGER PRIMARY KEY,
                            data JSONB NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """)
                    cur.execute("SELECT data FROM investlog_state WHERE id = %s", (STATE_ROW_ID,))
                    row = cur.fetchone()
                    if row is None:
                        cur.execute(
                            "INSERT INTO investlog_state (id, data, updated_at) VALUES (%s, %s::jsonb, NOW())",
                            (STATE_ROW_ID, json.dumps(DEFAULT_CLOUD_STATE, ensure_ascii=False)),
                        )
                    conn.commit()
            return {"ok": True, "backend": "postgres", "message": "PostgreSQL storage ready"}
        except Exception as e:
            return {"ok": False, "backend": "postgres", "message": str(e)}
    return {"ok": True, "backend": "json-file", "message": "Local JSON fallback. Set DATABASE_URL for cross-device cloud sync."}


def load_app_state() -> Dict[str, Any]:
    if DATABASE_URL:
        with _connect_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM investlog_state WHERE id = %s", (STATE_ROW_ID,))
                row = cur.fetchone()
                if not row:
                    return normalize_state(DEFAULT_CLOUD_STATE)
                return normalize_state(row[0])
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return normalize_state(json.load(f))
    except Exception:
        return normalize_state(DEFAULT_CLOUD_STATE)


def save_app_state(data: Any) -> Dict[str, Any]:
    state = normalize_state(data)
    if DATABASE_URL:
        with _connect_postgres() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO investlog_state (id, data, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (id)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                """, (STATE_ROW_ID, json.dumps(state, ensure_ascii=False)))
                conn.commit()
        return {"ok": True, "backend": "postgres", "updated_at": now_tw_text(), "data": state}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return {"ok": True, "backend": "json-file", "updated_at": now_tw_text(), "data": state}


def now_tw_text() -> str:
    return datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")


def normalize_code(code: str) -> str:
    text = str(code or "").strip().upper()
    text = re.sub(r"\.(TW|TWO)$", "", text, flags=re.I)
    text = re.sub(r"^(TSE_|OTC_)", "", text, flags=re.I)
    text = re.sub(r"\.TW$", "", text, flags=re.I)
    return text


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "").strip()
    if not text or text in {"-", "--", "null", "None"}:
        return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0


def cache_get(key: str):
    item = _cache.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > CACHE_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any):
    _cache[key] = (time.time(), value)


def http_get_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def http_get_json(url: str, timeout: int = 12) -> Any:
    key = "url:" + url
    cached = cache_get(key)
    if cached is not None:
        return cached
    text = http_get_text(url, timeout=timeout)
    data = json.loads(text)
    cache_set(key, data)
    return data


def upsert_price(out: Dict[str, Dict[str, Any]], code: str, price: float, source: str,
                 kind: str = "price", name: str = "", symbol: str = "", extra: Dict[str, Any] | None = None):
    code = normalize_code(code)
    if not code or not price or price <= 0:
        return
    item = {
        "code": code,
        "name": name or NAME_MAP.get(code, ""),
        "price": round(float(price), 4),
        "type": kind,
        "source": source,
        "symbol": symbol,
        "updated_at": now_tw_text(),
    }
    if extra:
        item.update(extra)
    out[code] = item


def fetch_yahoo_one(code: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    code = normalize_code(code)
    results: Dict[str, Dict[str, Any]] = {}
    attempts: List[str] = []
    for suffix in ("TW", "TWO"):
        symbol = f"{code}.{suffix}"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1d&interval=1m&_={int(time.time()*1000)}"
        try:
            data = http_get_json(url, timeout=5)
            result = (((data or {}).get("chart") or {}).get("result") or [None])[0]
            if not result:
                attempts.append(f"Yahoo {symbol}: 無資料")
                continue
            meta = result.get("meta") or {}
            price = to_float(meta.get("regularMarketPrice"))
            prev_close = to_float(meta.get("previousClose"))
            chart_close = 0.0
            try:
                closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                closes = [to_float(x) for x in closes if to_float(x) > 0]
                chart_close = closes[-1] if closes else 0.0
            except Exception:
                chart_close = 0.0
            final_price = price or chart_close or prev_close
            if final_price > 0:
                change = final_price - prev_close if prev_close else 0.0
                change_pct = (change / prev_close * 100) if prev_close else 0.0
                upsert_price(results, code, final_price, "Yahoo Finance 後端抓取", "live" if price else "close", NAME_MAP.get(code, ""), symbol, {
                    "previousClose": round(prev_close, 4) if prev_close else None,
                    "change": round(change, 4),
                    "changePercent": round(change_pct, 4),
                })
                return results, attempts
            attempts.append(f"Yahoo {symbol}: 沒有可用價格")
        except Exception as e:
            attempts.append(f"Yahoo {symbol}: {e}")
    return results, attempts


def fetch_twse_mis(codes: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    wanted = [normalize_code(c) for c in codes if normalize_code(c)]
    channels: List[str] = []
    for code in wanted:
        channels.append(f"tse_{code}.tw")
        channels.append(f"otc_{code}.tw")
    if not channels:
        return {}, []
    url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=" + urllib.parse.quote("|".join(channels)) + f"&json=1&delay=0&_={int(time.time()*1000)}"
    attempts: List[str] = []
    results: Dict[str, Dict[str, Any]] = {}
    try:
        data = http_get_json(url, timeout=5)
        msg = data.get("msgArray") or []
        for row in msg:
            code = normalize_code(row.get("c"))
            if code not in wanted:
                continue
            live = to_float(row.get("z"))
            prev = to_float(row.get("y"))
            open_p = to_float(row.get("o"))
            high = to_float(row.get("h"))
            low = to_float(row.get("l"))
            price = live or prev or open_p or high or low
            if price > 0:
                market = "上櫃" if str(row.get("ex", "")).lower() == "otc" else "上市"
                kind = "live" if live else "prev" if prev else "fallback"
                upsert_price(results, code, price, f"TWSE MIS {market}即時資料", kind, row.get("n") or NAME_MAP.get(code, ""), row.get("ch") or "")
        attempts.append(f"TWSE MIS: 成功 {len(results)}")
    except Exception as e:
        attempts.append(f"TWSE MIS: {e}")
    return results, attempts


def fetch_twse_close(codes: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    wanted = set(normalize_code(c) for c in codes if normalize_code(c))
    url = f"https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL?_={int(time.time()*1000)}"
    results: Dict[str, Dict[str, Any]] = {}
    attempts: List[str] = []
    try:
        rows = http_get_json(url, timeout=6)
        if not isinstance(rows, list):
            raise ValueError("回傳不是陣列")
        for row in rows:
            code = normalize_code(row.get("Code") or row.get("code") or row.get("股票代號") or row.get("證券代號"))
            if code not in wanted:
                continue
            price = to_float(row.get("ClosingPrice") or row.get("closingPrice") or row.get("收盤價") or row.get("Close") or row.get("close"))
            if price > 0:
                upsert_price(results, code, price, "TWSE 證交所 OpenAPI 最新收盤價", "close", row.get("Name") or row.get("name") or NAME_MAP.get(code, ""), code)
        attempts.append(f"TWSE OpenAPI: 成功 {len(results)}")
    except Exception as e:
        attempts.append(f"TWSE OpenAPI: {e}")
    return results, attempts


def fetch_tpex_close(codes: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    wanted = set(normalize_code(c) for c in codes if normalize_code(c))
    urls = [
        f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?_={int(time.time()*1000)}",
        f"https://www.tpex.org.tw/openapi/v1/tpex_esb_latest_statistics?_={int(time.time()*1000)}",
    ]
    results: Dict[str, Dict[str, Any]] = {}
    attempts: List[str] = []
    for url in urls:
        try:
            rows = http_get_json(url, timeout=6)
            if isinstance(rows, dict):
                rows = rows.get("data") or rows.get("Data") or []
            if not isinstance(rows, list):
                continue
            for row in rows:
                code = normalize_code(row.get("Code") or row.get("SecuritiesCompanyCode") or row.get("SecuritiesCode") or row.get("代號") or row.get("股票代號") or row.get("證券代號") or row.get("有價證券代號"))
                if code not in wanted:
                    continue
                price = to_float(row.get("ClosingPrice") or row.get("Close") or row.get("ClosePrice") or row.get("收盤") or row.get("收盤價") or row.get("最後成交價"))
                name = row.get("Name") or row.get("CompanyName") or row.get("SecuritiesCompanyName") or row.get("名稱") or row.get("股票名稱") or NAME_MAP.get(code, "")
                if price > 0:
                    upsert_price(results, code, price, "TPEx 櫃買中心 OpenAPI 最新收盤價", "close", name, code)
            attempts.append(f"TPEx OpenAPI: 成功 {len(results)}")
        except Exception as e:
            attempts.append(f"TPEx OpenAPI: {e}")
    return results, attempts


def fetch_finmind(codes: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    results: Dict[str, Dict[str, Any]] = {}
    attempts: List[str] = []
    start_date = (datetime.now(TW_TZ).date() - timedelta(days=20)).isoformat()
    for code in [normalize_code(c) for c in codes if normalize_code(c)]:
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={urllib.parse.quote(code)}&start_date={start_date}&_={int(time.time()*1000)}"
        try:
            data = http_get_json(url, timeout=6)
            rows = data.get("data") or []
            if not rows:
                attempts.append(f"FinMind {code}: 無資料")
                continue
            rows.sort(key=lambda r: str(r.get("date") or ""))
            last = rows[-1]
            price = to_float(last.get("close") or last.get("Close") or last.get("收盤價"))
            if price > 0:
                upsert_price(results, code, price, "FinMind 最新交易日收盤價", "close", NAME_MAP.get(code, ""), code)
        except Exception as e:
            attempts.append(f"FinMind {code}: {e}")
    if results:
        attempts.append(f"FinMind: 成功 {len(results)}")
    return results, attempts


def get_prices(codes: List[str]) -> Dict[str, Any]:
    codes = [normalize_code(c) for c in codes if normalize_code(c)]
    codes = list(dict.fromkeys(codes))
    prices: Dict[str, Dict[str, Any]] = {}
    attempts: List[str] = []

    # 1) TWSE MIS：一次批次查上市/上櫃，通常可拿到盤中延遲價；非交易時段會回昨收/可用價。
    pack, att = fetch_twse_mis(codes)
    attempts.extend(att)
    prices.update(pack)

    # 2) TWSE OpenAPI：上市最新收盤價備援。
    remaining = [c for c in codes if c not in prices]
    if remaining:
        pack, att = fetch_twse_close(remaining)
        attempts.extend(att)
        prices.update(pack)

    # 3) TPEx OpenAPI：上櫃最新收盤價備援。
    remaining = [c for c in codes if c not in prices]
    if remaining:
        pack, att = fetch_tpex_close(remaining)
        attempts.extend(att)
        prices.update(pack)

    # 4) Yahoo Finance：逐檔補抓，拿不到官方資料時仍有機會取得延遲報價。
    remaining = [c for c in codes if c not in prices]
    for code in remaining:
        pack, att = fetch_yahoo_one(code)
        attempts.extend(att)
        prices.update(pack)

    # 5) FinMind：最後備援。
    remaining = [c for c in codes if c not in prices]
    if remaining:
        pack, att = fetch_finmind(remaining)
        attempts.extend(att)
        prices.update(pack)

    missing = [c for c in codes if c not in prices]
    return {
        "ok": bool(prices),
        "version": APP_VERSION,
        "updated_at": now_tw_text(),
        "requested": codes,
        "prices": prices,
        "missing": missing,
        "attempts": attempts[-30:],
        "error": "沒有抓到任何股價" if not prices else "",
    }


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[server]", fmt % args)

    def _send_bytes(self, data: bytes, content_type: str = "text/html; charset=utf-8", status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj: Any, status: int = 200):
        self._send_bytes(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), "application/json; charset=utf-8", status)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/state":
            try:
                payload = self._read_json()
                saved = save_app_state(payload)
                return self._send_json(saved)
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "backend": "postgres" if DATABASE_URL else "json-file"}, 500)
        return self._send_json({"ok": False, "error": "Not found", "path": path}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/state":
            try:
                payload = self._read_json()
                saved = save_app_state(payload)
                return self._send_json(saved)
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "backend": "postgres" if DATABASE_URL else "json-file"}, 500)
        return self._send_json({"ok": False, "error": "Not found", "path": path}, 404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._send_bytes(EMBEDDED_INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")

        if path == "/health":
            storage_status = init_storage()
            return self._send_json({"ok": True, "version": APP_VERSION, "time": now_tw_text(), "storage": storage_status})

        if path == "/api/state":
            try:
                storage_status = init_storage()
                data = load_app_state()
                return self._send_json({"ok": True, "version": APP_VERSION, "updated_at": now_tw_text(), "storage": storage_status, "data": data})
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "backend": "postgres" if DATABASE_URL else "json-file"}, 500)

        if path == "/api/prices":
            raw = qs.get("codes", [""])[0]
            codes = [c.strip() for c in raw.split(",") if c.strip()]
            if not codes:
                return self._send_json({"ok": False, "error": "缺少 codes 參數，例如 /api/prices?codes=2330,0050"}, 400)
            try:
                data = get_prices(codes)
                return self._send_json(data, 200 if data.get("ok") else 502)
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "requested": codes, "updated_at": now_tw_text()}, 502)

        return self._send_json({"ok": False, "error": "Not found", "path": path}, 404)


def main():
    storage_status = init_storage()
    print(f"個人投資復盤助理啟動： http://127.0.0.1:{PORT}")
    print(f"資料儲存狀態：{storage_status}")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
