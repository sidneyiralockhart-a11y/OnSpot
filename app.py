# OnSpot - Account Intelligence Platform
# Verticalized with Industry Lens feature
# Stack: Flask + Anthropic API

import os
import re
import markdown
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from anthropic import Anthropic

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "onspot-secret-2026")
client = Anthropic()

PASSWORD = os.environ.get("APP_PASSWORD", "onspot2026")

# ─────────────────────────────────────────────
# INDUSTRY LENS PROMPTS
# ─────────────────────────────────────────────

INDUSTRY_PROMPTS = {

    "general": """You are an elite enterprise sales intelligence analyst embedded inside a world-class B2B revenue team. Your sole function is to produce hyper-specific, deal-accelerating pre-call briefs for senior Account Executives selling complex SaaS solutions. You do not produce generic summaries. You hunt for operational signal.

When given a target company, produce a structured intelligence brief with the following sections:

## 1. COMPANY SNAPSHOT
- Industry vertical, headcount band, revenue estimate, funding stage or public status
- Key business model (PLG, SLG, channel-led, enterprise direct)
- Recent strategic pivots or announced transformation initiatives

## 2. TECH STACK INTELLIGENCE
- Identify confirmed or likely CRM, ERP, HRIS, data warehouse, BI, and collaboration tools
- Flag any known legacy systems creating technical debt
- Identify cloud provider (AWS/Azure/GCP) and deployment posture (cloud-native, hybrid, on-prem heavy)
- Note any recent tech stack announcements, migrations, or vendor consolidation signals

## 3. C-SUITE OPERATIONAL BOTTLENECKS
- Identify the top 2-3 operational pressures facing the CEO, CRO, CFO, and COO based on company stage, market conditions, and public statements
- Flag any known board-level mandates (cost reduction, margin expansion, growth acceleration, M&A integration)
- Surface any efficiency or automation gaps typical of companies at this stage

## 4. BUYING SIGNALS & TRIGGER EVENTS
- Recent funding rounds, IPO activity, or M&A events
- Executive leadership changes (new CRO, CFO, CTO in last 12 months = high buying signal)
- New product launches, market expansions, or geographic growth suggesting infrastructure strain
- Layoffs or restructuring suggesting budget reallocation

## 5. COMPETITIVE LANDSCAPE
- Who are their top 3 competitors and how is this company positioned
- Any known vendor relationships or partnerships that signal openness or resistance to new technology
- Consolidation or displacement opportunities

## 6. ACCOUNT ENTRY STRATEGY
- Recommended persona to target first and why (economic buyer vs. champion vs. technical evaluator)
- 3 highly specific discovery questions tailored to this company's known pain points
- Recommended hook or opening frame for cold outreach

## 7. RED FLAGS & OBJECTION FORECAST
- Budget freeze signals, recent cost-cutting news, or hiring freezes
- Likely objections based on company profile and stage
- Political landmines (recent failed projects, vendor fatigue, internal champion risk)

---
Tone: Confident, direct, zero fluff. Write like a Goldman Sachs analyst briefing a managing director before a critical client call. Every sentence must earn its place.
""",

    "infrastructure": """You are a senior technical sales intelligence analyst specializing in Enterprise IT, OEM hardware, infrastructure software, and data center solutions. Your briefs are used by infrastructure AEs and solution architects selling to CTOs, VPs of Infrastructure, and IT Directors at Fortune 1000 companies. You do not produce marketing summaries. You produce technical buying intelligence.

When given a target company, produce a structured infrastructure intelligence brief:

## 1. INFRASTRUCTURE PROFILE
- Estimated server footprint: cloud-native, hybrid, or on-prem heavy
- Primary cloud provider(s): AWS, Azure, GCP — and estimated workload split
- Data center posture: owned DCs, colo facilities, edge deployments
- Headcount in IT/Infra/DevOps/SRE as a proxy for operational complexity

## 2. TECH STACK DEEP DIVE
- Known or inferred virtualization platform (VMware, Hyper-V, KVM, bare metal)
- Container orchestration posture (Kubernetes, ECS, OpenShift, or none)
- Storage architecture signals (NAS, SAN, object storage, hyperconverged)
- Networking stack (Cisco, Juniper, Arista, SD-WAN signals)
- Observability and monitoring tools (Datadog, Dynatrace, Splunk, New Relic, homegrown)
- Security posture: known SIEM, EDR, SASE, or zero-trust initiatives

## 3. TECHNICAL DEBT SIGNALS
- Age of infrastructure based on company founding and known migration history
- Legacy ERP or on-prem application dependencies that resist cloud migration
- Known compliance burdens (SOC2, PCI, HIPAA, FedRAMP) that constrain architecture decisions
- Any signals of over-provisioned, underutilized, or shadow IT environments

## 4. BUILD VS. BUY MENTALITY
- Engineering headcount ratio as a proxy for build culture
- Open source contribution signals suggesting NIH (Not Invented Here) bias
- History of large vendor contracts vs. point solution sprawl
- FinOps maturity signals — are they optimizing cloud spend or still in growth-at-all-costs mode

## 5. INFRASTRUCTURE TRIGGER EVENTS
- Cloud migration announcements or lift-and-shift initiatives
- Data center lease expirations or consolidation programs
- M&A activity requiring infrastructure integration
- New CTO, VP Infra, or CISO hire (high propensity to evaluate and replace incumbent vendors)
- Rapid headcount scaling creating capacity planning pressure

## 6. CTO/VP INFRA PAIN PROFILE
- Top 3 infrastructure operational pressures at this company's scale and stage
- Known or inferred SLA/uptime pressures based on their business model
- Cost optimization mandates from CFO filtering down to infrastructure budgets
- Security or compliance gaps that are board-visible

## 7. ACCOUNT ENTRY STRATEGY
- Primary target persona and secondary champion path
- 3 deeply technical discovery questions that will establish credibility in the first call
- Recommended proof point or reference customer from a similar infrastructure profile
- Cold outreach hook based on a specific, known infrastructure signal

## 8. COMPETITIVE DISPLACEMENT INTELLIGENCE
- Likely incumbent vendors in this account and their known weaknesses at this scale
- Consolidation opportunities (replacing 3 point solutions with a platform play)
- Renewal cycle signals if known

---
Tone: Peer-to-peer technical credibility. Write like a principal solutions architect briefing a field CTO. No vendor marketing language. Be specific, be technical, be useful.
""",

    "healthcare": """You are a senior healthcare IT sales intelligence analyst specializing in hospital systems, integrated delivery networks (IDNs), medical device companies, and health tech. Your briefs are used by enterprise AEs selling to CMIOs, CIOs, hospital network administrators, VP of Clinical Informatics, and GPO procurement leads. You have deep familiarity with Epic, Cerner, MEDITECH, and the full clinical and administrative IT stack.

When given a target company or health system, produce a structured healthcare intelligence brief:

## 1. HEALTH SYSTEM / ORGANIZATION PROFILE
- Organization type: IDN, standalone hospital, academic medical center, community health system, medical device OEM, health tech vendor
- Bed count, number of facilities, geographic footprint, affiliated physician count
- Ownership structure: nonprofit, for-profit, faith-based, government
- Revenue band and payer mix signals (commercial, Medicare/Medicaid heavy, value-based contracts)

## 2. CLINICAL IT STACK (EMR/EHR CORE)
- Primary EMR/EHR platform: Epic, Oracle Health (Cerner), MEDITECH, Allscripts, athenahealth, or other
- Go-live date and version — older implementations signal upgrade cycles and customization debt
- Known Epic module deployment: which pillars are live (Inpatient, Ambulatory, Revenue Cycle, Tapestry, Beaker, Radiant, etc.)
- Known third-party clinical applications layered on top of EMR (PACS, pharmacy, patient engagement, telehealth)
- Interoperability posture: HL7 FHIR adoption, CommonWell/Carequality membership, HIE participation

## 3. REVENUE CYCLE & ADMINISTRATIVE STACK
- RCM platform (Epic Resolute, Cerner RevElate, Experian Health, Waystar, Optum360, Change Healthcare)
- Known billing, coding, and prior authorization pain points
- Denials management and AR days benchmark vs. peers
- Patient access and scheduling platform

## 4. VALUE-BASED CARE & REGULATORY POSTURE
- ACO participation, MSSP tracks, or direct contracting programs
- Known CMS quality programs: MIPS/MACRA performance, star ratings, readmission penalties
- FDA compliance requirements if medical device manufacturer (510(k), PMA, UDI systems)
- HIPAA/HITECH compliance posture and any known breach history
- State-specific Medicaid waiver programs or risk-based contracts

## 5. GPO AFFILIATIONS & PROCUREMENT SIGNALS
- Known GPO memberships: Vizient, Premier, HealthTrust, Provista, Intalere
- Implications for contract vehicle requirements and price benchmarking
- Capital vs. operational budget cycles — most health systems run October fiscal year end
- Known approved vendor lists or sole-source contract preferences

## 6. STRATEGIC INITIATIVES & TRIGGER EVENTS
- System mergers, acquisitions, or affiliation announcements (highest infra displacement signal)
- Epic or Cerner migration/upgrade underway
- New CMIO, CIO, or CNO hire in last 12 months
- Digital health transformation initiatives (patient portal adoption, remote monitoring, AI/ML pilots)
- Cost reduction mandates from board or bond covenant pressure

## 7. CLINICAL CHAMPION & ECONOMIC BUYER MAP
- Primary target persona: CMIO, CIO, VP Clinical Informatics, or CNO depending on solution
- Economic buyer path: CFO, CEO, or Board-level capital committee
- Known internal committee structures (IT Steering Committee, Value Analysis Committee)
- Physician adoption risk — flag if solution requires clinical workflow change

## 8. ACCOUNT ENTRY STRATEGY
- Recommended entry persona and why
- 3 highly specific discovery questions that demonstrate clinical operations knowledge
- Reference customer or case study from a comparable health system
- Cold outreach hook tied to a specific clinical or financial pain signal

## 9. COMPETITIVE & COMPLIANCE RISKS
- Incumbent vendor relationships and contract lock-in risks
- Epic App Orchard or Cerner App Market participation requirements
- Interoperability mandates under 21st Century Cures Act as forcing function
- Likely objections: IT bandwidth, integration complexity, clinical validation requirements

---
Tone: Clinical credibility meets financial precision. Write like a Gartner healthcare analyst briefing a health system board. Never use consumer health language. Speak in the operational vocabulary of hospital administration and clinical informatics.
"""
}

LENS_LABELS = {
    "general": "Enterprise SaaS",
    "infrastructure": "IT & Infrastructure",
    "healthcare": "Healthcare & Medical Devices"
}

# ─────────────────────────────────────────────
# HTML TEMPLATE
# ─────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>OnSpot — Account Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg-base: #0d1117;
    --bg-surface: #161b22;
    --bg-elevated: #1c2128;
    --bg-card: #21262d;
    --border: #30363d;
    --border-muted: #21262d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --blue-accent: #2f81f7;
    --blue-dim: #1f6feb;
    --blue-subtle: #0d1f3c;
    --green: #3fb950;
    --green-subtle: #0d2a16;
    --amber: #d29922;
    --amber-subtle: #2a1f00;
    --red: #f85149;
    --purple: #a371f7;
    --lens-general: #2f81f7;
    --lens-infra: #a371f7;
    --lens-health: #3fb950;
  }

  html, body {
    height: 100%;
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.6;
  }

  .app-shell {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  .sidebar {
    width: 240px;
    min-width: 240px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 20px 16px 16px;
    border-bottom: 1px solid var(--border);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .logo-mark {
    width: 28px;
    height: 28px;
    background: var(--blue-accent);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.5px;
  }

  .logo-text {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.3px;
  }

  .logo-sub {
    font-size: 11px;
    color: var(--text-muted);
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-left: 36px;
  }

  .sidebar-status {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    flex-shrink: 0;
  }

  .sidebar-section {
    padding: 12px 16px 8px;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .sidebar-history {
    flex: 1;
    overflow-y: auto;
    padding: 0 8px 16px;
  }

  .history-item {
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
    margin-bottom: 2px;
  }

  .history-item:hover { background: var(--bg-elevated); }

  .history-company {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .history-meta {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 1px;
    display: flex;
    gap: 6px;
    align-items: center;
  }

  .history-lens-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .sidebar-footer {
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-muted);
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--bg-base);
  }

  .topbar {
    padding: 16px 28px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-surface);
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }

  .search-container {
    flex: 1;
    display: flex;
    gap: 10px;
    align-items: center;
    max-width: 820px;
  }

  .lens-select-wrap {
    position: relative;
    flex-shrink: 0;
  }

  .lens-select {
    appearance: none;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 500;
    padding: 9px 32px 9px 12px;
    cursor: pointer;
    transition: border-color 0.15s;
    min-width: 196px;
  }

  .lens-select:focus {
    outline: none;
    border-color: var(--blue-accent);
  }

  .lens-select-arrow {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--text-muted);
    font-size: 11px;
  }

  .company-input-wrap {
    flex: 1;
    position: relative;
  }

  .company-input {
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    padding: 9px 14px 9px 38px;
    transition: border-color 0.15s;
  }

  .company-input:focus {
    outline: none;
    border-color: var(--blue-accent);
    box-shadow: 0 0 0 3px rgba(47, 129, 247, 0.1);
  }

  .company-input::placeholder { color: var(--text-muted); }

  .input-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    font-size: 15px;
    pointer-events: none;
  }

  .generate-btn {
    background: var(--blue-accent);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    padding: 9px 20px;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .generate-btn:hover { background: #388bfd; }
  .generate-btn:active { transform: scale(0.98); }
  .generate-btn:disabled { background: var(--border); color: var(--text-muted); cursor: not-allowed; transform: none; }

  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 28px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    padding: 40px;
  }

  .empty-icon {
    font-size: 40px;
    margin-bottom: 16px;
    opacity: 0.4;
  }

  .empty-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }

  .empty-sub {
    font-size: 13px;
    color: var(--text-muted);
    max-width: 360px;
    line-height: 1.7;
  }

  .lens-pills {
    display: flex;
    gap: 8px;
    margin-top: 20px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .lens-pill {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid;
    cursor: pointer;
    transition: all 0.15s;
  }

  .loading-state {
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    gap: 24px;
  }

  .loading-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border);
    border-top-color: var(--blue-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .loading-steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 280px;
  }

  .loading-step {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    color: var(--text-muted);
    transition: color 0.3s;
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid var(--border-muted);
  }

  .loading-step.active {
    color: var(--text-primary);
    border-color: var(--blue-accent);
    background: rgba(47, 129, 247, 0.06);
  }

  .loading-step.done {
    color: var(--green);
    border-color: var(--green);
    background: var(--green-subtle);
  }

  .step-icon { font-size: 14px; width: 20px; text-align: center; }

  .brief-output { display: none; max-width: 900px; }

  .brief-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24px;
    gap: 16px;
    flex-wrap: wrap;
  }

  .brief-company-block { display: flex; align-items: center; gap: 14px; }

  .company-avatar {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: var(--blue-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: white;
    flex-shrink: 0;
    letter-spacing: -0.5px;
  }

  .brief-company-name {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.3px;
  }

  .brief-meta {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 3px;
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .brief-actions { display: flex; gap: 8px; flex-shrink: 0; }

  .action-btn {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: 6px;
    padding: 7px 14px;
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .action-btn:hover {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border-color: var(--text-muted);
  }

  .lens-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid;
  }

  .lens-badge.general {
    color: var(--lens-general);
    border-color: var(--lens-general);
    background: rgba(47, 129, 247, 0.08);
  }

  .lens-badge.infrastructure {
    color: var(--lens-infra);
    border-color: var(--lens-infra);
    background: rgba(163, 113, 247, 0.08);
  }

  .lens-badge.healthcare {
    color: var(--lens-health);
    border-color: var(--lens-health);
    background: rgba(63, 185, 80, 0.08);
  }

  .brief-content {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }

  .brief-content-inner {
    padding: 28px 32px;
  }

  .brief-content h2 {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin: 28px 0 12px;
    padding-top: 24px;
    border-top: 1px solid var(--border-muted);
  }

  .brief-content h2:first-child {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
  }

  .brief-content h3 {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    margin: 16px 0 6px;
  }

  .brief-content p {
    color: var(--text-secondary);
    font-size: 13.5px;
    margin-bottom: 10px;
    line-height: 1.75;
  }

  .brief-content ul, .brief-content ol {
    padding-left: 18px;
    margin-bottom: 12px;
  }

  .brief-content li {
    color: var(--text-secondary);
    font-size: 13.5px;
    margin-bottom: 6px;
    line-height: 1.7;
  }

  .brief-content strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .brief-content code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 6px;
    color: var(--purple);
  }

  .error-banner {
    display: none;
    background: rgba(248, 81, 73, 0.08);
    border: 1px solid rgba(248, 81, 73, 0.3);
    border-radius: 8px;
    padding: 14px 18px;
    color: var(--red);
    font-size: 13px;
    margin-bottom: 20px;
  }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

  @media print {
    .sidebar, .topbar { display: none !important; }
    .content-area { padding: 0; }
    .brief-actions { display: none; }
    .brief-output { display: block !important; max-width: 100%; }
  }
</style>
</head>
<body>

<div class="app-shell">

  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-mark">OS</div>
        <span class="logo-text">OnSpot</span>
      </div>
      <div class="logo-sub">Account Intelligence</div>
    </div>

    <div class="sidebar-status">
      <div class="status-dot"></div>
      API Connected &middot; Ready
    </div>

    <div class="sidebar-section">Recent Briefs</div>
    <div class="sidebar-history" id="briefHistory">
      <div style="padding: 8px 10px; font-size: 12px; color: var(--text-muted);">No briefs yet</div>
    </div>

    <div class="sidebar-footer">
      OnSpot v2.0 &middot; Industry Lens Edition<br>
      <a href="/logout" style="color: var(--text-muted); text-decoration: none;">Sign out</a>
    </div>
  </aside>

  <div class="main-content">

    <div class="topbar">
      <div class="search-container">

        <div class="lens-select-wrap">
          <select class="lens-select" id="industrySelect" onchange="updateLensStyle()">
            <option value="general">&#x1F537; Enterprise SaaS</option>
            <option value="infrastructure">&#x1F7E3; IT &amp; Infrastructure</option>
            <option value="healthcare">&#x1F7E2; Healthcare &amp; Med Devices</option>
          </select>
          <span class="lens-select-arrow">&#9662;</span>
        </div>

        <div class="company-input-wrap">
          <span class="input-icon">&#8982;</span>
          <input
            type="text"
            class="company-input"
            id="companyInput"
            placeholder="Enter company name (e.g. Salesforce, Mayo Clinic, Dell Technologies)"
            onkeydown="if(event.key==='Enter') generateBrief()"
          />
        </div>

        <button class="generate-btn" id="generateBtn" onclick="generateBrief()">
          <span>&#9889;</span> Generate Brief
        </button>
      </div>
    </div>

    <div class="content-area" id="contentArea">

      <div class="empty-state" id="emptyState">
        <div class="empty-icon">&#8859;</div>
        <div class="empty-title">Account Intelligence Platform</div>
        <div class="empty-sub">Enter a company name and select your Industry Lens to generate a deep pre-call intelligence brief.</div>
        <div class="lens-pills">
          <div class="lens-pill" style="color:#2f81f7; border-color:#2f81f7; background:rgba(47,129,247,0.08)" onclick="setLens('general')">&#x1F537; Enterprise SaaS</div>
          <div class="lens-pill" style="color:#a371f7; border-color:#a371f7; background:rgba(163,113,247,0.08)" onclick="setLens('infrastructure')">&#x1F7E3; IT &amp; Infrastructure</div>
          <div class="lens-pill" style="color:#3fb950; border-color:#3fb950; background:rgba(63,185,80,0.08)" onclick="setLens('healthcare')">&#x1F7E2; Healthcare</div>
        </div>
      </div>

      <div class="loading-state" id="loadingState">
        <div class="loading-spinner"></div>
        <div class="loading-steps">
          <div class="loading-step" id="step1"><span class="step-icon">&#128269;</span> Profiling target company</div>
          <div class="loading-step" id="step2"><span class="step-icon">&#129504;</span> Applying industry lens</div>
          <div class="loading-step" id="step3"><span class="step-icon">&#128225;</span> Mapping tech stack &amp; signals</div>
          <div class="loading-step" id="step4"><span class="step-icon">&#9881;&#65039;</span> Generating intelligence brief</div>
          <div class="loading-step" id="step5"><span class="step-icon">&#9989;</span> Compiling final output</div>
        </div>
      </div>

      <div class="error-banner" id="errorBanner"></div>

      <div class="brief-output" id="briefOutput">
        <div class="brief-header">
          <div class="brief-company-block">
            <div class="company-avatar" id="companyAvatar"></div>
            <div>
              <div class="brief-company-name" id="briefCompanyName"></div>
              <div class="brief-meta">
                <span id="briefTimestamp"></span>
                <span>&middot;</span>
                <span id="briefLensBadge"></span>
              </div>
            </div>
          </div>
          <div class="brief-actions">
            <button class="action-btn" onclick="newBrief()">&#8853; New Brief</button>
            <button class="action-btn" onclick="window.print()">&#8595; Export</button>
          </div>
        </div>

        <div class="brief-content">
          <div class="brief-content-inner" id="briefContentInner"></div>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
let briefHistory = [];
try { briefHistory = JSON.parse(localStorage.getItem('onspot_history') || '[]'); } catch(e) {}

const LENS_COLORS = {
  general: '#2f81f7',
  infrastructure: '#a371f7',
  healthcare: '#3fb950'
};

const LENS_LABELS = {
  general: 'Enterprise SaaS',
  infrastructure: 'IT & Infrastructure',
  healthcare: 'Healthcare & Med Devices'
};

function setLens(lens) {
  document.getElementById('industrySelect').value = lens;
  updateLensStyle();
  document.getElementById('companyInput').focus();
}

function updateLensStyle() {
  const lens = document.getElementById('industrySelect').value;
  const color = LENS_COLORS[lens];
  document.getElementById('industrySelect').style.borderColor = color;
  document.getElementById('industrySelect').style.color = color;
}

function renderHistory() {
  const container = document.getElementById('briefHistory');
  if (!briefHistory.length) {
    container.innerHTML = '<div style="padding: 8px 10px; font-size: 12px; color: var(--text-muted);">No briefs yet</div>';
    return;
  }
  container.innerHTML = briefHistory.slice(0, 20).map((item, i) => `
    <div class="history-item" onclick="loadHistoryItem(${i})">
      <div class="history-company">${item.company}</div>
      <div class="history-meta">
        <div class="history-lens-dot" style="background:${LENS_COLORS[item.lens]}"></div>
        <span>${LENS_LABELS[item.lens]}</span>
      </div>
    </div>
  `).join('');
}

function loadHistoryItem(i) {
  const item = briefHistory[i];
  showBrief(item.company, item.lens, item.html);
}

function showBrief(company, lens, html) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('briefOutput').style.display = 'block';

  const initials = company.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  document.getElementById('companyAvatar').textContent = initials;
  document.getElementById('companyAvatar').style.background = LENS_COLORS[lens];
  document.getElementById('briefCompanyName').textContent = company;
  document.getElementById('briefTimestamp').textContent = new Date().toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});

  const badge = document.getElementById('briefLensBadge');
  badge.innerHTML = '<span class="lens-badge ' + lens + '">\u25C9 ' + LENS_LABELS[lens] + ' Brief</span>';

  document.getElementById('briefContentInner').innerHTML = html;
}

async function generateBrief() {
  const company = document.getElementById('companyInput').value.trim();
  const industry = document.getElementById('industrySelect').value;

  if (!company) {
    document.getElementById('companyInput').focus();
    return;
  }

  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('briefOutput').style.display = 'none';
  document.getElementById('errorBanner').style.display = 'none';
  document.getElementById('loadingState').style.display = 'flex';
  document.getElementById('generateBtn').disabled = true;

  const steps = ['step1','step2','step3','step4','step5'];
  steps.forEach(s => document.getElementById(s).className = 'loading-step');
  let stepIndex = 0;
  const stepInterval = setInterval(() => {
    if (stepIndex > 0) {
      document.getElementById(steps[stepIndex-1]).className = 'loading-step done';
      document.getElementById(steps[stepIndex-1]).querySelector('.step-icon').textContent = '\u2713';
    }
    if (stepIndex < steps.length) {
      document.getElementById(steps[stepIndex]).className = 'loading-step active';
      stepIndex++;
    } else {
      clearInterval(stepInterval);
    }
  }, 4000);

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, industry })
    });

    clearInterval(stepInterval);
    steps.forEach(s => {
      document.getElementById(s).className = 'loading-step done';
      document.getElementById(s).querySelector('.step-icon').textContent = '\u2713';
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Generation failed');

    briefHistory.unshift({ company, lens: industry, html: data.html, ts: Date.now() });
    briefHistory = briefHistory.slice(0, 20);
    try { localStorage.setItem('onspot_history', JSON.stringify(briefHistory)); } catch(e) {}
    renderHistory();

    showBrief(company, industry, data.html);

  } catch (err) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('briefOutput').style.display = 'none';
    document.getElementById('emptyState').style.display = 'flex';
    const banner = document.getElementById('errorBanner');
    banner.textContent = '\u26A0 ' + err.message;
    banner.style.display = 'block';
  } finally {
    document.getElementById('generateBtn').disabled = false;
  }
}

function newBrief() {
  document.getElementById('briefOutput').style.display = 'none';
  document.getElementById('emptyState').style.display = 'flex';
  document.getElementById('companyInput').value = '';
  document.getElementById('companyInput').focus();
}

updateLensStyle();
renderHistory();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────
# LOGIN TEMPLATE
# ─────────────────────────────────────────────

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>OnSpot &mdash; Sign In</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0d1117;
    font-family: 'Inter', sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    color: #e6edf3;
  }
  .login-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 40px;
    width: 360px;
  }
  .logo { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
  .logo-mark {
    width: 32px; height: 32px; background: #2f81f7;
    border-radius: 7px; display: flex; align-items: center;
    justify-content: center; font-weight: 700; font-size: 14px;
  }
  .logo-text { font-size: 18px; font-weight: 700; }
  .tagline { font-size: 12px; color: #6e7681; margin-bottom: 28px; margin-left: 42px; }
  label { font-size: 12px; font-weight: 500; color: #8b949e; display: block; margin-bottom: 6px; }
  input[type=password] {
    width: 100%; background: #21262d; border: 1px solid #30363d;
    border-radius: 8px; color: #e6edf3; font-family: 'Inter', sans-serif;
    font-size: 14px; padding: 10px 14px; margin-bottom: 16px;
  }
  input[type=password]:focus { outline: none; border-color: #2f81f7; }
  .login-btn {
    width: 100%; background: #2f81f7; color: white; border: none;
    border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 14px;
    font-weight: 600; padding: 11px; cursor: pointer;
  }
  .login-btn:hover { background: #388bfd; }
  .error { color: #f85149; font-size: 12px; margin-bottom: 14px; }
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">
    <div class="logo-mark">OS</div>
    <span class="logo-text">OnSpot</span>
  </div>
  <div class="tagline">Account Intelligence Platform</div>
  {% if error %}<div class="error">&#9888; {{ error }}</div>{% endif %}
  <form method="POST">
    <label>Access Password</label>
    <input type="password" name="password" placeholder="Enter password" autofocus/>
    <button type="submit" class="login-btn">Sign In &rarr;</button>
  </form>
</div>
</body>
</html>
"""

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Incorrect password."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template_string(HTML_TEMPLATE)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    company = (data.get("company") or "").strip()
    industry = (data.get("industry") or "general").strip()

    if not company:
        return jsonify({"error": "Company name is required."}), 400

    if industry not in INDUSTRY_PROMPTS:
        industry = "general"

    system_prompt = INDUSTRY_PROMPTS[industry]
    user_message = f"Generate a complete intelligence brief for: {company}"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        raw_text = response.content[0].text

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        safe_name = re.sub(r'[^a-z0-9_]', '_', company.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_dir / f"{safe_name}_{industry}_{timestamp}_brief.md"
        filepath.write_text(raw_text, encoding="utf-8")

        html_output = markdown.markdown(raw_text, extensions=["extra"])
        return jsonify({"html": html_output, "markdown": raw_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  OnSpot Account Intelligence v2.0")
    print("  Industry Lens Edition")
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)