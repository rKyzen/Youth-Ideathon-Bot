# 🚀 Youth Ideathon Automated Idea Submission Bot & Web Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright" />
  <img src="https://img.shields.io/badge/FastAPI-Local%20Web%20GUI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Browser-Google%20Chrome-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chrome" />
  <img src="https://img.shields.io/badge/Platform-Youth%20Ideathon-FF5722?style=for-the-badge" alt="Youth Ideathon" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

An intelligent, resilient, and human-like automation pipeline and **local web GUI dashboard** built with **Playwright Python** and **FastAPI** to sequentially batch-submit innovation proposals to the [Youth Ideathon Portal](https://youthideathon.in/submit-your-idea/).

Includes a **modern Web UI on `http://localhost:8000`**, **live terminal log streaming**, **real-time ETA countdown**, **in-browser idea editor**, **AI agent prompt generator**, **dynamic AJAX mentor lookup**, **Cloudflare Turnstile bypass**, and **full-page screenshot auditing**.

---

## 📑 Table of Contents
- [Local Web GUI Dashboard](#-local-web-gui-dashboard-localhost8000)
- [Key Features](#-key-features)
- [Workflow Architecture](#-workflow-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Quick Start](#-quick-start)
  - [1. Launch Web Dashboard (Recommended)](#1-launch-web-dashboard-recommended)
  - [2. Terminal Interactive Mode](#2-terminal-interactive-mode)
  - [3. Dry-Run Mode (Safe Verification)](#3-dry-run-mode-safe-verification)
  - [4. Non-Interactive CLI Mode](#4-non-interactive-cli-mode)
- [AI Agent Prompt to Generate `Idea.md`](#-ai-agent-prompt-to-generate-ideamd)
- [Idea Catalog Format (`Idea.md`)](#-idea-catalog-format-ideamd)
  - [Standard Idea Template](#standard-idea-template)
  - [IRCTC Challenge Theme Template](#irctc-challenge-theme-template)
  - [Allowed Form Field Values](#allowed-form-field-values)
- [Estimated Completion Time (ETA)](#-estimated-completion-time-eta)
- [CLI Reference](#-cli-reference)
- [Audit Logging & Evidence](#-audit-logging--evidence)
- [Cloudflare Bypass Mechanism](#-cloudflare-bypass-mechanism)
- [License](#-license)

---

## 🖥️ Local Web GUI Dashboard (`localhost:8000`)

Run one command to launch the full-featured web console:

```powershell
python app.py
```

The browser opens automatically to **`http://localhost:8000`**, featuring:
- **Dashboard Stats**: Real-time cards for total ideas, submitted count, ETA remaining, and target finish time.
- **Dynamic Configuration Form**: Toggle *Team* vs *Individual*, edit Primary SID, Teammate SIDs, target Mentor, and catalog path.
- **AI Prompt Generator**: Choose your domain (*Electronics*, *Software*, *Mixed*), preview the custom prompt, and click **"Copy"** to paste into ChatGPT, Claude, or Gemini.
- **In-Browser Markdown Editor**: Edit and validate [`Idea.md`](Idea.md) directly on the web with instant character length validation.
- **Real-time Live Console**: Server-Sent Events (SSE) stream terminal logs live into an autoscrolling dark-mode console.
- **Screenshot Proof Gallery**: Visual grid of all captured full-page screenshots with click-to-zoom modal preview.
- **Dual Controls**: One-click **"Start Full Submission"** and **"Run Dry-Run Test"** buttons with live cancellation.

---

## 🌟 Key Features

- **Web GUI & Terminal Interfaces**: Choose between a rich local web interface or interactive command-line prompts.
- **Built-in AI Idea Generator**: Select your domain, and the tool outputs an optimized prompt ready to paste into ChatGPT, Claude, or Gemini to generate `Idea.md`.
- **Dynamic File Locator**: Browse or specify custom idea files on disk with validation.
- **Estimated Completion Time (ETA)**: Calculates batch ETA upfront and dynamically updates countdown and clock finish time after every submission.
- **Direct Sequential Submission**: Submits all ideas present in the catalog file sequentially without arbitrary skipping.
- **Native Markdown Parser (`Idea.md`)**: Full support for standard themes, IRCTC sub-themes, and blockquotes.
- **Dynamic AJAX Mentor Resolution**: Types Primary SID (`YI26-11860`) and dispatches `blur`/`change` events to trigger the portal's AJAX lookup (`action: yi26_get_mentors_by_sid`), automatically polling until the mentor option loads.
- **Dynamic Dropdown Handler**: Accurately selects options across origin, stage, projected reach, why great, main theme, and conditional IRCTC sub-themes.
- **Strict Pre-Validation**: Verifies idea descriptions are strictly $\le 500$ characters before launching the browser.
- **Undetectable Cloudflare Clearance**: Leverages persistent browser profiles with stealth flags (`--disable-blink-features=AutomationControlled`) to pass Cloudflare Turnstile verification.
- **Human-Like Pacing**:
  - $1.0\text{s} - 3.0\text{s}$ randomized pause between field inputs.
  - $8.0\text{s} - 12.0\text{s}$ randomized cooldown between submissions.
- **Fault-Tolerant Retries**: Retries failed attempts once with diagnostic error screenshots without crashing the batch run.
- **Audit Trails & Evidence**: Captures full-page screenshots for every idea into the `screenshots/` directory and logs to [`submission_log.csv`](submission_log.csv).

---

## 🔄 Workflow Architecture

```mermaid
flowchart TD
    A([Launch: python app.py / submit_ideas.py]) --> B{GUI or Terminal?}
    B -- Web GUI --> C[Open http://localhost:8000\nConfigure via Web Form]
    B -- Terminal --> D[Interactive Terminal Prompts\nTeam/Indiv, SIDs, Mentor]
    C --> E[Select Domain & Copy AI Prompt for Idea.md]
    D --> E
    E --> F[Load Idea.md & Compute ETA Upfront]
    F --> G{More ideas to submit?}
    G -- No --> Z([Batch Complete!])
    G -- Yes --> H[Select Next Idea]
    H --> I{Description <= 500 chars?}
    I -- No --> J[Log VALIDATION_ERROR\nSkip browser interaction]
    J --> G
    I -- Yes --> K[Launch Persistent Chrome Session]
    K --> L[Clear Cloudflare Turnstile]
    L --> M[Fill Participation Type & Primary SID]
    M --> N[Trigger Blur & AJAX Mentor Lookup]
    N --> O[Select Exact Mentor & Teammate SIDs]
    O --> P[Fill Origin, Stage, Reach, Theme & Description]
    P --> Q{Mode == Dry-Run?}
    Q -- Yes --> R[Capture Screenshot\nLog DRY_RUN - Do Not Submit]
    R --> U[Cooldown Delay: 8-12s]
    Q -- No --> S[Click 'Submit Idea'\nWait for /thank-you]
    S -- Success --> T[Capture Screenshot\nLog SUCCESS]
    S -- Fail --> V[Capture Error Shot\nRetry 1x -> Log FAILED]
    T --> U
    V --> U
    U --> G
```

---

## 📂 Project Structure

```text
Youth-Ideathon-Bot/
├── app.py                # FastAPI local web GUI server
├── templates/
│   └── index.html        # Modern Tailwind CSS dashboard
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
pip install playwright fastapi "uvicorn[standard]" jinja2 beautifulsoup4
playwright install chromium
```

---

## 🚀 Quick Start

### 1. Launch Web Dashboard (Recommended)
```powershell
python app.py
```
Open **`http://localhost:8000`** in your browser to configure and run visually.

### 2. Terminal Interactive Mode
```powershell
python submit_ideas.py
```

### 3. Dry-Run Mode (Safe Verification)
```powershell
# Dry-run all ideas
python submit_ideas.py --dry-run

# Dry-run only the first idea
python submit_ideas.py --dry-run --single-dry-run
```

### 4. Non-Interactive CLI Mode
```powershell
python submit_ideas.py `
  --non-interactive `
  --participation-type Team `
  --primary-sid "YI26-11860" `
  --sid-2 "YI26-08461" `
  --sid-3 "YI26-09892" `
  --mentor "Umesh Verma (ATL)" `
  --data-file "Idea.md"
```

---

## 🤖 AI Agent Prompt to Generate `Idea.md`

You can copy and paste the prompt below into ChatGPT, Claude, or Gemini to produce a ready-to-run `Idea.md`:

```text
You are an expert school/college innovation mentor for the Youth Ideathon 2026 competition.
Please generate an 'Idea.md' markdown file containing 10-15 novel, practical, and highly impactful
ideas in the domain: [Electronics / Software / Mixed].

Every idea MUST adhere strictly to the following markdown template:

### IDEA-01: [Title of Idea]
- **Theme:** [Select ONE: AI and Chip Innovation | Sustainability | Space | Next Billion Innovation Challenge | Supporting Girl Entrepreneurs | EdTech | IRCTC challenge | Open Innovation]
- **Origin:** [Select ONE: I read something like this in a book or internet | I faced this problem | My family or close friends faced this problem | I got this during a discussion with someone | From my teacher or mentor | Can't remember]
- **Stage:** [Select ONE: Idea Stage | User Research Stage | Design Stage | Early Prototyping Stage | Prototype Validation Stage | Already have few customers]
- **3-Year Projected Users:** [Select ONE: Less than 1,000 | 1,000 | 25,000 | 1,00,000 | 10,00,000 | More than 10,00,000]
- **Why Great:** [Select ONE: It solves a problem faced by many people | It solves a problem that has been unsolved for ages | I have already developed the solution | It is very innovative | It uses new technology | Other]
- **Description:**
> [Clear description strictly UNDER 500 characters explaining the problem, hardware/software architecture, and real-world impact. DO NOT EXCEED 500 CHARACTERS.]

*Important Guidelines:*
1. If Theme is 'IRCTC challenge', format as:
   - **Theme:** IRCTC challenge (Sub-theme)
   where Sub-theme is ONE of:
   - Innovation and Improvements in Railway Catering Services
   - Packaged Drinking Water
   - IRCTC- One Stop Shop Travel Solution
   - Think Ticketing, Think IRCTC
2. Ensure the description character count is strictly between 250 and 480 characters.
3. Do not include markdown code fence blocks inside descriptions.
```

---

## 📝 Idea Catalog Format (`Idea.md`)

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

## ⏱️ Estimated Completion Time (ETA)

At the start of execution, the engine calculates ETA upfront and reports dynamic progress:

```text
[INFO] ==============================================================
[INFO] [BATCH] Batch Submission Initialized
[INFO] [BATCH] Total Ideas to Submit : 15
[INFO] [ETA] Estimated Total Time    : ~7m 45s (~31s per idea)
[INFO] [ETA] Target Completion Time  : 13:15:29
[INFO] ==============================================================

[INFO] ==============================================================
[INFO] [SUBMITTING] (1/15): [IDEA-01] Smart Solar PV Self-Cleaning & Dust Detection Ring
[INFO] [ETA] Est. Remaining Time : ~7m 45s (Finish ~13:15:30)
[INFO] ==============================================================
...
[INFO] Completed [IDEA-01] in 28.2s -> Status: DRY_RUN
```

---

## ⚙️ CLI Reference

| Flag | Default | Description |
|---|---|---|
| `--data-file <path>` | Auto-detects `Idea.md` | Path to `Idea.md`, `ideas.json`, or `ideas.csv` |
| `--dry-run` | `False` | Fills form and saves screenshot without submitting |
| `--single-dry-run` | `False` | Halts execution after one dry-run idea |
| `--idea-id <ID>` | `None` | Filters run to a specific idea (e.g. `IDEA-05`) |
| `--max-ideas <N>` | `None` | Caps total ideas submitted in the session |
| `--skip-existing` | `False` | Only skips ideas if explicitly passed |
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
- `SKIPPED`: Marked as skipped only if `--skip-existing` is supplied.
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
