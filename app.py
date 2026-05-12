# -*- coding: utf-8 -*-
"""
個人投資復盤助理｜Render 後端股價版
- 首頁 HTML/CSS/JS 內嵌於 app.py，不需要 static 資料夾
- 前端呼叫 /api/prices，後端用 Python 連外抓取股價，避免瀏覽器 CORS 擋住
- 本機啟動：python app.py
- 本機網址：http://127.0.0.1:5000
"""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Any, Dict, List, Tuple

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
TW_TZ = timezone(timedelta(hours=8))
APP_VERSION = "investment-tracker-cloud-sync-no-gmail-v1"

EMBEDDED_INDEX_HTML = '<!DOCTYPE html>\n<html lang="zh-TW">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>個人投資復盤助理</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">\n<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>\n<style>\n*{box-sizing:border-box;margin:0;padding:0}\n:root{\n  --bg:#0f1117;--bg2:#161b27;--bg3:#1e2535;\n  --border:#2a3348;--text:#e8eaf2;--text2:#8892a4;--text3:#4a5568;\n  --accent:#3b82f6;--accent2:#1d4ed8;\n  --green:#10b981;--red:#ef4444;--yellow:#f59e0b;\n  --radius:10px;--radius-lg:14px;\n}\nbody{font-family:\'Noto Sans TC\',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px;line-height:1.6}\n.app{display:flex;height:100vh;overflow:hidden}\n.sidebar{width:220px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}\n.logo{padding:20px 18px 16px;border-bottom:1px solid var(--border)}\n.logo-text{font-family:\'Space Mono\',monospace;font-size:13px;font-weight:700;color:var(--accent);letter-spacing:.05em}\n.logo-sub{font-size:11px;color:var(--text2);margin-top:2px}\n.nav{padding:12px 8px;flex:1}\n.nav-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;color:var(--text2);font-size:13px;font-weight:500;transition:all .15s;margin-bottom:2px}\n.nav-item:hover{background:var(--bg3);color:var(--text)}\n.nav-item.active{background:rgba(59,130,246,.15);color:var(--accent)}\n.nav-item i{font-size:17px}\n.sidebar-bottom{padding:12px 8px;border-top:1px solid var(--border)}\n.main{flex:1;overflow-y:auto;background:var(--bg)}\n.page{display:none;padding:28px 32px}\n.page.active{display:block}\n.page-header{margin-bottom:24px;display:flex;align-items:flex-start;justify-content:space-between}\n.page-header-left .page-title{font-size:20px;font-weight:700;letter-spacing:-.3px}\n.page-header-left .page-sub{font-size:13px;color:var(--text2);margin-top:4px}\n.header-actions{display:flex;gap:10px;align-items:center}\n.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}\n.metric-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:18px 20px}\n.metric-label{font-size:11px;color:var(--text2);font-weight:500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}\n.metric-val{font-family:\'Space Mono\',monospace;font-size:22px;font-weight:700}\n.metric-val.pos{color:var(--green)}.metric-val.neg{color:var(--red)}\n.metric-sub{font-size:11px;color:var(--text2);margin-top:4px}\n.metric-sub.pos{color:var(--green)}.metric-sub.neg{color:var(--red)}\n.section{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);margin-bottom:20px;overflow:hidden}\n.section-head{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}\n.section-title{font-size:14px;font-weight:600}\ntable{width:100%;border-collapse:collapse}\nth{padding:10px 16px;text-align:left;font-size:11px;font-weight:500;color:var(--text2);text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--border);background:var(--bg3)}\ntd{padding:12px 16px;font-size:13px;border-bottom:1px solid var(--border)}\ntr:last-child td{border-bottom:none}\ntr:hover td{background:rgba(255,255,255,.02)}\n.badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600}\n.badge.profit{background:rgba(16,185,129,.15);color:var(--green)}\n.badge.loss{background:rgba(239,68,68,.15);color:var(--red)}\n.badge.hold{background:rgba(245,158,11,.12);color:var(--yellow)}\n.badge.near-stop{background:rgba(239,68,68,.25);color:#fca5a5}\n.badge.buy{background:rgba(59,130,246,.15);color:var(--accent)}\n.mono{font-family:\'Space Mono\',monospace;font-size:13px}\n.pos{color:var(--green)}.neg{color:var(--red)}\n.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:24px}\n.form-group{display:flex;flex-direction:column;gap:6px}\n.form-group.full{grid-column:1/-1}\nlabel{font-size:12px;font-weight:500;color:var(--text2)}\ninput,select,textarea{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border .15s;outline:none;width:100%}\ninput:focus,select:focus,textarea:focus{border-color:var(--accent)}\nselect option{background:var(--bg3)}\ntextarea{resize:vertical;min-height:70px}\n.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;font-family:inherit;transition:all .15s;white-space:nowrap}\n.btn-primary{background:var(--accent);color:#fff}\n.btn-primary:hover{background:var(--accent2)}\n.btn-ghost{background:transparent;color:var(--text2);border:1px solid var(--border)}\n.btn-ghost:hover{background:var(--bg3);color:var(--text)}\n.btn-green{background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3)}\n.btn-green:hover{background:rgba(16,185,129,.25)}\n.btn-row{display:flex;gap:10px;justify-content:flex-end;padding:0 24px 24px}\n.tab-row{display:flex;gap:2px;padding:14px 20px 0;border-bottom:1px solid var(--border)}\n.tab{padding:8px 16px;font-size:13px;font-weight:500;color:var(--text2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .15s}\n.tab.active{color:var(--accent);border-color:var(--accent)}\n.chart-wrap{padding:20px}\n.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}\n.progress-bar{height:6px;background:var(--bg3);border-radius:3px;overflow:hidden;margin-top:6px}\n.progress-fill{height:100%;border-radius:3px}\n.review-item{padding:18px 20px;border-bottom:1px solid var(--border)}\n.review-item:last-child{border-bottom:none}\n.review-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}\n.review-stock{font-weight:700;font-size:15px}\n.review-meta{font-size:12px;color:var(--text2);margin-bottom:8px}\n.review-note{font-size:13px;background:var(--bg3);border-radius:8px;padding:10px 14px;line-height:1.7;margin-bottom:8px}\n.review-note.ai{border-left:3px solid var(--accent);color:var(--text2)}\n\n.review-stock-section{overflow:hidden}\n.review-stock-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:14px 20px;border-bottom:1px solid var(--border);background:rgba(255,255,255,.015)}\n.review-summary-box{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:10px 12px;min-height:62px}\n.review-summary-label{font-size:11px;color:var(--text2);margin-bottom:4px}\n.review-summary-val{font-family:\'Space Mono\',monospace;font-size:14px;font-weight:700;color:var(--text)}\n.review-table-wrap{overflow-x:auto}\n.review-table{min-width:980px}\n.review-table .note-cell{max-width:260px;white-space:normal;color:var(--text2);line-height:1.65}\n.review-table .reason-cell{max-width:160px;white-space:normal}\n@media(max-width:820px){.review-stock-summary{grid-template-columns:repeat(2,1fr);padding:12px}.review-table{min-width:920px}}\n\n.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;margin-right:5px;margin-bottom:4px}\n.tag.tech{background:rgba(59,130,246,.15);color:var(--accent)}\n.tag.short{background:rgba(245,158,11,.12);color:var(--yellow)}\n.tag.long{background:rgba(16,185,129,.12);color:var(--green)}\n\n\n/* 原先持股管理 */\n.base-holdings-table-wrap{padding:0 20px 20px;overflow-x:auto}\n.base-holdings-table{min-width:760px}\n.base-holding-form-note{font-size:12px;color:var(--text2);line-height:1.8;padding:0 24px 16px}\n.base-holding-actions{display:flex;gap:8px;flex-wrap:wrap}\n.base-holding-actions .btn{padding:6px 10px;font-size:12px}\n@media(max-width:620px){.base-holdings-table-wrap{padding:0 14px 16px}.base-holding-form-note{padding:0 14px 14px}}\n\n\n/* 買進均價試算 */\n.avgcalc-wrap{padding:18px 20px}\n.avgcalc-intro{font-size:12px;color:var(--text2);line-height:1.8;margin-bottom:14px}\n.avgcalc-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:12px}\n.avgcalc-card{background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:12px;min-height:74px}\n.avgcalc-label{font-size:11px;color:var(--text2);margin-bottom:6px}\n.avgcalc-value{font-family:\'Space Mono\',monospace;font-size:15px;font-weight:700;color:var(--text)}\n.avgcalc-value.pos{color:var(--green)}.avgcalc-value.neg{color:var(--red)}.avgcalc-value.accent{color:var(--accent)}\n.avgcalc-note{font-size:12px;color:var(--text2);line-height:1.75;background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.16);border-radius:12px;padding:10px 12px}\n.avgcalc-empty{font-size:13px;color:var(--text2);line-height:1.8;padding:14px;background:var(--bg3);border:1px dashed var(--border);border-radius:12px;text-align:center}\n@media(max-width:1050px){.avgcalc-grid{grid-template-columns:repeat(3,1fr)}}\n@media(max-width:620px){.avgcalc-grid{grid-template-columns:repeat(2,1fr)}.avgcalc-wrap{padding:14px 14px}}\n\n\n/* 可編輯交易紀錄 */\n.edit-banner{display:none;margin:16px 24px 0;padding:12px 14px;border-radius:10px;border:1px solid rgba(59,130,246,.28);background:rgba(59,130,246,.10);color:var(--accent);font-size:13px;line-height:1.7;align-items:center;justify-content:space-between;gap:10px}\n.edit-banner.show{display:flex}\n.edit-banner button{padding:5px 10px;font-size:12px}\n.record-actions{display:flex;gap:6px;flex-wrap:wrap;align-items:center}\n.record-action-btn{border:none;border-radius:7px;padding:5px 8px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;background:var(--bg3);color:var(--text2);border:1px solid var(--border);transition:all .15s}\n.record-action-btn:hover{color:var(--text);border-color:var(--accent)}\n.record-action-btn.edit{color:var(--accent);background:rgba(59,130,246,.10);border-color:rgba(59,130,246,.25)}\n.record-action-btn.copy{color:var(--green);background:rgba(16,185,129,.10);border-color:rgba(16,185,129,.25)}\n.record-action-btn.delete{color:var(--red);background:rgba(239,68,68,.10);border-color:rgba(239,68,68,.25)}\n@media(max-width:720px){.edit-banner{margin:14px 14px 0;align-items:flex-start;flex-direction:column}.record-actions{min-width:210px}.record-action-btn{padding:6px 9px}}\n\n/* 即時股價 */\n.price-updating{animation:pulse 1.2s ease-in-out infinite}\n@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}\n.price-cell{display:flex;align-items:center;gap:6px}\n.price-dot{width:6px;height:6px;border-radius:50%;background:var(--green);flex-shrink:0}\n.price-dot.updating{background:var(--yellow);animation:pulse 1s infinite}\n.price-dot.error{background:var(--red)}\n.price-badge{font-size:10px;padding:1px 6px;border-radius:4px;background:rgba(16,185,129,.12);color:var(--green);font-weight:600}\n.price-badge.neg{background:rgba(239,68,68,.12);color:var(--red)}\n.refresh-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;background:rgba(59,130,246,.12);color:var(--accent);border:1px solid rgba(59,130,246,.25);font-family:inherit;transition:all .15s}\n.refresh-btn:hover{background:rgba(59,130,246,.2)}\n.refresh-btn.spinning i{animation:spin .8s linear infinite}\n@keyframes spin{to{transform:rotate(360deg)}}\n.price-note{font-size:11px;color:var(--text3);padding:8px 20px 14px;text-align:center}\n\n/* 匯出 */\n.export-panel{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;margin-bottom:20px}\n.export-title{font-size:14px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px}\n.export-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}\n.export-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;cursor:pointer;transition:all .15s;text-align:center}\n.export-card:hover{border-color:var(--accent);background:rgba(59,130,246,.05)}\n.export-card i{font-size:28px;display:block;margin-bottom:8px;color:var(--accent)}\n.export-card-title{font-size:13px;font-weight:600;margin-bottom:4px}\n.export-card-sub{font-size:11px;color:var(--text2)}\n\n/* toast */\n.toast{position:fixed;bottom:28px;right:28px;background:#1e2535;border:1px solid var(--border);border-radius:10px;padding:12px 18px;font-size:13px;display:flex;align-items:center;gap:10px;z-index:999;transform:translateY(80px);opacity:0;transition:all .3s}\n.toast.show{transform:translateY(0);opacity:1}\n.toast i{font-size:18px}\n.toast.success i{color:var(--green)}\n.toast.info i{color:var(--accent)}\n\n/* modal */\n.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;display:none;align-items:center;justify-content:center}\n.modal-overlay.show{display:flex}\n.modal{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:28px;width:480px;max-width:95vw}\n.modal-title{font-size:16px;font-weight:700;margin-bottom:16px}\n.modal-close{float:right;cursor:pointer;color:var(--text2);font-size:20px;line-height:1}\n\n\n/* 側邊目錄伸縮 / 手機抽屜 */\n.app{position:relative}\n.sidebar{transition:width .22s ease, transform .22s ease;z-index:30}\n.logo{position:relative}\n.logo-row{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}\n.logo-title-wrap{min-width:0}\n.sidebar-toggle,.mobile-menu-btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--border);background:var(--bg3);color:var(--text2);border-radius:8px;cursor:pointer;transition:all .15s}\n.sidebar-toggle{width:32px;height:32px;padding:0;flex-shrink:0}\n.sidebar-toggle:hover,.mobile-menu-btn:hover{color:var(--text);border-color:rgba(59,130,246,.5);background:rgba(59,130,246,.12)}\n.mobile-menu-btn{display:none;position:fixed;top:12px;left:12px;width:38px;height:38px;z-index:80;box-shadow:0 10px 24px rgba(0,0,0,.22)}\n.sidebar-backdrop{display:none}\n.nav-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.app.sidebar-collapsed .sidebar{width:68px}\n.app.sidebar-collapsed .logo{padding:14px 10px}\n.app.sidebar-collapsed .logo-row{justify-content:center}\n.app.sidebar-collapsed .logo-title-wrap{display:none}\n.app.sidebar-collapsed .sidebar-toggle i{transform:rotate(180deg)}\n.app.sidebar-collapsed .nav{padding:12px 8px}\n.app.sidebar-collapsed .nav-item{justify-content:center;gap:0;padding:12px 0}\n.app.sidebar-collapsed .nav-label{display:none}\n.app.sidebar-collapsed .nav-item i{font-size:20px}\n.app.sidebar-collapsed .sidebar-bottom{padding:12px 8px}\n\n@media (max-width: 820px){\n  .app{height:100vh;overflow:hidden}\n  .mobile-menu-btn{display:inline-flex}\n  .sidebar{position:fixed;left:0;top:0;bottom:0;width:240px;max-width:82vw;transform:translateX(-105%);box-shadow:18px 0 38px rgba(0,0,0,.38)}\n  .app.sidebar-open .sidebar{transform:translateX(0)}\n  .app.sidebar-collapsed .sidebar{width:240px;max-width:82vw}\n  .app.sidebar-collapsed .logo{padding:20px 18px 16px}\n  .app.sidebar-collapsed .logo-row{justify-content:space-between}\n  .app.sidebar-collapsed .logo-title-wrap{display:block}\n  .app.sidebar-collapsed .nav-item{justify-content:flex-start;gap:10px;padding:9px 12px}\n  .app.sidebar-collapsed .nav-label{display:inline}\n  .app.sidebar-collapsed .nav-item i{font-size:17px}\n  .app.sidebar-open .sidebar-backdrop{display:block;position:fixed;inset:0;background:rgba(0,0,0,.56);z-index:20}\n  .main{width:100%;padding-top:48px}\n  .page{padding:18px 14px 28px}\n  .page-header{gap:12px;flex-direction:column}\n  .header-actions{width:100%;flex-wrap:wrap}\n  .metric-grid{grid-template-columns:repeat(2, minmax(0,1fr));gap:10px}\n  .metric-card{padding:14px}\n  .metric-val{font-size:18px}\n  .two-col{grid-template-columns:1fr}\n  .form-grid{grid-template-columns:1fr;padding:18px}\n  .export-grid{grid-template-columns:1fr}\n  table{min-width:720px}\n  .section{overflow:auto}\n}\n@media (max-width: 520px){\n  .metric-grid{grid-template-columns:1fr}\n  .page-title{padding-left:2px}\n}\n\n\n\n/* AI 股票分析 */\n.ai-control-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:18px 20px}\n.ai-control-row input[type="date"]{max-width:180px}\n.ai-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}\n.ai-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);padding:18px 20px;overflow:hidden}\n.ai-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:12px}\n.ai-name{font-size:18px;font-weight:800;letter-spacing:-.2px}\n.ai-symbol{font-size:12px;color:var(--text2);margin-top:2px}\n.ai-price-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:8px 0 12px}\n.ai-price{font-family:\'Space Mono\',monospace;font-size:26px;font-weight:700}\n.ai-change{font-family:\'Space Mono\',monospace;font-size:14px;font-weight:700}\n.ai-kv{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}\n.ai-kv div{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:9px 10px;min-height:58px}\n.ai-kv b{display:block;font-size:11px;color:var(--text2);font-weight:500;margin-bottom:3px}\n.ai-kv span{font-family:\'Space Mono\',monospace;font-size:13px;font-weight:700}\n.ai-decision{background:linear-gradient(135deg,rgba(59,130,246,.12),rgba(16,185,129,.06));border:1px solid rgba(59,130,246,.22);border-radius:12px;padding:12px 14px;margin:12px 0}\n.ai-decision-title{font-size:12px;color:var(--text2);font-weight:700;margin-bottom:4px}\n.ai-decision-action{font-size:18px;font-weight:800;margin-bottom:4px}\n.ai-decision-action.buy{color:var(--red)}\n.ai-decision-action.sell{color:var(--green)}\n.ai-decision-action.hold{color:var(--accent)}\n.ai-text{font-size:13px;color:var(--text2);line-height:1.8;margin-top:8px}\n.ai-list{margin:8px 0 0 18px;color:var(--text2);font-size:13px;line-height:1.75}\n.ai-list li{margin-bottom:5px}\n.ai-context{background:rgba(59,130,246,.07);border:1px solid rgba(59,130,246,.16);border-radius:12px;padding:12px 14px;margin-top:12px;color:var(--text2);font-size:13px;line-height:1.85}\n.ai-context-title{font-size:12px;color:var(--accent);font-weight:800;margin-bottom:5px;display:flex;align-items:center;gap:6px}\n.ai-strategy{background:linear-gradient(135deg,rgba(239,68,68,.10),rgba(59,130,246,.08));border:1px solid rgba(239,68,68,.20);border-radius:12px;padding:12px 14px;margin:12px 0}\n.ai-strategy-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}\n.ai-strategy-box{background:rgba(15,17,23,.45);border:1px solid var(--border);border-radius:10px;padding:9px 10px;min-height:58px}\n.ai-strategy-box b{display:block;color:var(--text2);font-size:11px;margin-bottom:3px}\n.ai-strategy-box span{font-family:\'Space Mono\',monospace;font-size:13px;font-weight:700;color:var(--text)}\n.ai-assessment{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}\n.ai-assessment-card{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text2);font-size:13px;line-height:1.75}\n.ai-assessment-card b{display:block;color:var(--text);margin-bottom:4px}\n\n.ai-personal{background:linear-gradient(135deg,rgba(59,130,246,.09),rgba(16,185,129,.05));border:1px solid rgba(59,130,246,.22);border-radius:14px;padding:14px;margin:12px 0}\n.ai-personal.sell{background:linear-gradient(135deg,rgba(239,68,68,.12),rgba(245,158,11,.05));border-color:rgba(239,68,68,.28)}\n.ai-personal.buy{background:linear-gradient(135deg,rgba(16,185,129,.12),rgba(59,130,246,.06));border-color:rgba(16,185,129,.26)}\n.ai-personal.hold{background:linear-gradient(135deg,rgba(245,158,11,.10),rgba(59,130,246,.05));border-color:rgba(245,158,11,.24)}\n.ai-personal-title{font-size:12px;color:var(--accent);font-weight:800;margin-bottom:10px;display:flex;align-items:center;gap:6px}\n.ai-personal.sell .ai-personal-title{color:#fca5a5}.ai-personal.buy .ai-personal-title{color:var(--green)}.ai-personal.hold .ai-personal-title{color:var(--yellow)}\n.ai-personal-decision{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;background:rgba(15,17,23,.48);border:1px solid var(--border);border-radius:12px;padding:12px 14px;margin-bottom:10px}\n.ai-personal-decision-main{font-size:15px;font-weight:900;color:var(--text);line-height:1.4}\n.ai-personal-decision-sub{font-size:12px;color:var(--text2);line-height:1.75;margin-top:4px}\n.ai-personal-action-pill{display:inline-flex;align-items:center;justify-content:center;min-width:92px;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:900;white-space:nowrap}\n.ai-personal-action-pill.sell{color:#fca5a5;background:rgba(239,68,68,.16)}\n.ai-personal-action-pill.buy{color:var(--green);background:rgba(16,185,129,.15)}\n.ai-personal-action-pill.hold{color:var(--yellow);background:rgba(245,158,11,.13)}\n.ai-personal-snapshot{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}\n.ai-personal-mini{background:rgba(15,17,23,.38);border:1px solid var(--border);border-radius:10px;padding:9px 10px;min-height:58px}\n.ai-personal-mini b{display:block;color:var(--text2);font-size:11px;margin-bottom:3px;font-weight:700}\n.ai-personal-mini span{font-family:"Space Mono",monospace;font-size:13px;font-weight:800;color:var(--text)}\n.ai-personal-exec{width:100%;border-collapse:separate;border-spacing:0;margin-top:10px;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:rgba(15,17,23,.32)}\n.ai-personal-exec th{width:116px;background:rgba(255,255,255,.035);color:var(--text2);font-size:11px;text-transform:none;letter-spacing:0;padding:10px 12px;vertical-align:top;border-bottom:1px solid var(--border)}\n.ai-personal-exec td{font-size:13px;color:var(--text);line-height:1.75;padding:10px 12px;border-bottom:1px solid var(--border);white-space:normal}\n.ai-personal-exec tr:last-child th,.ai-personal-exec tr:last-child td{border-bottom:none}\n.ai-personal-summary{font-size:13px;color:var(--text2);line-height:1.85;margin-top:10px;background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:12px;padding:10px 12px}\n.ai-personal-warning{font-size:12px;color:#fbbf24;line-height:1.75;margin-top:8px}\n@media (max-width: 820px){.ai-personal-snapshot{grid-template-columns:repeat(2,minmax(0,1fr))}.ai-personal-decision{flex-direction:column}.ai-personal-action-pill{min-width:0}}\n@media (max-width: 520px){.ai-personal-snapshot{grid-template-columns:1fr}.ai-personal-exec th{width:96px}}\n@media (max-width: 700px){.ai-strategy-grid,.ai-assessment{grid-template-columns:1fr}}\n.ai-loading{padding:40px;text-align:center;color:var(--text2)}\n.ai-error{padding:18px 20px;color:#fca5a5;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.18);border-radius:var(--radius-lg)}\n@media (max-width: 960px){.ai-grid{grid-template-columns:1fr}.ai-kv{grid-template-columns:repeat(2,minmax(0,1fr))}}\n@media (max-width: 560px){.ai-control-row input[type="date"],.ai-control-row button{width:100%;max-width:none}.ai-kv{grid-template-columns:1fr}}\n\n\n\n/* 手機快速新增交易 */\n.quick-add-fab{display:none;position:fixed;right:18px;bottom:18px;z-index:80;align-items:center;gap:8px;border:none;border-radius:999px;padding:13px 18px;background:var(--accent);color:#fff;box-shadow:0 16px 38px rgba(59,130,246,.38);font-weight:800;cursor:pointer}\n.quick-add-fab i{font-size:19px}\n.quick-modal{width:520px;max-height:90vh;overflow-y:auto;padding:0}\n.quick-modal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:20px 22px;border-bottom:1px solid var(--border)}\n.quick-modal-title{font-size:16px;font-weight:800}\n.quick-modal-sub{font-size:12px;color:var(--text2);margin-top:4px;line-height:1.6}\n.quick-form{padding:18px 22px 22px}\n.quick-action-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}\n.quick-action-btn{border:1px solid var(--border);background:var(--bg3);color:var(--text2);border-radius:10px;padding:11px 12px;font-weight:800;cursor:pointer;text-align:center}\n.quick-action-btn.active.buy{border-color:rgba(59,130,246,.45);background:rgba(59,130,246,.16);color:var(--accent)}\n.quick-action-btn.active.sell{border-color:rgba(239,68,68,.45);background:rgba(239,68,68,.15);color:var(--red)}\n.quick-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}\n.quick-grid .full{grid-column:1/-1}\n.quick-advanced{margin-top:14px;border:1px solid var(--border);border-radius:12px;background:rgba(255,255,255,.02);overflow:hidden}\n.quick-advanced summary{cursor:pointer;padding:12px 14px;font-size:13px;font-weight:700;color:var(--text2)}\n.quick-advanced .quick-advanced-inner{padding:0 14px 14px}\n.quick-summary{margin-top:12px;padding:12px 14px;border-radius:12px;background:var(--bg3);font-size:12px;color:var(--text2);line-height:1.7}\n.quick-summary strong{color:var(--text)}\n.quick-modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}\n.quick-modal-actions .btn{justify-content:center}\n@media(max-width:760px){\n  .quick-add-fab{display:inline-flex}\n  .quick-modal{width:calc(100vw - 24px);max-height:92vh}\n  .quick-modal-head{padding:18px 18px 12px}\n  .quick-form{padding:16px 18px 18px}\n  .quick-grid{grid-template-columns:1fr}\n  .quick-modal-actions{position:sticky;bottom:-18px;background:var(--bg2);padding-top:12px}\n  .quick-modal-actions .btn{flex:1}\n}\n\n</style>\n</head>\n<body>\n\n<div class="toast" id="toast">\n  <i class="ti ti-check"></i>\n  <span id="toast-msg">已完成</span>\n</div>\n\n<div class="modal-overlay" id="import-modal">\n  <div class="modal">\n    <div class="modal-title">匯入 CSV 交易紀錄 <span class="modal-close" onclick="closeImportModal()">✕</span></div>\n    <div style="margin-bottom:14px;font-size:13px;color:var(--text2);line-height:1.8">\n      CSV 格式需包含以下欄位（第一行為標題）：<br>\n      <code style="background:var(--bg3);padding:8px 12px;border-radius:6px;display:block;margin:8px 0;font-size:12px;color:var(--accent)">日期,股票代號,股票名稱,動作,股數,價格,手續費,進場理由,備注</code>\n      動作填「買進」或「賣出」\n    </div>\n    <div class="form-group" style="margin-bottom:16px">\n      <label>選擇 CSV 檔案</label>\n      <input type="file" accept=".csv" id="csv-file-input" style="padding:8px">\n    </div>\n    <div id="import-preview" style="display:none;margin-bottom:16px">\n      <div style="font-size:12px;color:var(--text2);margin-bottom:6px">預覽（前3筆）：</div>\n      <div id="import-preview-content" style="background:var(--bg3);border-radius:8px;padding:10px 12px;font-size:12px;color:var(--text);font-family:monospace;max-height:120px;overflow-y:auto"></div>\n    </div>\n    <div style="display:flex;gap:10px;justify-content:flex-end">\n      <button class="btn btn-ghost" onclick="closeImportModal()">取消</button>\n      <button class="btn btn-primary" onclick="confirmImport()"><i class="ti ti-upload"></i> 匯入</button>\n    </div>\n  </div>\n\n</div>\n\n<button class="quick-add-fab" type="button" onclick="openQuickAdd()">\n  <i class="ti ti-plus"></i> 新增交易\n</button>\n\n<div class="modal-overlay" id="quick-trade-modal">\n  <div class="modal quick-modal">\n    <div class="quick-modal-head">\n      <div>\n        <div class="quick-modal-title">快速新增交易</div>\n        <div class="quick-modal-sub">手機版只先填必要欄位，其他細節可展開進階設定。</div>\n      </div>\n      <span class="modal-close" onclick="closeQuickAdd()">✕</span>\n    </div>\n    <div class="quick-form">\n      <div class="quick-action-row">\n        <button class="quick-action-btn active buy" id="q-action-buy" type="button" onclick="setQuickAction(\'buy\')">買進</button>\n        <button class="quick-action-btn sell" id="q-action-sell" type="button" onclick="setQuickAction(\'sell\')">賣出</button>\n      </div>\n      <div class="quick-grid">\n        <div class="form-group"><label>股票代號</label><input type="text" id="q-code" placeholder="例：2330" oninput="autoFillQuickName();calcQuickFee();updateQuickSummary()"></div>\n        <div class="form-group"><label>日期</label><input type="date" id="q-date"></div>\n        <div class="form-group"><label>股數</label><input type="number" id="q-qty" placeholder="例：10" inputmode="decimal" oninput="calcQuickFee();updateQuickSummary()"></div>\n        <div class="form-group"><label>價格（元）</label><input type="number" id="q-price" placeholder="例：800" inputmode="decimal" step="0.01" oninput="calcQuickFee();updateQuickSummary()"></div>\n      </div>\n      <details class="quick-advanced">\n        <summary>進階設定：名稱、手續費、稅、停損停利、備註</summary>\n        <div class="quick-advanced-inner">\n          <div class="quick-grid">\n            <div class="form-group"><label>股票名稱</label><input type="text" id="q-name" placeholder="可空白，自動帶入常見股票"></div>\n            <div class="form-group"><label>手續費（元）</label><input type="number" id="q-fee" placeholder="自動估算" oninput="updateQuickSummary()"></div>\n            <div class="form-group" id="q-tax-group" style="display:none"><label>證交稅（元）</label><input type="number" id="q-tax" placeholder="賣出自動估算" oninput="updateQuickSummary()"></div>\n            <div class="form-group"><label>操作方向</label><select id="q-direction"><option>短線（1週內）</option><option>波段（1-3個月）</option><option selected>中期（3-6個月）</option><option>長期（6個月以上）</option></select></div>\n            <div class="form-group full"><label>進場 / 出場理由</label><select id="q-reason"><option>快速新增</option><option>技術面突破（量增價漲）</option><option>財報優於預期</option><option>產業題材/新聞</option><option>試水溫/分批佈局</option><option>均線支撐買入</option><option>跌深反彈</option><option>停利賣出</option><option>停損賣出</option><option>其他</option></select></div>\n            <div class="form-group"><label>停損價</label><input type="number" id="q-stop" placeholder="可空白"></div>\n            <div class="form-group"><label>停利價</label><input type="number" id="q-target" placeholder="可空白"></div>\n            <div class="form-group full"><label>備註</label><textarea id="q-note" placeholder="可選填，例如：手機快速新增、券商成交價、盤後交易等"></textarea></div>\n          </div>\n        </div>\n      </details>\n      <div class="quick-summary" id="q-summary">輸入股票代號、股數與價格後，會自動估算成交金額與費用。</div>\n      <div class="quick-modal-actions">\n        <button class="btn btn-ghost" type="button" onclick="closeQuickAdd()">取消</button>\n        <button class="btn btn-primary" type="button" onclick="saveQuickRecord()"><i class="ti ti-check"></i> 儲存</button>\n      </div>\n    </div>\n  </div>\n</div>\n\n<button class="mobile-menu-btn" type="button" onclick="toggleSidebar()" aria-label="開啟目錄"><i class="ti ti-menu-2"></i></button>\n<div class="app" id="app-shell">\n<div class="sidebar-backdrop" onclick="closeSidebarOnMobile()"></div>\n<aside class="sidebar">\n  <div class="logo">\n    <div class="logo-row">\n      <div class="logo-title-wrap">\n        <div class="logo-text">INVEST LOG</div>\n        <div class="logo-sub">個人投資復盤助理</div>\n      </div>\n      <button class="sidebar-toggle" type="button" onclick="toggleSidebar()" aria-label="收合或展開目錄" title="收合/展開目錄"><i class="ti ti-layout-sidebar-left-collapse"></i></button>\n    </div>\n  </div>\n  <nav class="nav">\n    <div class="nav-item active" onclick="showPage(\'overview\')"><i class="ti ti-layout-dashboard"></i><span class="nav-label">持股總覽</span></div>\n    <div class="nav-item" onclick="showPage(\'add\')"><i class="ti ti-plus"></i><span class="nav-label">新增交易</span></div>\n    <div class="nav-item" onclick="showPage(\'pnl\')"><i class="ti ti-chart-bar"></i><span class="nav-label">損益分析</span></div>\n    <div class="nav-item" onclick="showPage(\'review\')"><i class="ti ti-notebook"></i><span class="nav-label">投資復盤</span></div>\n    <div class="nav-item" onclick="showPage(\'ai\')"><i class="ti ti-sparkles"></i><span class="nav-label">AI 股票分析</span></div>\n    <div class="nav-item" onclick="showPage(\'export\')"><i class="ti ti-database-export"></i><span class="nav-label">匯出 / 匯入</span></div>\n  </nav>\n  <div class="sidebar-bottom">\n    <div class="nav-item" onclick="showPage(\'settings\')"><i class="ti ti-settings"></i><span class="nav-label">設定</span></div>\n  </div>\n</aside>\n\n<main class="main">\n\n<!-- ═══ 持股總覽 ═══ -->\n<div class="page active" id="page-overview">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">持股總覽</div>\n      <div class="page-sub" id="last-update-text">Render 後端股價服務載入中...</div>\n    </div>\n    <div class="header-actions">\n      <button class="refresh-btn" id="refresh-btn" onclick="refreshPrices()">\n        <i class="ti ti-refresh"></i> 更新股價\n      </button>\n    </div>\n  </div>\n\n  <div class="metric-grid">\n    <div class="metric-card">\n      <div class="metric-label">總投入成本</div>\n      <div class="metric-val mono" id="m-cost">$567,490</div>\n      <div class="metric-sub">含手續費</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">目前市值</div>\n      <div class="metric-val mono" id="m-value">$601,230</div>\n      <div class="metric-sub">以現價計算</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">未實現損益</div>\n      <div class="metric-val mono pos" id="m-unrealized">+$33,740</div>\n      <div class="metric-sub pos" id="m-unrealized-pct">+5.95%</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">已實現損益</div>\n      <div class="metric-val mono" id="m-realized">$0</div>\n      <div class="metric-sub">歷史交易統計</div>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">目前持股</span>\n      <div style="display:flex;gap:8px;align-items:center">\n        <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text2)">\n          <span class="price-dot" id="dot-status"></span>\n          <span id="price-status-text">尚未更新</span>\n        </div>\n        <button class="btn btn-ghost" style="padding:5px 11px;font-size:12px" onclick="showPage(\'add\')">\n          <i class="ti ti-plus"></i> 新增\n        </button>\n      </div>\n    </div>\n    <table>\n      <thead>\n        <tr>\n          <th>股票</th>\n          <th>持有股數</th>\n          <th>平均成本</th>\n          <th>現價</th>\n          <th>漲跌</th>\n          <th>未實現損益</th>\n          <th>報酬率</th>\n          <th>狀態</th>\n        </tr>\n      </thead>\n      <tbody id="holdings-tbody"></tbody>\n    </table>\n    <div class="price-note" id="price-note">\n      ⚠ 股價會優先抓盤中即時資料；若瀏覽器擋住或休市，會改用最新收盤價。僅供參考，不構成投資建議。\n    </div>\n  </div>\n\n  <div class="two-col">\n    <div class="section">\n      <div class="section-head"><span class="section-title">持股比例</span></div>\n      <div class="chart-wrap" style="height:230px;position:relative">\n        <canvas id="pieChart" role="img" aria-label="持股比例圓餅圖">持股比例圖</canvas>\n      </div>\n    </div>\n    <div class="section">\n      <div class="section-head"><span class="section-title">個股損益比較</span></div>\n      <div class="chart-wrap" style="height:230px;position:relative">\n        <canvas id="barChart" role="img" aria-label="個股損益長條圖">個股損益比較</canvas>\n      </div>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 新增交易 ═══ -->\n<div class="page" id="page-add">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">新增交易紀錄</div>\n      <div class="page-sub">記錄每筆買賣，建立完整投資日誌</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="tab-row">\n      <div class="tab active" id="tab-buy" onclick="switchTab(\'buy\')">買進</div>\n      <div class="tab" id="tab-sell" onclick="switchTab(\'sell\')">賣出</div>\n    </div>\n    <div class="edit-banner" id="edit-banner">\n      <span id="edit-banner-text">正在編輯交易紀錄</span>\n      <button class="btn btn-ghost" type="button" onclick="cancelEditRecord()"><i class="ti ti-x"></i> 取消編輯</button>\n    </div>\n    <div class="form-grid">\n      <div class="form-group">\n        <label>股票代號</label>\n        <input type="text" placeholder="例：2330" id="f-code" oninput="autoFillName()">\n      </div>\n      <div class="form-group">\n        <label>股票名稱</label>\n        <input type="text" placeholder="例：台積電" id="f-name">\n      </div>\n      <div class="form-group">\n        <label>交易日期</label>\n        <input type="date" id="f-date">\n      </div>\n      <div class="form-group">\n        <label>股數</label>\n        <input type="number" placeholder="例：10" id="f-qty" oninput="calcFee()">\n      </div>\n      <div class="form-group">\n        <label>價格（元）</label>\n        <input type="number" placeholder="例：800" id="f-price" oninput="calcFee()">\n      </div>\n      <div class="form-group">\n        <label>手續費（元）</label>\n        <input type="number" placeholder="自動計算" id="f-fee">\n      </div>\n      <div class="form-group" id="sell-tax-group" style="display:none">\n        <label>證交稅（元）</label>\n        <input type="number" placeholder="自動計算 0.3%" id="f-tax">\n      </div>\n      <div class="form-group">\n        <label>操作方向</label>\n        <select id="f-direction">\n          <option>短線（1週內）</option>\n          <option>波段（1-3個月）</option>\n          <option selected>中期（3-6個月）</option>\n          <option>長期（6個月以上）</option>\n        </select>\n      </div>\n      <div class="form-group full">\n        <label>進場理由</label>\n        <select id="f-reason">\n          <option>技術面突破（量增價漲）</option>\n          <option>財報優於預期</option>\n          <option>產業題材/新聞</option>\n          <option>試水溫/分批佈局</option>\n          <option>均線支撐買入</option>\n          <option>跌深反彈</option>\n          <option>其他</option>\n        </select>\n      </div>\n      <div class="form-group">\n        <label>停損價</label>\n        <input type="number" placeholder="停損觸發價" id="f-stop">\n      </div>\n      <div class="form-group">\n        <label>停利價</label>\n        <input type="number" placeholder="停利目標價" id="f-target">\n      </div>\n      <div class="form-group full">\n        <label>當時判斷 / 備注</label>\n        <textarea placeholder="記錄當時技術面判斷、新聞背景、心理狀態等..." id="f-note"></textarea>\n      </div>\n    </div>\n    <div class="btn-row">\n      <button class="btn btn-ghost" id="form-clear-btn" onclick="clearForm()"><i class="ti ti-x"></i> 清除</button>\n      <button class="btn btn-primary" id="record-submit-btn" onclick="saveRecord()"><i class="ti ti-check"></i> 儲存紀錄</button>\n    </div>\n  </div>\n\n  <div class="section" id="avgcalc-section">\n    <div class="section-head">\n      <span class="section-title">買進均價即時試算</span>\n      <span style="font-size:11px;color:var(--text2)">輸入上方股票代號、價格、股數後自動計算</span>\n    </div>\n    <div class="avgcalc-wrap">\n      <div class="avgcalc-intro">\n        用來回答：「如果我以 X 元買 Y 股，均價會變多少？」系統會把你的原先持股與後續交易一起納入計算，並用目前手續費率估算買進後的新成本。\n      </div>\n      <div id="avgcalc-result" class="avgcalc-empty">請先在上方輸入股票代號、買進價格與股數。</div>\n    </div>\n  </div>\n\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">交易紀錄</span>\n      <button class="btn btn-ghost" style="padding:5px 11px;font-size:12px" onclick="exportCSV(\'records\')">\n        <i class="ti ti-download"></i> 匯出此表\n      </button>\n    </div>\n    <table>\n      <thead>\n        <tr><th>日期</th><th>股票</th><th>動作</th><th>股數</th><th>價格</th><th>進場理由</th><th>備注</th><th>操作</th></tr>\n      </thead>\n      <tbody id="records-tbody"></tbody>\n    </table>\n  </div>\n</div>\n\n<!-- ═══ 損益分析 ═══ -->\n<div class="page" id="page-pnl">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">損益分析</div>\n      <div class="page-sub">賣出後會自動計算已實現損益、勝率與每筆賣出結果</div>\n    </div>\n    <div class="header-actions">\n      <button class="btn btn-ghost" onclick="exportCSV(\'pnl\')"><i class="ti ti-download"></i> 匯出損益表</button>\n    </div>\n  </div>\n  <div class="metric-grid">\n    <div class="metric-card">\n      <div class="metric-label">交易勝率</div>\n      <div class="metric-val mono" id="p-winrate">—</div>\n      <div class="metric-sub" id="p-winrate-sub">尚無已實現交易</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">平均持有天數</div>\n      <div class="metric-val mono" id="p-avgdays">—</div>\n      <div class="metric-sub" id="p-avgdays-sub">原先持股無買進日期</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">最大單筆獲利</div>\n      <div class="metric-val mono pos" id="p-maxwin">—</div>\n      <div class="metric-sub" id="p-maxwin-sub">—</div>\n    </div>\n    <div class="metric-card">\n      <div class="metric-label">最大單筆虧損</div>\n      <div class="metric-val mono neg" id="p-maxloss">—</div>\n      <div class="metric-sub" id="p-maxloss-sub">—</div>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">已實現交易明細</span>\n      <span style="font-size:11px;color:var(--text2)">依賣出紀錄計算，原先持股也會列入成本</span>\n    </div>\n    <div class="table-wrap">\n      <table>\n        <thead>\n          <tr>\n            <th>賣出日期</th>\n            <th>股票</th>\n            <th>賣出股數</th>\n            <th>成本均價</th>\n            <th>賣出價</th>\n            <th>已實現損益</th>\n            <th>報酬率</th>\n            <th>持有天數</th>\n            <th>來源 / 理由</th>\n          </tr>\n        </thead>\n        <tbody id="realized-tbody"></tbody>\n      </table>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head"><span class="section-title">進場理由勝率分析</span></div>\n    <div style="padding:16px 20px" id="reason-pnl">\n      <div style="color:var(--text2);font-size:13px">賣出後，這裡會依買進來源 / 理由統計勝率與損益。</div>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 投資復盤 ═══ -->\n<div class="page" id="page-review">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">投資復盤</div>\n      <div class="page-sub">依股票分類檢視每支股票的交易復盤</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="section-head"><span class="section-title">依股票分類的交易復盤</span></div>\n    <div id="review-list">\n      <div style="padding:40px;text-align:center;color:var(--text2)">\n        <i class="ti ti-notebook" style="font-size:36px;display:block;margin-bottom:12px;color:var(--text3)"></i>\n        尚無交易紀錄，請先在「新增交易」頁面新增紀錄。\n      </div>\n    </div>\n  </div>\n</div>\n\n\n<!-- ═══ AI 股票分析 ═══ -->\n<div class="page" id="page-ai">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">AI 股票分析</div>\n      <div class="page-sub">自動讀取目前持股；新增其他股票後，AI 分析會自動加入該股票</div>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">查詢設定</span>\n      <span style="font-size:11px;color:var(--text2)">資料由 Render 後端抓取，避免前端 CORS 問題</span>\n    </div>\n    <div class="ai-control-row">\n      <div style="display:flex;flex-direction:column;gap:6px">\n        <label for="ai-date">查詢日期</label>\n        <input type="date" id="ai-date">\n      </div>\n      <button class="btn btn-primary" onclick="loadAiAnalysis(false)"><i class="ti ti-chart-line"></i> 查看分析</button>\n      <button class="btn btn-ghost" onclick="loadAiAnalysis(true)"><i class="ti ti-refresh"></i> 重新抓取</button>\n    </div>\n  </div>\n\n  <div id="ai-analysis-content">\n    <div class="section"><div class="ai-loading">切換到此頁後會自動載入股票分析。</div></div>\n  </div>\n</div>\n\n<!-- ═══ 匯出 / 匯入 ═══ -->\n<div class="page" id="page-export">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">匯出 / 匯入</div>\n      <div class="page-sub">備份資料或匯入歷史紀錄</div>\n    </div>\n  </div>\n\n  <div class="export-panel">\n    <div class="export-title"><i class="ti ti-download" style="font-size:18px;color:var(--accent)"></i> 匯出 CSV</div>\n    <div class="export-grid">\n      <div class="export-card" onclick="exportCSV(\'all\')">\n        <i class="ti ti-file-spreadsheet"></i>\n        <div class="export-card-title">完整交易紀錄</div>\n        <div class="export-card-sub">所有買賣紀錄，含備注</div>\n      </div>\n      <div class="export-card" onclick="exportCSV(\'holdings\')">\n        <i class="ti ti-chart-pie"></i>\n        <div class="export-card-title">目前持股清單</div>\n        <div class="export-card-sub">現有持股與成本</div>\n      </div>\n      <div class="export-card" onclick="exportCSV(\'pnl\')">\n        <i class="ti ti-report-money"></i>\n        <div class="export-card-title">損益分析表</div>\n        <div class="export-card-sub">已實現損益統計</div>\n      </div>\n    </div>\n  </div>\n\n  <div class="export-panel">\n    <div class="export-title"><i class="ti ti-upload" style="font-size:18px;color:var(--green)"></i> 匯入 CSV</div>\n    <div style="font-size:13px;color:var(--text2);margin-bottom:16px;line-height:1.8">\n      支援從 Excel 或其他工具匯出的 CSV 格式，系統自動解析並加入交易紀錄。<br>\n      <strong style="color:var(--text)">格式：</strong>\n      <code style="background:var(--bg2);padding:4px 8px;border-radius:5px;font-size:12px;color:var(--accent)">\n        日期, 股票代號, 股票名稱, 動作, 股數, 價格, 手續費, 進場理由, 備注\n      </code>\n    </div>\n    <div style="display:flex;gap:12px;align-items:center">\n      <button class="btn btn-green" onclick="openImportModal()"><i class="ti ti-upload"></i> 選擇 CSV 檔案</button>\n      <button class="btn btn-ghost" onclick="downloadTemplate()"><i class="ti ti-template"></i> 下載範本</button>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">資料管理</span>\n    </div>\n    <div style="padding:20px;display:flex;gap:12px;align-items:center">\n      <button class="btn btn-ghost" onclick="exportCSV(\'backup\')">\n        <i class="ti ti-database-export"></i> 完整備份（JSON）\n      </button>\n      <button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" onclick="clearAllData()">\n        <i class="ti ti-trash"></i> 清除所有資料\n      </button>\n    </div>\n  </div>\n</div>\n\n<!-- ═══ 設定 ═══ -->\n<div class="page" id="page-settings">\n  <div class="page-header">\n    <div class="page-header-left">\n      <div class="page-title">設定</div>\n      <div class="page-sub">個人化你的投資助理</div>\n    </div>\n  </div>\n  <div class="section">\n    <div class="section-head"><span class="section-title">交易參數</span></div>\n    <div class="form-grid">\n      <div class="form-group">\n        <label>手續費率（%）</label>\n        <input type="number" value="0.1425" step="0.001" id="s-fee-rate">\n      </div>\n      <div class="form-group">\n        <label>總資金（元）</label>\n        <input type="number" placeholder="600000" id="s-capital">\n      </div>\n      <div class="form-group full">\n        <label>停損警示門檻</label>\n        <select id="s-stop-threshold">\n          <option>距停損價 5%</option>\n          <option selected>距停損價 3%</option>\n          <option>距停損價 1%</option>\n        </select>\n      </div>\n    </div>\n    <div class="btn-row">\n      <button class="btn btn-primary" onclick="saveSettings()"><i class="ti ti-check"></i> 儲存設定</button>\n    </div>\n  </div>\n\n  <div class="section">\n    <div class="section-head">\n      <span class="section-title">原先持股管理</span>\n      <span style="font-size:11px;color:var(--text2)">會同步到雲端，清除新增資料時不會刪除</span>\n    </div>\n    <div class="form-grid">\n      <div class="form-group">\n        <label>股票代號</label>\n        <input type="text" id="base-code" placeholder="例如：2330" oninput="autoFillBaseName(); calcBaseTotalPreview();">\n      </div>\n      <div class="form-group">\n        <label>股票名稱</label>\n        <input type="text" id="base-name" placeholder="例如：台積電">\n      </div>\n      <div class="form-group">\n        <label>股數</label>\n        <input type="number" id="base-qty" step="1" min="0" placeholder="例如：60" oninput="calcBaseTotalPreview()">\n      </div>\n      <div class="form-group">\n        <label>成本均價</label>\n        <input type="number" id="base-avg" step="0.01" min="0" placeholder="例如：1956.02" oninput="calcBaseTotalPreview()">\n      </div>\n      <div class="form-group">\n        <label>投資成本</label>\n        <input type="number" id="base-total" step="1" min="0" placeholder="可自動帶入，也可手動修正">\n      </div>\n      <div class="form-group">\n        <label>操作</label>\n        <div style="display:flex;gap:8px;flex-wrap:wrap">\n          <button class="btn btn-primary" type="button" onclick="saveBaseHolding()"><i class="ti ti-device-floppy"></i> 新增 / 更新</button>\n          <button class="btn btn-ghost" type="button" onclick="clearBaseHoldingForm()"><i class="ti ti-x"></i> 清空</button>\n        </div>\n      </div>\n    </div>\n    <div class="base-holding-form-note">\n      原先持股是你的初始部位，會參與持股總覽、損益分析、投資復盤與 AI 股票分析。之後要新增或修改原先持股，直接在這裡編輯，不需要再改程式碼。\n    </div>\n    <div class="base-holdings-table-wrap">\n      <table class="base-holdings-table">\n        <thead>\n          <tr><th>股票</th><th>股數</th><th>成本均價</th><th>投資成本</th><th>操作</th></tr>\n        </thead>\n        <tbody id="base-holdings-tbody"></tbody>\n      </table>\n    </div>\n  </div>\n</div>\n\n</main>\n</div>\n\n<script>\n// ═══════════════════════════════════════════\n// 資料層 — 雲端同步（Render 後端 + PostgreSQL / Supabase）\n// ═══════════════════════════════════════════\nconst STORE_KEY = \'investlog_v3_editable_base_holdings\';\nconst OLD_STORE_KEY = \'investlog_v2_base_holdings\';\nconst LEGACY_STORE_KEY = \'investlog_v1\';\n\nconst DEFAULT_BASE_HOLDINGS = [\n  { code:\'0050\', name:\'元大台灣50\', qty:307, avgCost:76.95, totalCost:23624 },\n  { code:\'2303\', name:\'聯電\', qty:150, avgCost:72.37, totalCost:10855 },\n  { code:\'2308\', name:\'台達電\', qty:35, avgCost:2008.66, totalCost:70303 },\n  { code:\'2330\', name:\'台積電\', qty:60, avgCost:1956.02, totalCost:117361 },\n  { code:\'2454\', name:\'聯發科\', qty:5, avgCost:3414.8, totalCost:17074 }\n];\n\nfunction normalizeBaseHoldings(list) {\n  if (!Array.isArray(list)) return [];\n  const seen = new Set();\n  return list.map(item => {\n    const code = normalizeStockCode(item?.code || \'\');\n    const qty = Number(item?.qty) || 0;\n    const avgCost = Number(item?.avgCost) || 0;\n    const totalCost = Number(item?.totalCost) || qty * avgCost;\n    return {\n      code,\n      name: String(item?.name || code || \'\').trim(),\n      qty,\n      avgCost: qty > 0 ? totalCost / qty : avgCost,\n      totalCost\n    };\n  }).filter(item => {\n    if (!item.code || item.qty <= 0) return false;\n    if (seen.has(item.code)) return false;\n    seen.add(item.code);\n    return true;\n  });\n}\n\nfunction emptyData() {\n  return { records: [], prices: {}, priceType: {}, priceSource: {}, baseHoldings: normalizeBaseHoldings(DEFAULT_BASE_HOLDINGS), settings: { feeRate: 0.1425 } };\n}\n\nfunction getBaseHoldings() {\n  if (db && Array.isArray(db.baseHoldings)) return normalizeBaseHoldings(db.baseHoldings);\n  return normalizeBaseHoldings(DEFAULT_BASE_HOLDINGS);\n}\n\nfunction isOldSampleRecord(r) {\n  const key = `${r?.date}|${r?.code}|${r?.action}|${r?.qty}|${r?.price}`;\n  return [\n    \'2025-04-01|2330|buy|10|800\',\n    \'2025-04-05|2303|buy|100|48\',\n    \'2025-04-10|5190|buy|1|5190\',\n    \'2025-04-20|2454|buy|5|1200\'\n  ].includes(key);\n}\n\nfunction normalizeData(d) {\n  const base = emptyData();\n  const incomingBase = Array.isArray(d?.baseHoldings) ? d.baseHoldings : base.baseHoldings;\n  return Object.assign(base, d || {}, {\n    records: Array.isArray(d?.records) ? d.records : [],\n    prices: d?.prices || {},\n    priceType: d?.priceType || {},\n    priceSource: d?.priceSource || {},\n    baseHoldings: normalizeBaseHoldings(incomingBase),\n    settings: d?.settings || { feeRate: 0.1425 }\n  });\n}\n\nfunction loadLocalBackup() {\n  try {\n    const saved = JSON.parse(localStorage.getItem(STORE_KEY));\n    if (saved && Array.isArray(saved.records)) return normalizeData(saved);\n  } catch(e) {}\n  try {\n    const old = JSON.parse(localStorage.getItem(OLD_STORE_KEY));\n    if (old && Array.isArray(old.records)) return normalizeData(old);\n  } catch(e) {}\n  try {\n    const legacy = JSON.parse(localStorage.getItem(LEGACY_STORE_KEY));\n    if (legacy && Array.isArray(legacy.records)) {\n      const migrated = emptyData();\n      migrated.records = legacy.records.filter(r => !isOldSampleRecord(r));\n      migrated.prices = legacy.prices || {};\n      migrated.priceType = legacy.priceType || {};\n      migrated.priceSource = legacy.priceSource || {};\n      migrated.settings = legacy.settings || { feeRate: 0.1425 };\n      return normalizeData(migrated);\n    }\n  } catch(e) {}\n  return emptyData();\n}\n\nlet db = emptyData();\nlet cloudReady = false;\nlet saveTimer = null;\n\nasync function loadCloudData() {\n  try {\n    const res = await fetch(\'/api/state\', { cache: \'no-store\' });\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    const payload = await res.json();\n    db = normalizeData(payload.data);\n    cloudReady = true;\n    localStorage.setItem(STORE_KEY, JSON.stringify(db));\n    setDot(\'ok\', \'雲端資料已載入\');\n    return true;\n  } catch (err) {\n    console.warn(\'cloud load failed:\', err);\n    db = loadLocalBackup();\n    cloudReady = false;\n    setDot(\'error\', \'雲端載入失敗，暫用本機備份\');\n    showToast(\'雲端資料載入失敗，請確認 Render 後端與 DATABASE_URL\', \'info\');\n    return false;\n  }\n}\n\nfunction saveData(d) {\n  const normalized = normalizeData(d);\n  localStorage.setItem(STORE_KEY, JSON.stringify(normalized));\n  db = normalized;\n  queueCloudSave(normalized);\n}\n\nfunction queueCloudSave(d) {\n  clearTimeout(saveTimer);\n  saveTimer = setTimeout(() => syncCloudData(d), 450);\n}\n\nasync function syncCloudData(d) {\n  try {\n    const res = await fetch(\'/api/state\', {\n      method: \'PUT\',\n      headers: { \'Content-Type\': \'application/json\' },\n      body: JSON.stringify(d)\n    });\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    cloudReady = true;\n    const text = document.getElementById(\'last-update-text\');\n    if (text) text.textContent = `雲端已同步 · ${new Date().toLocaleString(\'zh-TW\')} · 台股`;\n  } catch (err) {\n    cloudReady = false;\n    console.warn(\'cloud save failed:\', err);\n    const text = document.getElementById(\'last-update-text\');\n    if (text) text.textContent = `雲端同步失敗，已暫存本機 · ${new Date().toLocaleString(\'zh-TW\')}`;\n  }\n}\n\n// ═══════════════════════════════════════════\n// 股價更新 — Render 後端代理版\n// 這版不再讓瀏覽器直接連外部股價 API，而是呼叫同網域 /api/prices。\n// 部署到 Render 後：前端 → Render app.py → 外部股價來源 → 回傳前端。\n// ═══════════════════════════════════════════\nlet priceCharts = {};\n\nfunction isTradingHours() {\n  const now = new Date();\n  const day = now.getDay();\n  if (day === 0 || day === 6) return false;\n  const h = now.getHours(), m = now.getMinutes();\n  const mins = h * 60 + m;\n  return mins >= 9 * 60 && mins <= 13 * 60 + 30;\n}\n\nfunction normalizeStockCode(code) {\n  return String(code || \'\')\n    .trim()\n    .toUpperCase()\n    .replace(/\\.TW$|\\.TWO$/i, \'\')\n    .replace(/^TSE_|^OTC_/i, \'\')\n    .replace(/\\.tw$/i, \'\');\n}\n\nasync function refreshPrices() {\n  const holdings = calcHoldings();\n  const codes = [...new Set(holdings.map(h => normalizeStockCode(h.code)))].filter(Boolean);\n  if (!codes.length) { showToast(\'尚無持股，請先新增交易紀錄\', \'info\'); return; }\n\n  const btn = document.getElementById(\'refresh-btn\');\n  if (btn) {\n    btn.classList.add(\'spinning\');\n    btn.innerHTML = \'<i class="ti ti-refresh"></i> 更新中...\';\n  }\n  setDot(\'updating\', \'Render 後端抓取中...\');\n\n  try {\n    const res = await fetch(`/api/prices?codes=${encodeURIComponent(codes.join(\',\'))}&_=${Date.now()}`, { cache: \'no-store\' });\n    const payload = await res.json();\n    if (!res.ok || !payload.ok) {\n      throw new Error(payload.error || \'後端股價 API 回傳失敗\');\n    }\n\n    const priceMap = payload.prices || {};\n    const successCodes = Object.keys(priceMap).filter(code => priceMap[code] && Number(priceMap[code].price) > 0);\n\n    if (!successCodes.length) {\n      throw new Error((payload.attempts || []).join(\'；\') || \'沒有取得任何股價\');\n    }\n\n    for (const code of successCodes) {\n      const q = priceMap[code];\n      db.prices[code] = Number(q.price);\n      db.priceType = db.priceType || {};\n      db.priceSource = db.priceSource || {};\n      db.priceType[code] = q.type || \'price\';\n      db.priceSource[code] = q.source || \'Render 後端\';\n\n      if (q.name) {\n        db.records = db.records.map(r => {\n          const rc = normalizeStockCode(r.code);\n          if (rc === code && (!r.name || r.name === r.code)) return { ...r, name: q.name };\n          return r;\n        });\n      }\n    }\n\n    saveData(db);\n    renderAll();\n\n    const now = new Date();\n    const timeStr = now.toLocaleTimeString(\'zh-TW\', {hour:\'2-digit\', minute:\'2-digit\'});\n    const trading = isTradingHours();\n    const allLive = successCodes.every(c => (priceMap[c].type || \'\').includes(\'live\'));\n    const note = allLive && trading\n      ? `盤中即時報價 · ${timeStr} 更新`\n      : `最新可用價格／收盤價 · ${timeStr} 更新`;\n    document.getElementById(\'last-update-text\').textContent = note;\n\n    const failCount = codes.length - successCodes.length;\n    setDot(\'ok\', failCount ? `成功 ${successCodes.length}/${codes.length}，部分使用快取` : `成功 ${successCodes.length}/${codes.length}`);\n    showToast(`股價更新成功（${successCodes.length}/${codes.length} 支）`, \'success\');\n    console.log(\'[Render 後端股價更新成功]\', payload);\n  } catch (e) {\n    setDot(\'error\', \'抓取失敗，使用快取\');\n    showToast(\'無法抓取股價；請確認 Render 網址已正常部署，或稍後重試。\', \'info\');\n    console.error(\'[Render 後端股價抓取失敗]\', e);\n  }\n\n  if (btn) {\n    btn.classList.remove(\'spinning\');\n    btn.innerHTML = \'<i class="ti ti-refresh"></i> 更新股價\';\n  }\n}\n\nfunction setDot(state, text) {\n  const dot = document.getElementById(\'dot-status\');\n  const txt = document.getElementById(\'price-status-text\');\n  if (!dot || !txt) return;\n  dot.className = \'price-dot\';\n  if (state === \'ok\') { dot.style.background = \'var(--green)\'; }\n  else if (state === \'updating\') { dot.className = \'price-dot updating\'; dot.style.background = \'\'; }\n  else if (state === \'error\') { dot.style.background = \'var(--red)\'; }\n  txt.textContent = text;\n}\n\n// ═══════════════════════════════════════════\n// 計算持股\n// ═══════════════════════════════════════════\nfunction calcHoldings() {\n  const holdings = {};\n\n  // 先放入固定原先持股，確保「清除所有資料」也不會刪掉這些部位。\n  for (const b of getBaseHoldings()) {\n    const k = normalizeStockCode(b.code);\n    holdings[k] = {\n      code: k,\n      name: b.name,\n      qty: Number(b.qty) || 0,\n      totalCost: Number(b.totalCost) || (Number(b.qty) || 0) * (Number(b.avgCost) || 0),\n      stop: 0,\n      target: 0,\n      isBase: true\n    };\n  }\n\n  // 再疊加使用者後續新增的買賣紀錄。\n  for (const r of db.records) {\n    const k = normalizeStockCode(r.code);\n    if (!k) continue;\n    if (!holdings[k]) holdings[k] = { code:k, name:r.name, qty:0, totalCost:0, stop:r.stop, target:r.target, isBase:false };\n    if (r.name && (!holdings[k].name || holdings[k].name === k)) holdings[k].name = r.name;\n    if (r.stop) holdings[k].stop = r.stop;\n    if (r.target) holdings[k].target = r.target;\n\n    const qty = parseFloat(r.qty) || 0;\n    const price = parseFloat(r.price) || 0;\n    const fee = parseFloat(r.fee) || 0;\n\n    if (r.action === \'buy\') {\n      holdings[k].qty += qty;\n      holdings[k].totalCost += qty * price + fee;\n    } else {\n      const beforeQty = holdings[k].qty;\n      const avgCost = beforeQty > 0 ? holdings[k].totalCost / beforeQty : 0;\n      const matchedQty = Math.min(qty, Math.max(beforeQty, 0));\n      holdings[k].qty -= qty;\n      holdings[k].totalCost -= avgCost * matchedQty;\n      if (holdings[k].qty <= 0) {\n        holdings[k].qty = 0;\n        holdings[k].totalCost = 0;\n      }\n    }\n  }\n  return Object.values(holdings).filter(h => h.qty > 0);\n}\nfunction getStatus(pnlPct, price, stop) {\n  if (stop && price <= stop * 1.01) return [\'near-stop\',\'接近停損\'];\n  if (pnlPct >= 10) return [\'profit\',\'獲利中\'];\n  if (pnlPct >= 3) return [\'profit\',\'穩定持有\'];\n  if (pnlPct >= -2) return [\'hold\',\'成本附近\'];\n  if (pnlPct >= -8) return [\'hold\',\'小虧觀察\'];\n  return [\'near-stop\',\'停損觀察\'];\n}\n\nfunction renderHoldings() {\n  const holdings = calcHoldings();\n  const tbody = document.getElementById(\'holdings-tbody\');\n  tbody.innerHTML = \'\';\n  for (const h of holdings) {\n    const avgCost = h.totalCost / h.qty;\n    const price = db.prices[h.code] || avgCost;\n    const pnl = (price - avgCost) * h.qty;\n    const pnlPct = ((price - avgCost) / avgCost * 100);\n    const [sc, label] = getStatus(pnlPct, price, h.stop);\n    // price change vs yesterday (simulate from cache delta)\n    const chg = pnlPct.toFixed(2);\n    const pt = db.priceType?.[h.code];\n    const labelText = pt === \'live\' ? \'盤中\' : pt === \'prev\' ? \'昨收\' : pt === \'close\' ? \'收盤\' : pt === \'fallback\' ? \'參考\' : \'\';\n    const labelColor = pt === \'live\' ? \'var(--green)\' : \'var(--text2)\';\n    const priceLabel = db.prices[h.code] && labelText\n      ? `<span style="font-size:10px;color:${labelColor};margin-left:4px">${labelText}</span>` : \'\';\n    tbody.innerHTML += `<tr>\n      <td><strong>${h.code}</strong><br><span style="color:var(--text2);font-size:11px">${h.name}</span>${h.isBase ? \'<br><span style="color:var(--accent);font-size:10px">原先持股</span>\' : \'\'}</td>\n      <td class="mono">${h.qty}</td>\n      <td class="mono">${Math.round(avgCost).toLocaleString()}</td>\n      <td>\n        <div class="price-cell">\n          <span class="mono">${Math.round(price).toLocaleString()}</span>\n          ${priceLabel}\n          ${db.prices[h.code] ? \'<span class="price-dot" style="background:var(--green)"></span>\' : \'\'}\n        </div>\n      </td>\n      <td><span class="price-badge ${pnlPct<0?\'neg\':\'\'}">${pnlPct>=0?\'+\':\'\'}${chg}%</span></td>\n      <td class="mono ${pnl>=0?\'pos\':\'neg\'}">${pnl>=0?\'+\':\'\'}${Math.round(pnl).toLocaleString()}</td>\n      <td class="mono ${pnlPct>=0?\'pos\':\'neg\'}">${pnlPct>=0?\'+\':\'\'}${pnlPct.toFixed(2)}%</td>\n      <td><span class="badge ${sc}">${label}</span></td>\n    </tr>`;\n  }\n  if (!holdings.length) {\n    tbody.innerHTML = \'<tr><td colspan="8" style="text-align:center;color:var(--text2);padding:32px">尚無持股</td></tr>\';\n  }\n}\n\nfunction calcRealizedPnl() {\n  const positions = {};\n  for (const b of getBaseHoldings()) {\n    const k = normalizeStockCode(b.code);\n    positions[k] = {\n      qty: Number(b.qty) || 0,\n      cost: Number(b.totalCost) || (Number(b.qty) || 0) * (Number(b.avgCost) || 0)\n    };\n  }\n  let realized = 0;\n  const sorted = [...db.records].sort((a, b) => {\n    const dateCompare = String(a.date || \'\').localeCompare(String(b.date || \'\'));\n    if (dateCompare !== 0) return dateCompare;\n    return (a.ts || a.id || 0) - (b.ts || b.id || 0);\n  });\n\n  for (const r of sorted) {\n    const code = normalizeStockCode(r.code);\n    if (!code) continue;\n    if (!positions[code]) positions[code] = { qty: 0, cost: 0 };\n\n    const qty = parseFloat(r.qty) || 0;\n    const price = parseFloat(r.price) || 0;\n    const fee = parseFloat(r.fee) || 0;\n    const tax = parseFloat(r.tax) || 0;\n    const amount = qty * price;\n\n    if (r.action === \'buy\') {\n      positions[code].qty += qty;\n      positions[code].cost += amount + fee;\n    } else if (r.action === \'sell\') {\n      const pos = positions[code];\n      const avgCost = pos.qty > 0 ? pos.cost / pos.qty : 0;\n      const matchedQty = Math.min(qty, Math.max(pos.qty, 0));\n      const costRemoved = avgCost * matchedQty;\n      const proceeds = amount - fee - tax;\n      realized += proceeds - costRemoved;\n\n      pos.qty -= qty;\n      pos.cost -= costRemoved;\n      if (pos.qty <= 0) {\n        pos.qty = 0;\n        pos.cost = 0;\n      }\n    }\n  }\n\n  return realized;\n}\n\nfunction updateMetrics() {\n  const holdings = calcHoldings();\n  let totalCost = 0, totalValue = 0;\n  for (const h of holdings) {\n    totalCost += h.totalCost;\n    totalValue += (db.prices[h.code] || h.totalCost / h.qty) * h.qty;\n  }\n  const unreal = totalValue - totalCost;\n  const unrealPct = totalCost ? (unreal / totalCost * 100) : 0;\n  document.getElementById(\'m-cost\').textContent = \'$\' + Math.round(totalCost).toLocaleString();\n  document.getElementById(\'m-value\').textContent = \'$\' + Math.round(totalValue).toLocaleString();\n  const uEl = document.getElementById(\'m-unrealized\');\n  uEl.textContent = (unreal>=0?\'+\':\'\') + \'$\' + Math.round(unreal).toLocaleString();\n  uEl.className = \'metric-val mono \' + (unreal>=0?\'pos\':\'neg\');\n  document.getElementById(\'m-unrealized-pct\').textContent = (unrealPct>=0?\'+\':\'\') + unrealPct.toFixed(2) + \'%\';\n  document.getElementById(\'m-unrealized-pct\').className = \'metric-sub \' + (unrealPct>=0?\'pos\':\'neg\');\n\n  const realized = calcRealizedPnl();\n  const rEl = document.getElementById(\'m-realized\');\n  if (rEl) {\n    rEl.textContent = (realized >= 0 ? \'+\' : \'-\') + \'$\' + Math.abs(Math.round(realized)).toLocaleString();\n    if (Math.round(realized) === 0) rEl.textContent = \'$0\';\n    rEl.className = \'metric-val mono \' + (realized > 0 ? \'pos\' : realized < 0 ? \'neg\' : \'\');\n  }\n}\n\n// ═══════════════════════════════════════════\n// 圖表\n// ═══════════════════════════════════════════\nfunction updateCharts() {\n  const holdings = calcHoldings();\n  const labels = holdings.map(h => h.name || h.code);\n  const pnlData = holdings.map(h => {\n    const avgCost = h.totalCost / h.qty;\n    const price = db.prices[h.code] || avgCost;\n    return Math.round((price - avgCost) * h.qty);\n  });\n  const weights = holdings.map(h => (db.prices[h.code] || h.totalCost/h.qty) * h.qty);\n\n  const colors = [\'#3b82f6\',\'#10b981\',\'#f59e0b\',\'#ef4444\',\'#a855f7\',\'#ec4899\'];\n\n  if (priceCharts.pie) { priceCharts.pie.destroy(); }\n  const pieCtx = document.getElementById(\'pieChart\');\n  if (pieCtx && weights.some(w=>w>0)) {\n    priceCharts.pie = new Chart(pieCtx, {\n      type: \'doughnut\',\n      data: { labels, datasets: [{ data: weights, backgroundColor: colors.slice(0, labels.length), borderWidth: 0, hoverOffset: 4 }] },\n      options: { responsive:true, maintainAspectRatio:false, cutout:\'68%\',\n        plugins: { legend:{display:false}, tooltip:{callbacks:{label:ctx=>`${ctx.label}: ${(ctx.parsed/weights.reduce((a,b)=>a+b,0)*100).toFixed(1)}%`}} } }\n    });\n  }\n\n  if (priceCharts.bar) { priceCharts.bar.destroy(); }\n  const barCtx = document.getElementById(\'barChart\');\n  if (barCtx && pnlData.length) {\n    priceCharts.bar = new Chart(barCtx, {\n      type: \'bar\',\n      data: { labels, datasets: [{ label:\'未實現損益\', data:pnlData, backgroundColor: pnlData.map(v=>v>=0?\'#10b981\':\'#ef4444\'), borderRadius:5 }] },\n      options: { responsive:true, maintainAspectRatio:false,\n        plugins: { legend:{display:false} },\n        scales: { y:{ grid:{color:\'rgba(255,255,255,0.05)\'}, ticks:{color:\'#8892a4\',font:{size:11}} }, x:{ grid:{display:false}, ticks:{color:\'#8892a4\',font:{size:11}} } } }\n    });\n  }\n}\n\n// ═══════════════════════════════════════════\n// 新增交易\n// ═══════════════════════════════════════════\nlet currentTab = \'buy\';\nlet editingRecordId = null;\nlet duplicateMode = false;\n\nfunction switchTab(t) {\n  currentTab = t;\n  document.getElementById(\'tab-buy\').classList.toggle(\'active\', t===\'buy\');\n  document.getElementById(\'tab-sell\').classList.toggle(\'active\', t===\'sell\');\n  document.getElementById(\'sell-tax-group\').style.display = t===\'sell\'?\'flex\':\'none\';\n  updateAvgCalculator();\n  renderBaseHoldingsSettings();\n}\n\nconst stockNames = {\'0050\':\'元大台灣50\',\'2308\':\'台達電\',\'2330\':\'台積電\',\'2303\':\'聯電\',\'2454\':\'聯發科\',\'5190\':\'旺矽\',\'2317\':\'鴻海\',\'2002\':\'中鋼\',\'1301\':\'台塑\',\'2881\':\'富邦金\',\'3008\':\'大立光\',\'2379\':\'瑞昱\'};\nfunction autoFillName() {\n  const c = normalizeStockCode(document.getElementById(\'f-code\').value.trim());\n  if (stockNames[c]) document.getElementById(\'f-name\').value = stockNames[c];\n  updateAvgCalculator();\n}\nfunction calcFee() {\n  const qty = parseFloat(document.getElementById(\'f-qty\').value)||0;\n  const price = parseFloat(document.getElementById(\'f-price\').value)||0;\n  const rate = db.settings?.feeRate || 0.1425;\n  const fee = Math.round(qty * price * rate / 100);\n  document.getElementById(\'f-fee\').value = fee ? fee : \'\';\n  if (currentTab===\'sell\') {\n    const tax = Math.round(qty * price * 0.3 / 100);\n    document.getElementById(\'f-tax\').value = tax ? tax : \'\';\n  }\n  updateAvgCalculator();\n}\n\nfunction formatAvgMoney(v, digits=2) {\n  const n = Number(v || 0);\n  if (!Number.isFinite(n)) return \'—\';\n  return n.toLocaleString(\'zh-TW\', { minimumFractionDigits: digits, maximumFractionDigits: digits });\n}\n\nfunction formatWholeMoney(v) {\n  const n = Math.round(Number(v || 0));\n  return \'$\' + n.toLocaleString(\'zh-TW\');\n}\n\nfunction getHoldingForCode(code) {\n  const key = normalizeStockCode(code);\n  return calcHoldings().find(h => normalizeStockCode(h.code) === key) || { code:key, name: stockNames[key] || key, qty:0, totalCost:0, isBase:false };\n}\n\nfunction updateAvgCalculator() {\n  const box = document.getElementById(\'avgcalc-result\');\n  if (!box) return;\n  if (currentTab !== \'buy\') {\n    box.className = \'avgcalc-empty\';\n    box.innerHTML = \'這個試算器是用來試算「加碼買進後的新均價」。請切回「買進」分頁使用。\';\n    return;\n  }\n\n  const code = normalizeStockCode(document.getElementById(\'f-code\').value.trim());\n  const qty = parseFloat(document.getElementById(\'f-qty\').value) || 0;\n  const price = parseFloat(document.getElementById(\'f-price\').value) || 0;\n  if (!code || qty <= 0 || price <= 0) {\n    box.className = \'avgcalc-empty\';\n    box.innerHTML = \'請先在上方輸入股票代號、買進價格與股數。\';\n    return;\n  }\n\n  const holding = getHoldingForCode(code);\n  const currentQty = Number(holding.qty || 0);\n  const currentCost = Number(holding.totalCost || 0);\n  const currentAvg = currentQty > 0 ? currentCost / currentQty : 0;\n  const amount = qty * price;\n  const feeInput = document.getElementById(\'f-fee\').value;\n  const rate = db.settings?.feeRate || 0.1425;\n  const estimatedFee = feeInput !== \'\' ? (parseFloat(feeInput) || 0) : Math.round(amount * rate / 100);\n  const newQty = currentQty + qty;\n  const newCost = currentCost + amount + estimatedFee;\n  const newAvg = newQty > 0 ? newCost / newQty : 0;\n  const avgDiff = currentQty > 0 ? newAvg - currentAvg : 0;\n  const avgDiffPct = currentQty > 0 && currentAvg > 0 ? (avgDiff / currentAvg * 100) : 0;\n  const currentPrice = db.prices?.[code] || 0;\n  const currentPriceText = currentPrice ? `目前快取股價約 ${formatAvgMoney(currentPrice, currentPrice >= 1000 ? 0 : 2)} 元；` : \'尚無目前股價快取；\';\n  const directionText = currentQty > 0\n    ? (avgDiff > 0 ? `均價會上升 ${formatAvgMoney(avgDiff)} 元（+${avgDiffPct.toFixed(2)}%）。` : avgDiff < 0 ? `均價會下降 ${formatAvgMoney(Math.abs(avgDiff))} 元（${avgDiffPct.toFixed(2)}%）。` : \'均價幾乎不變。\')\n    : \'這是新股票部位，試算均價會等於本次買進成本加上手續費後的均價。\';\n  const name = document.getElementById(\'f-name\').value.trim() || holding.name || stockNames[code] || code;\n\n  box.className = \'\';\n  box.innerHTML = `\n    <div class="avgcalc-grid">\n      <div class="avgcalc-card"><div class="avgcalc-label">股票</div><div class="avgcalc-value accent">${code} ${name}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">目前股數</div><div class="avgcalc-value">${currentQty.toLocaleString()} 股</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">目前均價</div><div class="avgcalc-value">${currentQty ? formatAvgMoney(currentAvg) : \'—\'}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">本次買進</div><div class="avgcalc-value">${qty.toLocaleString()} 股 @ ${formatAvgMoney(price, price >= 1000 ? 0 : 2)}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">估算手續費</div><div class="avgcalc-value">${formatWholeMoney(estimatedFee)}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">買後總股數</div><div class="avgcalc-value">${newQty.toLocaleString()} 股</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">買後總成本</div><div class="avgcalc-value">${formatWholeMoney(newCost)}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">買後新均價</div><div class="avgcalc-value ${avgDiff <= 0 ? \'pos\' : \'neg\'}">${formatAvgMoney(newAvg)}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">均價變化</div><div class="avgcalc-value ${avgDiff <= 0 ? \'pos\' : \'neg\'}">${currentQty ? (avgDiff >= 0 ? \'+\' : \'\') + formatAvgMoney(avgDiff) : \'新部位\'}</div></div>\n      <div class="avgcalc-card"><div class="avgcalc-label">本次所需資金</div><div class="avgcalc-value">${formatWholeMoney(amount + estimatedFee)}</div></div>\n    </div>\n    <div class="avgcalc-note">${currentPriceText}${directionText} 試算結果尚未儲存，按「儲存紀錄」後才會正式加入雲端交易紀錄。</div>\n  `;\n}\n\nfunction buildRecordFromForm(existingId=null, existingTs=null) {\n  const code = normalizeStockCode(document.getElementById(\'f-code\').value.trim());\n  const name = document.getElementById(\'f-name\').value.trim();\n  const qty = parseFloat(document.getElementById(\'f-qty\').value);\n  const price = parseFloat(document.getElementById(\'f-price\').value);\n  const date = document.getElementById(\'f-date\').value;\n  if (!code || !qty || !price || !date) return null;\n  return {\n    id: existingId || Date.now(),\n    date,\n    code,\n    name: name || stockNames[code] || code,\n    action: currentTab,\n    qty,\n    price,\n    fee: parseFloat(document.getElementById(\'f-fee\').value)||0,\n    tax: parseFloat(document.getElementById(\'f-tax\').value)||0,\n    direction: document.getElementById(\'f-direction\').value,\n    reason: document.getElementById(\'f-reason\').value,\n    stop: parseFloat(document.getElementById(\'f-stop\').value)||0,\n    target: parseFloat(document.getElementById(\'f-target\').value)||0,\n    note: document.getElementById(\'f-note\').value.trim(),\n    ts: existingTs || Date.now(),\n    updatedAt: Date.now()\n  };\n}\n\nfunction saveRecord() {\n  const editingId = editingRecordId;\n  const existing = editingId ? db.records.find(r => String(r.id) === String(editingId)) : null;\n  const record = buildRecordFromForm(editingId || null, existing?.ts || null);\n  if (!record) { showToast(\'請填寫股票代號、日期、股數與價格\', \'info\'); return; }\n\n  if (editingId) {\n    const idx = db.records.findIndex(r => String(r.id) === String(editingId));\n    if (idx === -1) {\n      showToast(\'找不到要更新的交易紀錄，請重新整理後再試\', \'info\');\n      return;\n    }\n    db.records[idx] = { ...db.records[idx], ...record };\n    showToast(\'交易紀錄已更新並同步到雲端！\', \'success\');\n  } else {\n    db.records.push(record);\n    showToast(duplicateMode ? \'複製交易已儲存並同步到雲端！\' : \'交易紀錄已儲存並同步到雲端！\', \'success\');\n  }\n\n  saveData(db);\n  renderAll();\n  clearForm();\n  const code = record.code;\n  if (code) refreshPrices();\n}\n\nfunction setEditMode(id=null, mode=\'new\') {\n  editingRecordId = id;\n  duplicateMode = mode === \'copy\';\n  const banner = document.getElementById(\'edit-banner\');\n  const bannerText = document.getElementById(\'edit-banner-text\');\n  const submitBtn = document.getElementById(\'record-submit-btn\');\n  const clearBtn = document.getElementById(\'form-clear-btn\');\n  if (!banner || !submitBtn) return;\n\n  if (mode === \'edit\' && id) {\n    banner.classList.add(\'show\');\n    if (bannerText) bannerText.textContent = \'正在編輯既有交易紀錄。修改完成後請按「更新紀錄」。\';\n    submitBtn.innerHTML = \'<i class="ti ti-device-floppy"></i> 更新紀錄\';\n    if (clearBtn) clearBtn.innerHTML = \'<i class="ti ti-x"></i> 取消\';\n  } else if (mode === \'copy\') {\n    banner.classList.add(\'show\');\n    if (bannerText) bannerText.textContent = \'已複製一筆類似交易到表單。請確認日期、股數與價格後再儲存成新紀錄。\';\n    submitBtn.innerHTML = \'<i class="ti ti-copy-check"></i> 儲存複製紀錄\';\n    if (clearBtn) clearBtn.innerHTML = \'<i class="ti ti-x"></i> 清除\';\n  } else {\n    banner.classList.remove(\'show\');\n    if (bannerText) bannerText.textContent = \'正在編輯交易紀錄\';\n    submitBtn.innerHTML = \'<i class="ti ti-check"></i> 儲存紀錄\';\n    if (clearBtn) clearBtn.innerHTML = \'<i class="ti ti-x"></i> 清除\';\n    editingRecordId = null;\n    duplicateMode = false;\n  }\n}\n\nfunction fillTradeForm(record, options={}) {\n  const mode = options.mode || \'edit\';\n  switchTab(record.action === \'sell\' ? \'sell\' : \'buy\');\n  document.getElementById(\'f-code\').value = normalizeStockCode(record.code || \'\');\n  document.getElementById(\'f-name\').value = record.name || stockNames[normalizeStockCode(record.code)] || \'\';\n  document.getElementById(\'f-date\').value = options.useToday ? new Date().toISOString().split(\'T\')[0] : (record.date || new Date().toISOString().split(\'T\')[0]);\n  document.getElementById(\'f-qty\').value = record.qty ?? \'\';\n  document.getElementById(\'f-price\').value = record.price ?? \'\';\n  document.getElementById(\'f-fee\').value = record.fee ?? \'\';\n  document.getElementById(\'f-tax\').value = record.tax ?? \'\';\n  document.getElementById(\'f-direction\').value = record.direction || \'中期（3-6個月）\';\n  document.getElementById(\'f-reason\').value = record.reason || \'其他\';\n  document.getElementById(\'f-stop\').value = record.stop || \'\';\n  document.getElementById(\'f-target\').value = record.target || \'\';\n  document.getElementById(\'f-note\').value = record.note || \'\';\n  updateAvgCalculator();\n  showPage(\'add\');\n  setTimeout(() => document.getElementById(\'f-code\')?.focus(), 50);\n  setEditMode(mode === \'edit\' ? record.id : null, mode);\n}\n\nfunction editRecord(id) {\n  const record = db.records.find(r => String(r.id) === String(id));\n  if (!record) { showToast(\'找不到這筆交易紀錄\', \'info\'); return; }\n  fillTradeForm(record, { mode:\'edit\', useToday:false });\n}\n\nfunction copyRecord(id) {\n  const record = db.records.find(r => String(r.id) === String(id));\n  if (!record) { showToast(\'找不到這筆交易紀錄\', \'info\'); return; }\n  fillTradeForm(record, { mode:\'copy\', useToday:true });\n  showToast(\'已複製到表單，確認後按「儲存複製紀錄」\', \'info\');\n}\n\nfunction cancelEditRecord() {\n  clearForm();\n  showToast(\'已取消編輯\', \'info\');\n}\n\nfunction renderRecords() {\n  const tbody = document.getElementById(\'records-tbody\');\n  tbody.innerHTML = \'\';\n  const sorted = [...db.records].reverse();\n  for (const r of sorted) {\n    const reasonText = (r.reason || \'其他\').split(\'（\')[0];\n    const actionLabel = r.action === \'buy\' ? \'買進\' : \'賣出\';\n    tbody.innerHTML += `<tr>\n      <td>${htmlSafe(r.date || \'\')}</td>\n      <td><strong>${htmlSafe(normalizeStockCode(r.code))}</strong> ${htmlSafe(r.name || \'\')}</td>\n      <td><span class="badge ${r.action===\'buy\'?\'buy\':\'loss\'}">${actionLabel}</span></td>\n      <td class="mono">${Number(r.qty || 0).toLocaleString()}</td>\n      <td class="mono">${Number(r.price || 0).toLocaleString()}</td>\n      <td><span class="tag tech">${htmlSafe(reasonText)}</span></td>\n      <td style="color:var(--text2);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${htmlSafe(r.note || \'\')}">${htmlSafe(r.note||\'—\')}</td>\n      <td>\n        <div class="record-actions">\n          <button class="record-action-btn edit" onclick="editRecord(${JSON.stringify(r.id)})" title="編輯這筆交易"><i class="ti ti-pencil"></i> 編輯</button>\n          <button class="record-action-btn copy" onclick="copyRecord(${JSON.stringify(r.id)})" title="複製成類似交易"><i class="ti ti-copy"></i> 複製</button>\n          <button class="record-action-btn delete" onclick="deleteRecord(${JSON.stringify(r.id)})" title="刪除這筆交易"><i class="ti ti-trash"></i> 刪除</button>\n        </div>\n      </td>\n    </tr>`;\n  }\n  if (!sorted.length) {\n    tbody.innerHTML = \'<tr><td colspan="8" style="text-align:center;color:var(--text2);padding:28px">尚無紀錄</td></tr>\';\n  }\n}\n\nfunction deleteRecord(id) {\n  if (!confirm(\'確定刪除此筆紀錄？\')) return;\n  db.records = db.records.filter(r => String(r.id) !== String(id));\n  if (String(editingRecordId) === String(id)) setEditMode(null, \'new\');\n  saveData(db);\n  renderAll();\n  showToast(\'已刪除並同步到雲端\', \'info\');\n}\n\nfunction clearForm() {\n  [\'f-code\',\'f-name\',\'f-qty\',\'f-price\',\'f-fee\',\'f-tax\',\'f-stop\',\'f-target\',\'f-note\'].forEach(id=>{\n    const el=document.getElementById(id); if(el) el.value=\'\';\n  });\n  document.getElementById(\'f-date\').value = new Date().toISOString().split(\'T\')[0];\n  if (document.getElementById(\'q-date\')) document.getElementById(\'q-date\').value = new Date().toISOString().split(\'T\')[0];\n  document.getElementById(\'f-direction\').value = \'中期（3-6個月）\';\n  document.getElementById(\'f-reason\').value = \'技術面突破（量增價漲）\';\n  setEditMode(null, \'new\');\n  updateAvgCalculator();\n}\n\n\nfunction getTodayISO() {\n  return new Date().toISOString().split(\'T\')[0];\n}\n\nlet quickAction = \'buy\';\n\nfunction openQuickAdd() {\n  const modal = document.getElementById(\'quick-trade-modal\');\n  if (!modal) return;\n  clearQuickForm(false);\n  setQuickAction(\'buy\');\n  document.getElementById(\'q-date\').value = getTodayISO();\n  modal.classList.add(\'show\');\n  setTimeout(() => document.getElementById(\'q-code\')?.focus(), 80);\n}\n\nfunction closeQuickAdd() {\n  const modal = document.getElementById(\'quick-trade-modal\');\n  if (modal) modal.classList.remove(\'show\');\n}\n\nfunction setQuickAction(action) {\n  quickAction = action === \'sell\' ? \'sell\' : \'buy\';\n  document.getElementById(\'q-action-buy\')?.classList.toggle(\'active\', quickAction === \'buy\');\n  document.getElementById(\'q-action-sell\')?.classList.toggle(\'active\', quickAction === \'sell\');\n  const taxGroup = document.getElementById(\'q-tax-group\');\n  if (taxGroup) taxGroup.style.display = quickAction === \'sell\' ? \'flex\' : \'none\';\n  calcQuickFee();\n  updateQuickSummary();\n}\n\nfunction autoFillQuickName() {\n  const code = normalizeStockCode(document.getElementById(\'q-code\')?.value || \'\');\n  const nameEl = document.getElementById(\'q-name\');\n  if (nameEl && !nameEl.value && stockNames[code]) nameEl.value = stockNames[code];\n}\n\nfunction calcQuickFee() {\n  const qty = parseFloat(document.getElementById(\'q-qty\')?.value) || 0;\n  const price = parseFloat(document.getElementById(\'q-price\')?.value) || 0;\n  const amount = qty * price;\n  const rate = db.settings?.feeRate || 0.1425;\n  const fee = Math.round(amount * rate / 100);\n  const feeEl = document.getElementById(\'q-fee\');\n  if (feeEl && document.activeElement !== feeEl) feeEl.value = fee ? fee : \'\';\n  const taxEl = document.getElementById(\'q-tax\');\n  if (taxEl && quickAction === \'sell\' && document.activeElement !== taxEl) {\n    const tax = Math.round(amount * 0.3 / 100);\n    taxEl.value = tax ? tax : \'\';\n  }\n}\n\nfunction updateQuickSummary() {\n  const box = document.getElementById(\'q-summary\');\n  if (!box) return;\n  const code = normalizeStockCode(document.getElementById(\'q-code\')?.value || \'\');\n  const qty = parseFloat(document.getElementById(\'q-qty\')?.value) || 0;\n  const price = parseFloat(document.getElementById(\'q-price\')?.value) || 0;\n  const fee = parseFloat(document.getElementById(\'q-fee\')?.value) || 0;\n  const tax = quickAction === \'sell\' ? (parseFloat(document.getElementById(\'q-tax\')?.value) || 0) : 0;\n  if (!code || qty <= 0 || price <= 0) {\n    box.innerHTML = \'輸入股票代號、股數與價格後，會自動估算成交金額與費用。\';\n    return;\n  }\n  const amount = qty * price;\n  const total = quickAction === \'buy\' ? amount + fee : amount - fee - tax;\n  const holding = getHoldingForCode(code);\n  const actionText = quickAction === \'buy\' ? \'買進需準備\' : \'賣出預估入帳\';\n  box.innerHTML = `\n    <strong>${code}</strong> ${quickAction === \'buy\' ? \'買進\' : \'賣出\'} ${qty.toLocaleString()} 股 @ ${price.toLocaleString()} 元<br>\n    成交金額：${formatWholeMoney(amount)}｜手續費：${formatWholeMoney(fee)}${quickAction === \'sell\' ? `｜證交稅：${formatWholeMoney(tax)}` : \'\'}<br>\n    ${actionText}：<strong>${formatWholeMoney(total)}</strong>｜目前持有：${Number(holding.qty || 0).toLocaleString()} 股\n  `;\n}\n\nfunction clearQuickForm(close=true) {\n  [\'q-code\',\'q-name\',\'q-qty\',\'q-price\',\'q-fee\',\'q-tax\',\'q-stop\',\'q-target\',\'q-note\'].forEach(id => {\n    const el = document.getElementById(id); if (el) el.value = \'\';\n  });\n  const dateEl = document.getElementById(\'q-date\');\n  if (dateEl) dateEl.value = getTodayISO();\n  const dirEl = document.getElementById(\'q-direction\');\n  if (dirEl) dirEl.value = \'中期（3-6個月）\';\n  const reasonEl = document.getElementById(\'q-reason\');\n  if (reasonEl) reasonEl.value = \'快速新增\';\n  updateQuickSummary();\n  if (close) closeQuickAdd();\n}\n\nfunction buildQuickRecord() {\n  const code = normalizeStockCode(document.getElementById(\'q-code\')?.value || \'\');\n  const qty = parseFloat(document.getElementById(\'q-qty\')?.value);\n  const price = parseFloat(document.getElementById(\'q-price\')?.value);\n  const date = document.getElementById(\'q-date\')?.value || getTodayISO();\n  if (!code || !qty || !price || !date) return null;\n  const name = (document.getElementById(\'q-name\')?.value || \'\').trim() || stockNames[code] || code;\n  return {\n    id: Date.now(),\n    date,\n    code,\n    name,\n    action: quickAction,\n    qty,\n    price,\n    fee: parseFloat(document.getElementById(\'q-fee\')?.value) || 0,\n    tax: parseFloat(document.getElementById(\'q-tax\')?.value) || 0,\n    direction: document.getElementById(\'q-direction\')?.value || \'中期（3-6個月）\',\n    reason: document.getElementById(\'q-reason\')?.value || \'快速新增\',\n    stop: parseFloat(document.getElementById(\'q-stop\')?.value) || 0,\n    target: parseFloat(document.getElementById(\'q-target\')?.value) || 0,\n    note: (document.getElementById(\'q-note\')?.value || \'\').trim(),\n    ts: Date.now(),\n    updatedAt: Date.now(),\n    quickAdd: true\n  };\n}\n\nfunction saveQuickRecord() {\n  const record = buildQuickRecord();\n  if (!record) {\n    showToast(\'請填寫股票代號、日期、股數與價格\', \'info\');\n    return;\n  }\n  db.records.push(record);\n  saveData(db);\n  renderAll();\n  closeQuickAdd();\n  clearQuickForm(false);\n  showToast(\'快速交易紀錄已儲存並同步到雲端！\', \'success\');\n  refreshPrices();\n}\n\n\n\n// ═══════════════════════════════════════════\n// 損益分析頁\n// ═══════════════════════════════════════════\nfunction daysBetween(start, end) {\n  if (!start || start === \'原先持股\' || !end) return null;\n  const s = new Date(start + \'T00:00:00\');\n  const e = new Date(end + \'T00:00:00\');\n  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;\n  return Math.max(0, Math.round((e - s) / 86400000));\n}\n\nfunction moneyText(n) {\n  const v = Math.round(Number(n || 0));\n  if (v === 0) return \'$0\';\n  return (v > 0 ? \'+$\' : \'-$\') + Math.abs(v).toLocaleString();\n}\n\nfunction calculateRealizedDetails() {\n  const lots = {};\n  const details = [];\n\n  for (const b of getBaseHoldings()) {\n    const code = normalizeStockCode(b.code);\n    const qty = Number(b.qty) || 0;\n    const totalCost = Number(b.totalCost) || qty * (Number(b.avgCost) || 0);\n    if (!lots[code]) lots[code] = [];\n    if (qty > 0) {\n      lots[code].push({\n        code,\n        name: b.name,\n        remainingQty: qty,\n        unitCost: qty ? totalCost / qty : 0,\n        date: \'原先持股\',\n        reason: \'原先持股\',\n        direction: \'原先持股\',\n        isBase: true\n      });\n    }\n  }\n\n  const sorted = [...db.records].sort((a, b) => {\n    const dateCompare = String(a.date || \'\').localeCompare(String(b.date || \'\'));\n    if (dateCompare !== 0) return dateCompare;\n    return (a.ts || a.id || 0) - (b.ts || b.id || 0);\n  });\n\n  for (const r of sorted) {\n    const code = normalizeStockCode(r.code);\n    if (!code) continue;\n    if (!lots[code]) lots[code] = [];\n\n    const qty = Number(r.qty) || 0;\n    const price = Number(r.price) || 0;\n    const fee = Number(r.fee) || 0;\n    const tax = Number(r.tax) || 0;\n    const name = r.name || lots[code][0]?.name || code;\n\n    if (r.action === \'buy\') {\n      if (qty > 0 && price > 0) {\n        lots[code].push({\n          code,\n          name,\n          remainingQty: qty,\n          unitCost: (qty * price + fee) / qty,\n          date: r.date,\n          reason: r.reason || \'未填理由\',\n          direction: r.direction || \'\',\n          isBase: false\n        });\n      }\n      continue;\n    }\n\n    if (r.action !== \'sell\') continue;\n\n    let left = qty;\n    let matchedQty = 0;\n    let costBasis = 0;\n    let proceeds = 0;\n    let weightedDays = 0;\n    let dayQty = 0;\n    const buyDates = new Set();\n    const reasons = new Set();\n    const directions = new Set();\n\n    while (left > 0.000001 && lots[code].length) {\n      const lot = lots[code][0];\n      const take = Math.min(left, lot.remainingQty);\n      const ratio = qty > 0 ? take / qty : 0;\n      const lotCost = lot.unitCost * take;\n      const lotProceeds = take * price - (fee + tax) * ratio;\n      const d = daysBetween(lot.date, r.date);\n\n      matchedQty += take;\n      costBasis += lotCost;\n      proceeds += lotProceeds;\n      if (d !== null) {\n        weightedDays += d * take;\n        dayQty += take;\n      }\n      buyDates.add(lot.date || \'未知\');\n      reasons.add(lot.reason || \'未填理由\');\n      if (lot.direction) directions.add(lot.direction);\n\n      lot.remainingQty -= take;\n      left -= take;\n      if (lot.remainingQty <= 0.000001) lots[code].shift();\n    }\n\n    if (matchedQty > 0) {\n      const pnl = proceeds - costBasis;\n      details.push({\n        sellId: r.id,\n        date: r.date,\n        code,\n        name,\n        qty: matchedQty,\n        sellPrice: price,\n        avgCost: matchedQty ? costBasis / matchedQty : 0,\n        costBasis,\n        proceeds,\n        pnl,\n        pnlPct: costBasis ? (pnl / costBasis * 100) : 0,\n        days: dayQty ? Math.round(weightedDays / dayQty) : null,\n        buyDate: buyDates.size === 1 ? [...buyDates][0] : \'多筆成本\',\n        reason: reasons.size === 1 ? [...reasons][0] : [...reasons].join(\'、\'),\n        direction: directions.size === 1 ? [...directions][0] : [...directions].join(\'、\'),\n        calculable: true\n      });\n    }\n\n    if (left > 0.000001 && matchedQty === 0) {\n      details.push({\n        sellId: r.id,\n        date: r.date,\n        code,\n        name,\n        qty,\n        sellPrice: price,\n        avgCost: 0,\n        costBasis: 0,\n        proceeds: qty * price - fee - tax,\n        pnl: 0,\n        pnlPct: 0,\n        days: null,\n        buyDate: \'無成本資料\',\n        reason: \'找不到對應買進 / 原先持股\',\n        direction: \'\',\n        calculable: false\n      });\n    }\n  }\n\n  return details;\n}\n\nfunction updatePnlPage() {\n  const details = calculateRealizedDetails();\n  const valid = details.filter(d => d.calculable);\n  const wins = valid.filter(d => d.pnl > 0);\n  const losses = valid.filter(d => d.pnl < 0);\n  const winrate = valid.length ? Math.round(wins.length / valid.length * 100) : null;\n  const totalPnl = valid.reduce((sum, d) => sum + d.pnl, 0);\n\n  const winEl = document.getElementById(\'p-winrate\');\n  const winSub = document.getElementById(\'p-winrate-sub\');\n  if (winEl) winEl.textContent = winrate === null ? \'—\' : winrate + \'%\';\n  if (winEl) winEl.className = \'metric-val mono \' + (winrate === null ? \'\' : winrate >= 50 ? \'pos\' : \'neg\');\n  if (winSub) winSub.textContent = valid.length ? `${wins.length}勝 / ${losses.length}敗｜總已實現 ${moneyText(totalPnl)}` : \'尚無可計算的賣出交易\';\n\n  const dayDetails = valid.filter(d => d.days !== null);\n  const avgDays = dayDetails.length ? Math.round(dayDetails.reduce((sum, d) => sum + d.days, 0) / dayDetails.length) : null;\n  const avgDaysEl = document.getElementById(\'p-avgdays\');\n  const avgDaysSub = document.getElementById(\'p-avgdays-sub\');\n  if (avgDaysEl) avgDaysEl.textContent = avgDays === null ? \'—\' : avgDays + \'天\';\n  if (avgDaysSub) avgDaysSub.textContent = dayDetails.length ? `已排除原先持股等無買進日資料` : (valid.length ? \'原先持股無買進日期，無法計算天數\' : \'尚無已實現交易\');\n\n  const maxWin = wins.length ? [...wins].sort((a, b) => b.pnl - a.pnl)[0] : null;\n  const maxLoss = losses.length ? [...losses].sort((a, b) => a.pnl - b.pnl)[0] : null;\n  const maxWinEl = document.getElementById(\'p-maxwin\');\n  const maxWinSub = document.getElementById(\'p-maxwin-sub\');\n  const maxLossEl = document.getElementById(\'p-maxloss\');\n  const maxLossSub = document.getElementById(\'p-maxloss-sub\');\n  if (maxWinEl) maxWinEl.textContent = maxWin ? moneyText(maxWin.pnl) : \'—\';\n  if (maxWinSub) maxWinSub.textContent = maxWin ? `${maxWin.code} ${maxWin.name}｜${maxWin.date}` : \'尚無獲利賣出\';\n  if (maxLossEl) maxLossEl.textContent = maxLoss ? moneyText(maxLoss.pnl) : \'—\';\n  if (maxLossSub) maxLossSub.textContent = maxLoss ? `${maxLoss.code} ${maxLoss.name}｜${maxLoss.date}` : \'尚無虧損賣出\';\n\n  const tbody = document.getElementById(\'realized-tbody\');\n  if (tbody) {\n    if (!details.length) {\n      tbody.innerHTML = \'<tr><td colspan="9" style="text-align:center;color:var(--text2);padding:28px">尚無賣出紀錄。賣出後，這裡會顯示每筆已實現損益。</td></tr>\';\n    } else {\n      tbody.innerHTML = details.slice().reverse().map(d => {\n        const pnlClass = d.pnl >= 0 ? \'pos\' : \'neg\';\n        const daysText = d.days === null ? \'—\' : d.days + \'天\';\n        const badge = d.calculable ? `<span class="badge ${d.pnl >= 0 ? \'profit\' : \'loss\'}">${d.pnl >= 0 ? \'獲利\' : \'虧損\'}</span>` : \'<span class="badge hold">無成本</span>\';\n        return `<tr>\n          <td>${d.date || \'—\'}</td>\n          <td><strong>${d.code}</strong><br><span style="color:var(--text2);font-size:11px">${d.name || \'\'}</span></td>\n          <td class="mono">${Number(d.qty || 0).toLocaleString()}</td>\n          <td class="mono">${d.avgCost ? d.avgCost.toFixed(2) : \'—\'}</td>\n          <td class="mono">${Number(d.sellPrice || 0).toLocaleString()}</td>\n          <td class="mono ${pnlClass}">${d.calculable ? moneyText(d.pnl) : \'無法計算\'}<br>${badge}</td>\n          <td class="mono ${pnlClass}">${d.calculable ? (d.pnlPct >= 0 ? \'+\' : \'\') + d.pnlPct.toFixed(2) + \'%\' : \'—\'}</td>\n          <td>${daysText}</td>\n          <td style="white-space:normal;max-width:220px;color:var(--text2)">${d.reason || \'—\'}<br><span style="font-size:11px">買進來源：${d.buyDate || \'—\'}</span></td>\n        </tr>`;\n      }).join(\'\');\n    }\n  }\n\n  const reasonMap = {};\n  for (const d of valid) {\n    const key = d.reason || \'未填理由\';\n    if (!reasonMap[key]) reasonMap[key] = { win: 0, total: 0, pnl: 0, qty: 0 };\n    reasonMap[key].total += 1;\n    reasonMap[key].qty += Number(d.qty || 0);\n    reasonMap[key].pnl += d.pnl;\n    if (d.pnl > 0) reasonMap[key].win += 1;\n  }\n\n  const rEl = document.getElementById(\'reason-pnl\');\n  const entries = Object.entries(reasonMap).sort((a, b) => Math.abs(b[1].pnl) - Math.abs(a[1].pnl));\n  if (!rEl) return;\n  if (!entries.length) {\n    rEl.innerHTML = \'<div style="color:var(--text2);font-size:13px">尚無可計算的已實現交易。若你是賣出原先持股，請確認賣出股票代號與原先持股代號一致。</div>\';\n    return;\n  }\n  rEl.innerHTML = entries.map(([k, v]) => {\n    const rate = Math.round(v.win / v.total * 100) || 0;\n    const col = v.pnl >= 0 ? \'var(--green)\' : \'var(--red)\';\n    return `<div style="margin-bottom:14px">\n      <div style="display:flex;justify-content:space-between;gap:12px;font-size:13px;margin-bottom:4px;align-items:center">\n        <span>${k}</span>\n        <span class="mono" style="color:${col}">${moneyText(v.pnl)}｜勝率 ${rate}%｜${v.total}筆</span>\n      </div>\n      <div class="progress-bar"><div class="progress-fill" style="width:${Math.max(4, Math.min(100, rate))}%;background:${col}"></div></div>\n    </div>`;\n  }).join(\'\');\n}\n\n// ═══════════════════════════════════════════\n// 投資復盤\n// ═══════════════════════════════════════════\nfunction renderReview() {\n  const el = document.getElementById(\'review-list\');\n  const records = [...db.records].filter(r => r && r.code);\n  if (!records.length) {\n    el.innerHTML = `<div style="padding:40px;text-align:center;color:var(--text2)">\n      <i class="ti ti-notebook" style="font-size:36px;display:block;margin-bottom:12px;color:var(--text3)"></i>\n      尚無交易紀錄\n    </div>`;\n    return;\n  }\n\n  const holdingMap = {};\n  for (const h of calcHoldings()) {\n    const avgCost = h.qty ? h.totalCost / h.qty : 0;\n    const price = db.prices[h.code] || avgCost;\n    const pnl = (price - avgCost) * h.qty;\n    const pnlPct = avgCost ? ((price - avgCost) / avgCost * 100) : 0;\n    holdingMap[h.code] = { ...h, avgCost, price, pnl, pnlPct };\n  }\n\n  const grouped = {};\n  for (const r of records) {\n    const code = String(r.code || \'\').trim();\n    if (!grouped[code]) grouped[code] = [];\n    grouped[code].push(r);\n  }\n\n  const sections = Object.keys(grouped).sort((a,b)=>a.localeCompare(b, \'zh-Hant\')).map(code => {\n    const stockRecords = grouped[code].sort((a,b) => (b.date || \'\').localeCompare(a.date || \'\') || (b.ts || 0) - (a.ts || 0));\n    const stockName = stockRecords.find(r => r.name)?.name || code;\n    const holding = holdingMap[code];\n    const buyCount = stockRecords.filter(r => r.action === \'buy\').length;\n    const sellCount = stockRecords.filter(r => r.action === \'sell\').length;\n    const latest = stockRecords[0];\n\n    const summaryBoxes = holding ? `\n      <div class="review-summary-box"><div class="review-summary-label">目前持股</div><div class="review-summary-val">${holding.qty.toLocaleString()} 股</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">平均成本</div><div class="review-summary-val">${Math.round(holding.avgCost).toLocaleString()}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">目前價格</div><div class="review-summary-val">${Math.round(holding.price).toLocaleString()}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">未實現損益</div><div class="review-summary-val ${holding.pnl >= 0 ? \'pos\' : \'neg\'}">${holding.pnl >= 0 ? \'+\' : \'\'}${Math.round(holding.pnl).toLocaleString()}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">交易筆數</div><div class="review-summary-val">買 ${buyCount}｜賣 ${sellCount}</div></div>\n    ` : `\n      <div class="review-summary-box"><div class="review-summary-label">目前狀態</div><div class="review-summary-val">已無持股</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">最後交易</div><div class="review-summary-val">${latest?.date || \'—\'}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">交易筆數</div><div class="review-summary-val">買 ${buyCount}｜賣 ${sellCount}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">目前價格</div><div class="review-summary-val">${db.prices[code] ? Math.round(db.prices[code]).toLocaleString() : \'—\'}</div></div>\n      <div class="review-summary-box"><div class="review-summary-label">備註</div><div class="review-summary-val">僅顯示歷史紀錄</div></div>\n    `;\n\n    const rows = stockRecords.map(r => {\n      const price = db.prices[r.code] || r.price;\n      const pnlPct = r.price ? ((price - r.price) / r.price * 100) : 0;\n      const [sc, label] = getStatus(pnlPct, price, r.stop);\n      const amount = (Number(r.qty || 0) * Number(r.price || 0)) + Number(r.fee || 0) + Number(r.tax || 0);\n      return `<tr>\n        <td>${r.date || \'—\'}</td>\n        <td><span class="badge ${r.action === \'buy\' ? \'buy\' : \'loss\'}">${r.action === \'buy\' ? \'買進\' : \'賣出\'}</span></td>\n        <td class="mono">${Number(r.qty || 0).toLocaleString()}</td>\n        <td class="mono">${Number(r.price || 0).toLocaleString()}</td>\n        <td class="mono">${Math.round(amount).toLocaleString()}</td>\n        <td class="reason-cell"><span class="tag tech">${String(r.reason || \'其他\').split(\'（\')[0]}</span></td>\n        <td>${r.direction || \'—\'}</td>\n        <td class="mono">${r.stop ? r.stop.toLocaleString() : \'—\'} / ${r.target ? r.target.toLocaleString() : \'—\'}</td>\n        <td><span class="badge ${sc}">${label}</span></td>\n        <td class="note-cell">${r.note || \'—\'}</td>\n      </tr>`;\n    }).join(\'\');\n\n    return `<div class="section review-stock-section">\n      <div class="section-head">\n        <span class="section-title">${code} ${stockName}</span>\n        <span style="font-size:12px;color:var(--text2)">${stockRecords.length} 筆交易紀錄</span>\n      </div>\n      <div class="review-stock-summary">${summaryBoxes}</div>\n      <div class="review-table-wrap">\n        <table class="review-table">\n          <thead>\n            <tr>\n              <th>日期</th><th>動作</th><th>股數</th><th>價格</th><th>成交金額</th><th>理由</th><th>方向</th><th>停損/停利</th><th>狀態</th><th>備註</th>\n            </tr>\n          </thead>\n          <tbody>${rows}</tbody>\n        </table>\n      </div>\n    </div>`;\n  }).join(\'\');\n\n  el.innerHTML = sections;\n}\n\n// ═══════════════════════════════════════════\n// CSV 匯出\n// ═══════════════════════════════════════════\nfunction exportCSV(type) {\n  let rows = [], filename = \'\';\n\n  if (type === \'all\' || type === \'records\') {\n    filename = `交易紀錄_${today()}.csv`;\n    rows.push([\'日期\',\'股票代號\',\'股票名稱\',\'動作\',\'股數\',\'價格\',\'手續費\',\'稅\',\'進場理由\',\'操作方向\',\'停損\',\'停利\',\'備注\']);\n    for (const r of db.records) {\n      rows.push([r.date, r.code, r.name, r.action===\'buy\'?\'買進\':\'賣出\', r.qty, r.price, r.fee, r.tax, r.reason, r.direction, r.stop||\'\', r.target||\'\', r.note||\'\']);\n    }\n  } else if (type === \'holdings\') {\n    filename = `持股清單_${today()}.csv`;\n    rows.push([\'股票代號\',\'股票名稱\',\'持有股數\',\'平均成本\',\'現價\',\'未實現損益\',\'報酬率%\']);\n    for (const h of calcHoldings()) {\n      const avgCost = h.totalCost / h.qty;\n      const price = db.prices[h.code] || avgCost;\n      const pnl = Math.round((price - avgCost) * h.qty);\n      const pct = ((price - avgCost)/avgCost*100).toFixed(2);\n      rows.push([h.code, h.name, h.qty, Math.round(avgCost), Math.round(price), pnl, pct]);\n    }\n  } else if (type === \'pnl\') {\n    filename = `已實現損益_${today()}.csv`;\n    rows.push([\'賣出日期\',\'股票代號\',\'股票名稱\',\'賣出股數\',\'成本均價\',\'賣出價\',\'已實現損益\',\'報酬率%\',\'持有天數\',\'來源/理由\']);\n    const details = calculateRealizedDetails();\n    for (const d of details) {\n      rows.push([d.date, d.code, d.name, d.qty, d.avgCost ? d.avgCost.toFixed(2) : \'\', d.sellPrice, d.calculable ? Math.round(d.pnl) : \'\', d.calculable ? d.pnlPct.toFixed(2) : \'\', d.days ?? \'\', d.reason || \'\']);\n    }\n  } else if (type === \'backup\') {\n    const blob = new Blob([JSON.stringify(db, null, 2)], { type: \'application/json\' });\n    const a = document.createElement(\'a\');\n    a.href = URL.createObjectURL(blob);\n    a.download = `投資助理備份_${today()}.json`;\n    a.click();\n    showToast(\'JSON 備份已下載\', \'success\');\n    return;\n  }\n\n  const bom = \'\\uFEFF\'; // UTF-8 BOM for Excel\n  const csv = bom + rows.map(r => r.map(cell => `"${String(cell).replace(/"/g,\'""\')}"`).join(\',\')).join(\'\\n\');\n  const blob = new Blob([csv], { type: \'text/csv;charset=utf-8\' });\n  const a = document.createElement(\'a\');\n  a.href = URL.createObjectURL(blob);\n  a.download = filename;\n  a.click();\n  showToast(`已匯出 ${filename}`, \'success\');\n}\n\nfunction downloadTemplate() {\n  const bom = \'\\uFEFF\';\n  const rows = [\n    [\'日期\',\'股票代號\',\'股票名稱\',\'動作\',\'股數\',\'價格\',\'手續費\',\'進場理由\',\'備注\'],\n    [\'2025-04-01\',\'2330\',\'台積電\',\'買進\',\'10\',\'800\',\'114\',\'技術面突破（量增價漲）\',\'站上800元整數關卡\'],\n    [\'2025-04-10\',\'2303\',\'聯電\',\'賣出\',\'50\',\'52\',\'74\',\'\',\'獲利了結\']\n  ];\n  const csv = bom + rows.map(r => r.map(c=>`"${c}"`).join(\',\')).join(\'\\n\');\n  const blob = new Blob([csv], {type:\'text/csv;charset=utf-8\'});\n  const a = document.createElement(\'a\'); a.href=URL.createObjectURL(blob); a.download=\'交易紀錄範本.csv\'; a.click();\n  showToast(\'範本已下載，請用 Excel 開啟填寫\', \'success\');\n}\n\n// ═══════════════════════════════════════════\n// CSV 匯入\n// ═══════════════════════════════════════════\nlet importedRows = [];\n\nfunction openImportModal() {\n  document.getElementById(\'import-modal\').classList.add(\'show\');\n}\nfunction closeImportModal() {\n  document.getElementById(\'import-modal\').classList.remove(\'show\');\n  document.getElementById(\'csv-file-input\').value = \'\';\n  document.getElementById(\'import-preview\').style.display = \'none\';\n  importedRows = [];\n}\n\ndocument.addEventListener(\'DOMContentLoaded\', () => {\n  const fileInput = document.getElementById(\'csv-file-input\');\n  if (fileInput) {\n    fileInput.addEventListener(\'change\', e => {\n      const file = e.target.files[0];\n      if (!file) return;\n      const reader = new FileReader();\n      reader.onload = ev => {\n        const text = ev.target.result.replace(/^\\uFEFF/,\'\'); // strip BOM\n        const lines = text.trim().split(\'\\n\');\n        const headers = lines[0].split(\',\').map(h=>h.replace(/"/g,\'\').trim());\n        importedRows = [];\n        for (let i = 1; i < lines.length; i++) {\n          const vals = lines[i].split(\',\').map(v=>v.replace(/"/g,\'\').trim());\n          if (vals.length < 5) continue;\n          importedRows.push({\n            id: Date.now() + i,\n            date: vals[0]||\'\', code: vals[1]||\'\', name: vals[2]||vals[1]||\'\',\n            action: vals[3]===\'賣出\'?\'sell\':\'buy\',\n            qty: parseFloat(vals[4])||0, price: parseFloat(vals[5])||0,\n            fee: parseFloat(vals[6])||0, tax: 0,\n            direction: \'中期（3-6個月）\',\n            reason: vals[7]||\'其他\', stop: 0, target: 0,\n            note: vals[8]||\'\', ts: Date.now()\n          });\n        }\n        const preview = importedRows.slice(0,3).map(r=>`${r.date} ${r.code} ${r.name} ${r.action===\'buy\'?\'買進\':\'賣出\'} ${r.qty}股 @${r.price}`).join(\'\\n\');\n        document.getElementById(\'import-preview-content\').textContent = preview || \'（無法解析）\';\n        document.getElementById(\'import-preview\').style.display = \'block\';\n      };\n      reader.readAsText(file, \'UTF-8\');\n    });\n  }\n});\n\nfunction confirmImport() {\n  if (!importedRows.length) { showToast(\'沒有可匯入的資料\', \'info\'); return; }\n  db.records.push(...importedRows);\n  saveData(db);\n  renderAll();\n  closeImportModal();\n  showToast(`已匯入 ${importedRows.length} 筆交易紀錄`, \'success\');\n}\n\n// ═══════════════════════════════════════════\n// 工具\n// ═══════════════════════════════════════════\nfunction today() {\n  return new Date().toISOString().split(\'T\')[0].replace(/-/g,\'\');\n}\n\nfunction showToast(msg, type=\'success\') {\n  const t = document.getElementById(\'toast\');\n  const icon = t.querySelector(\'i\');\n  document.getElementById(\'toast-msg\').textContent = msg;\n  icon.className = type===\'success\' ? \'ti ti-check\' : \'ti ti-info-circle\';\n  t.className = `toast ${type} show`;\n  setTimeout(()=>t.className=`toast ${type}`,2800);\n}\n\nfunction clearAllData() {\n  if (!confirm(\'確定清除所有新增交易、股價快取與設定？原先持股會保留。\')) return;\n  const keptBaseHoldings = getBaseHoldings();\n  db = emptyData();\n  db.baseHoldings = keptBaseHoldings;\n  saveData(db);\n  renderAll();\n  showToast(\'已清除新增資料並同步雲端；原先持股已保留\', \'info\');\n  refreshPrices();\n}\n\n\nfunction moneyPlain(n) {\n  const v = Math.round(Number(n || 0));\n  return v.toLocaleString();\n}\n\nfunction renderBaseHoldingsSettings() {\n  const tbody = document.getElementById(\'base-holdings-tbody\');\n  if (!tbody) return;\n  const list = getBaseHoldings();\n  if (!list.length) {\n    tbody.innerHTML = \'<tr><td colspan="5" style="text-align:center;color:var(--text2);padding:24px">尚未設定原先持股</td></tr>\';\n    return;\n  }\n  tbody.innerHTML = list.map(item => {\n    const avg = Number(item.avgCost || (item.qty ? item.totalCost / item.qty : 0));\n    return `<tr>\n      <td><strong>${htmlSafe(item.code)}</strong><br><span style="color:var(--text2);font-size:11px">${htmlSafe(item.name || item.code)}</span></td>\n      <td class="mono">${Number(item.qty || 0).toLocaleString()}</td>\n      <td class="mono">${avg.toLocaleString(undefined,{maximumFractionDigits:2})}</td>\n      <td class="mono">${moneyPlain(item.totalCost)}</td>\n      <td>\n        <div class="base-holding-actions">\n          <button class="btn btn-ghost" type="button" onclick="editBaseHolding(\'${htmlSafe(item.code)}\')"><i class="ti ti-pencil"></i> 修改</button>\n          <button class="btn btn-ghost" style="color:var(--red);border-color:rgba(239,68,68,.3)" type="button" onclick="deleteBaseHolding(\'${htmlSafe(item.code)}\')"><i class="ti ti-trash"></i> 刪除</button>\n        </div>\n      </td>\n    </tr>`;\n  }).join(\'\');\n}\n\nfunction autoFillBaseName() {\n  const code = normalizeStockCode(document.getElementById(\'base-code\')?.value || \'\');\n  const nameInput = document.getElementById(\'base-name\');\n  if (!code || !nameInput || nameInput.value.trim()) return;\n  const existing = getBaseHoldings().find(x => normalizeStockCode(x.code) === code);\n  if (existing?.name) nameInput.value = existing.name;\n  else if (stockNames[code]) nameInput.value = stockNames[code];\n}\n\nfunction calcBaseTotalPreview() {\n  const qty = Number(document.getElementById(\'base-qty\')?.value || 0);\n  const avg = Number(document.getElementById(\'base-avg\')?.value || 0);\n  const totalInput = document.getElementById(\'base-total\');\n  if (!totalInput) return;\n  if (qty > 0 && avg > 0 && (!totalInput.value || totalInput.dataset.auto === \'1\')) {\n    totalInput.value = Math.round(qty * avg);\n    totalInput.dataset.auto = \'1\';\n  }\n}\n\nfunction clearBaseHoldingForm() {\n  [\'base-code\',\'base-name\',\'base-qty\',\'base-avg\',\'base-total\'].forEach(id => {\n    const el = document.getElementById(id);\n    if (el) { el.value = \'\'; if (id === \'base-total\') el.dataset.auto = \'1\'; }\n  });\n}\n\nfunction editBaseHolding(code) {\n  const item = getBaseHoldings().find(x => normalizeStockCode(x.code) === normalizeStockCode(code));\n  if (!item) return;\n  document.getElementById(\'base-code\').value = item.code;\n  document.getElementById(\'base-name\').value = item.name || item.code;\n  document.getElementById(\'base-qty\').value = item.qty;\n  document.getElementById(\'base-avg\').value = Number(item.avgCost || (item.qty ? item.totalCost / item.qty : 0)).toFixed(2);\n  const totalInput = document.getElementById(\'base-total\');\n  totalInput.value = Math.round(Number(item.totalCost || 0));\n  totalInput.dataset.auto = \'0\';\n  showPage(\'settings\');\n}\n\nfunction saveBaseHolding() {\n  const code = normalizeStockCode(document.getElementById(\'base-code\')?.value || \'\');\n  const name = (document.getElementById(\'base-name\')?.value || \'\').trim() || stockNames[code] || code;\n  const qty = Number(document.getElementById(\'base-qty\')?.value || 0);\n  const avgCostInput = Number(document.getElementById(\'base-avg\')?.value || 0);\n  const totalCostInput = Number(document.getElementById(\'base-total\')?.value || 0);\n  if (!code || qty <= 0 || (avgCostInput <= 0 && totalCostInput <= 0)) {\n    showToast(\'請填寫股票代號、股數，以及成本均價或投資成本\', \'info\');\n    return;\n  }\n  const totalCost = totalCostInput > 0 ? totalCostInput : qty * avgCostInput;\n  const avgCost = qty > 0 ? totalCost / qty : avgCostInput;\n  const next = getBaseHoldings().filter(x => normalizeStockCode(x.code) !== code);\n  next.push({ code, name, qty, avgCost, totalCost });\n  next.sort((a,b) => a.code.localeCompare(b.code));\n  db.baseHoldings = normalizeBaseHoldings(next);\n  saveData(db);\n  renderAll();\n  clearBaseHoldingForm();\n  showToast(`${code} 原先持股已新增 / 更新並同步雲端`, \'success\');\n  refreshPrices();\n}\n\nfunction deleteBaseHolding(code) {\n  const key = normalizeStockCode(code);\n  const item = getBaseHoldings().find(x => normalizeStockCode(x.code) === key);\n  if (!item) return;\n  if (!confirm(`確定刪除 ${key} ${item.name || \'\'} 的原先持股？這只會刪除初始部位，不會刪除後續交易紀錄。`)) return;\n  db.baseHoldings = getBaseHoldings().filter(x => normalizeStockCode(x.code) !== key);\n  saveData(db);\n  renderAll();\n  showToast(`${key} 原先持股已刪除並同步雲端`, \'info\');\n  refreshPrices();\n}\n\nfunction saveSettings() {\n  const rate = parseFloat(document.getElementById(\'s-fee-rate\').value);\n  if (!db.settings) db.settings = {};\n  db.settings.feeRate = rate || 0.1425;\n  saveData(db);\n  showToast(\'設定已儲存並同步雲端\', \'success\');\n}\n\n\nfunction isMobileSidebar() {\n  return window.matchMedia(\'(max-width: 820px)\').matches;\n}\n\nfunction closeSidebarOnMobile() {\n  const app = document.getElementById(\'app-shell\');\n  if (app) app.classList.remove(\'sidebar-open\');\n}\n\nfunction toggleSidebar() {\n  const app = document.getElementById(\'app-shell\');\n  if (!app) return;\n  if (isMobileSidebar()) {\n    app.classList.toggle(\'sidebar-open\');\n    return;\n  }\n  const collapsed = app.classList.toggle(\'sidebar-collapsed\');\n  localStorage.setItem(\'investlog_sidebar_collapsed\', collapsed ? \'1\' : \'0\');\n}\n\nfunction initSidebarState() {\n  const app = document.getElementById(\'app-shell\');\n  if (!app) return;\n  if (!isMobileSidebar() && localStorage.getItem(\'investlog_sidebar_collapsed\') === \'1\') {\n    app.classList.add(\'sidebar-collapsed\');\n  }\n  window.addEventListener(\'resize\', () => {\n    if (!isMobileSidebar()) app.classList.remove(\'sidebar-open\');\n  });\n}\n\n\n// ═══════════════════════════════════════════\n// AI 股票分析\n// ═══════════════════════════════════════════\nlet aiAnalysisLoaded = false;\n\nfunction htmlSafe(v) {\n  return String(v ?? \'\')\n    .replaceAll(\'&\',\'&amp;\')\n    .replaceAll(\'<\',\'&lt;\')\n    .replaceAll(\'>\',\'&gt;\')\n    .replaceAll(\'"\',\'&quot;\')\n    .replaceAll("\'",\'&#039;\');\n}\n\nfunction signedPct(v) {\n  const n = Number(v || 0);\n  return (n >= 0 ? \'+\' : \'\') + n.toFixed(2) + \'%\';\n}\n\nfunction getAiAnalysisHoldings() {\n  const holdings = calcHoldings();\n  const seen = new Set();\n  return holdings\n    .filter(h => h && Number(h.qty || 0) > 0 && String(h.code || \'\').trim())\n    .map(h => ({ code: String(h.code).trim().toUpperCase(), name: String(h.name || h.code || \'\').trim() }))\n    .filter(h => {\n      if (seen.has(h.code)) return false;\n      seen.add(h.code);\n      return true;\n    });\n}\n\nasync function loadAiAnalysis(force=false) {\n  const dateEl = document.getElementById(\'ai-date\');\n  const box = document.getElementById(\'ai-analysis-content\');\n  if (!dateEl || !box) return;\n  if (!dateEl.value) dateEl.value = new Date().toISOString().slice(0,10);\n  const date = dateEl.value;\n  const holdings = getAiAnalysisHoldings();\n  if (!holdings.length) {\n    box.innerHTML = \'<div class="section"><div class="ai-loading">目前沒有持股，新增買進紀錄後，AI 股票分析會自動加入該股票，並結合你的成本與持股比例。</div></div>\';\n    return;\n  }\n  const codes = holdings.map(h => h.code).join(\',\');\n  const names = holdings.map(h => `${h.code}:${h.name}`).join(\'|\');\n  box.innerHTML = `<div class="section"><div class="ai-loading"><i class="ti ti-loader-2" style="font-size:22px"></i><br>正在分析目前持股：${htmlSafe(codes)}<br><span style="color:var(--text2)">新增其他股票後，這裡會自動帶入新股票。</span></div></div>`;\n  try {\n    const params = new URLSearchParams({ date, refresh: force ? \'1\' : \'0\', codes, names });\n    const res = await fetch(`/api/analyze?${params.toString()}`);\n    const data = await res.json();\n    if (!res.ok || !data.ok) throw new Error(data.error || \'讀取失敗\');\n    renderAiAnalysis(data);\n    aiAnalysisLoaded = true;\n  } catch (err) {\n    box.innerHTML = `<div class="section"><div class="ai-error">AI 股票分析讀取失敗：${htmlSafe(err.message)}<br><span style="color:var(--text2)">請稍後再試，或確認 Render 服務可以連外抓資料。</span></div></div>`;\n  }\n}\n\nfunction renderAiPlanActionClass(level) {\n  if (level === "buy") return "buy";\n  if (level === "sell") return "sell";\n  return "hold";\n}\n\nfunction renderAiTomorrowPlan(stocks) {\n  const okStocks = (stocks || []).filter(s => s && s.status === "ok");\n  if (!okStocks.length) return "";\n  const rows = okStocks.map(s => {\n    const d = s.decision || {};\n    const strategy = d.strategy || {};\n    const p = s.portfolio_context || {};\n    const actionClass = renderAiPlanActionClass(d.level);\n    let suggestQty = p && p.has_position ? (p.add_qty_text || "—") : "—";\n    if (d.level === "sell") {\n      const halfQty = Number(p.half_sell_qty || 0);\n      suggestQty = halfQty > 0 ? `不加碼；反彈可先賣 ${fmtShares(halfQty)} 股` : "不加碼";\n    } else if (!suggestQty || suggestQty === "不建議加碼") {\n      suggestQty = d.level === "buy" ? "小量試單" : "0 股，等突破";\n    }\n    const close = s.metrics && s.metrics.close ? fmtMetric(s.metrics.close) : "—";\n    const weight = p && p.has_position ? `${fmtMetric(p.weight_pct)}%` : "—";\n    return `\n      <tr>\n        <td><div class="ai-plan-stock">${htmlSafe(s.code)}</div><div class="ai-plan-name">${htmlSafe(s.name || "")}｜現價 ${htmlSafe(close)}｜佔比 ${htmlSafe(weight)}</div></td>\n        <td><div class="ai-plan-action ${actionClass}">${htmlSafe(d.action || "觀望")}</div></td>\n        <td><span class="ai-plan-chip">${htmlSafe(strategy.add_range || "—")}</span></td>\n        <td><span class="ai-plan-chip">${htmlSafe(strategy.trim_range || "—")}</span></td>\n        <td><span class="ai-plan-chip">${htmlSafe(strategy.stop_range || "—")}</span></td>\n        <td>${htmlSafe(suggestQty)}</td>\n      </tr>`;\n  }).join("");\n  return `\n    <div class="ai-plan-section">\n      <div class="ai-plan-head">\n        <div class="ai-plan-title"><i class="ti ti-calendar-stats"></i>明日操作計畫</div>\n        <div class="ai-plan-sub">依照目前持股、成本均價、部位佔比、最近 1～5 日波動與 AI 技術/題材判斷整理</div>\n      </div>\n      <div class="ai-plan-table-wrap">\n        <table class="ai-plan-table">\n          <thead><tr><th>股票</th><th>明日動作</th><th>可買區間</th><th>可賣區間</th><th>停損價</th><th>建議股數</th></tr></thead>\n          <tbody>${rows}</tbody>\n        </table>\n      </div>\n      <div class="ai-plan-note">使用方式：隔天開盤前先看這張表。若開盤價直接高於可賣區間，不追高加碼；若跌入停損區，先控風險；若落在可買區間且盤中沒有爆量轉弱，再依建議股數分批執行。</div>\n    </div>`;\n}\n\nfunction renderAiAnalysis(data) {\n  const box = document.getElementById("ai-analysis-content");\n  const stocks = data.stocks || [];\n  const plan = renderAiTomorrowPlan(stocks);\n  const cards = stocks.map(renderAiCard).join("");\n  box.innerHTML = `\n    ${plan}\n    <div class="section">\n      <div class="section-head">\n        <span class="section-title">分析結果｜${stocks.length} 檔持股</span>\n        <span style="font-size:11px;color:var(--text2)">查詢日期：${htmlSafe(data.query_date)}｜更新：${htmlSafe(data.updated_at)}</span>\n      </div>\n      <div style="padding:18px 20px">\n        <div class="ai-grid">${cards}</div>\n        <div class="price-note" style="padding:16px 0 0">提醒：AI 已結合你的成本、持股比例與加減碼均價試算；明日操作計畫提供的是隔日可執行價格帶，內容僅供復盤與觀察，不構成投資建議。</div>\n      </div>\n    </div>\n  `;\n}\n\nfunction renderAiCard(s) {\n  if (s.status !== \'ok\') {\n    return `<article class="ai-card"><div class="ai-card-head"><div><div class="ai-name">${htmlSafe(s.name || s.code)}</div><div class="ai-symbol">${htmlSafe(s.code)}</div></div><span class="badge near-stop">失敗</span></div><div class="ai-error">${htmlSafe(s.message || \'抓不到資料\')}</div></article>`;\n  }\n  const m = s.metrics || {};\n  const d = s.decision || {};\n  const strategy = d.strategy || {};\n  const p = s.portfolio_context || {};\n  const trendClass = (m.change_pct || 0) >= 0 ? \'pos\' : \'neg\';\n  const actionClass = d.level === \'buy\' ? \'buy\' : d.level === \'sell\' ? \'sell\' : \'hold\';\n  const exact = s.is_exact_date ? \'\' : `<div class="ai-text">你選的日期沒有交易資料，已自動顯示最近交易日：<b>${htmlSafe(s.actual_date)}</b></div>`;\n  const reasons = (d.reasons || []).map(x => `<li>${htmlSafe(x)}</li>`).join(\'\');\n  const newsContext = s.news_context || \'目前沒有抓到足夠新聞，先以技術面與既有產業重點判斷。\';\n  const confidence = strategy.confidence ? `｜信心度 ${htmlSafe(strategy.confidence)}` : \'\';\n  const personalLevel = d.level === "sell" ? "sell" : d.level === "buy" ? "buy" : "hold";\n  const personalActionLabel = personalLevel === "sell" ? "減碼 / 賣出" : personalLevel === "buy" ? "分批加碼" : "續抱 / 等待";\n  const personalMain = personalLevel === "sell" ? "已觸發賣出優先邏輯，不再建議加碼" : personalLevel === "buy" ? "可以加碼，但只在可買區間內分批執行" : "目前未觸發明確買賣點，先以續抱或觀察為主";\n  const personalSub = personalLevel === "sell" ? "此區塊已與明日操作計畫、具體建議同步：若價格達到可賣區間或跌入失守區，優先減碼控風險。" : personalLevel === "buy" ? "此區塊已與明日操作計畫、具體建議同步：只有價格落在隔日可買區且量價沒有轉弱，才執行小量加碼。" : "此區塊已與明日操作計畫、具體建議同步：沒有進入可買或可賣區前，不新增部位也不急著賣出。";\n  const personalBuyCondition = personalLevel === "sell" ? "不加碼；目前以賣出/減碼訊號為優先" : personalLevel === "buy" ? `只在 ${strategy.add_range || "可買區間"} 分批買進` : `暫不加碼；若回到 ${strategy.add_range || "可買區間"} 再重新評估`;\n  const personalSellCondition = personalLevel === "sell" ? `達到 ${strategy.trim_range || "可賣區間"} 可分批賣出；若跌入 ${strategy.stop_range || "失守區"} 先控風險` : personalLevel === "buy" ? `若急漲到 ${strategy.trim_range || "可賣區間"}，不追價，反而可考慮小量減碼` : `若反彈到 ${strategy.trim_range || "可賣區間"} 可小量調節；跌破 ${strategy.stop_range || "失守區"} 再降風險`;\n  const personalQtyInstruction = personalLevel === "sell" ? (Number(p.half_sell_qty || 0) > 0 ? `先賣 ${fmtShares(p.half_sell_qty)} 股左右，剩餘部位再觀察` : "不加碼，先降低風險") : personalLevel === "buy" ? `${htmlSafe(p.add_qty_text || "小量試單")}；不要超過此上限` : "0 股；等價格進入可買區或突破後再說";\n  const personalImpactTitle = personalLevel === "sell" ? "賣出影響" : personalLevel === "buy" ? "加碼影響" : "若硬要試單的影響";\n  const personalImpactValue = personalLevel === "sell" ? `${fmtShares(p.half_sell_qty)} 股｜估計實現 ${fmtMoney(p.half_sell_pnl, true)}` : personalLevel === "buy" ? `買 ${htmlSafe(p.add_qty_text || "—")}｜新均價約 ${fmtMetric(p.new_avg_if_add)}｜資金 ${fmtMoney(p.add_cash_needed)}` : `建議先不動；若買入，均價約 ${fmtMetric(p.new_avg_if_add)}`;\n  const personalRiskText = Number(p.weight_pct || 0) >= 40 ? "這檔佔比偏高，任何加碼都要比操作計畫更保守；若是賣出訊號，應優先減碼。" : personalLevel === "sell" ? "賣出訊號優先於加碼訊號，避免可賣區還繼續追買。" : "注意隔日開盤若跳空超出區間，不要用原本區間硬追價。";\n  const personalSection = p.has_position ? `\n    <div class="ai-personal ${personalLevel}">\n      <div class="ai-personal-title"><i class="ti ti-user-dollar"></i>個人化持股判斷｜已與明日操作計畫一致</div>\n      <div class="ai-personal-decision">\n        <div>\n          <div class="ai-personal-decision-main">${htmlSafe(personalMain)}</div>\n          <div class="ai-personal-decision-sub">${htmlSafe(personalSub)}</div>\n        </div>\n        <span class="ai-personal-action-pill ${personalLevel}">${htmlSafe(personalActionLabel)}</span>\n      </div>\n      <div class="ai-personal-snapshot">\n        <div class="ai-personal-mini"><b>你的持股 / 均價</b><span>${fmtShares(p.qty)} 股｜${fmtMetric(p.avg_cost)}</span></div>\n        <div class="ai-personal-mini"><b>目前報酬率</b><span class="${Number(p.return_pct || 0) >= 0 ? "pos" : "neg"}">${signedPct(p.return_pct)}</span></div>\n        <div class="ai-personal-mini"><b>部位佔比</b><span>${fmtMetric(p.weight_pct)}%</span></div>\n        <div class="ai-personal-mini"><b>距離成本</b><span class="${Number(p.distance_from_cost_pct || 0) >= 0 ? "pos" : "neg"}">${fmtMetric(p.distance_from_cost_amount)}｜${signedPct(p.distance_from_cost_pct)}</span></div>\n      </div>\n      <table class="ai-personal-exec">\n        <tbody>\n          <tr><th>現在到底做什麼</th><td><b>${htmlSafe(personalActionLabel)}</b>。${htmlSafe(personalMain)}</td></tr>\n          <tr><th>買進條件</th><td>${htmlSafe(personalBuyCondition)}</td></tr>\n          <tr><th>賣出條件</th><td>${htmlSafe(personalSellCondition)}</td></tr>\n          <tr><th>建議股數</th><td>${personalQtyInstruction}</td></tr>\n          <tr><th>${htmlSafe(personalImpactTitle)}</th><td>${personalImpactValue}</td></tr>\n          <tr><th>風險提醒</th><td>${htmlSafe(personalRiskText)}</td></tr>\n        </tbody>\n      </table>\n      <div class="ai-personal-summary"><b>判斷理由：</b>${htmlSafe(s.personalized_advice || p.personal_summary || "")}</div>\n    </div>` : "";\n  return `<article class="ai-card">\n    <div class="ai-card-head">\n      <div><div class="ai-name">${htmlSafe(s.name)}</div><div class="ai-symbol">${htmlSafe(s.code)}｜分析交易日 ${htmlSafe(s.actual_date)}</div></div>\n      <span class="badge ${m.change_pct >= 0 ? \'profit\' : \'loss\'}">${htmlSafe(m.trend)}</span>\n    </div>\n    ${exact}\n    <div class="ai-price-row"><div class="ai-price">${Number(m.close || 0).toLocaleString()}</div><div class="ai-change ${trendClass}">${signedPct(m.change_pct)}（${Number(m.change || 0).toFixed(2)}）</div></div>\n    ${personalSection}\n\n    <div class="ai-strategy">\n      <div class="ai-decision-title">隔日加碼 / 賣出具體建議${confidence}</div>\n      <div class="ai-decision-action ${actionClass}">${htmlSafe(d.action || \'觀望\')}</div>\n      <div class="ai-text">${htmlSafe(d.summary || \'\')}</div>\n      ${strategy.basis ? `<div class="ai-text"><b>區間依據：</b>${htmlSafe(strategy.basis)}</div>` : \'\'}\n      <div class="ai-strategy-grid">\n        <div class="ai-strategy-box"><b>隔日加碼區間</b><span>${htmlSafe(strategy.add_range || \'—\')}</span></div>\n        <div class="ai-strategy-box"><b>隔日減碼/賣出區間</b><span>${htmlSafe(strategy.trim_range || \'—\')}</span></div>\n        <div class="ai-strategy-box"><b>隔日失守賣出區間</b><span>${htmlSafe(strategy.stop_range || \'—\')}</span></div>\n        <div class="ai-strategy-box"><b>隔日短線目標</b><span>${htmlSafe(strategy.target_range || \'—\')}</span></div>\n      </div>\n      <ul class="ai-list">${reasons}</ul>\n    </div>\n\n    <div class="ai-assessment">\n      <div class="ai-assessment-card"><b>技術面判斷</b>${htmlSafe(s.technical_assessment || \'\')}</div>\n      <div class="ai-assessment-card"><b>基本面 / 題材判斷</b>${htmlSafe(s.fundamental_assessment || \'\')}</div>\n    </div>\n\n    <div class="ai-kv">\n      <div><b>MA5</b><span>${fmtMetric(m.ma5)}</span></div>\n      <div><b>MA20</b><span>${fmtMetric(m.ma20)}</span></div>\n      <div><b>MA60</b><span>${fmtMetric(m.ma60)}</span></div>\n      <div><b>RSI14</b><span>${fmtMetric(m.rsi14)}</span></div>\n      <div><b>支撐</b><span>${fmtMetric(m.support)}</span></div>\n      <div><b>壓力</b><span>${fmtMetric(m.resistance)}</span></div>\n    </div>\n\n    <div class="ai-context"><div class="ai-context-title"><i class="ti ti-news"></i>時事脈絡重點</div>${htmlSafe(newsContext)}</div>\n    <div class="ai-text"><b>短線觀察：</b>${htmlSafe(s.explanation || \'\')}</div>\n    <div class="ai-text">資料來源：${htmlSafe(s.source || \'\')}｜新聞來源：${htmlSafe(s.news_source || \'\')}</div>\n  </article>`;\n}\n\nfunction fmtMoney(v, signed=false) {\n  const n = Number(v || 0);\n  const prefix = signed && n > 0 ? \'+\' : n < 0 ? \'-\' : \'\';\n  return prefix + \'$\' + Math.abs(n).toLocaleString(undefined,{maximumFractionDigits:0});\n}\n\nfunction fmtShares(v) {\n  const n = Number(v || 0);\n  if (!Number.isFinite(n)) return \'0\';\n  return n.toLocaleString(undefined,{maximumFractionDigits: n % 1 === 0 ? 0 : 2});\n}\n\nfunction fmtMetric(v) {\n  const n = Number(v || 0);\n  if (!Number.isFinite(n) || n === 0) return \'—\';\n  return n >= 1000 ? n.toLocaleString(undefined,{maximumFractionDigits:0}) : n.toLocaleString(undefined,{maximumFractionDigits:2});\n}\n\nfunction showPage(id) {\n  document.querySelectorAll(\'.page\').forEach(p=>p.classList.remove(\'active\'));\n  document.querySelectorAll(\'.nav-item\').forEach(n=>n.classList.remove(\'active\'));\n  document.getElementById(\'page-\'+id).classList.add(\'active\');\n  const map = { overview:0, add:1, pnl:2, review:3, ai:4, export:5, settings:6 };\n  const items = document.querySelectorAll(\'.nav-item\');\n  if (map[id]!==undefined && items[map[id]]) items[map[id]].classList.add(\'active\');\n  if (id === \'ai\' && !aiAnalysisLoaded) loadAiAnalysis(false);\n  closeSidebarOnMobile();\n}\n\nfunction renderAll() {\n  renderRecords();\n  renderHoldings();\n  updateMetrics();\n  updateCharts();\n  renderReview();\n  updatePnlPage();\n  updateAvgCalculator();\n  renderBaseHoldingsSettings();\n}\n\n// ═══════════════════════════════════════════\n// 啟動\n// ═══════════════════════════════════════════\ndocument.addEventListener(\'DOMContentLoaded\', async () => {\n  initSidebarState();\n  [\'f-code\',\'f-name\',\'f-qty\',\'f-price\',\'f-fee\'].forEach(id => {\n    const el = document.getElementById(id);\n    if (el) el.addEventListener(\'input\', updateAvgCalculator);\n  });\n  const baseTotalInput = document.getElementById(\'base-total\');\n  if (baseTotalInput) {\n    baseTotalInput.dataset.auto = \'1\';\n    baseTotalInput.addEventListener(\'input\', () => { baseTotalInput.dataset.auto = \'0\'; });\n  }\n  document.getElementById(\'f-date\').value = new Date().toISOString().split(\'T\')[0];\n  document.getElementById(\'last-update-text\').textContent = \'正在載入雲端資料...\';\n  setDot(\'updating\', \'載入雲端資料...\');\n  await loadCloudData();\n  const aiDate = document.getElementById(\'ai-date\');\n  if (aiDate && !aiDate.value) aiDate.value = new Date().toISOString().slice(0,10);\n  renderAll();\n  refreshPrices();\n});\n</script>\n</body>\n</html>\n'

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

DEFAULT_BASE_HOLDINGS: List[Dict[str, Any]] = [
    {"code": "0050", "name": "元大台灣50", "qty": 307, "avgCost": 76.95, "totalCost": 23624},
    {"code": "2303", "name": "聯電", "qty": 150, "avgCost": 72.37, "totalCost": 10855},
    {"code": "2308", "name": "台達電", "qty": 35, "avgCost": 2008.66, "totalCost": 70303},
    {"code": "2330", "name": "台積電", "qty": 60, "avgCost": 1956.02, "totalCost": 117361},
    {"code": "2454", "name": "聯發科", "qty": 5, "avgCost": 3414.8, "totalCost": 17074},
]

DEFAULT_CLOUD_STATE: Dict[str, Any] = {
    "records": [],
    "prices": {},
    "priceType": {},
    "priceSource": {},
    "baseHoldings": DEFAULT_BASE_HOLDINGS,
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
    out["baseHoldings"] = out.get("baseHoldings") if isinstance(out.get("baseHoldings"), list) else DEFAULT_BASE_HOLDINGS
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


# ═══════════════════════════════════════════
# AI 股票分析 API
# ═══════════════════════════════════════════
AI_STOCKS: Dict[str, Dict[str, Any]] = {
    "0050": {
        "name": "元大台灣50",
        "keywords": "0050 元大台灣50 台股 ETF 台積電 外資 大盤",
        "focus": ["台股大盤", "台積電權重", "ETF 長期配置", "外資動向"],
    },
    "2303": {
        "name": "聯電",
        "keywords": "聯電 2303 晶圓代工 成熟製程 法說會 外資",
        "focus": ["成熟製程", "晶圓代工報價", "股息殖利率", "法說展望"],
    },
    "2308": {
        "name": "台達電",
        "keywords": "台達電 2308 AI伺服器 電源 資料中心 外資",
        "focus": ["AI伺服器電源", "資料中心", "電源管理", "估值變化"],
    },
    "2330": {
        "name": "台積電",
        "keywords": "台積電 2330 AI 半導體 先進製程 法說會 外資",
        "focus": ["AI需求", "先進製程", "外資買賣超", "美股半導體"],
    },
    "2454": {
        "name": "聯發科",
        "keywords": "聯發科 2454 AI手機 IC設計 法說會 外資",
        "focus": ["AI手機", "IC設計", "毛利率", "法說展望", "外資動向"],
    },
}


def ai_parse_date(value: str | None) -> date:
    if not value:
        return datetime.now(TW_TZ).date()
    value = str(value).strip().replace("/", "-")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return datetime.now(TW_TZ).date()


def ai_to_unix(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=TW_TZ).timestamp())


def ai_clean_number(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        if isinstance(x, float) and math.isnan(x):
            return None
        return float(x)
    text = str(x).replace(",", "").replace("+", "").strip()
    if text in {"", "-", "--", "None", "null", "NaN"}:
        return None
    try:
        return float(text)
    except Exception:
        return None


def ai_fetch_yahoo_history(code: str, target: date, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], str]:
    start = target - timedelta(days=260)
    end = target + timedelta(days=2)
    suffixes = ["TW"] if code in AI_STOCKS else ["TW", "TWO"]
    last_error = ""
    for suffix in suffixes:
        symbol = f"{normalize_code(code)}.{suffix}"
        cache_buster = f"&_={int(time.time()*1000)}" if force_refresh else ""
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
            f"?period1={ai_to_unix(start)}&period2={ai_to_unix(end)}"
            f"&interval=1d&events=history&includeAdjustedClose=true{cache_buster}"
        )
        try:
            data = http_get_json(url, timeout=5)
            result = (((data or {}).get("chart") or {}).get("result") or [None])[0]
            if not result:
                last_error = f"Yahoo {symbol}: 無資料"
                continue
            timestamps = result.get("timestamp") or []
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            rows: List[Dict[str, Any]] = []
            for i, ts in enumerate(timestamps):
                dt = datetime.fromtimestamp(int(ts), tz=TW_TZ).date().isoformat()
                close = ai_clean_number((quote.get("close") or [None])[i] if i < len(quote.get("close") or []) else None)
                if close is None:
                    continue
                rows.append({
                    "date": dt,
                    "open": ai_clean_number((quote.get("open") or [None])[i] if i < len(quote.get("open") or []) else None),
                    "high": ai_clean_number((quote.get("high") or [None])[i] if i < len(quote.get("high") or []) else None),
                    "low": ai_clean_number((quote.get("low") or [None])[i] if i < len(quote.get("low") or []) else None),
                    "close": close,
                    "volume": int(ai_clean_number((quote.get("volume") or [0])[i] if i < len(quote.get("volume") or []) else 0) or 0),
                })
            rows.sort(key=lambda r: r["date"])
            if rows:
                return rows, f"Yahoo Finance Chart API（{symbol}）"
            last_error = f"Yahoo {symbol}: 空行情"
        except Exception as e:
            last_error = f"Yahoo {symbol}: {e}"
    return [], last_error or "Yahoo Finance 抓取失敗"


def ai_fetch_finmind_history(code: str, target: date, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], str]:
    start = (target - timedelta(days=260)).isoformat()
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={urllib.parse.quote(normalize_code(code))}&start_date={start}"
    if force_refresh:
        url += f"&_={int(time.time()*1000)}"
    try:
        data = http_get_json(url, timeout=5)
        rows = data.get("data") or []
        out: List[Dict[str, Any]] = []
        for r in rows:
            close = ai_clean_number(r.get("close"))
            if close is None:
                continue
            out.append({
                "date": str(r.get("date") or ""),
                "open": ai_clean_number(r.get("open")),
                "high": ai_clean_number(r.get("max")),
                "low": ai_clean_number(r.get("min")),
                "close": close,
                "volume": int(ai_clean_number(r.get("Trading_Volume")) or 0),
            })
        out.sort(key=lambda x: x["date"])
        return out, "FinMind TaiwanStockPrice"
    except Exception as e:
        return [], f"FinMind: {e}"


def ai_sma(values: List[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def ai_rsi(values: List[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: List[float] = []
    losses: List[float] = []
    recent = values[-(period + 1):]
    for i in range(1, len(recent)):
        diff = recent[i] - recent[i - 1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def ai_round(v: Any, digits: int = 2):
    try:
        if v is None:
            return None
        return round(float(v), digits)
    except Exception:
        return None


def ai_tick_size(price: float | None) -> float:
    """Taiwan stock tick size, used to make next-session ranges look tradable."""
    try:
        p = abs(float(price or 0))
    except Exception:
        return 0.01
    if p < 10:
        return 0.01
    if p < 50:
        return 0.05
    if p < 100:
        return 0.1
    if p < 500:
        return 0.5
    if p < 1000:
        return 1.0
    return 5.0


def ai_round_to_tick(price: float | None, mode: str = "nearest") -> float | None:
    if price is None:
        return None
    try:
        p = float(price)
    except Exception:
        return None
    if p <= 0:
        return 0.0
    tick = ai_tick_size(p)
    if mode == "down":
        return math.floor(p / tick) * tick
    if mode == "up":
        return math.ceil(p / tick) * tick
    return round(p / tick) * tick


def ai_price_range_text(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "—"
    low_f = float(low)
    high_f = float(high)
    if high_f < low_f:
        low_f, high_f = high_f, low_f
    low_f = ai_round_to_tick(low_f, "down") or 0
    high_f = ai_round_to_tick(high_f, "up") or 0
    if max(abs(low_f), abs(high_f)) >= 1000:
        return f"{low_f:,.0f}～{high_f:,.0f}"
    if max(abs(low_f), abs(high_f)) >= 100:
        return f"{low_f:,.1f}～{high_f:,.1f}"
    return f"{low_f:,.2f}～{high_f:,.2f}"


def ai_atr(rows: List[Dict[str, Any]], period: int = 14) -> float | None:
    usable = []
    prev_close = None
    for r in rows:
        high = ai_clean_number(r.get("high")) or ai_clean_number(r.get("close"))
        low = ai_clean_number(r.get("low")) or ai_clean_number(r.get("close"))
        close = ai_clean_number(r.get("close"))
        if high is None or low is None or close is None:
            continue
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        if tr >= 0:
            usable.append(tr)
        prev_close = close
    if not usable:
        return None
    recent = usable[-period:]
    return sum(recent) / len(recent)


def ai_avg_abs_change_pct(closes: List[float], period: int = 5) -> float | None:
    if len(closes) < 2:
        return None
    vals = []
    recent = closes[-(period + 1):]
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        cur = recent[i]
        if prev:
            vals.append(abs((cur - prev) / prev * 100))
    if not vals:
        return None
    return sum(vals) / len(vals)


def ai_news_score(news: List[Dict[str, str]]) -> int:
    positive = ["成長", "創高", "上修", "買超", "看好", "優於", "需求", "漲價", "獲利", "法說", "AI", "伺服器", "目標價", "訂單"]
    negative = ["下修", "賣超", "衰退", "低於", "庫存", "虧損", "降評", "壓力", "關稅", "禁令", "砍單", "疲弱", "下滑"]
    text = " ".join(str(n.get("title") or "") for n in (news or []))
    score = 0
    for w in positive:
        if w.lower() in text.lower():
            score += 1
    for w in negative:
        if w.lower() in text.lower():
            score -= 1
    return max(-3, min(3, score))


def ai_summarize_news_context(code: str, name: str, news: List[Dict[str, str]], focus: List[str]) -> str:
    titles = [str(n.get("title") or "").strip() for n in (news or []) if str(n.get("title") or "").strip()]
    if not titles:
        return f"目前沒有抓到 {name}（{code}）足夠的新近新聞，因此時事脈絡先以產業焦點「{'、'.join(focus) if focus else '股價趨勢、法人動向、財報變化'}」搭配技術面判斷。"
    cleaned: List[str] = []
    for t in titles[:6]:
        cleaned.append(re.sub(r"\s+-\s+[^-]{2,30}$", "", t))
    joined = "；".join(cleaned[:4])
    score = ai_news_score(news)
    tilt = "偏正向" if score > 0 else "偏負向" if score < 0 else "中性偏觀望"
    focus_text = "、".join(focus[:4]) if focus else "股價、財報、法人動向"
    return f"近期 {name}（{code}）相關消息主要圍繞「{joined}」。整體新聞語氣判讀為{tilt}；觀察重點可放在 {focus_text} 是否延續。如果新聞題材能搭配股價站穩均線，較有利於加碼；若新聞偏弱又跌破支撐，則應優先減碼控風險。"



def ai_portfolio_from_saved_state() -> Dict[str, Dict[str, Any]]:
    """Build current portfolio from editable base holdings + cloud transaction records."""
    try:
        state = load_app_state()
    except Exception:
        state = normalize_state(DEFAULT_CLOUD_STATE)

    positions: Dict[str, Dict[str, Any]] = {}

    def ensure(code: str, name: str = "") -> Dict[str, Any]:
        code = normalize_code(code)
        if code not in positions:
            positions[code] = {"code": code, "name": name or NAME_MAP.get(code, code), "qty": 0.0, "total_cost": 0.0}
        elif name and not positions[code].get("name"):
            positions[code]["name"] = name
        return positions[code]

    for h in state.get("baseHoldings", []) or []:
        if not isinstance(h, dict):
            continue
        code = normalize_code(h.get("code"))
        if not code:
            continue
        qty = to_float(h.get("qty"))
        avg = to_float(h.get("avgCost") or h.get("avg_cost"))
        total = to_float(h.get("totalCost") or h.get("total_cost"))
        if total <= 0 and qty > 0 and avg > 0:
            total = qty * avg
        if qty > 0:
            p = ensure(code, str(h.get("name") or NAME_MAP.get(code, code)))
            p["qty"] += qty
            p["total_cost"] += total

    records = state.get("records", []) or []
    try:
        records = sorted(records, key=lambda r: (str(r.get("date", "")), float(r.get("ts", 0) or 0)))
    except Exception:
        pass

    for r in records:
        if not isinstance(r, dict):
            continue
        code = normalize_code(r.get("code"))
        if not code:
            continue
        qty = to_float(r.get("qty"))
        price = to_float(r.get("price"))
        fee = to_float(r.get("fee"))
        action = str(r.get("action") or "buy").lower()
        p = ensure(code, str(r.get("name") or NAME_MAP.get(code, code)))
        if action == "buy":
            p["qty"] += qty
            p["total_cost"] += qty * price + fee
        else:
            current_qty = p.get("qty", 0.0)
            avg_cost = (p.get("total_cost", 0.0) / current_qty) if current_qty > 0 else price
            sold_qty = min(qty, max(current_qty, 0.0))
            p["qty"] = max(0.0, current_qty - qty)
            p["total_cost"] = max(0.0, p.get("total_cost", 0.0) - avg_cost * sold_qty)

    active = {code: p for code, p in positions.items() if p.get("qty", 0.0) > 0}
    portfolio_total_cost = sum(max(0.0, p.get("total_cost", 0.0)) for p in active.values())
    for p in active.values():
        qty = p.get("qty", 0.0)
        cost = p.get("total_cost", 0.0)
        p["avg_cost"] = cost / qty if qty > 0 else 0.0
        p["portfolio_total_cost"] = portfolio_total_cost
        p["cost_weight_pct"] = (cost / portfolio_total_cost * 100) if portfolio_total_cost > 0 else 0.0
    return active


def ai_codes_from_portfolio_state() -> Tuple[List[str], Dict[str, str]]:
    try:
        portfolio = ai_portfolio_from_saved_state()
        codes = list(portfolio.keys())
        names = {code: str(p.get("name") or NAME_MAP.get(code, code)) for code, p in portfolio.items()}
        return codes, names
    except Exception:
        return [], {}


def ai_share_text(low_qty: int, high_qty: int) -> str:
    low_qty = int(max(0, low_qty))
    high_qty = int(max(0, high_qty))
    if high_qty <= 0:
        return "不建議加碼"
    if low_qty <= 0:
        return f"最多 {high_qty} 股"
    if low_qty == high_qty:
        return f"{high_qty} 股"
    return f"{low_qty}～{high_qty} 股"


def ai_build_portfolio_context(code: str, name: str, metrics: Dict[str, Any], decision: Dict[str, Any], portfolio_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    code = normalize_code(code)
    p = portfolio_map.get(code)
    close = float(metrics.get("close") or 0)
    if not p or p.get("qty", 0) <= 0 or close <= 0:
        return {
            "has_position": False,
            "personal_summary": f"目前 {name}（{code}）沒有在你的持股中，本段只提供股票本身的技術與題材觀察。",
        }

    qty = float(p.get("qty") or 0)
    total_cost = float(p.get("total_cost") or 0)
    avg_cost = float(p.get("avg_cost") or (total_cost / qty if qty else 0))
    portfolio_total_cost = float(p.get("portfolio_total_cost") or total_cost or 0)
    weight_pct = (total_cost / portfolio_total_cost * 100) if portfolio_total_cost > 0 else 0.0
    market_value = close * qty
    unrealized = (close - avg_cost) * qty
    return_pct = ((close - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0
    distance_from_cost_pct = ((close - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0
    distance_from_cost_amount = close - avg_cost

    strategy = decision.get("strategy") or {}
    add_low = float(strategy.get("add_low") or close)
    add_high = float(strategy.get("add_high") or close)
    add_mid = (add_low + add_high) / 2 if add_low and add_high else close
    level = str(decision.get("level") or "hold")

    if level == "sell":
        add_high_qty = 0
    else:
        if weight_pct >= 45:
            budget_ratio = 0.030
            qty_ratio = 0.08 if level == "buy" else 0.04
        elif weight_pct >= 30:
            budget_ratio = 0.045
            qty_ratio = 0.12 if level == "buy" else 0.06
        else:
            budget_ratio = 0.070
            qty_ratio = 0.18 if level == "buy" else 0.09
        budget_qty = int((portfolio_total_cost * budget_ratio) / add_mid) if add_mid > 0 and portfolio_total_cost > 0 else 0
        ratio_qty = int(qty * qty_ratio)
        add_high_qty = max(1, min(max(1, ratio_qty), max(1, budget_qty))) if qty > 0 else 0
    add_low_qty = max(1, int(add_high_qty * 0.5)) if add_high_qty > 1 else add_high_qty

    add_qty_for_calc = add_high_qty
    if add_qty_for_calc > 0 and add_mid > 0:
        new_avg = (total_cost + add_mid * add_qty_for_calc) / (qty + add_qty_for_calc)
        new_total_cost = total_cost + add_mid * add_qty_for_calc
        add_cash = add_mid * add_qty_for_calc
    else:
        new_avg = avg_cost
        new_total_cost = total_cost
        add_cash = 0.0

    half_qty = int(qty // 2) if qty >= 2 else int(qty)
    sell_amount = close * half_qty
    est_fee_tax = sell_amount * (0.001425 + 0.003) if half_qty > 0 else 0.0
    half_sell_pnl = (close - avg_cost) * half_qty - est_fee_tax if half_qty > 0 else 0.0

    concentration = "偏高" if weight_pct >= 40 else "中高" if weight_pct >= 25 else "正常"
    add_qty_text = ai_share_text(add_low_qty, add_high_qty)

    if level == "sell":
        next_step = f"技術/題材訊號偏弱，這檔不建議加碼；若反彈到減碼區，可先賣出約一半（{half_qty:g} 股）觀察。"
    elif weight_pct >= 40:
        next_step = f"雖然策略允許加碼，但這檔佔投資成本 {weight_pct:.1f}% 已偏高，建議把加碼控制在 {add_qty_text}，避免單一持股過度集中。"
    elif return_pct < -8 and level != "buy":
        next_step = f"目前仍低於你的成本較多，若沒有站回加碼區上緣，不建議用大部位攤平；可等轉強再小量試單。"
    elif level == "buy":
        next_step = f"若隔日落在加碼區且量價沒有轉弱，可考慮 {add_qty_text} 分批買進。"
    else:
        next_step = f"目前較適合區間操作，若要試單以 {add_qty_text} 為上限，突破短線目標再提高部位。"

    personal_summary = (
        f"你目前持有 {qty:g} 股，成本均價 {avg_cost:,.2f}，目前報酬率 {return_pct:+.2f}%，"
        f"此股約佔投資成本 {weight_pct:.1f}%（部位{concentration}）。"
        f"現在價格距離你的成本 {distance_from_cost_amount:+,.2f} 元（{distance_from_cost_pct:+.2f}%）。"
        f"{next_step}"
    )
    if add_high_qty > 0:
        personal_summary += f" 若以加碼區中位價約 {add_mid:,.2f} 買 {add_high_qty:g} 股，買後均價約 {new_avg:,.2f}。"
    if half_qty > 0:
        personal_summary += f" 若以目前價位賣出一半約 {half_qty:g} 股，估計可實現損益約 {half_sell_pnl:+,.0f} 元（已粗估手續費與證交稅）。"

    return {
        "has_position": True,
        "qty": ai_round(qty, 4),
        "avg_cost": ai_round(avg_cost),
        "total_cost": ai_round(total_cost),
        "current_price": ai_round(close),
        "market_value": ai_round(market_value),
        "unrealized_pnl": ai_round(unrealized),
        "return_pct": ai_round(return_pct),
        "weight_pct": ai_round(weight_pct),
        "distance_from_cost_amount": ai_round(distance_from_cost_amount),
        "distance_from_cost_pct": ai_round(distance_from_cost_pct),
        "concentration": concentration,
        "add_qty_low": add_low_qty,
        "add_qty_high": add_high_qty,
        "add_qty_text": add_qty_text,
        "add_price_for_calc": ai_round(add_mid),
        "new_avg_if_add": ai_round(new_avg),
        "new_total_cost_if_add": ai_round(new_total_cost),
        "add_cash_needed": ai_round(add_cash),
        "half_sell_qty": half_qty,
        "half_sell_pnl": ai_round(half_sell_pnl),
        "personal_summary": personal_summary,
    }

def ai_technical_assessment(metrics: Dict[str, Any]) -> str:
    close = metrics.get("close") or 0
    ma5, ma20, ma60 = metrics.get("ma5"), metrics.get("ma20"), metrics.get("ma60")
    rsi = metrics.get("rsi14")
    support = metrics.get("support") or close
    resistance = metrics.get("resistance") or close
    parts: List[str] = []
    if ma5 and ma20 and ma60:
        if close > ma5 > ma20 > ma60:
            parts.append("短中期均線呈多頭排列，動能明顯偏強。")
        elif close < ma5 < ma20:
            parts.append("股價位於短中期均線下方，短線轉弱訊號較明顯。")
        elif close > ma20:
            parts.append("股價仍站在 MA20 之上，波段結構尚可。")
        else:
            parts.append("股價未能有效站上 MA20，波段仍偏整理或偏弱。")
    if rsi is not None:
        if rsi >= 75:
            parts.append("RSI 過熱，追價勝率下降，較適合等拉回。")
        elif rsi >= 60:
            parts.append("RSI 偏強，代表買盤仍有動能。")
        elif rsi <= 35:
            parts.append("RSI 偏低，有跌深反彈機會，但需先確認支撐。")
        else:
            parts.append("RSI 中性，尚未出現極端過熱或超跌。")
    parts.append(f"目前主要支撐約在 {ai_price_range_text(support, support)}，壓力約在 {ai_price_range_text(resistance, resistance)}。")
    return "".join(parts)


def ai_fundamental_assessment(code: str, name: str, cfg: Dict[str, Any], news: List[Dict[str, str]]) -> str:
    focus = cfg.get("focus") or []
    score = ai_news_score(news)
    tilt = "偏正向" if score > 0 else "偏負向" if score < 0 else "中性"
    focus_text = "、".join(focus[:5]) if focus else "財報、產業需求、法人動向、估值變化"
    if news:
        return f"基本面此版主要依近期新聞與題材脈絡評估，尚未直接讀取完整財報數字。{name} 的核心觀察為 {focus_text}；目前新聞語氣偏{tilt}。若後續營收、法說或法人動向能支持題材，股價較容易延續；若新聞熱度降溫或財報不支撐估值，則要提高減碼意識。"
    return f"目前新聞資料不足，基本面先以 {focus_text} 作為追蹤主軸；這種情況下不應只靠新聞追價，需以技術面區間和風險價位為主。"


def ai_decision(metrics: Dict[str, Any], news: List[Dict[str, str]] | None = None, cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:
    close = metrics.get("close") or 0
    ma5 = metrics.get("ma5")
    ma20 = metrics.get("ma20")
    ma60 = metrics.get("ma60")
    rsi = metrics.get("rsi14")
    change_pct = metrics.get("change_pct") or 0
    support = metrics.get("support") or close
    resistance = metrics.get("resistance") or close
    code = normalize_code(metrics.get("code") or (cfg or {}).get("code") or "")
    news = news or []
    reasons: List[str] = []
    tech_score = 0

    if ma5 and close > ma5:
        tech_score += 1; reasons.append("股價站上 MA5，短線買盤有延續。")
    elif ma5:
        tech_score -= 1; reasons.append("股價低於 MA5，短線動能轉弱。")
    if ma20 and close > ma20:
        tech_score += 2; reasons.append("股價站上 MA20，波段趨勢仍偏多。")
    elif ma20:
        tech_score -= 2; reasons.append("股價跌破 MA20，波段趨勢需要提高警覺。")
    if ma60 and close > ma60:
        tech_score += 1; reasons.append("股價仍高於 MA60，中期結構未明顯破壞。")
    elif ma60:
        tech_score -= 1; reasons.append("股價低於 MA60，中期趨勢偏弱。")

    if rsi is not None:
        if rsi >= 75:
            tech_score -= 2; reasons.append("RSI 高於 75，短線過熱，隔日不適合追太遠。")
        elif rsi >= 60:
            tech_score += 1; reasons.append("RSI 高於 60，動能偏強。")
        elif rsi <= 30:
            tech_score += 1; reasons.append("RSI 低於 30，有跌深反彈機會，但需確認止跌。")
        elif rsi <= 40:
            tech_score -= 1; reasons.append("RSI 偏弱，買盤尚未明顯回來。")

    if change_pct >= 3:
        reasons.append("單日漲幅較大，隔日若開高要避免一次追滿，優先等回落到可執行區間。")
    elif change_pct <= -3:
        reasons.append("單日跌幅較大，隔日若續弱跌破失守區，先減碼避免硬攤平。")

    fundamental_score = ai_news_score(news)
    total_score = tech_score + fundamental_score
    confidence = "高" if abs(total_score) >= 4 else "中" if abs(total_score) >= 2 else "低"

    close_f = float(close or 0)
    ma5_f = float(ma5 or close_f or 0)
    ma20_f = float(ma20 or close_f or 0)
    support_f = float(support or close_f or 0)
    resistance_f = float(resistance or close_f or 0)
    prev_low = float(metrics.get("prev_low") or metrics.get("recent_low_3") or support_f or close_f)
    prev_high = float(metrics.get("prev_high") or metrics.get("recent_high_3") or resistance_f or close_f)
    recent_low_3 = float(metrics.get("recent_low_3") or prev_low or support_f or close_f)
    recent_high_3 = float(metrics.get("recent_high_3") or prev_high or resistance_f or close_f)
    recent_low_5 = float(metrics.get("recent_low_5") or recent_low_3 or support_f or close_f)
    recent_high_5 = float(metrics.get("recent_high_5") or recent_high_3 or resistance_f or close_f)

    # 隔日操作區間應該貼近最近 1～5 日行情，而不是拿 20 日低點當加碼價。
    # 用 ATR14、近 5 日平均波動與今日漲跌幅估計「隔天比較可能摸到的價格帶」。
    is_etf = code.startswith("00")
    floor_pct = 0.45 if is_etf else 0.85
    cap_pct = 2.1 if is_etf else 4.2
    atr_pct = float(metrics.get("atr_pct") or 0)
    avg_abs_pct = float(metrics.get("avg_abs_change_pct5") or 0)
    suggested_pct = max(floor_pct, atr_pct * 0.85, avg_abs_pct * 1.15, abs(float(change_pct or 0)) * 0.45)
    band_pct = min(cap_pct, suggested_pct)
    band = max(close_f * band_pct / 100, ai_tick_size(close_f) * 2)

    overheat = (rsi is not None and rsi >= 72) or change_pct >= 3
    weak = total_score <= -2 or (ma20 and close_f < ma20_f and (rsi or 50) < 45)
    bullish = total_score >= 2 and not weak

    def clamp_next(low: float, high: float, extra_up: float = 1.0, extra_down: float = 1.0) -> Tuple[float, float]:
        max_down = close_f - band * extra_down
        max_up = close_f + band * extra_up
        low = max(0, low, max_down)
        high = min(high, max_up)
        if high < low:
            mid = max(0, (low + high) / 2)
            low = max(0, mid - band * 0.22)
            high = mid + band * 0.22
        return low, high

    if bullish:
        if overheat:
            add_low, add_high = clamp_next(close_f - band * 0.95, close_f - band * 0.30, extra_up=0.35, extra_down=1.20)
            reasons.append("雖然偏多，但短線偏熱，加碼區間改以隔日拉回價為主，不把加碼價設太遠。")
        else:
            base_low = max(recent_low_3, min(ma5_f, close_f) - band * 0.25)
            add_low, add_high = clamp_next(base_low, close_f + band * 0.18, extra_up=0.35, extra_down=0.85)
        trim_low, trim_high = clamp_next(max(prev_high * 0.995, close_f + band * 0.55), close_f + band * 1.25, extra_up=1.45, extra_down=0.05)
        stop_low, stop_high = clamp_next(min(recent_low_3, close_f - band * 1.05), close_f - band * 0.62, extra_up=0.05, extra_down=1.45)
        target_low, target_high = clamp_next(max(prev_high, close_f + band * 0.78), close_f + band * 1.65, extra_up=1.85, extra_down=0.05)
    elif weak:
        # 偏弱時「加碼」不代表攤平，而是隔日若收復關鍵價才小量試單。
        reclaim = max(ma5_f, close_f + band * 0.20)
        add_low, add_high = clamp_next(reclaim, reclaim + band * 0.45, extra_up=0.90, extra_down=0.05)
        trim_low, trim_high = clamp_next(close_f + band * 0.32, min(recent_high_3, close_f + band * 1.05), extra_up=1.20, extra_down=0.05)
        stop_low, stop_high = clamp_next(close_f - band * 0.95, min(recent_low_3, close_f - band * 0.45), extra_up=0.05, extra_down=1.25)
        target_low, target_high = clamp_next(close_f + band * 0.55, close_f + band * 1.15, extra_up=1.35, extra_down=0.05)
    else:
        add_low, add_high = clamp_next(max(recent_low_3, close_f - band * 0.72), close_f - band * 0.18, extra_up=0.05, extra_down=0.95)
        trim_low, trim_high = clamp_next(close_f + band * 0.52, min(recent_high_5, close_f + band * 1.15), extra_up=1.30, extra_down=0.05)
        stop_low, stop_high = clamp_next(close_f - band * 1.05, min(recent_low_3, close_f - band * 0.58), extra_up=0.05, extra_down=1.35)
        target_low, target_high = clamp_next(max(prev_high, close_f + band * 0.70), close_f + band * 1.35, extra_up=1.55, extra_down=0.05)

    if total_score >= 4:
        action = "積極分批加碼"
        level = "buy"
        summary = "技術面與題材面同時偏強，隔日可以大膽採取分批加碼；但加碼價改抓最近 1～5 日真實波動，不再等待過低價。若開盤落在隔日加碼區間且沒有爆量長黑，可優先買；衝到減碼區則分批停利。"
    elif total_score >= 2:
        action = "偏多續抱，拉回加碼"
        level = "buy"
        summary = "多方條件略占優勢，隔日策略以續抱為主，拉回到可成交的加碼區間可以分批加碼；若直接開高到減碼區，不追高，先做部分獲利了結。"
    elif total_score <= -4:
        action = "明確減碼 / 跌破失守區賣出"
        level = "sell"
        summary = "技術面與題材面同步偏弱，隔日不建議硬攤平。若反彈到減碼區先降部位；若跌入失守賣出區，建議果斷賣出控風險。"
    elif total_score <= -2:
        action = "偏弱，反彈減碼"
        level = "sell"
        summary = "目前風險大於機會，隔日若有反彈接近減碼區，建議降低部位；只有重新站回隔日加碼區上緣並放量，才考慮小量試單。"
    else:
        action = "區間操作，等突破再加碼"
        level = "hold"
        summary = "多空訊號不夠一致，隔日以區間操作為主。拉回加碼區可小量試單；突破短線目標區才加碼，跌入失守區則先退出。"

    # 操作計畫與具體建議必須一致：
    # 若目前/更新後價格已落入「可賣區間」或「失守賣出區間」，
    # 具體建議要直接改成賣出/減碼，不可以下方又說持續加碼。
    in_trim_zone = close_f >= float(trim_low or 0) if trim_low else False
    in_stop_zone = close_f <= float(stop_high or 0) if stop_high else False
    if close_f > 0 and in_stop_zone:
        action = "已跌入失守區，先賣出控風險"
        level = "sell"
        summary = (
            f"目前價格 {close_f:,.2f} 已落在失守賣出區間 {ai_price_range_text(stop_low, stop_high)} 內或更低，"
            "實際操作以停損/減碼優先，不建議加碼或攤平。除非重新站回 MA5/MA20 並放量轉強，否則先保留現金。"
        )
        reasons.insert(0, "目前價格已觸發失守賣出條件，優先順序高於所有加碼訊號。")
    elif close_f > 0 and in_trim_zone:
        action = "已達可賣區，先分批賣出"
        level = "sell"
        summary = (
            f"目前價格 {close_f:,.2f} 已進入隔日減碼/賣出區間 {ai_price_range_text(trim_low, trim_high)}，"
            "因此具體建議改為先分批賣出或至少減碼，不再建議加碼。若你仍想續抱，應等拉回重新落到加碼區且量價沒有轉弱後再考慮買回。"
        )
        reasons.insert(0, "目前價格已達可賣區間，操作計畫與具體建議同步改為賣出/減碼。")

    return {
        "action": action,
        "level": level,
        "summary": summary,
        "reasons": reasons[:7],
        "score": total_score,
        "technical_score": tech_score,
        "fundamental_score": fundamental_score,
        "strategy": {
            "confidence": confidence,
            "basis": f"以最近 1～5 日 OHLC、ATR14 與近 5 日平均波動估計隔日波動帶約 ±{band_pct:.2f}%",
            "add_range": ai_price_range_text(add_low, add_high),
            "trim_range": ai_price_range_text(trim_low, trim_high),
            "stop_range": ai_price_range_text(stop_low, stop_high),
            "target_range": ai_price_range_text(target_low, target_high),
            "add_low": ai_round(add_low),
            "add_high": ai_round(add_high),
            "trim_low": ai_round(trim_low),
            "trim_high": ai_round(trim_high),
            "stop_low": ai_round(stop_low),
            "stop_high": ai_round(stop_high),
            "target_low": ai_round(target_low),
            "target_high": ai_round(target_high),
        },
    }

def ai_fetch_news(code: str, name: str, keywords: str) -> Tuple[List[Dict[str, str]], str]:
    q = urllib.parse.quote(keywords)
    url = f"https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        raw = http_get_text(url, timeout=5)
        root = ET.fromstring(raw)
        items: List[Dict[str, str]] = []
        for item in root.findall(".//item")[:5]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or ""
            if title:
                items.append({"title": title, "link": link, "published": pub})
        return items, "Google News RSS"
    except Exception as e:
        return [], f"Google News RSS: {e}"


def ai_parse_codes(raw: str | None) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,|\s]+", str(raw))
    out: List[str] = []
    seen = set()
    for part in parts:
        code = normalize_code(part)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def ai_parse_names(raw: str | None) -> Dict[str, str]:
    names: Dict[str, str] = {}
    if not raw:
        return names
    for part in str(raw).split("|"):
        if not part.strip():
            continue
        if ":" in part:
            code, name = part.split(":", 1)
        elif "=" in part:
            code, name = part.split("=", 1)
        else:
            continue
        code = normalize_code(code)
        name = str(name or "").strip()
        if code and name:
            names[code] = name
    return names


def ai_codes_from_saved_state() -> Tuple[List[str], Dict[str, str]]:
    """Fallback for direct /api/analyze calls: derive current holdings from editable base holdings + records."""
    return ai_codes_from_portfolio_state()


def ai_build_config(code: str, names_map: Dict[str, str] | None = None) -> Dict[str, Any]:
    code = normalize_code(code)
    base = dict(AI_STOCKS.get(code, {}))
    base["code"] = code
    name = (names_map or {}).get(code) or base.get("name") or NAME_MAP.get(code) or code
    if code not in AI_STOCKS:
        base.update({
            "name": name,
            "keywords": f"{name} {code} 台股 股價 財報 法說會 外資 新聞",
            "focus": ["股價趨勢", "成交量", "法人動向", "產業新聞"],
        })
    else:
        base["name"] = name
        base["keywords"] = str(base.get("keywords") or f"{name} {code} 台股 股價 新聞")
    return base


def ai_analyze_one(code: str, target: date, force_refresh: bool = False, names_map: Dict[str, str] | None = None, portfolio_map: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    code = normalize_code(code)
    cfg = ai_build_config(code, names_map)
    name = cfg.get("name") or NAME_MAP.get(code, code)
    rows, source = ai_fetch_yahoo_history(code, target, force_refresh)
    if not rows:
        rows, source = ai_fetch_finmind_history(code, target, force_refresh)
    if not rows:
        return {"status": "error", "code": code, "name": name, "message": source or "抓不到歷史資料"}
    usable = [r for r in rows if r.get("date") and r["date"] <= target.isoformat()]
    if not usable:
        usable = rows
    row = usable[-1]
    actual_date = row["date"]
    closes = [float(r["close"]) for r in usable if ai_clean_number(r.get("close")) is not None]
    prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
    close = float(row["close"])
    change = close - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0
    recent_rows = usable[-20:]
    lows = [ai_clean_number(r.get("low")) or ai_clean_number(r.get("close")) or 0 for r in recent_rows]
    highs = [ai_clean_number(r.get("high")) or ai_clean_number(r.get("close")) or 0 for r in recent_rows]
    lows3 = [ai_clean_number(r.get("low")) or ai_clean_number(r.get("close")) or 0 for r in usable[-3:]]
    highs3 = [ai_clean_number(r.get("high")) or ai_clean_number(r.get("close")) or 0 for r in usable[-3:]]
    lows5 = [ai_clean_number(r.get("low")) or ai_clean_number(r.get("close")) or 0 for r in usable[-5:]]
    highs5 = [ai_clean_number(r.get("high")) or ai_clean_number(r.get("close")) or 0 for r in usable[-5:]]
    ma5 = ai_sma(closes, 5)
    ma20 = ai_sma(closes, 20)
    ma60 = ai_sma(closes, 60)
    rsi = ai_rsi(closes, 14)
    atr14 = ai_atr(usable, 14)
    atr_pct = (atr14 / close * 100) if atr14 and close else None
    avg_abs_pct5 = ai_avg_abs_change_pct(closes, 5)
    support = min([x for x in lows5 if x > 0], default=min([x for x in lows if x > 0], default=close))
    resistance = max([x for x in highs5 if x > 0], default=max([x for x in highs if x > 0], default=close))
    trend = "上漲" if change_pct > 0.2 else "下跌" if change_pct < -0.2 else "平盤附近"
    metrics = {
        "code": code,
        "close": ai_round(close),
        "open": ai_round(row.get("open")),
        "high": ai_round(row.get("high")),
        "low": ai_round(row.get("low")),
        "prev_high": ai_round(row.get("high")),
        "prev_low": ai_round(row.get("low")),
        "volume": int(row.get("volume") or 0),
        "change": ai_round(change),
        "change_pct": ai_round(change_pct),
        "trend": trend,
        "ma5": ai_round(ma5),
        "ma20": ai_round(ma20),
        "ma60": ai_round(ma60),
        "rsi14": ai_round(rsi),
        "support": ai_round(support),
        "resistance": ai_round(resistance),
        "recent_low_3": ai_round(min([x for x in lows3 if x > 0], default=close)),
        "recent_high_3": ai_round(max([x for x in highs3 if x > 0], default=close)),
        "recent_low_5": ai_round(min([x for x in lows5 if x > 0], default=close)),
        "recent_high_5": ai_round(max([x for x in highs5 if x > 0], default=close)),
        "atr14": ai_round(atr14),
        "atr_pct": ai_round(atr_pct),
        "avg_abs_change_pct5": ai_round(avg_abs_pct5),
    }
    news, news_source = ai_fetch_news(code, name, str(cfg.get("keywords") or f"{name} {code} 股價"))
    decision = ai_decision(metrics, news, cfg)
    portfolio_context = ai_build_portfolio_context(code, name, metrics, decision, portfolio_map or {})
    focus_list = cfg.get("focus") or []
    focus = "、".join(focus_list)
    news_context = ai_summarize_news_context(code, name, news, focus_list)
    technical_assessment = ai_technical_assessment(metrics)
    fundamental_assessment = ai_fundamental_assessment(code, name, cfg, news)
    explanation = f"隔日操作價位已改用最近 1～5 日真實高低點、ATR14 與近 5 日平均波動估算，較適合隔天開盤到盤中執行；接下來可搭配量能、外資動向與{focus or '相關題材'}確認。"
    return {
        "status": "ok",
        "code": code,
        "name": name,
        "actual_date": actual_date,
        "is_exact_date": actual_date == target.isoformat(),
        "source": source,
        "news_source": news_source,
        "metrics": metrics,
        "decision": decision,
        "portfolio_context": portfolio_context,
        "personalized_advice": portfolio_context.get("personal_summary", ""),
        "technical_assessment": technical_assessment,
        "fundamental_assessment": fundamental_assessment,
        "news_context": news_context,
        "explanation": explanation,
        "news": news,
    }




def ai_build_tomorrow_plan(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for s in stocks or []:
        if not isinstance(s, dict) or s.get("status") != "ok":
            continue
        d = s.get("decision") or {}
        strategy = d.get("strategy") or {}
        p = s.get("portfolio_context") or {}
        qty_text = p.get("add_qty_text") or "—"
        if d.get("level") == "sell":
            half_qty = p.get("half_sell_qty") or 0
            qty_text = f"不加碼；反彈可先賣 {half_qty:g} 股" if half_qty else "不加碼"
        is_sell_action = d.get("level") == "sell"
        plan.append({
            "code": s.get("code"),
            "name": s.get("name"),
            "action": d.get("action") or "觀望",
            "buy_range": "不加碼" if is_sell_action else (strategy.get("add_range") or "—"),
            "sell_range": strategy.get("trim_range") or "—",
            "stop_range": strategy.get("stop_range") or "—",
            "suggest_qty": qty_text,
            "weight_pct": (p or {}).get("weight_pct"),
            "current_price": (s.get("metrics") or {}).get("close"),
        })
    return plan

def get_ai_analysis(query_date: str | None, force_refresh: bool = False, codes: List[str] | None = None, names_map: Dict[str, str] | None = None) -> Dict[str, Any]:
    target = ai_parse_date(query_date)
    names_map = names_map or {}
    dynamic_codes = [normalize_code(c) for c in (codes or []) if normalize_code(c)]
    if not dynamic_codes:
        dynamic_codes, saved_names = ai_codes_from_saved_state()
        names_map = {**saved_names, **names_map}
    if not dynamic_codes:
        dynamic_codes = list(AI_STOCKS.keys())

    seen = set()
    final_codes: List[str] = []
    for code in dynamic_codes:
        if code and code not in seen:
            seen.add(code)
            final_codes.append(code)

    portfolio_map = ai_portfolio_from_saved_state()
    for _code, _p in portfolio_map.items():
        if _p.get("name"):
            names_map.setdefault(_code, str(_p.get("name")))
    stocks: List[Dict[str, Any]] = []
    # 逐檔抓資料改成平行處理，避免某個資料源逾時拖慢整個頁面。
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(6, max(1, len(final_codes)))) as executor:
        future_map = {executor.submit(ai_analyze_one, code, target, force_refresh, names_map, portfolio_map): code for code in final_codes}
        for future in concurrent.futures.as_completed(future_map, timeout=45):
            code = future_map[future]
            try:
                stocks.append(future.result())
            except Exception as e:
                cfg = ai_build_config(code, names_map)
                stocks.append({"status": "error", "code": code, "name": cfg.get("name", code), "message": str(e)})
    order = {code: i for i, code in enumerate(final_codes)}
    stocks.sort(key=lambda s: order.get(str(s.get("code", "")), 999))
    return {
        "ok": True,
        "version": APP_VERSION,
        "query_date": target.isoformat(),
        "updated_at": now_tw_text(),
        "requested_codes": final_codes,
        "tomorrow_plan": ai_build_tomorrow_plan(stocks),
        "stocks": stocks,
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

        if path == "/api/analyze":
            try:
                query_date = qs.get("date", [""])[0]
                force = qs.get("refresh", ["0"])[0] in {"1", "true", "yes"}
                codes = ai_parse_codes(qs.get("codes", [""])[0])
                names_map = ai_parse_names(qs.get("names", [""])[0])
                data = get_ai_analysis(query_date, force, codes, names_map)
                return self._send_json(data)
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e), "updated_at": now_tw_text()}, 502)

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
