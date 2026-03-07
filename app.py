import os
import re
import anthropic
import markdown
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, session

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "onspot-secret-2026")

ROOT_DIR = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PROMPT_TEMPLATE = """\
You are a world-class B2B sales research analyst working for OnSpot, an elite account intelligence platform built for tech sales professionals. Given a company name, produce a comprehensive pre-call intelligence brief.

Company: {company_name}

Generate a detailed brief with these sections, using markdown formatting:

## 1. Company Overview
What they do, approximate size (employees/revenue), industry, HQ location, key business segments.

## 2. Recent News & Developments
Key events from the last 6 months: acquisitions, product launches, earnings, leadership changes, strategic pivots.

## 3. Likely Tech Stack & Infrastructure
What technologies they probably use internally and what they sell/build. Include categories like cloud, CRM, data, DevOps, security.

## 4. Key Business Challenges / Pain Points
Their biggest strategic, operational, and financial challenges right now.

## 5. Potential Decision Makers
Job titles to target depending on what you're selling, organized by function (IT, Sales, Marketing, Finance, etc).

## 6. Suggested Talking Points & Opening Angle
Specific conversation starters, email subject lines, and approaches tailored to this company's current situation.

## 7. Red Flags or Risks
Sales cycle warnings, procurement complexity, build-vs-buy tendencies, budget constraints, competitive vendor relationships.

Be specific, data-driven, and actionable. Write for a tech sales professional who needs to sound informed on a call tomorrow.
"""

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnSpot — Account Intelligence</title>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg: #080910;
            --bg-panel: #0d0e14;
            --bg-card: #111318;
            --bg-hover: #161820;
            --bg-input: #0a0b10;
            --border: rgba(255,255,255,0.06);
            --border-active: rgba(99,102,241,0.4);
            --text-primary: #eceef5;
            --text-secondary: #7b7f96;
            --text-muted: #3d4057;
            --accent: #6366f1;
            --accent-dim: rgba(99,102,241,0.12);
            --accent-glow: rgba(99,102,241,0.25);
            --green: #22d3a0;
            --green-dim: rgba(34,211,160,0.1);
            --sidebar-width: 280px;
        }

        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* ===== SIDEBAR ===== */
        .sidebar {
            width: var(--sidebar-width);
            min-width: var(--sidebar-width);
            height: 100vh;
            background: var(--bg-panel);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .sidebar-logo {
            padding: 24px 20px 20px;
            border-bottom: 1px solid var(--border);
        }

        .logo-mark {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 4px;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #6366f1, #818cf8);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 800;
            color: white;
            font-family: 'Syne', sans-serif;
            flex-shrink: 0;
        }

        .logo-text {
            font-family: 'Syne', sans-serif;
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, #eceef5, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .logo-tag {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding-left: 42px;
        }

        .sidebar-status {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 12px 20px;
            border-bottom: 1px solid var(--border);
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 8px var(--green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .status-text {
            font-family: 'DM Mono', monospace;
            font-size: 11px;
            color: var(--green);
            letter-spacing: 1px;
        }

        .sidebar-section {
            padding: 16px 20px 8px;
        }

        .sidebar-section-label {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .new-brief-btn {
            width: 100%;
            padding: 10px 14px;
            background: var(--accent-dim);
            border: 1px solid var(--border-active);
            border-radius: 8px;
            color: #818cf8;
            font-family: 'DM Sans', sans-serif;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .new-brief-btn:hover {
            background: rgba(99,102,241,0.2);
            transform: translateY(-1px);
        }

        .history-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px 12px;
        }

        .history-list::-webkit-scrollbar { width: 3px; }
        .history-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

        .history-item {
            padding: 10px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s;
            margin-bottom: 2px;
            border: 1px solid transparent;
        }

        .history-item:hover { background: var(--bg-hover); border-color: var(--border); }
        .history-item.active { background: var(--accent-dim); border-color: var(--border-active); }

        .history-company {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: 3px;
        }

        .history-item.active .history-company { color: #818cf8; }

        .history-time {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
        }

        .history-empty {
            padding: 20px 10px;
            font-size: 12px;
            color: var(--text-muted);
            text-align: center;
            line-height: 1.6;
        }

        .sidebar-footer {
            padding: 16px 20px;
            border-top: 1px solid var(--border);
        }

        .sidebar-footer p {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
        }

        /* ===== MAIN ===== */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        .topbar {
            height: 56px;
            min-height: 56px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 28px;
            background: var(--bg-panel);
        }

        .topbar-title {
            font-family: 'Syne', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .topbar-title .sep { color: var(--text-muted); }
        .topbar-title .current { color: var(--text-primary); }

        .logout-btn {
            padding: 6px 14px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-secondary);
            font-family: 'DM Sans', sans-serif;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .logout-btn:hover { border-color: var(--border-active); color: var(--text-primary); }

        .content {
            flex: 1;
            overflow-y: auto;
            padding: 32px 36px;
        }

        .content::-webkit-scrollbar { width: 4px; }
        .content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

        /* ===== SEARCH VIEW ===== */
        .search-view { max-width: 640px; margin: 60px auto 0; }

        .search-hero { text-align: center; margin-bottom: 40px; }

        .search-hero h1 {
            font-family: 'Syne', sans-serif;
            font-size: 42px;
            font-weight: 800;
            letter-spacing: -1.5px;
            line-height: 1.1;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #eceef5 0%, #6366f1 60%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .search-hero p {
            font-size: 15px;
            color: var(--text-secondary);
            font-weight: 300;
            line-height: 1.6;
        }

        .search-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            transition: border-color 0.2s, box-shadow 0.2s;
            margin-bottom: 24px;
        }

        .search-box:focus-within {
            border-color: var(--border-active);
            box-shadow: 0 0 0 4px var(--accent-dim);
        }

        .search-label {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 10px;
            display: block;
        }

        .search-row { display: flex; gap: 10px; }

        .search-input {
            flex: 1;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            color: var(--text-primary);
            outline: none;
            transition: border-color 0.2s;
        }

        .search-input::placeholder { color: var(--text-muted); }
        .search-input:focus { border-color: var(--accent); }

        .search-btn {
            padding: 12px 24px;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 8px;
            font-family: 'Syne', sans-serif;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
            letter-spacing: 0.5px;
        }

        .search-btn:hover { background: #818cf8; transform: translateY(-1px); box-shadow: 0 4px 20px var(--accent-glow); }
        .search-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

        .quick-searches { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }

        .quick-chip {
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 100px;
            font-size: 13px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .quick-chip:hover { background: var(--accent-dim); border-color: var(--border-active); color: #818cf8; }

        /* ===== LOADING ===== */
        .loading-view { display: none; max-width: 640px; margin: 80px auto 0; }
        .loading-view.active { display: block; }

        .loading-title {
            font-family: 'Syne', sans-serif;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 24px;
            color: var(--text-primary);
        }

        .stage {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 13px;
            color: var(--text-muted);
            transition: all 0.3s;
        }

        .stage.active { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); }
        .stage.done { color: var(--green); }

        .stage-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            flex-shrink: 0;
            transition: all 0.3s;
        }

        .stage.active .stage-icon { border-color: var(--accent); border-top-color: transparent; animation: spin 0.8s linear infinite; }
        .stage.done .stage-icon { background: var(--green); border-color: var(--green); color: #080910; animation: none; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ===== BRIEF VIEW ===== */
        .brief-view { display: none; }
        .brief-view.active { display: block; }

        .brief-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }

        .brief-company-info h2 {
            font-family: 'Syne', sans-serif;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }

        .brief-meta { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }

        .meta-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            font-family: 'DM Mono', monospace;
            font-size: 11px;
            color: var(--text-muted);
        }

        .meta-badge .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--green); }

        .action-btn {
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-secondary);
            font-family: 'DM Sans', sans-serif;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }

        .action-btn:hover { border-color: var(--border-active); color: var(--text-primary); }

        .brief-sections { display: grid; gap: 16px; }

        .brief-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: border-color 0.2s;
        }

        .brief-section:hover { border-color: rgba(255,255,255,0.1); }

        .section-header {
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.02);
        }

        .section-num {
            font-family: 'DM Mono', monospace;
            font-size: 10px;
            color: var(--accent);
            letter-spacing: 1px;
            background: var(--accent-dim);
            padding: 2px 7px;
            border-radius: 4px;
        }

        .section-title {
            font-family: 'Syne', sans-serif;
            font-size: 13px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .section-body { padding: 20px; }
        .section-body p { font-size: 14px; color: var(--text-secondary); line-height: 1.75; margin-bottom: 12px; }
        .section-body p:last-child { margin-bottom: 0; }
        .section-body strong { color: var(--text-primary); font-weight: 600; }
        .section-body ul, .section-body ol { padding-left: 20px; margin-bottom: 12px; }
        .section-body li { font-size: 14px; color: var(--text-secondary); line-height: 1.7; margin-bottom: 6px; }
        .section-body h3 { font-family: 'Syne', sans-serif; font-size: 13px; font-weight: 700; color: var(--text-primary); margin-top: 16px; margin-bottom: 8px; }
        .section-body blockquote { border-left: 3px solid var(--accent); padding: 10px 16px; background: var(--accent-dim); border-radius: 0 6px 6px 0; margin: 12px 0; }
        .section-body blockquote p { color: var(--text-primary); margin-bottom: 0; }
        .section-body code { font-family: 'DM Mono', monospace; background: var(--bg-input); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #818cf8; }
        .section-body table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 12px 0; }
        .section-body th { background: var(--bg-input); color: var(--text-primary); font-weight: 600; text-align: left; padding: 8px 12px; border: 1px solid var(--border); }
        .section-body td { padding: 8px 12px; border: 1px solid var(--border); color: var(--text-secondary); }

        /* ===== ERROR ===== */
        .error-view { display: none; background: rgba(244,63,94,0.08); border: 1px solid rgba(244,63,94,0.2); border-radius: 10px; padding: 16px 20px; color: #fda4af; font-size: 13px; max-width: 640px; margin: 0 auto 16px; }
        .error-view.active { display: block; }
        .error-view strong { color: #f43f5e; }

        @media (max-width: 768px) {
            .sidebar { display: none; }
            .content { padding: 20px 16px; }
            .brief-header { flex-direction: column; gap: 16px; }
        }
    </style>
</head>
<body>
    <aside class="sidebar">
        <div class="sidebar-logo">
            <div class="logo-mark">
                <div class="logo-icon">O</div>
                <span class="logo-text">OnSpot</span>
            </div>
            <div class="logo-tag">Account Intelligence</div>
        </div>
        <div class="sidebar-status">
            <div class="status-dot"></div>
            <span class="status-text">SYSTEM ONLINE</span>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-section-label">Actions</div>
            <button class="new-brief-btn" onclick="showSearch()">
                <span>+</span> Research a Company
            </button>
        </div>
        <div class="sidebar-section">
            <div class="sidebar-section-label">Recent Briefs</div>
        </div>
        <div class="history-list" id="historyList">
            <div class="history-empty" id="historyEmpty">No briefs yet.<br>Search a company to get started.</div>
        </div>
        <div class="sidebar-footer">
            <p>OnSpot v1.0 &mdash; Built by Sid Lockhart</p>
        </div>
    </aside>

    <main class="main">
        <div class="topbar">
            <div class="topbar-title">
                <span>OnSpot</span>
                <span class="sep">/</span>
                <span class="current" id="topbarTitle">New Brief</span>
            </div>
            <button class="logout-btn" onclick="window.location.href='/logout'">Logout</button>
        </div>

        <div class="content">
            <div class="error-view" id="errorView"></div>

            <div class="search-view" id="searchView">
                <div class="search-hero">
                    <h1>Who are you<br>calling today?</h1>
                    <p>Get a full intelligence brief on any company<br>in under 60 seconds.</p>
                </div>
                <div class="search-box">
                    <label class="search-label">Target Company</label>
                    <div class="search-row">
                        <input type="text" class="search-input" id="companyInput" placeholder="e.g. Salesforce, CrowdStrike, HubSpot..." autocomplete="off" />
                        <button class="search-btn" id="generateBtn" onclick="generateBrief()">Run Brief</button>
                    </div>
                </div>
                <div class="quick-searches">
                    <div class="quick-chip" onclick="quickSearch('Salesforce')">Salesforce</div>
                    <div class="quick-chip" onclick="quickSearch('CrowdStrike')">CrowdStrike</div>
                    <div class="quick-chip" onclick="quickSearch('HubSpot')">HubSpot</div>
                    <div class="quick-chip" onclick="quickSearch('Snowflake')">Snowflake</div>
                    <div class="quick-chip" onclick="quickSearch('Datadog')">Datadog</div>
                    <div class="quick-chip" onclick="quickSearch('Okta')">Okta</div>
                </div>
            </div>

            <div class="loading-view" id="loadingView">
                <div class="loading-title" id="loadingCompany">Building brief...</div>
                <div class="stage active" id="stage1"><div class="stage-icon"></div><span>Researching company profile...</span></div>
                <div class="stage" id="stage2"><div class="stage-icon"></div><span>Analyzing tech stack & infrastructure...</span></div>
                <div class="stage" id="stage3"><div class="stage-icon"></div><span>Identifying decision makers...</span></div>
                <div class="stage" id="stage4"><div class="stage-icon"></div><span>Building talking points & strategy...</span></div>
                <div class="stage" id="stage5"><div class="stage-icon"></div><span>Finalizing intelligence brief...</span></div>
            </div>

            <div class="brief-view" id="briefView">
                <div class="brief-header">
                    <div class="brief-company-info">
                        <h2 id="briefCompanyName"></h2>
                        <div class="brief-meta">
                            <span class="meta-badge"><span class="dot"></span> Brief Complete</span>
                            <span class="meta-badge" id="briefTimestamp"></span>
                        </div>
                    </div>
                    <button class="action-btn" onclick="showSearch()">+ New Brief</button>
                </div>
                <div class="brief-sections" id="briefSections"></div>
            </div>
        </div>
    </main>

    <script>
        const briefHistory = [];
        let stageInterval = null;

        const searchView = document.getElementById('searchView');
        const loadingView = document.getElementById('loadingView');
        const errorView = document.getElementById('errorView');
        const briefView = document.getElementById('briefView');
        const companyInput = document.getElementById('companyInput');
        const generateBtn = document.getElementById('generateBtn');
        const topbarTitle = document.getElementById('topbarTitle');

        companyInput.addEventListener('keydown', e => { if (e.key === 'Enter') generateBrief(); });

        function hideAll() {
            searchView.style.display = 'none';
            loadingView.classList.remove('active');
            briefView.classList.remove('active');
            errorView.classList.remove('active');
        }

        function showSearch() {
            hideAll();
            searchView.style.display = 'block';
            topbarTitle.textContent = 'New Brief';
            document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
            companyInput.focus();
        }

        function quickSearch(company) {
            companyInput.value = company;
            generateBrief();
        }

        function startStages(company) {
            const stages = ['stage1','stage2','stage3','stage4','stage5'];
            stages.forEach(id => {
                const el = document.getElementById(id);
                el.classList.remove('active','done');
                el.querySelector('.stage-icon').textContent = '';
            });
            document.getElementById('stage1').classList.add('active');
            document.getElementById('loadingCompany').textContent = 'Building brief for ' + company + '...';
            let current = 0;
            stageInterval = setInterval(() => {
                if (current < stages.length - 1) {
                    const cur = document.getElementById(stages[current]);
                    cur.classList.remove('active');
                    cur.classList.add('done');
                    cur.querySelector('.stage-icon').textContent = '✓';
                    current++;
                    document.getElementById(stages[current]).classList.add('active');
                }
            }, 11000);
        }

        function stopStages() {
            if (stageInterval) { clearInterval(stageInterval); stageInterval = null; }
        }

        async function generateBrief() {
            const company = companyInput.value.trim();
            if (!company) { companyInput.focus(); return; }

            generateBtn.disabled = true;
            generateBtn.textContent = 'Running...';
            hideAll();
            loadingView.classList.add('active');
            topbarTitle.textContent = company;
            startStages(company);

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company })
                });
                const data = await response.json();
                stopStages();

                if (data.success) {
                    addToHistory(company, data.timestamp, data.html);
                    showBrief(company, data.timestamp, data.html);
                } else {
                    hideAll();
                    searchView.style.display = 'block';
                    errorView.innerHTML = '<strong>Error:</strong> ' + data.error;
                    errorView.classList.add('active');
                }
            } catch (err) {
                stopStages();
                hideAll();
                searchView.style.display = 'block';
                errorView.innerHTML = '<strong>Connection error:</strong> ' + err.message;
                errorView.classList.add('active');
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = 'Run Brief';
            }
        }

        function parseSections(html) {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const sections = [];
            const labels = ['Company Overview','Recent News & Developments','Tech Stack & Infrastructure','Business Challenges','Decision Makers','Talking Points & Strategy','Red Flags & Risks'];
            const h2s = doc.querySelectorAll('h2');
            h2s.forEach((h2, idx) => {
                let content = '';
                let sib = h2.nextElementSibling;
                while (sib && sib.tagName !== 'H2') { content += sib.outerHTML; sib = sib.nextElementSibling; }
                sections.push({ num: String(idx+1).padStart(2,'0'), title: labels[idx] || h2.textContent.replace(/^\d+\.\s*/,''), content });
            });
            if (!sections.length) sections.push({ num: '01', title: 'Intelligence Brief', content: html });
            return sections;
        }

        function showBrief(company, timestamp, html) {
            hideAll();
            briefView.classList.add('active');
            topbarTitle.textContent = company;
            document.getElementById('briefCompanyName').textContent = company;
            document.getElementById('briefTimestamp').textContent = timestamp;
            const container = document.getElementById('briefSections');
            container.innerHTML = '';
            parseSections(html).forEach(sec => {
                const div = document.createElement('div');
                div.className = 'brief-section';
                div.innerHTML = `<div class="section-header"><span class="section-num">${sec.num}</span><span class="section-title">${sec.title}</span></div><div class="section-body">${sec.content}</div>`;
                container.appendChild(div);
            });
        }

        function addToHistory(company, timestamp, html) {
            briefHistory.unshift({ company, timestamp, html });
            const empty = document.getElementById('historyEmpty');
            if (empty) empty.style.display = 'none';
            const list = document.getElementById('historyList');
            document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
            const div = document.createElement('div');
            div.className = 'history-item active';
            div.innerHTML = `<div class="history-company">${company}</div><div class="history-time">${timestamp}</div>`;
            div.addEventListener('click', () => {
                document.querySelectorAll('.history-item').forEach(i => i.classList.remove('active'));
                div.classList.add('active');
                showBrief(company, timestamp, html);
            });
            list.insertBefore(div, list.firstChild);
        }

        showSearch();
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnSpot — Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'DM Sans', sans-serif; background: #080910; color: #eceef5; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .box { width: 100%; max-width: 380px; padding: 40px; background: #0d0e14; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; }
        .logo { text-align: center; margin-bottom: 32px; }
        .logo-icon { width: 48px; height: 48px; background: linear-gradient(135deg, #6366f1, #818cf8); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800; color: white; margin: 0 auto 12px; }
        .logo h1 { font-family: 'Syne', sans-serif; font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #eceef5, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .logo p { font-size: 13px; color: #7b7f96; margin-top: 4px; }
        label { display: block; font-size: 11px; color: #3d4057; letter-spacing: 1.5px; text-transform: uppercase; font-family: monospace; margin-bottom: 8px; }
        input { width: 100%; padding: 12px 16px; background: #0a0b10; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; color: #eceef5; font-size: 15px; font-family: 'DM Sans', sans-serif; outline: none; margin-bottom: 16px; transition: border-color 0.2s; }
        input:focus { border-color: rgba(99,102,241,0.4); }
        button { width: 100%; padding: 12px; background: #6366f1; color: white; border: none; border-radius: 8px; font-family: 'Syne', sans-serif; font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
        button:hover { background: #818cf8; transform: translateY(-1px); }
        .error { background: rgba(244,63,94,0.08); border: 1px solid rgba(244,63,94,0.2); border-radius: 8px; padding: 10px 14px; color: #fda4af; font-size: 13px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="box">
        <div class="logo">
            <div class="logo-icon">O</div>
            <h1>OnSpot</h1>
            <p>Account Intelligence Platform</p>
        </div>
        {% if error %}<div class="error">Incorrect password. Try again.</div>{% endif %}
        <form method="POST" action="/login">
            <label>Access Password</label>
            <input type="password" name="password" placeholder="Enter password..." autofocus />
            <button type="submit">Enter OnSpot</button>
        </form>
    </div>
</body>
</html>
"""

PASSWORD = "onspot2026"

@app.route("/")
def index():
    if not session.get("authenticated"):
        return render_template_string(LOGIN_TEMPLATE, error=False)
    return render_template_string(HTML_TEMPLATE)

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("password") == PASSWORD:
        session["authenticated"] = True
        return render_template_string(HTML_TEMPLATE)
    return render_template_string(LOGIN_TEMPLATE, error=True)

@app.route("/logout")
def logout():
    session.clear()
    return render_template_string(LOGIN_TEMPLATE, error=False)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Not authenticated."})

    data = request.get_json()
    company_name = data.get("company", "").strip()

    if not company_name:
        return jsonify({"success": False, "error": "Please enter a company name."})

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not found."})

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(company_name=company_name)}],
        )

        brief_text = response.content[0].text
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", company_name.replace(" ", "_"))
        filename = f"{safe_name}_brief.md"
        filepath = OUTPUT_DIR / filename
        filepath.write_text(f"\n\n\n" + brief_text, encoding="utf-8")

        html = markdown.markdown(brief_text, extensions=["tables", "fenced_code", "nl2br"])

        return jsonify({"success": True, "html": html, "timestamp": timestamp, "filename": filename})

    except anthropic.AuthenticationError:
        return jsonify({"success": False, "error": "Invalid API key."})
    except anthropic.RateLimitError:
        return jsonify({"success": False, "error": "Rate limited. Wait a moment and try again."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  ONSPOT — Account Intelligence")
    print("  Open: http://127.0.0.1:5000")
    print("  Password: onspot2026")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)