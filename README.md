# Youth Ideathon 2026 - Idea Submission Automation

Automated submission pipeline built with Playwright Python for sequentially submitting ideas to [Youth Ideathon](https://youthideathon.in/submit-your-idea/).

---

## Interactive Startup Experience

When launched without `--non-interactive`, the CLI prompts interactively for session parameters (with default fallbacks when pressing `[Enter]`):

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

If **Individual** is selected, Teammate SID prompts are automatically bypassed.

---

## Idea Catalog Format (`Idea.md`)

The script natively reads and parses ideas directly from [`Idea.md`](file:///c:/Users/Atomix/Documents/script/Idea.md). You can add, edit, or remove ideas using standard Markdown format.

### Template / Schema

````markdown
### IDEA-01: Smart Solar PV Self-Cleaning & Dust Detection Ring
- **Theme:** Sustainability
- **Origin:** I faced this problem
- **Stage:** Early Prototyping Stage
- **3-Year Projected Users:** 1,00,000
- **Why Great:** It solves a problem faced by many people
- **Description:**
> An automated, water-free wiper frame using electrostatic micro-brushes and solar-powered edge rollers. Dust accumulation reduces solar panel efficiency by up to 30% in dusty climates; this system tracks light reduction using photo-sensors and initiates automated mechanical dusting during non-peak hours, increasing net clean energy output without wasting potable water.
````

### For IRCTC Challenge Themes

For ideas under the **IRCTC challenge**, specify the sub-theme either in parentheses or using `- **IRCTC Sub-theme:**`:

````markdown
### IDEA-03: AI Edge Vision for Real-Time Railway Track Debris Warning
- **Theme:** IRCTC challenge (IRCTC- One Stop Shop Travel Solution)
- **Origin:** I read something like this in a book or internet
- **Stage:** Idea Stage
- **3-Year Projected Users:** 10,00,000
- **Why Great:** It solves a problem that has been unsolved for ages
- **Description:**
> A solar-backed edge computing camera node for rail crossings and blind bends. Running lightweight YOLO vision models on local micro-NPUs, it detects fallen boulders, stalled vehicles, and wildlife intrusions within 300m, transmitting low-latency RF warning signals directly to locomotive telemetry and local signal boxes before visual range.
````

### Field Value Reference

| Field | Allowed Values |
|---|---|
| **Theme** | `AI and Chip Innovation`, `Sustainability`, `Space`, `Next Billion Innovation Challenge`, `Supporting Girl Entrepreneurs`, `EdTech`, `IRCTC challenge`, `Open Innovation` |
| **IRCTC Sub-theme** | `Innovation and Improvements in Railway Catering Services`, `Packaged Drinking Water`, `IRCTC- One Stop Shop Travel Solution`, `Think Ticketing, Think IRCTC` |
| **Origin** | `I read something like this in a book or internet`, `I faced this problem`, `My family or close friends faced this problem`, `I got this during a discussion with someone`, `From my teacher or mentor`, `Can't remember` |
| **Stage** | `Idea Stage`, `User Research Stage`, `Design Stage`, `Early Prototyping Stage`, `Prototype Validation Stage`, `Already have few customers` |
| **3-Year Projected Users** | `Less than 1,00,000`, `1,000`, `25,000`, `1,00,000`, `10,00,000`, `More than 10,00,000` |
| **Why Great** | `It solves a problem faced by many people`, `It solves a problem that has been unsolved for ages`, `I have already developed the solution`, `It is very innovative`, `It uses new technology`, `Other` |
| **Description** | Plain text / blockquote strictly $\le 500$ characters. |

---

## Features

- **Interactive Startup Prompt**: User can configure Team/Individual, SIDs, and exact Mentor on startup.
- **Dynamic AJAX Mentor Resolution**: Inputs primary SID (`YI26-11860`) and fires `blur`/`change` events to trigger the AJAX lookup (`action: yi26_get_mentors_by_sid`), polling until `"Umesh Verma (ATL)"` is loaded.
- **Dynamic Dropdown Selection**: Text-based matching for standard and dynamic dropdowns (Theme, IRCTC sub-theme, Stage, Origin, Impact, Mentor).
- **Strict Character Validation**: Validates that idea descriptions are strictly $\le 500$ characters before any browser interaction.
- **Cloudflare Bypass**: Uses a persistent Chrome context with stealth flags (`--disable-blink-features=AutomationControlled`, disabled automation extension) to seamlessly pass Cloudflare Turnstile bot detection.
- **Human-like Delays**:
  - $1.0\text{s} - 3.0\text{s}$ randomized pause between input fields.
  - $8.0\text{s} - 12.0\text{s}$ randomized pause between submissions.
- **Dry-run Mode (`--dry-run`)**: Populates all inputs, captures full-page screenshot into `screenshots/`, logs state, and terminates before clicking the final submit button.
- **Resilient & Idempotent**:
  - Logs execution results to [`submission_log.csv`](file:///c:/Users/Atomix/Documents/script/submission_log.csv).
  - Skips any idea already marked `SUCCESS` in the log.
  - Automatically retries once per failed idea before continuing to the next idea.

---

## Usage

### 1. Interactive Execution (Recommended)
Prompts for Team/Individual, SIDs, and Mentor in terminal:
```powershell
python submit_ideas.py
```

### 2. Dry-Run Mode
Test form population and capture verification screenshots without submitting:
```powershell
python submit_ideas.py --dry-run
```

### 3. Non-Interactive / CI Execution
Bypass interactive prompts using command-line arguments:
```powershell
python submit_ideas.py --non-interactive --participation-type Team --primary-sid YI26-11860 --sid-2 YI26-08461 --sid-3 YI26-09892 --mentor "Umesh Verma (ATL)"
```

### 4. Target a Specific Idea
```powershell
python submit_ideas.py --dry-run --idea-id IDEA-03
```

---

## Pushing to GitHub

To push this repository to GitHub:

```powershell
# 1. Initialize git (if not already done)
git init -b main

# 2. Add files and commit
git add .
git commit -m "Youth Ideathon Playwright automation with interactive prompt and Idea.md support"

# 3. Add your remote GitHub repository URL and push
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
git push -u origin main
```
