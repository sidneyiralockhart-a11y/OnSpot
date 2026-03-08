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

    "general": """You are an elite enterprise sales intelligence analyst embedded inside a world-class B2B revenue team. Your sole
function is to produce hyper-specific, deal-accelerating pre-call briefs for senior Account Executives selling complex SaaS
solutions. You do not produce generic summaries. You hunt for operational signal.

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
- Identify the top 2-3 operational pressures facing the CEO, CRO, CFO, and COO based on company stage, market conditions, and
public statements
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
Tone: Confident, direct, zero fluff. Write like a Goldman Sachs analyst briefing a managing director before a critical client call.
 Every sentence must earn its place.
""",

    "infrastructure": """You are a senior technical sales intelligence analyst specializing in Enterprise IT, OEM hardware,
infrastructure software, and data center solutions. Your briefs are used by infrastructure AEs and solution architects selling to
CTOs, VPs of Infrastructure, and IT Directors at Fortune 1000 companies. You do not produce marketing summaries. You produce
technical buying intelligence.

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
Tone: Peer-to-peer technical credibility. Write like a principal solutions architect briefing a field CTO. No vendor marketing
language. Be specific, be technical, be useful.
""",

    "healthcare": """You are a senior healthcare IT sales intelligence analyst specializing in hospital systems, integrated
delivery networks (IDNs), medical device companies, and health tech. Your briefs are used by enterprise AEs selling to CMIOs, CIOs,
 hospital network administrators, VP of Clinical Informatics, and GPO procurement leads. You have deep familiarity with Epic,
Cerner, MEDITECH, and the full clinical and administrative IT stack.

When given a target company or health system, produce a structured healthcare intelligence brief:

## 1. HEALTH SYSTEM / ORGANIZATION PROFILE
- Organization type: IDN, standalone hospital, academic medical center, community health system, medical device OEM, health tech
vendor
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
Tone: Clinical credibility meets financial precision. Write like a Gartner healthcare analyst briefing a health system board. Never
 use consumer health language. Speak in the operational vocabulary of hospital administration and clinical informatics.
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
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14.
.32,700;1,14..32,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg-base: #09090b;
    --bg-surface: #111113;
    --bg-elevated: #18181b;
    --bg-card: #1c1c1f;
    --bg-hover: #27272a;
    --border: #27272a;
    --border-subtle: #1c1c1f;
    --border-focus: #3f3f46;
    --text-primary: #fafafa;
    --text-secondary: #a1a1aa;
    --text-muted: #52525b;
    --text-placeholder: #3f3f46;
    --blue: #3b82f6;
    --blue-hover: #2563eb;
    --blue-dim: #1d4ed8;
    --blue-glow: rgba(59,130,246,0.12);
    --blue-border: rgba(59,130,246,0.25);
    --green: #22c55e;
    --green-dim: rgba(34,197,94,0.1);
    --green-border: rgba(34,197,94,0.2);
    --amber: #f59e0b;
    --amber-dim: rgba(245,158,11,0.1);
    --red: #ef4444;
    --red-dim: rgba(239,68,68,0.08);
    --red-border: rgba(239,68,68,0.2);
    --purple: #a855f7;
    --purple-dim: rgba(168,85,247,0.1);
    --purple-border: rgba(168,85,247,0.25);
    --lens-general: #3b82f6;
    --lens-infra: #a855f7;
    --lens-health: #22c55e;
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
  }

  html, body {
    height: 100%;
    background: var(--bg-base);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Layout Shell ── */
  .app-shell {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  /* ── Sidebar ── */
  .sidebar {
    width: 232px;
    min-width: 232px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 16px 14px 14px;
    border-bottom: 1px solid var(--border);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 9px;
  }

  .logo-mark {
    width: 26px;
    height: 26px;
    background: var(--blue);
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.3px;
    flex-shrink: 0;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.4), 0 2px 8px rgba(59,130,246,0.25);
  }

  .logo-text {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.2px;
  }

  .logo-badge {
    font-size: 10px;
    font-weight: 500;
    color: var(--text-muted);
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
    margin-left: auto;
    letter-spacing: 0.2px;
  }

  .api-status {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 9px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-muted);
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 0 2px var(--green-dim);
    flex-shrink: 0;
    animation: pulse-dot 3s ease-in-out infinite;
  }

  @keyframes pulse-dot {
    0%, 100% { box-shadow: 0 0 0 2px var(--green-dim); }
    50% { box-shadow: 0 0 0 4px var(--green-dim); }
  }

  .sidebar-label {
    padding: 14px 14px 6px;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }

  .sidebar-history {
    flex: 1;
    overflow-y: auto;
    padding: 0 6px 8px;
  }

  .history-empty {
    padding: 10px 8px;
    font-size: 12px;
    color: var(--text-muted);
    font-style: italic;
  }

  .history-item {
    padding: 7px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.12s;
    margin-bottom: 1px;
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }

  .history-item:hover { background: var(--bg-elevated); }
  .history-item.active { background: var(--bg-hover); }

  .history-lens-bar {
    width: 2px;
    height: 32px;
    border-radius: 2px;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .history-info { min-width: 0; flex: 1; }

  .history-company {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
  }

  .history-lens {
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 1px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sidebar-divider {
    height: 1px;
    background: var(--border);
    margin: 4px 0;
  }

  .sidebar-footer {
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .footer-version {
    font-size: 11px;
    color: var(--text-muted);
  }

  .footer-signout {
    font-size: 11px;
    color: var(--text-muted);
    text-decoration: none;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid var(--border);
    transition: all 0.12s;
  }

  .footer-signout:hover {
    color: var(--text-secondary);
    border-color: var(--border-focus);
    background: var(--bg-elevated);
  }

  /* ── Main ── */
  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--bg-base);
  }

  /* ── Topbar ── */
  .topbar {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-surface);
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
  }

  /* Lens selector */
  .lens-select-wrap {
    position: relative;
    flex-shrink: 0;
  }

  .lens-select {
    appearance: none;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    padding: 8px 28px 8px 10px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
    min-width: 184px;
    letter-spacing: -0.1px;
  }

  .lens-select:focus { outline: none; }

  .lens-chevron {
    position: absolute;
    right: 9px;
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--text-muted);
    line-height: 1;
  }

  /* Company search input */
  .company-input-wrap {
    flex: 1;
    position: relative;
    min-width: 0;
  }

  .company-input {
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    padding: 8px 12px 8px 36px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .company-input:focus {
    outline: none;
    border-color: var(--blue);
    box-shadow: 0 0 0 3px var(--blue-glow);
  }

  .company-input::placeholder { color: var(--text-placeholder); }

  .input-search-icon {
    position: absolute;
    left: 11px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    pointer-events: none;
    display: flex;
    align-items: center;
  }

  /* Generate button */
  .generate-btn {
    background: var(--blue);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 16px;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
    letter-spacing: -0.1px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(59,130,246,0.3);
  }

  .generate-btn:hover {
    background: var(--blue-hover);
    box-shadow: 0 2px 8px rgba(59,130,246,0.3), 0 0 0 1px rgba(59,130,246,0.4);
  }

  .generate-btn:active { transform: scale(0.98); }

  .generate-btn:disabled {
    background: var(--bg-hover);
    color: var(--text-muted);
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }

  /* ── Content Area ── */
  .content-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px 28px;
    position: relative;
  }

  /* ── Empty State ── */
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    padding: 48px 24px;
  }

  .empty-wordmark {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 20px;
  }

  .empty-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.5px;
    margin-bottom: 10px;
    line-height: 1.3;
  }

  .empty-sub {
    font-size: 14px;
    color: var(--text-secondary);
    max-width: 400px;
    line-height: 1.7;
    margin-bottom: 36px;
  }

  .empty-lens-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    max-width: 560px;
    width: 100%;
  }

  .empty-lens-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 16px 14px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s, transform 0.12s;
    text-align: left;
  }

  .empty-lens-card:hover {
    background: var(--bg-elevated);
    transform: translateY(-1px);
  }

  .lens-card-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-bottom: 10px;
  }

  .lens-card-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .lens-card-desc {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .empty-divider {
    width: 40px;
    height: 1px;
    background: var(--border);
    margin: 32px auto;
  }

  .empty-features {
    display: flex;
    gap: 24px;
    justify-content: center;
    flex-wrap: wrap;
  }

  .empty-feature {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .empty-feature-icon {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    flex-shrink: 0;
  }

  /* ── Loading State ── */
  .loading-state {
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 28px;
  }

  .loading-header {
    text-align: center;
  }

  .loading-company-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.3px;
    margin-bottom: 4px;
  }

  .loading-sub {
    font-size: 12px;
    color: var(--text-muted);
  }

  .loading-track {
    width: 280px;
    height: 2px;
    background: var(--bg-elevated);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }

  .loading-bar {
    position: absolute;
    left: -60%;
    width: 60%;
    height: 100%;
    background: linear-gradient(90deg, transparent, var(--blue), transparent);
    animation: sweep 1.4s ease-in-out infinite;
    border-radius: 2px;
  }

  @keyframes sweep {
    0% { left: -60%; }
    100% { left: 100%; }
  }

  .loading-steps {
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 300px;
  }

  .loading-step {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-muted);
    padding: 9px 12px;
    border-radius: var(--radius-md);
    border: 1px solid transparent;
    transition: all 0.25s ease;
    background: transparent;
  }

  .loading-step.active {
    color: var(--text-primary);
    border-color: var(--blue-border);
    background: var(--blue-glow);
  }

  .loading-step.done {
    color: var(--green);
    border-color: var(--green-border);
    background: var(--green-dim);
  }

  .step-indicator {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1px solid currentColor;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    flex-shrink: 0;
    font-weight: 600;
    opacity: 0.6;
  }

  .loading-step.active .step-indicator,
  .loading-step.done .step-indicator { opacity: 1; }

  /* ── Error Banner ── */
  .error-banner {
    display: none;
    background: var(--red-dim);
    border: 1px solid var(--red-border);
    border-radius: var(--radius-md);
    padding: 12px 16px;
    color: var(--red);
    font-size: 12px;
    margin-bottom: 20px;
    display: none;
    align-items: center;
    gap: 8px;
  }

  /* ── Brief Output ── */
  .brief-output { display: none; max-width: 860px; }

  .brief-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 20px;
    gap: 16px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }

  .brief-company-block {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .company-avatar {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 700;
    color: white;
    flex-shrink: 0;
    letter-spacing: -0.5px;
  }

  .brief-company-name {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.4px;
    line-height: 1.2;
  }

  .brief-meta-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    flex-wrap: wrap;
  }

  .brief-timestamp {
    font-size: 11px;
    color: var(--text-muted);
  }

  .meta-sep {
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: var(--text-muted);
    opacity: 0.4;
    flex-shrink: 0;
  }

  .lens-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border: 1px solid;
  }

  .lens-badge.general {
    color: var(--lens-general);
    border-color: rgba(59,130,246,0.3);
    background: rgba(59,130,246,0.08);
  }

  .lens-badge.infrastructure {
    color: var(--lens-infra);
    border-color: var(--purple-border);
    background: var(--purple-dim);
  }

  .lens-badge.healthcare {
    color: var(--lens-health);
    border-color: var(--green-border);
    background: var(--green-dim);
  }

  .brief-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
    align-items: center;
  }

  .action-btn {
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    border-radius: var(--radius-sm);
    padding: 6px 12px;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.12s;
    display: flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
    letter-spacing: -0.1px;
  }

  .action-btn:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--border-focus);
  }

  .action-btn.copy-done {
    color: var(--green);
    border-color: var(--green-border);
    background: var(--green-dim);
  }

  /* ── Brief Content Styling ── */
  .brief-content {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .brief-content-inner {
    padding: 0;
  }

  /* Section blocks */
  .brief-content h2 {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--text-muted);
    padding: 16px 24px 12px;
    border-bottom: 1px solid var(--border-subtle);
    border-top: 1px solid var(--border);
    margin: 0;
    background: var(--bg-base);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .brief-content h2::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 12px;
    background: var(--blue);
    border-radius: 2px;
    flex-shrink: 0;
  }

  .brief-content h2:first-child {
    border-top: none;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  .brief-content h3 {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 14px 24px 6px;
  }

  .brief-content p {
    color: var(--text-secondary);
    font-size: 13px;
    margin: 0 24px 10px;
    line-height: 1.7;
  }

  .brief-content ul, .brief-content ol {
    padding: 0 24px 0 42px;
    margin-bottom: 14px;
  }

  .brief-content li {
    color: var(--text-secondary);
    font-size: 13px;
    margin-bottom: 5px;
    line-height: 1.7;
    padding-left: 2px;
  }

  .brief-content li::marker {
    color: var(--text-muted);
  }

  .brief-content strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .brief-content em {
    color: var(--text-secondary);
    font-style: italic;
  }

  .brief-content code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
    color: var(--purple);
  }

  .brief-content hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0;
  }

  /* Padding blocks between h2 sections */
  .brief-content h2 + * { margin-top: 14px; }
  .brief-content > *:last-child { margin-bottom: 20px; }

  /* ── Scrollbars ── */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--border-focus); }

  /* ── Print ── */
  @media print {
    .sidebar, .topbar, .brief-actions { display: none !important; }
    .content-area { padding: 0; overflow: visible; }
    .brief-output { display: block !important; max-width: 100%; }
    .app-shell { height: auto; overflow: visible; }
    .main-content { overflow: visible; }
    .brief-content h2 { background: #f4f4f5; color: #52525b; }
    body { background: white; color: black; }
  }

  /* ── Kbd hint ── */
  .kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text-muted);
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
    line-height: 1.6;
  }
</style>
</head>
<body>

<div class="app-shell">

  <!-- ═══ Sidebar ═══ -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-mark">OS</div>
        <span class="logo-text">OnSpot</span>
        <span class="logo-badge">v2</span>
      </div>
    </div>

    <div class="api-status">
      <div class="status-dot"></div>
      <span>Claude API &mdash; Connected</span>
    </div>

    <div class="sidebar-label">Recent Briefs</div>
    <div class="sidebar-history" id="briefHistory">
      <div class="history-empty">No briefs generated yet</div>
    </div>

    <div class="sidebar-footer">
      <span class="footer-version">Account Intelligence</span>
      <a href="/logout" class="footer-signout">Sign out</a>
    </div>
  </aside>

  <!-- ═══ Main ═══ -->
  <div class="main-content">

    <!-- Topbar -->
    <div class="topbar">
      <div class="topbar-left">

        <div class="lens-select-wrap">
          <select class="lens-select" id="industrySelect" onchange="updateLensStyle()">
            <option value="general">Enterprise SaaS</option>
            <option value="infrastructure">IT &amp; Infrastructure</option>
            <option value="healthcare">Healthcare &amp; Med Devices</option>
          </select>
          <svg class="lens-chevron" width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>

        <div class="company-input-wrap">
          <span class="input-search-icon">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"/>
              <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </span>
          <input
            type="text"
            class="company-input"
            id="companyInput"
            placeholder="Company name — e.g. Salesforce, Mayo Clinic, Dell Technologies"
            onkeydown="if(event.key==='Enter') generateBrief()"
            autocomplete="off"
            spellcheck="false"
          />
        </div>

        <button class="generate-btn" id="generateBtn" onclick="generateBrief()">
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M1 6h10" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
          Generate Brief
        </button>

      </div>
    </div>

    <!-- Content -->
    <div class="content-area" id="contentArea">

      <!-- Empty State -->
      <div class="empty-state" id="emptyState">
        <div class="empty-wordmark">OnSpot Intelligence</div>
        <div class="empty-title">Pre-call intelligence,<br>in seconds.</div>
        <div class="empty-sub">Select an industry lens, enter a target company, and get a structured brief built for enterprise
sales conversations.</div>

        <div class="empty-lens-grid">
          <div class="empty-lens-card" onclick="setLens('general')">
            <div class="lens-card-dot" style="background:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,0.15)"></div>
            <div class="lens-card-title">Enterprise SaaS</div>
            <div class="lens-card-desc">CRM, ERP, buying signals, CRO/CFO pain</div>
          </div>
          <div class="empty-lens-card" onclick="setLens('infrastructure')">
            <div class="lens-card-dot" style="background:#a855f7;box-shadow:0 0 0 3px rgba(168,85,247,0.15)"></div>
            <div class="lens-card-title">IT &amp; Infrastructure</div>
            <div class="lens-card-desc">Stack depth, cloud posture, CTO targeting</div>
          </div>
          <div class="empty-lens-card" onclick="setLens('healthcare')">
            <div class="lens-card-dot" style="background:#22c55e;box-shadow:0 0 0 3px rgba(34,197,94,0.15)"></div>
            <div class="lens-card-title">Healthcare</div>
            <div class="lens-card-desc">EMR intel, GPO, CMIO/CIO entry maps</div>
          </div>
        </div>

        <div class="empty-divider"></div>

        <div class="empty-features">
          <div class="empty-feature">
            <div class="empty-feature-icon">⚡</div>
            AI-powered research
          </div>
          <div class="empty-feature">
            <div class="empty-feature-icon">🎯</div>
            Deal-specific signals
          </div>
          <div class="empty-feature">
            <div class="empty-feature-icon">📋</div>
            Export to Markdown
          </div>
          <div class="empty-feature">
            <div class="empty-feature-icon">🕐</div>
            Session history
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div class="loading-state" id="loadingState">
        <div class="loading-header">
          <div class="loading-company-name" id="loadingCompanyName"></div>
          <div class="loading-sub">Generating intelligence brief&hellip;</div>
        </div>
        <div class="loading-track">
          <div class="loading-bar"></div>
        </div>
        <div class="loading-steps">
          <div class="loading-step" id="step1">
            <div class="step-indicator">1</div>
            Profiling target company
          </div>
          <div class="loading-step" id="step2">
            <div class="step-indicator">2</div>
            Applying industry lens
          </div>
          <div class="loading-step" id="step3">
            <div class="step-indicator">3</div>
            Mapping tech stack &amp; signals
          </div>
          <div class="loading-step" id="step4">
            <div class="step-indicator">4</div>
            Generating intelligence brief
          </div>
          <div class="loading-step" id="step5">
            <div class="step-indicator">5</div>
            Compiling final output
          </div>
        </div>
      </div>

      <!-- Error Banner -->
      <div class="error-banner" id="errorBanner" style="display:none">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style="flex-shrink:0">
          <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 5v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
        </svg>
        <span id="errorMessage"></span>
      </div>

      <!-- Brief Output -->
      <div class="brief-output" id="briefOutput">

        <div class="brief-header">
          <div class="brief-company-block">
            <div class="company-avatar" id="companyAvatar"></div>
            <div>
              <div class="brief-company-name" id="briefCompanyName"></div>
              <div class="brief-meta-row">
                <span class="brief-timestamp" id="briefTimestamp"></span>
                <div class="meta-sep"></div>
                <span id="briefLensBadge"></span>
              </div>
            </div>
          </div>
          <div class="brief-actions">
            <button class="action-btn" id="copyBtn" onclick="copyMarkdown()">
              <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                <rect x="4" y="4" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
                <path d="M2 10V2.5A1.5 1.5 0 013.5 1H10" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
              </svg>
              Copy Markdown
            </button>
            <button class="action-btn" onclick="window.print()">
              <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                <path d="M3 5V1.5A.5.5 0 013.5 1h7a.5.5 0 01.5.5V5" stroke="currentColor" stroke-width="1.3"
stroke-linecap="round"/>
                <rect x="1" y="5" width="12" height="6" rx="1.5" stroke="currentColor" stroke-width="1.3"/>
                <path d="M3 13h8M3 11h8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
              </svg>
              Export PDF
            </button>
            <button class="action-btn" onclick="newBrief()">
              <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                <path d="M7 1v12M1 7h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
              New Brief
            </button>
          </div>
        </div>

        <div class="brief-content">
          <div class="brief-content-inner" id="briefContentInner"></div>
        </div>

      </div>

    </div><!-- /content-area -->
  </div><!-- /main-content -->
</div><!-- /app-shell -->

<script>
let briefHistory = [];
let currentMarkdown = '';

try { briefHistory = JSON.parse(localStorage.getItem('onspot_history') || '[]'); } catch(e) {}

const LENS_COLORS = {
  general: '#3b82f6',
  infrastructure: '#a855f7',
  healthcare: '#22c55e'
};

const LENS_LABELS = {
  general: 'Enterprise SaaS',
  infrastructure: 'IT & Infrastructure',
  healthcare: 'Healthcare & Med Devices'
};

// ── Lens ──
function setLens(lens) {
  document.getElementById('industrySelect').value = lens;
  updateLensStyle();
  document.getElementById('companyInput').focus();
}

function updateLensStyle() {
  const lens = document.getElementById('industrySelect').value;
  const color = LENS_COLORS[lens];
  const sel = document.getElementById('industrySelect');
  sel.style.borderColor = color;
  sel.style.color = color;
}

// ── History ──
function renderHistory() {
  const container = document.getElementById('briefHistory');
  if (!briefHistory.length) {
    container.innerHTML = '<div class="history-empty">No briefs generated yet</div>';
    return;
  }
  container.innerHTML = briefHistory.slice(0, 20).map((item, i) => `
    <div class="history-item" onclick="loadHistoryItem(${i})">
      <div class="history-lens-bar" style="background:${LENS_COLORS[item.lens]}"></div>
      <div class="history-info">
        <div class="history-company">${escHtml(item.company)}</div>
        <div class="history-lens">${LENS_LABELS[item.lens]}</div>
      </div>
    </div>
  `).join('');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function loadHistoryItem(i) {
  const item = briefHistory[i];
  currentMarkdown = item.markdown || '';
  showBrief(item.company, item.lens, item.html);
  document.querySelectorAll('.history-item').forEach((el, idx) => {
    el.classList.toggle('active', idx === i);
  });
}

// ── Show Brief ──
function showBrief(company, lens, html) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('briefOutput').style.display = 'block';

  const initials = company.trim().split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const avatar = document.getElementById('companyAvatar');
  avatar.textContent = initials;
  avatar.style.background = LENS_COLORS[lens];
  avatar.style.boxShadow = `0 0 0 1px ${LENS_COLORS[lens]}40`;

  document.getElementById('briefCompanyName').textContent = company;
  document.getElementById('briefTimestamp').textContent = new Date().toLocaleDateString('en-US', { month:'short', day:'numeric',
year:'numeric' });

  const badge = document.getElementById('briefLensBadge');
  badge.innerHTML = `<span class="lens-badge ${lens}">${LENS_LABELS[lens]}</span>`;

  document.getElementById('briefContentInner').innerHTML = html;

  // Reset copy button
  const copyBtn = document.getElementById('copyBtn');
  copyBtn.classList.remove('copy-done');
  copyBtn.innerHTML = `<svg width="11" height="11" viewBox="0 0 14 14" fill="none"><rect x="4" y="4" width="9" height="9" rx="1.5"
stroke="currentColor" stroke-width="1.3"/><path d="M2 10V2.5A1.5 1.5 0 013.5 1H10" stroke="currentColor" stroke-width="1.3"
stroke-linecap="round"/></svg> Copy Markdown`;
}

// ── Generate ──
async function generateBrief() {
  const company = document.getElementById('companyInput').value.trim();
  const industry = document.getElementById('industrySelect').value;
  if (!company) { document.getElementById('companyInput').focus(); return; }

  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('briefOutput').style.display = 'none';
  document.getElementById('errorBanner').style.display = 'none';
  document.getElementById('loadingState').style.display = 'flex';
  document.getElementById('loadingCompanyName').textContent = company;
  document.getElementById('generateBtn').disabled = true;

  const steps = ['step1','step2','step3','step4','step5'];
  steps.forEach(s => {
    const el = document.getElementById(s);
    el.className = 'loading-step';
    el.querySelector('.step-indicator').textContent = s.replace('step','');
  });

  let stepIndex = 0;
  const stepInterval = setInterval(() => {
    if (stepIndex > 0) {
      const prev = document.getElementById(steps[stepIndex - 1]);
      prev.className = 'loading-step done';
      prev.querySelector('.step-indicator').textContent = '✓';
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
      const el = document.getElementById(s);
      el.className = 'loading-step done';
      el.querySelector('.step-indicator').textContent = '✓';
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Generation failed');

    currentMarkdown = data.markdown || '';

    briefHistory.unshift({ company, lens: industry, html: data.html, markdown: data.markdown, ts: Date.now() });
    briefHistory = briefHistory.slice(0, 20);
    try { localStorage.setItem('onspot_history', JSON.stringify(briefHistory)); } catch(e) {}
    renderHistory();
    document.querySelectorAll('.history-item')[0]?.classList.add('active');

    showBrief(company, industry, data.html);

  } catch(err) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('emptyState').style.display = 'flex';
    const banner = document.getElementById('errorBanner');
    document.getElementById('errorMessage').textContent = err.message;
    banner.style.display = 'flex';
  } finally {
    document.getElementById('generateBtn').disabled = false;
  }
}

// ── Copy Markdown ──
async function copyMarkdown() {
  if (!currentMarkdown) return;
  try {
    await navigator.clipboard.writeText(currentMarkdown);
    const btn = document.getElementById('copyBtn');
    btn.classList.add('copy-done');
    btn.innerHTML = `<svg width="11" height="11" viewBox="0 0 14 14" fill="none"><path d="M2 7l4 4 6-6" stroke="currentColor"
stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Copied`;
    setTimeout(() => {
      btn.classList.remove('copy-done');
      btn.innerHTML = `<svg width="11" height="11" viewBox="0 0 14 14" fill="none"><rect x="4" y="4" width="9" height="9" rx="1.5"
stroke="currentColor" stroke-width="1.3"/><path d="M2 10V2.5A1.5 1.5 0 013.5 1H10" stroke="currentColor" stroke-width="1.3"
stroke-linecap="round"/></svg> Copy Markdown`;
    }, 2000);
  } catch(e) {}
}

// ── New Brief ──
function newBrief() {
  document.getElementById('briefOutput').style.display = 'none';
  document.getElementById('emptyState').style.display = 'flex';
  document.getElementById('companyInput').value = '';
  document.getElementById('companyInput').focus();
  document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
  currentMarkdown = '';
}

// ── Init ──
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap"
rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #09090b;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    color: #fafafa;
    -webkit-font-smoothing: antialiased;
    position: relative;
    overflow: hidden;
  }

  /* Subtle background grid */
  body::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
  }

  /* Glow behind card */
  body::after {
    content: '';
    position: absolute;
    width: 600px;
    height: 400px;
    background: radial-gradient(ellipse, rgba(59,130,246,0.06) 0%, transparent 70%);
    pointer-events: none;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }

  .login-wrap {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 380px;
    padding: 20px;
  }

  .login-card {
    background: #111113;
    border: 1px solid #27272a;
    border-radius: 14px;
    padding: 36px 32px;
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.02) inset,
      0 24px 64px rgba(0,0,0,0.6),
      0 4px 16px rgba(0,0,0,0.4);
  }

  .login-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 28px;
  }

  .login-logo-mark {
    width: 30px;
    height: 30px;
    background: #3b82f6;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.3px;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.4), 0 4px 12px rgba(59,130,246,0.3);
    flex-shrink: 0;
  }

  .login-logo-text {
    font-size: 16px;
    font-weight: 600;
    color: #fafafa;
    letter-spacing: -0.3px;
  }

  .login-logo-badge {
    margin-left: auto;
    font-size: 10px;
    font-weight: 500;
    color: #52525b;
    background: #1c1c1f;
    border: 1px solid #27272a;
    border-radius: 4px;
    padding: 2px 6px;
  }

  .login-heading {
    font-size: 17px;
    font-weight: 600;
    color: #fafafa;
    letter-spacing: -0.4px;
    margin-bottom: 6px;
  }

  .login-sub {
    font-size: 13px;
    color: #71717a;
    margin-bottom: 28px;
    line-height: 1.5;
  }

  .field-label {
    display: block;
    font-size: 11px;
    font-weight: 600;
    color: #a1a1aa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 7px;
  }

  .field-wrap {
    position: relative;
    margin-bottom: 14px;
  }

  .field-icon {
    position: absolute;
    left: 11px;
    top: 50%;
    transform: translateY(-50%);
    color: #52525b;
    pointer-events: none;
    display: flex;
    align-items: center;
  }

  input[type=password] {
    width: 100%;
    background: #1c1c1f;
    border: 1px solid #27272a;
    border-radius: 8px;
    color: #fafafa;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    padding: 10px 14px 10px 36px;
    transition: border-color 0.15s, box-shadow 0.15s;
    letter-spacing: 0.5px;
  }

  input[type=password]:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
  }

  input[type=password]::placeholder { color: #3f3f46; letter-spacing: 0; }

  .login-btn {
    width: 100%;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    padding: 11px;
    cursor: pointer;
    transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
    margin-top: 4px;
    letter-spacing: -0.1px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(59,130,246,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .login-btn:hover {
    background: #2563eb;
    box-shadow: 0 4px 12px rgba(59,130,246,0.3), 0 0 0 1px rgba(59,130,246,0.4);
  }

  .login-btn:active { transform: scale(0.99); }

  .error-box {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 7px;
    padding: 10px 12px;
    color: #ef4444;
    font-size: 12px;
    margin-bottom: 18px;
    line-height: 1.4;
  }

  .login-footer {
    margin-top: 20px;
    text-align: center;
    font-size: 11px;
    color: #3f3f46;
  }
</style>
</head>
<body>
<div class="login-wrap">
  <div class="login-card">

    <div class="login-logo">
      <div class="login-logo-mark">OS</div>
      <span class="login-logo-text">OnSpot</span>
      <span class="login-logo-badge">Sales Intel</span>
    </div>

    <div class="login-heading">Welcome back</div>
    <div class="login-sub">Sign in to access your account intelligence workspace.</div>

    {% if error %}
    <div class="error-box">
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style="flex-shrink:0">
        <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
        <path d="M8 5v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="8" cy="11.5" r="0.75" fill="currentColor"/>
      </svg>
      {{ error }}
    </div>
    {% endif %}

    <form method="POST" autocomplete="off">
      <label class="field-label">Password</label>
      <div class="field-wrap">
        <span class="field-icon">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <rect x="3" y="7" width="10" height="8" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
            <path d="M5 7V5a3 3 0 016 0v2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <circle cx="8" cy="11" r="1" fill="currentColor"/>
          </svg>
        </span>
        <input type="password" name="password" placeholder="Enter your password" autofocus/>
      </div>

      <button type="submit" class="login-btn">
        Sign In
        <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
          <path d="M1 7h12M8 2l5 5-5 5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </form>

  </div>
  <div class="login-footer">
    OnSpot &mdash; Account Intelligence Platform &middot; For AE use only
  </div>
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
