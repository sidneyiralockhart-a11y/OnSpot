import os
import re
from datetime import datetime
from pathlib import Path

import anthropic
import markdown
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, session

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "onspot-default-secret-key-change-me")

# Set your password here, or use the APP_PASSWORD environment variable
APP_PASSWORD = os.environ.get("APP_PASSWORD", "onspot2026")

ROOT_DIR = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PROMPT_TEMPLATE = """\
You are a world-class B2B sales research analyst. Given a company name, produce a comprehensive pre-call intelligence brief.

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

Be specific, data-driven, and actionable. Write for a sales professional who needs to sound informed on a call tomorrow.
"""

LOGIN_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnSpot</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a0b0f">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0b0f;
            --bg-card: #161722;
            --bg-input: #1a1b2e;
            --border: #2a2b3d;
            --border-focus: #6366f1;
            --text-primary: #e2e4f0;
            --text-muted: #5a5e73;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.15);
            --accent-hover: #818cf8;
            --error: #f87171;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .bg-grid {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background-image: linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px);
            background-size: 60px 60px; pointer-events: none;
        }
        .bg-glow {
            position: fixed; top: -200px; left: 50%; transform: translateX(-50%);
            width: 800px; height: 600px;
            background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%);
            pointer-events: none;
        }
        .login-card {
            position: relative; z-index: 1;
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 20px; padding: 48px 40px;
            width: 100%; max-width: 420px; margin: 20px; text-align: center;
        }
        .login-card h1 {
            font-size: 36px; font-weight: 800; letter-spacing: -1px; margin-bottom: 8px;
            background: linear-gradient(135deg, #e2e4f0 0%, #6366f1 50%, #818cf8 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        .subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: 36px; font-weight: 300; }
        .input-label {
            font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted);
            letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 10px; display: block; text-align: left;
        }
        .login-input {
            width: 100%; background: var(--bg-input); border: 1px solid var(--border);
            border-radius: 10px; padding: 14px 18px; font-family: 'Outfit', sans-serif;
            font-size: 16px; color: var(--text-primary); outline: none; transition: all 0.3s;
            margin-bottom: 20px; text-align: center; letter-spacing: 2px;
        }
        .login-input::placeholder { color: var(--text-muted); letter-spacing: 0; }
        .login-input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-glow); }
        .login-btn {
            width: 100%; padding: 14px; background: var(--accent); color: white; border: none;
            border-radius: 10px; font-family: 'Outfit', sans-serif; font-size: 15px;
            font-weight: 600; cursor: pointer; transition: all 0.3s;
        }
        .login-btn:hover { background: var(--accent-hover); transform: translateY(-1px); box-shadow: 0 4px 20px rgba(99,102,241,0.3); }
        .error-msg { color: var(--error); font-size: 13px; margin-top: 16px; display: none; }
        .error-msg.active { display: block; }
        .lock-icon { font-size: 40px; margin-bottom: 16px; opacity: 0.6; }
    </style>
</head>
<body>
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    <div class="login-card">
        <div class="lock-icon">&#128274;</div>
        <h1>OnSpot</h1>
        <p class="subtitle">Enter access code to continue</p>
        <label class="input-label">Access Code</label>
        <input type="password" class="login-input" id="passwordInput" placeholder="Enter password" autocomplete="off" />
        <button class="login-btn" onclick="doLogin()">Unlock</button>
        <div class="error-msg" id="errorMsg">Incorrect access code. Try again.</div>
    </div>
    <script>
        document.getElementById('passwordInput').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
        async function doLogin() {
            const pw = document.getElementById('passwordInput').value.trim();
            if (!pw) return;
            const res = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: pw }) });
            const data = await res.json();
            if (data.success) { window.location.href = '/app'; }
            else { document.getElementById('errorMsg').classList.add('active'); document.getElementById('passwordInput').value = ''; }
        }
    </script>
</body>
</html>
"""

APP_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnSpot</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a0b0f">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0b0f; --bg-card: #161722; --bg-input: #1a1b2e;
            --border: #2a2b3d; --border-focus: #6366f1;
            --text-primary: #e2e4f0; --text-secondary: #8b8fa3; --text-muted: #5a5e73;
            --accent: #6366f1; --accent-glow: rgba(99,102,241,0.15); --accent-hover: #818cf8;
            --success: #34d399;
        }
        body { font-family: 'Outfit', sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; overflow-x: hidden; }
        .bg-grid { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px); background-size: 60px 60px; pointer-events: none; z-index: 0; }
        .bg-glow { position: fixed; top: -200px; left: 50%; transform: translateX(-50%); width: 800px; height: 600px; background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%); pointer-events: none; z-index: 0; }
        .container { position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 60px 24px 80px; }
        .header { text-align: center; margin-bottom: 50px; }
        .header-top { display: flex; justify-content: center; align-items: center; margin-bottom: 24px; position: relative; }
        .header-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 16px; background: var(--accent-glow); border: 1px solid rgba(99,102,241,0.2); border-radius: 100px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); letter-spacing: 1.5px; text-transform: uppercase; }
        .header-badge .dot { width: 6px; height: 6px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .logout-btn { position: absolute; right: 0; background: none; border: 1px solid var(--border); border-radius: 8px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 6px 14px; cursor: pointer; transition: all 0.3s; }
        .logout-btn:hover { border-color: var(--text-secondary); color: var(--text-secondary); }
        .header h1 { font-size: 48px; font-weight: 800; letter-spacing: -1.5px; line-height: 1.1; margin-bottom: 12px; background: linear-gradient(135deg, #e2e4f0 0%, #6366f1 50%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .header p { font-size: 17px; color: var(--text-secondary); font-weight: 300; max-width: 500px; margin: 0 auto; line-height: 1.6; }
        .input-section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 32px; margin-bottom: 32px; transition: border-color 0.3s; }
        .input-section:focus-within { border-color: var(--border-focus); box-shadow: 0 0 0 4px var(--accent-glow); }
        .input-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 12px; display: block; }
        .input-row { display: flex; gap: 12px; }
        .input-field { flex: 1; background: var(--bg-input); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; font-family: 'Outfit', sans-serif; font-size: 16px; color: var(--text-primary); outline: none; transition: all 0.3s; }
        .input-field::placeholder { color: var(--text-muted); }
        .input-field:focus { border-color: var(--accent); background: rgba(26,27,46,0.8); }
        .btn-generate { padding: 14px 28px; background: var(--accent); color: white; border: none; border-radius: 10px; font-family: 'Outfit', sans-serif; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.3s; white-space: nowrap; }
        .btn-generate:hover { background: var(--accent-hover); transform: translateY(-1px); box-shadow: 0 4px 20px rgba(99,102,241,0.3); }
        .btn-generate:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .loading-section { display: none; text-align: center; padding: 60px 20px; }
        .loading-section.active { display: block; }
        .spinner { width: 48px; height: 48px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 24px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text { font-size: 16px; color: var(--text-secondary); font-weight: 300; }
        .loading-sub { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-muted); margin-top: 8px; }
        .result-section { display: none; }
        .result-section.active { display: block; }
        .result-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
        .result-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); display: flex; align-items: center; gap: 8px; }
        .result-title .check { width: 20px; height: 20px; background: var(--success); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #0a0b0f; font-weight: 700; }
        .result-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); }
        .brief-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 40px; line-height: 1.75; }
        .brief-container h1, .brief-container h2 { font-family: 'Outfit', sans-serif; color: var(--text-primary); margin-top: 36px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
        .brief-container h1 { font-size: 26px; font-weight: 700; }
        .brief-container h2 { font-size: 20px; font-weight: 600; color: var(--accent-hover); border-bottom-color: rgba(99,102,241,0.15); }
        .brief-container h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-top: 24px; margin-bottom: 10px; }
        .brief-container h1:first-child, .brief-container h2:first-child { margin-top: 0; }
        .brief-container p { color: var(--text-secondary); margin-bottom: 14px; font-size: 15px; }
        .brief-container strong { color: var(--text-primary); font-weight: 600; }
        .brief-container ul, .brief-container ol { padding-left: 24px; margin-bottom: 14px; }
        .brief-container li { color: var(--text-secondary); font-size: 15px; margin-bottom: 6px; }
        .brief-container table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
        .brief-container th { background: var(--bg-input); color: var(--text-primary); font-weight: 600; text-align: left; padding: 10px 14px; border: 1px solid var(--border); }
        .brief-container td { padding: 10px 14px; border: 1px solid var(--border); color: var(--text-secondary); }
        .brief-container tr:nth-child(even) td { background: rgba(22,23,34,0.5); }
        .brief-container blockquote { border-left: 3px solid var(--accent); padding: 12px 20px; margin: 16px 0; background: var(--accent-glow); border-radius: 0 8px 8px 0; }
        .brief-container blockquote p { color: var(--text-primary); margin-bottom: 0; }
        .brief-container code { font-family: 'JetBrains Mono', monospace; background: var(--bg-input); padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        .brief-container hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
        .error-section { display: none; background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); border-radius: 12px; padding: 20px 24px; color: #fca5a5; font-size: 14px; }
        .error-section.active { display: block; }
        .error-section strong { color: #f87171; }
        .footer { text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border); }
        .footer p { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); }
        @media (max-width: 600px) { .header h1 { font-size: 32px; } .input-row { flex-direction: column; } .brief-container { padding: 24px; } .container { padding: 32px 16px 60px; } .logout-btn { position: static; margin-top: 12px; } .header-top { flex-direction: column; } }
    </style>
</head>
<body>
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    <div class="container">
        <div class="header">
            <div class="header-top">
                <div class="header-badge"><span class="dot"></span> System Online</div>
                <button class="logout-btn" onclick="window.location.href='/logout'">Logout</button>
            </div>
            <h1>OnSpot</h1>
            <p>Generate comprehensive pre-call intelligence briefs for any company in seconds.</p>
        </div>
        <div class="input-section">
            <label class="input-label">Target Company</label>
            <div class="input-row">
                <input type="text" class="input-field" id="companyInput" placeholder="e.g. Salesforce, CrowdStrike, HubSpot..." autocomplete="off" />
                <button class="btn-generate" id="generateBtn" onclick="generateBrief()">Generate Brief</button>
            </div>
        </div>
        <div class="loading-section" id="loadingSection">
            <div class="spinner"></div>
            <div class="loading-text">Generating intelligence brief...</div>
            <div class="loading-sub">This typically takes 30-60 seconds</div>
        </div>
        <div class="error-section" id="errorSection"></div>
        <div class="result-section" id="resultSection">
            <div class="result-header">
                <div class="result-title"><span class="check">&#10003;</span><span id="resultCompany">Brief generated</span></div>
                <div class="result-meta" id="resultMeta"></div>
            </div>
            <div class="brief-container" id="briefContent"></div>
        </div>
        <div class="footer"><p>OnSpot v1.0 — Built by Sid Lockhart</p></div>
    </div>
    <script>
        document.getElementById('companyInput').addEventListener('keydown', e => { if (e.key === 'Enter') generateBrief(); });
        async function generateBrief() {
            const company = document.getElementById('companyInput').value.trim();
            const btn = document.getElementById('generateBtn');
            if (!company) return;
            btn.disabled = true; btn.textContent = 'Generating...';
            document.getElementById('loadingSection').classList.add('active');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('errorSection').classList.remove('active');
            try {
                const res = await fetch('/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ company }) });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('briefContent').innerHTML = data.html;
                    document.getElementById('resultCompany').textContent = company + ' — Brief Complete';
                    document.getElementById('resultMeta').textContent = data.timestamp + ' · ' + data.filename;
                    document.getElementById('resultSection').classList.add('active');
                } else {
                    document.getElementById('errorSection').innerHTML = '<strong>Error:</strong> ' + data.error;
                    document.getElementById('errorSection').classList.add('active');
                }
            } catch (err) {
                document.getElementById('errorSection').innerHTML = '<strong>Error:</strong> ' + err.message;
                document.getElementById('errorSection').classList.add('active');
            } finally {
                document.getElementById('loadingSection').classList.remove('active');
                btn.disabled = false; btn.textContent = 'Generate Brief';
            }
        }
    </script>
</body>
</html>
"""

MANIFEST = '{"name":"OnSpot","short_name":"OnSpot","description":"AI-powered sales intelligence","start_url":"/","display":"standalone","background_color":"#0a0b0f","theme_color":"#0a0b0f","icons":[]}'

@app.route("/")
def index():
    if session.get("authenticated"):
        return render_template_string(APP_TEMPLATE)
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/app")
def app_page():
    if not session.get("authenticated"):
        return render_template_string(LOGIN_TEMPLATE)
    return render_template_string(APP_TEMPLATE)

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if data.get("password", "") == APP_PASSWORD:
        session["authenticated"] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/logout")
def logout():
    session.clear()
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/manifest.json")
def manifest():
    return app.response_class(MANIFEST, mimetype="application/json")

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
        filepath.write_text(f"<!-- Generated by OnSpot -->\n<!-- Timestamp: {timestamp} -->\n\n" + brief_text, encoding="utf-8")
        html = markdown.markdown(brief_text, extensions=["tables", "fenced_code", "nl2br"])
        return jsonify({"success": True, "html": html, "timestamp": timestamp, "filename": filename})
    except anthropic.AuthenticationError:
        return jsonify({"success": False, "error": "Invalid API key."})
    except anthropic.RateLimitError:
        return jsonify({"success": False, "error": "Rate limited. Wait and try again."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  ONSPOT — Account Intelligence Briefer")
    print("  Open: http://127.0.0.1:5000")
    print(f"  Password: {APP_PASSWORD}")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
