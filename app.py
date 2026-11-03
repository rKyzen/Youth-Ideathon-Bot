"""
Youth Ideathon 2026 - Local Web GUI & Automation Hub
---------------------------------------------------
FastAPI backend providing a web-based localhost dashboard for Youth Ideathon submissions:
- Real-time SSE streaming for live console logs and ETA countdown
- Form parameters configuration (Team/Individual, SIDs, Mentor)
- Markdown idea catalog editor & character validator
- Built-in AI prompt generator for ChatGPT/Claude/Gemini
- Live screenshot evidence gallery
"""

import asyncio
import base64
import json
import logging
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

# In PyInstaller --windowed builds sys.stdin/stdout/stderr can be None.
# Replace them with devnull streams before importing/initialising libraries
# that inspect them (uvicorn calls sys.stdout.isatty() during logging setup,
# which crashes a windowed EXE silently).
if sys.stdin is None:
    sys.stdin = open(os.devnull, "r", encoding="utf-8", errors="replace")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")

# For frozen builds, run from the EXE folder before importing the submission
# module, so its log file and screenshot/profile paths resolve next to the EXE
# regardless of the working directory Explorer/shortcuts start us in.
if getattr(sys, "frozen", False):
    try:
        os.chdir(Path(sys.executable).resolve().parent)
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Import core submission utilities
from submit_ideas import (
    LOG_CSV_FILE,
    SCREENSHOTS_DIR,
    USER_DATA_DIR,
    chrome_channel,
    fill_form_for_idea,
    format_duration,
    get_successful_idea_ids,
    load_ideas,
    log_result,
    parse_markdown_ideas,
    process_idea,
)

# Ensure UTF-8 output encoding across Windows consoles
if sys.platform == "win32":
    try:
        if sys.stdout.encoding.lower() != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr.encoding.lower() != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _app_base_dir() -> Path:
    """Directory where runtime files (logs, screenshots, profile) are written."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resource_dir() -> Path:
    """Directory containing bundled read-only resources (templates)."""
    return Path(getattr(sys, "_MEIPASS", _app_base_dir()))


APP_DIR = _app_base_dir()
RESOURCE_DIR = _resource_dir()

# Run with the app folder as working directory so relative runtime paths
# (screenshots, logs, chrome profile) resolve correctly in the frozen EXE.
try:
    os.chdir(APP_DIR)
except Exception:
    pass

# Ensure directories exist
Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
(RESOURCE_DIR / "templates").mkdir(parents=True, exist_ok=True)

# On first run from a fresh folder, materialise the bundled catalog files next
# to the EXE so relative reads/writes (Idea.md, ideas.json, ideas.csv) work.
for _data_name in ("Idea.md", "ideas.json", "ideas.csv"):
    _src = RESOURCE_DIR / _data_name
    _dest = APP_DIR / _data_name
    if _src.exists() and _src.resolve() != _dest.resolve() and not _dest.exists():
        try:
            shutil.copy2(_src, _dest)
        except Exception:
            pass

app = FastAPI(title="Youth Ideathon Automation Console")
templates = Jinja2Templates(directory=str(RESOURCE_DIR / "templates"))
app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")

# SSE Subscriber Queues
sse_subscribers: Set[asyncio.Queue] = set()

# Global State Tracker
runner_state = {
    "status": "idle",  # idle, running, completed, stopped, error
    "current_idea_text": "Ready to begin",
    "total_ideas": 0,
    "completed_ideas": 0,
    "eta_seconds": 0,
    "eta_str": "--",
    "finish_clock": "--",
    "is_dry_run": False
}

active_task: Optional[asyncio.Task] = None


class LogBroadcastHandler(logging.Handler):
    """Custom logging handler to broadcast logs to all connected web clients."""
    def emit(self, record):
        try:
            msg = self.format(record)
            payload = json.dumps({"type": "log", "message": msg})
            for q in list(sse_subscribers):
                try:
                    q.put_nowait(payload)
                except Exception:
                    pass
        except Exception:
            pass


# Attach broadcast handler to automation logger
log_handler = LogBroadcastHandler()
log_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
logging.getLogger("YouthIdeathonAutomation").addHandler(log_handler)
logger = logging.getLogger("YouthIdeathonAutomation")


def broadcast_status():
    """Broadcast state snapshot to all SSE listeners."""
    payload = json.dumps({"type": "status", **runner_state})
    for q in list(sse_subscribers):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


class StartRequest(BaseModel):
    participation_type: str = "Team"
    primary_sid: str = "YI26-11860"
    teammate_1_sid: str = "YI26-08461"
    teammate_2_sid: str = "YI26-09892"
    teammate_3_sid: str = "YI26-10123"
    teammate_4_sid: str = "YI26-11567"
    mentor_target: str = "Umesh Verma (ATL)"
    data_file: str = "Idea.md"
    dry_run: bool = False
    skip_existing: bool = False


class CatalogUpdateRequest(BaseModel):
    content: str


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Serve modern single-page dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/ideas")
async def get_ideas(file_path: str = "Idea.md"):
    """Returns parsed ideas list with validation status."""
    try:
        ideas = load_ideas(file_path)
        return {"success": True, "ideas": ideas}
    except Exception as e:
        return {"success": False, "error": str(e), "ideas": []}


@app.get("/api/raw-idea-file")
async def get_raw_idea_file(file_path: str = "Idea.md"):
    """Returns raw text content of the markdown idea file."""
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "content": ""}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {"success": True, "content": content}


@app.post("/api/raw-idea-file")
async def update_raw_idea_file(req: CatalogUpdateRequest, file_path: str = "Idea.md"):
    """Writes updated markdown content back to disk."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.content)
    logger.info(f"Updated {file_path} via web console editor.")
    return {"success": True}


@app.get("/api/prompt")
async def get_agent_prompt(domain: str = "mixed"):
    """Returns generated static AI prompt for ChatGPT/Claude/Gemini."""
    domain_map = {
        "electronics": "Electronic & Hardware Innovation (Sensors, Microcontrollers, IoT, Embedded Systems)",
        "software": "Software & AI Solutions (Web apps, Mobile applications, Machine Learning, Cloud Platforms)",
        "mixed": "Mixed Innovation (Hardware + Software, IoT telemetry, Connected Robotics, DeepTech)"
    }
    selected_domain = domain_map.get(domain, domain_map["mixed"])

    prompt = f"""You are an expert school/college innovation mentor for the Youth Ideathon 2026 competition.
Please generate an 'Idea.md' markdown file containing 10-15 novel, practical, and highly impactful ideas in the domain: {selected_domain}.

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
3. Do not include markdown code fence blocks inside descriptions."""
    return {"prompt": prompt}


# ---------------------------------------------------------------------------
# Automated AI generation (Playwright-driven)
# ---------------------------------------------------------------------------

class AIGenerateRequest(BaseModel):
    prompt: str
    provider: str = "chatgpt"  # chatgpt, gemini, arena
    timeout_seconds: int = 180


AI_AUTOMATION_CONFIG = {
    "chatgpt": {
        "url": "https://chatgpt.com/",
        "textarea_selector": "textarea#prompt-textarea, div[contenteditable='true'][data-testid='textbox'], textarea[data-id='root']",
        "submit_selector": "button[data-testid='send-button'], button[aria-label='Send message']",
        "response_selector": "div[data-message-author-role='assistant'], .markdown.prose, .group.w-full",
        "wait_for_login": True,
    },
    "gemini": {
        "url": "https://gemini.google.com/app",
        "textarea_selector": "textarea[aria-label='Enter a prompt here'], div[contenteditable='true'][role='textbox']",
        "submit_selector": "button[aria-label='Send message'], button[data-testid='send-button']",
        "response_selector": "div[data-message-author='model'], .model-response-text",
        "wait_for_login": True,
    },
    "arena": {
        "url": "https://arena.ai/",
        "textarea_selector": "textarea, div[contenteditable='true']",
        "submit_selector": "button[type='submit'], button:has-text('Send')",
        "response_selector": ".response, .message.assistant",
        "wait_for_login": False,
    },
}


async def run_ai_automation(prompt: str, provider: str, timeout_seconds: int) -> Dict[str, object]:
    """Run Playwright automation to send prompt to AI and extract response."""
    config = AI_AUTOMATION_CONFIG.get(provider.lower())
    if not config:
        return {"success": False, "error": f"Unknown provider: {provider}"}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright not installed. Run 'pip install playwright' and 'playwright install chromium'."}

    user_data_dir = APP_DIR / "ai_automation_profile" / provider.lower()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    browser = None
    context = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                viewport={"width": 1280, "height": 960},
            )
            context = browser
            page = context.pages[0] if context.pages else await context.new_page()

            # Navigate to AI site
            await page.goto(config["url"], wait_until="domcontentloaded", timeout=60000)

            # Wait for login if needed
            if config.get("wait_for_login"):
                # Wait for the chat interface to be ready (textarea visible)
                try:
                    await page.wait_for_selector(config["textarea_selector"], state="visible", timeout=120000)
                except Exception:
                    return {"success": False, "error": f"Login required or chat interface not found for {provider}. Please log in manually first."}

            # Fill the prompt
            textarea = await page.wait_for_selector(config["textarea_selector"], state="visible", timeout=30000)
            await textarea.fill(prompt)

            # Submit
            submit_btn = await page.wait_for_selector(config["submit_selector"], state="visible", timeout=10000)
            await submit_btn.click()

            # Wait for response - look for the assistant message to appear and stop streaming
            response_text = ""
            start_time = asyncio.get_event_loop().time()
            last_length = 0
            stable_count = 0

            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                try:
                    # Get all assistant messages
                    responses = await page.query_selector_all(config["response_selector"])
                    if responses:
                        # Get the last (most recent) response
                        last_response = responses[-1]
                        text = await last_response.inner_text()
                        if text and len(text) > len(prompt):  # Has actual response
                            if len(text) == last_length:
                                stable_count += 1
                                if stable_count >= 3:  # Response stable for 3 checks
                                    response_text = text
                                    break
                            else:
                                stable_count = 0
                                last_length = len(text)
                except Exception:
                    pass
                await asyncio.sleep(2)

            if not response_text:
                return {"success": False, "error": f"Timeout waiting for {provider} response."}

            # Extract markdown code blocks or use full response
            import re
            markdown_blocks = re.findall(r'```(?:markdown|md)?\n(.*?)```', response_text, re.DOTALL)
            if markdown_blocks:
                extracted = markdown_blocks[0].strip()
            else:
                # Try to find the Idea.md content pattern
                idea_match = re.search(r'(### IDEA-\d+:.*?)(?=### IDEA-\d+:|\Z)', response_text, re.DOTALL)
                if idea_match:
                    extracted = idea_match.group(1).strip()
                else:
                    extracted = response_text.strip()

            return {"success": True, "content": extracted, "raw_response": response_text}

    except Exception as e:
        logger.exception("AI automation failed")
        return {"success": False, "error": f"Automation error: {e}"}
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass


@app.post("/api/ai/generate")
async def ai_generate(req: AIGenerateRequest):
    """Automate AI to generate Idea.md content from prompt."""
    if not req.prompt.strip():
        return {"success": False, "error": "Prompt is empty."}

    result = await run_ai_automation(req.prompt.strip(), req.provider, req.timeout_seconds)
    return result


# ---------------------------------------------------------------------------
# Native file / folder picker (Windows common dialogs)
# ---------------------------------------------------------------------------

class PickPathRequest(BaseModel):
    mode: str = "file"
    initial: str = ""
    title: str = "Select a file"
    filter: str = ""


# ---------------------------------------------------------------------------
# Native file / folder picker (Windows common dialogs)
# ---------------------------------------------------------------------------

_PICKER_PS = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$out = $env:YI_PICK_OUT
try {
    $owner = New-Object System.Windows.Forms.Form
    $owner.FormBorderStyle = 'None'
    $owner.ShowInTaskbar = $false
    $owner.TopMost = $true
    $owner.StartPosition = 'CenterScreen'
    $owner.Width = 1
    $owner.Height = 1
    $owner.Opacity = 0
    $owner.Show()
    if ($env:YI_PICK_MODE -eq 'dir') {
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = $env:YI_PICK_TITLE
        $dlg.ShowNewFolderButton = $true
        if ($env:YI_PICK_INITIAL -and (Test-Path -LiteralPath $env:YI_PICK_INITIAL)) {
            $dlg.SelectedPath = $env:YI_PICK_INITIAL
        }
        $result = $dlg.ShowDialog($owner)
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            [System.IO.File]::WriteAllText($out, $dlg.SelectedPath, (New-Object System.Text.UTF8Encoding($false)))
        }
    } else {
        $dlg = New-Object System.Windows.Forms.OpenFileDialog
        $dlg.Title = $env:YI_PICK_TITLE
        $dlg.CheckFileExists = $true
        $dlg.CheckPathExists = $true
        $dlg.Multiselect = $false
        $dlg.RestoreDirectory = $true
        if ($env:YI_PICK_FILTER) { $dlg.Filter = $env:YI_PICK_FILTER }
        if ($env:YI_PICK_INITIAL -and (Test-Path -LiteralPath $env:YI_PICK_INITIAL)) {
            $dlg.InitialDirectory = $env:YI_PICK_INITIAL
        }
        $result = $dlg.ShowDialog($owner)
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            [System.IO.File]::WriteAllText($out, $dlg.FileName, (New-Object System.Text.UTF8Encoding($false)))
        }
    }
    $owner.Close()
} catch {
    [System.IO.File]::WriteAllText($env:YI_PICK_OUT + '.err', $_.Exception.Message, (New-Object System.Text.UTF8Encoding($false)))
}
"""


def _display_path(path: Path) -> str:
    """Prefer a relative path for files inside the app folder."""
    try:
        return str(path.resolve().relative_to(APP_DIR.resolve()))
    except Exception:
        return str(path)


def _initial_picker_directory(initial: str) -> str:
    """Resolve the starting folder for the native dialog."""
    if not initial:
        return str(APP_DIR)
    candidate = Path(initial)
    if not candidate.is_absolute():
        candidate = APP_DIR / candidate
    try:
        if candidate.is_dir():
            return str(candidate)
        if candidate.parent.exists():
            return str(candidate.parent)
    except OSError:
        pass
    return str(APP_DIR)


def _pick_path_windows(mode: str, initial: str, title: str, file_filter: str) -> Dict[str, object]:
    out_fd, out_name = tempfile.mkstemp(prefix="yi-pick-", suffix=".txt")
    os.close(out_fd)
    out_path = Path(out_name)
    err_path = Path(out_name + ".err")
    try:
        env = os.environ.copy()
        env.update(
            {
                "YI_PICK_OUT": str(out_path),
                "YI_PICK_MODE": "dir" if mode == "dir" else "file",
                "YI_PICK_TITLE": title,
                "YI_PICK_INITIAL": initial,
                "YI_PICK_FILTER": file_filter,
            }
        )
        encoded = base64.b64encode(_PICKER_PS.encode("utf-16-le")).decode("ascii")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            env=env,
            timeout=300,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        if err_path.exists():
            message = err_path.read_text(encoding="utf-8", errors="replace").strip()
            return {"success": False, "cancelled": False, "error": message or "The native picker failed."}
        if not out_path.exists():
            return {"success": False, "cancelled": True, "error": ""}

        selected = out_path.read_text(encoding="utf-8", errors="replace").strip()
        if not selected:
            return {"success": False, "cancelled": True, "error": ""}
        return {"success": True, "cancelled": False, "path": _display_path(Path(selected)), "error": ""}
    finally:
        for path in (out_path, err_path):
            try:
                path.unlink()
            except OSError:
                pass


@app.post("/api/pick-path")
def pick_path(req: PickPathRequest):
    """Open the native Windows file or folder dialog on this machine."""
    if sys.platform != "win32":
        return {"success": False, "cancelled": False, "error": "The native path picker is only available on Windows."}

    mode = "dir" if req.mode.strip().lower() in ("dir", "folder", "directory") else "file"
    title = req.title.strip() or ("Select a folder" if mode == "dir" else "Select a file")
    file_filter = req.filter.strip() or "All files (*.*)|*.*"
    try:
        return _pick_path_windows(mode, _initial_picker_directory(req.initial.strip()), title, file_filter)
    except subprocess.TimeoutExpired:
        return {"success": False, "cancelled": False, "error": "The file picker timed out."}
    except Exception as exc:
        logger.exception("Native path picker failed")
        return {"success": False, "cancelled": False, "error": str(exc)}


@app.get("/api/screenshots")
async def list_screenshots():
    """Returns list of captured screenshots sorted by time descending."""
    shot_dir = Path(SCREENSHOTS_DIR)
    if not shot_dir.exists():
        return {"screenshots": []}

    files = sorted(shot_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
    return {
        "screenshots": [
            {"name": f.name, "url": f"/screenshots/{f.name}", "time": datetime.fromtimestamp(os.path.getmtime(f)).strftime("%H:%M:%S")}
            for f in files
        ]
    }


@app.get("/api/status")
async def get_status():
    """Returns active runner state."""
    return runner_state


@app.get("/api/stream")
async def stream_events(request: Request):
    """Server-Sent Events (SSE) stream for real-time logs and state updates."""
    queue = asyncio.Queue()
    sse_subscribers.add(queue)

    # Send immediate initial status
    await queue.put(json.dumps({"type": "status", **runner_state}))

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_subscribers.discard(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def run_submission_process(req: StartRequest):
    """Executes the Playwright automation in an async background task."""
    global runner_state
    from playwright.async_api import async_playwright

    ideas = load_ideas(req.data_file)
    successful_ids = get_successful_idea_ids() if req.skip_existing else set()

    runner_state["status"] = "running"
    runner_state["total_ideas"] = len(ideas)
    runner_state["completed_ideas"] = 0
    runner_state["is_dry_run"] = req.dry_run

    # Calculate ETA
    est_per_idea = (2.0 * 12) + 6.0 + (10.0 if not req.dry_run else 1.0)
    total_est = est_per_idea * len(ideas)
    runner_state["eta_seconds"] = total_est
    runner_state["eta_str"] = format_duration(total_est)
    runner_state["finish_clock"] = (datetime.now() + timedelta(seconds=total_est)).strftime("%H:%M:%S")
    broadcast_status()

    logger.info("=" * 60)
    logger.info(f"[WEB GUI] Started {'DRY-RUN' if req.dry_run else 'LIVE'} submission batch")
    logger.info(f"[WEB GUI] Total Ideas: {len(ideas)} | ETA: ~{runner_state['eta_str']}")
    logger.info("=" * 60)

    config = {
        "participation_type": req.participation_type,
        "primary_sid": req.primary_sid,
        "teammate_1_sid": req.teammate_1_sid,
        "teammate_2_sid": req.teammate_2_sid,
        "teammate_3_sid": req.teammate_3_sid,
        "teammate_4_sid": req.teammate_4_sid,
        "mentor_target": req.mentor_target,
        "awards": [],
        "agreement": True,
    }

    user_data_path = os.path.abspath(USER_DATA_DIR)

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                channel=chrome_channel(),
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                ignore_default_args=["--enable-automation"],
                no_viewport=True
            )
            page = context.pages[0] if context.pages else await context.new_page()

            for idx, idea in enumerate(ideas):
                idea_id = idea.get("id", f"IDEA-{idx+1:02d}")
                title = idea.get("title", "Untitled")

                if req.skip_existing and idea_id in successful_ids:
                    logger.info(f"Skipping [{idea_id}] '{title}': Already marked SUCCESS.")
                    continue

                runner_state["current_idea_text"] = f"[{idx+1}/{len(ideas)}] {idea_id}: {title}"
                rem_seconds = (len(ideas) - idx) * est_per_idea
                runner_state["eta_str"] = format_duration(rem_seconds)
                runner_state["finish_clock"] = (datetime.now() + timedelta(seconds=rem_seconds)).strftime("%H:%M:%S")
                broadcast_status()

                logger.info(f"[WEB GUI] Submitting ({idx+1}/{len(ideas)}): [{idea_id}] {title}")
                status, shot_path, notes = await process_idea(
                    page=page,
                    idea=idea,
                    config=config,
                    dry_run=req.dry_run,
                    input_delay_min=1.0,
                    input_delay_max=2.5
                )

                log_result(idea_id=idea_id, title=title, status=status, screenshot_path=shot_path, notes=notes)
                runner_state["completed_ideas"] = idx + 1
                broadcast_status()

                if idx < len(ideas) - 1:
                    wait_s = random.uniform(8.0, 11.0) if not req.dry_run else 2.0
                    logger.info(f"Cooldown {wait_s:.1f}s before next idea...")
                    await asyncio.sleep(wait_s)

            await context.close()
            runner_state["status"] = "completed"
            runner_state["current_idea_text"] = "Batch Completed Successfully!"
            runner_state["eta_str"] = "0s"
            broadcast_status()
            logger.info("🎉 All ideas processed successfully!")

    except asyncio.CancelledError:
        runner_state["status"] = "stopped"
        runner_state["current_idea_text"] = "Execution stopped by user."
        broadcast_status()
        logger.warning("Batch execution halted by user.")
    except Exception as e:
        runner_state["status"] = "error"
        runner_state["current_idea_text"] = f"Error: {str(e)}"
        broadcast_status()
        logger.error(f"Unexpected error: {e}")


@app.post("/api/start")
async def start_submission(req: StartRequest):
    """Trigger background submission task."""
    global active_task
    if runner_state["status"] == "running":
        return {"success": False, "error": "A submission batch is already in progress."}

    active_task = asyncio.create_task(run_submission_process(req))
    return {"success": True}


@app.post("/api/stop")
async def stop_submission():
    """Cancel currently running task."""
    global active_task
    if active_task and not active_task.done():
        active_task.cancel()
        return {"success": True}
    return {"success": False, "message": "No active task running."}


def _port_in_use(port: int) -> bool:
    """Return True when something is listening on 127.0.0.1:<port>."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _is_existing_dashboard(port: int) -> bool:
    """Return True when an instance of this dashboard is already running."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/status", timeout=0.8
        ) as response:
            return response.status == 200
    except Exception:
        return False


def start_server(port: int = 8000, open_browser: bool = True):
    """Starts local Uvicorn server and automatically opens localhost dashboard."""
    # Double-clicking the app again should focus the running dashboard rather
    # than silently failing because the port is already bound.
    if _is_existing_dashboard(port):
        print(f"\n  Youth Ideathon dashboard is already running on http://localhost:{port}\n")
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")
        return

    # If another program owns the default port, use the next free one.
    original_port = port
    while _port_in_use(port):
        port += 1
        if port > original_port + 20:
            print("\n  No free local port found (8000-8020). Close other apps and retry.\n")
            return

    url = f"http://localhost:{port}"
    print(f"\n========================================================")
    print(f"  🚀 Youth Ideathon Web GUI Running on {url}")
    print(f"========================================================\n")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    start_server(port=8000, open_browser=True)
