# 🚀 Youth Ideathon Automated Idea Submission Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright" />
  <img src="https://img.shields.io/badge/Browser-Google%20Chrome-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chrome" />
  <img src="https://img.shields.io/badge/Platform-Youth%20Ideathon-FF5722?style=for-the-badge" alt="Youth Ideathon" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

An intelligent, resilient, and human-like automation pipeline built with **Playwright Python** to sequentially batch-submit innovation proposals to the [Youth Ideathon Portal](https://youthideathon.in/submit-your-idea/).

Includes **interactive startup prompts**, native **Markdown (`Idea.md`) parsing**, **dynamic AJAX mentor lookup**, **Cloudflare Turnstile bypass**, **character validation**, **idempotent re-runs**, and **automatic screenshot auditing**.

---

## 📑 Table of Contents
- [Key Features](#-key-features)
- [Workflow Architecture](#-workflow-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Quick Start](#-quick-start)
  - [1. Interactive Mode (Default)](#1-interactive-mode-default)
  - [2. Dry-Run Mode (Safe Verification)](#2-dry-run-mode-safe-verification)
  - [3. Non-Interactive CLI Mode](#3-non-interactive-cli-mode)
  - [4. Targeted Submission](#4-targeted-submission)
- [Idea Catalog Format (`Idea.md`)](#-idea-catalog-format-ideamd)
  - [Standard Idea Template](#standard-idea-template)
  - [IRCTC Challenge Theme Template](#irctc-challenge-theme-template)
  - [Allowed Form Field Values](#allowed-form-field-values)
- [CLI Reference](#-cli-reference)
- [Audit Logging & Evidence](#-audit-logging--evidence)
- [Cloudflare Bypass Mechanism](#-cloudflare-bypass-mechanism)
- [License](#-license)

---

## 🌟 Key Features

- **Interactive Startup Wizard**: On launch, interactively configures participation type (*Team* or *Individual*), SIDs, and exact mentor string with sensible defaults.
- **Native Markdown Parser (`Idea.md`)**: Write and review ideas in formatted Markdown. Supports standard themes, IRCTC sub-themes, and custom blockquotes.
- **Dynamic AJAX Mentor Resolution**: Inputs primary SID (`YI26-11860`) and dispatches native `blur`/`change` events to trigger the portal's AJAX lookup (`action: yi26_get_mentors_by_sid`), automatically polling until the mentor option loads.
- **Dynamic Dropdown Handler**: Accurately selects options across origin, stage, projected reach, why great, main theme, and conditional IRCTC sub-themes.
- **Strict Pre-Validation**: Verifies idea descriptions are strictly $\le 500$ characters before launching or touching the browser, preventing form submission rejections.
- **Undetectable Cloudflare Clearance**: Leverages persistent browser profiles with stealth flags (`--disable-blink-features=AutomationControlled`) to pass Cloudflare Turnstile verification.
- **Human-Like Pacing**:
  - $1.0\text{s} - 3.0\text{s}$ randomized pause between field inputs.
  - $8.0\text{s} - 12.0\text{s}$ randomized cooldown between idea submissions.
- **Full Idempotency**: Automatically reads [`submission_log.csv`](submission_log.csv) on startup and skips ideas already marked `SUCCESS`. Safe to re-run anytime.
- **Fault-Tolerant Retries**: Retries failed attempts once with diagnostic error screenshots without crashing the batch run.
- **Audit Trails & Screenshots**: Captures pre-submission, dry-run, and confirmation screenshots for every idea into the `screenshots/` directory.

---

## 🔄 Workflow Architecture

```mermaid
flowchart TD
    A([Start: submit_ideas.py]) --> B[Interactive Configuration Wizard\nTeam/Indiv, SID 1/2/3, Mentor]
    B --> C[Load Ideas from Idea.md / JSON / CSV]
    C --> D[Read submission_log.csv\nFilter already SUCCESS ideas]
    D --> E{Remaining ideas?}
    E -- No --> Z([All Ideas Processed - Exit])
    E -- Yes --> F[Select Next Idea]
    F --> G{Description <= 500 chars?}
    G -- No --> H[Log VALIDATION_ERROR\nSkip browser interaction]
    H --> E
    G -- Yes --> I[Launch Persistent Chrome Session]
    I --> J[Clear Cloudflare Turnstile]
    J --> K[Fill Participation Type & Primary SID]
    K --> L[Trigger Blur & AJAX Mentor Lookup]
    L --> M[Select Exact Mentor & Teammate SIDs]
    M --> N[Fill Origin, Stage, Reach, Theme & Description]
    N --> O{Mode == Dry-Run?}
    O -- Yes --> P[Capture Screenshot\nLog DRY_RUN - Do Not Submit]
    P --> T[Inter-submission Delay: 8-12s]
    O -- No --> Q[Click 'Submit Idea'\nWait for /thank-you]
    Q -- Success --> R[Capture Screenshot\nLog SUCCESS]
    Q -- Fail --> S[Capture Error Shot\nRetry 1x -> Log FAILED]
    R --> T
    S --> T
    T --> E
```

---

## 📂 Project Structure

```text
Youth-Ideathon-Bot/
├── Idea.md               # Primary idea catalog in clean Markdown
├── ideas.json            # JSON export of ideas catalog
├── ideas.csv             # CSV export of ideas catalog
├── submit_ideas.py       # Core Playwright automation & CLI engine
├── submission_log.csv    # Audit log recording timestamps, statuses & proof paths
├── screenshots/          # Full-page verification & confirmation screenshots
├── .gitignore            # Git exclusion rules (Chrome profiles, logs)
└── README.md             # Project documentation
```

---

## 🛠️ Prerequisites & Installation

### 1. Requirements
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: Version 3.10, 3.11, or 3.12
- **Browser**: Google Chrome or Microsoft Edge installed

### 2. Clone the Repository
```powershell
git clone https://github.com/rKyzen/Youth-Ideathon-Bot.git
cd Youth-Ideathon-Bot
```

### 3. Install Python Dependencies
```powershell
pip install playwright beautifulsoup4
playwright install chromium
```

---

## 🚀 Quick Start

### 1. Interactive Mode (Default)
Run the script directly in your terminal. You will be prompted to confirm or customize the parameters:

```powershell
python submit_ideas.py
```

```text
==============================================================
      YOUTH IDEATHON 2026 - SUBMISSION CONFIGURATION
==============================================================
Press [Enter] to accept the suggested default value in [brackets].

1. Participation Type (Team / Individual) [Team]: 
2. SID 1 (Primary Student ID) [YI26-11860]: 
3. SID 2 (Teammate 1 SID) [YI26-08461]: 
4. SID 3 (Teammate 2 SID) [YI26-09892]: 
5. Mentor Name (exact detail, e.g. Name (Stream)) [Umesh Verma (ATL)]: 

--- Active Submission Parameters ---
Participation Type : Team
Primary SID (SID 1): YI26-11860
Teammate 1 (SID 2) : YI26-08461
Teammate 2 (SID 3) : YI26-09892
Mentor (Exact)     : Umesh Verma (ATL)
==============================================================
```

### 2. Dry-Run Mode (Safe Verification)
Populates all fields on the live portal, captures a full-page verification screenshot in `screenshots/`, and exits **without** clicking submit:

```powershell
# Dry run for all ideas
python submit_ideas.py --dry-run

# Dry run for just the first idea
python submit_ideas.py --dry-run --single-dry-run
```

### 3. Non-Interactive CLI Mode
Ideal for scheduled tasks, batch scripts, or CI/CD pipelines:

```powershell
python submit_ideas.py `
  --non-interactive `
  --participation-type Team `
  --primary-sid "YI26-11860" `
  --sid-2 "YI26-08461" `
  --sid-3 "YI26-09892" `
  --mentor "Umesh Verma (ATL)"
```

### 4. Targeted Submission
Submit or dry-run a specific idea ID:

```powershell
python submit_ideas.py --dry-run --idea-id IDEA-03
```

---

## 📝 Idea Catalog Format (`Idea.md`)

The engine natively parses ideas from [`Idea.md`](Idea.md). Add your ideas using the following Markdown schema:

### Standard Idea Template

```markdown
### IDEA-01: Smart Solar PV Self-Cleaning & Dust Detection Ring
- **Theme:** Sustainability
- **Origin:** I faced this problem
- **Stage:** Early Prototyping Stage
- **3-Year Projected Users:** 1,00,000
- **Why Great:** It solves a problem faced by many people
- **Description:**
> An automated, water-free wiper frame using electrostatic micro-brushes and solar-powered edge rollers. Dust accumulation reduces solar panel efficiency by up to 30% in dusty climates; this system tracks light reduction using photo-sensors and initiates automated mechanical dusting during non-peak hours, increasing net clean energy output without wasting potable water.
```

### IRCTC Challenge Theme Template

When targeting the **IRCTC challenge**, declare the sub-theme either in parentheses or with `- **IRCTC Sub-theme:**`:

```markdown
### IDEA-03: AI Edge Vision for Real-Time Railway Track Debris Warning
- **Theme:** IRCTC challenge (IRCTC- One Stop Shop Travel Solution)
- **Origin:** I read something like this in a book or internet
- **Stage:** Idea Stage
- **3-Year Projected Users:** 10,00,000
- **Why Great:** It solves a problem that has been unsolved for ages
- **Description:**
> A solar-backed edge computing camera node for rail crossings and blind bends. Running lightweight YOLO vision models on local micro-NPUs, it detects fallen boulders, stalled vehicles, and wildlife intrusions within 300m, transmitting low-latency RF warning signals directly to locomotive telemetry and local signal boxes before visual range.
```

---

### Allowed Form Field Values

| Field | Accepted Exact Values on Portal |
|---|---|
| **Theme** | `AI and Chip Innovation`, `Sustainability`, `Space`, `Next Billion Innovation Challenge`, `Supporting Girl Entrepreneurs`, `EdTech`, `IRCTC challenge`, `Open Innovation` |
| **IRCTC Sub-theme** | `Innovation and Improvements in Railway Catering Services`, `Packaged Drinking Water`, `IRCTC- One Stop Shop Travel Solution`, `Think Ticketing, Think IRCTC` |
| **Origin** | `I read something like this in a book or internet`, `I faced this problem`, `My family or close friends faced this problem`, `I got this during a discussion with someone`, `From my teacher or mentor`, `Can't remember` |
| **Stage** | `Idea Stage`, `User Research Stage`, `Design Stage`, `Early Prototyping Stage`, `Prototype Validation Stage`, `Already have few customers` |
| **3-Year Projected Users** | `Less than 1,000`, `1,000`, `25,000`, `1,00,000`, `10,00,000`, `More than 10,00,000` |
| **Why Great** | `It solves a problem faced by many people`, `It solves a problem that has been unsolved for ages`, `I have already developed the solution`, `It is very innovative`, `It uses new technology`, `Other` |
| **Description** | Free text strictly **$\le 500$ characters**. |

---

## ⚙️ CLI Reference

| Flag | Default | Description |
|---|---|---|
| `--data-file <path>` | Auto-detects `Idea.md` | Path to `Idea.md`, `ideas.json`, or `ideas.csv` |
| `--dry-run` | `False` | Fills form and saves screenshot without submitting |
| `--single-dry-run` | `False` | Halts execution after one dry-run idea |
| `--idea-id <ID>` | `None` | Filters run to a specific idea (e.g. `IDEA-05`) |
| `--max-ideas <N>` | `None` | Caps total ideas submitted in the session |
| `--non-interactive` | `False` | Bypasses interactive startup prompts |
| `--participation-type` | `Team` | `Team` or `Individual` |
| `--primary-sid <SID>` | `YI26-11860` | Primary student ID (SID 1) |
| `--sid-2 <SID>` | `YI26-08461` | Teammate 1 ID (SID 2) |
| `--sid-3 <SID>` | `YI26-09892` | Teammate 2 ID (SID 3) |
| `--mentor <name>` | `Umesh Verma (ATL)` | Exact mentor text to select from dynamic list |
| `--headless` | `False` | Run browser in headless mode |
| `--log-file <path>` | `submission_log.csv` | Output audit CSV filepath |
| `--delay-inputs-min` | `1.0` | Minimum seconds between field inputs |
| `--delay-inputs-max` | `3.0` | Maximum seconds between field inputs |
| `--delay-submit-min` | `8.0` | Minimum cooldown between submissions (seconds) |
| `--delay-submit-max` | `12.0` | Maximum cooldown between submissions (seconds) |

---

## 📊 Audit Logging & Evidence

Every submission is appended to [`submission_log.csv`](submission_log.csv) with columns:
`idea_id, title, status, timestamp, screenshot_path, notes`

### Status Glossary
- `SUCCESS`: Submission verified and redirected to `/thank-you`.
- `DRY_RUN`: All inputs populated and screenshot saved; submit was not clicked.
- `SKIPPED`: Already recorded as `SUCCESS` in previous runs (idempotency).
- `VALIDATION_ERROR`: Description exceeded 500 characters; blocked before browser launch.
- `FAILED`: Submission failed twice; diagnostic screenshot captured.

---

## 🛡️ Cloudflare Bypass Mechanism

The Youth Ideathon website utilizes **Cloudflare Turnstile** protection. Standard automated browsers are blocked by `navigator.webdriver` detection.

This automation utilizes:
1. **Persistent Chrome User Context** (`launch_persistent_context`).
2. `--disable-blink-features=AutomationControlled` to remove browser fingerprint flags.
3. Disabled automation extension (`ignore_default_args=["--enable-automation"]`).
4. Native window focus to clear challenges seamlessly without third-party captcha solvers.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">
  <b>Built for Youth Ideathon 2026 Innovation Submissions</b>
</p>
