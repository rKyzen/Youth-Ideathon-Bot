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
import json
import logging
import os
import random
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

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

# Ensure directories exist
Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
Path("templates").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Youth Ideathon Automation Console")
templates = Jinja2Templates(directory="templates")
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
        "mentor_target": req.mentor_target,
        "awards": [],
        "agreement": True,
    }

    user_data_path = os.path.abspath(USER_DATA_DIR)

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                channel="chrome",
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


def start_server(port: int = 8000, open_browser: bool = True):
    """Starts local Uvicorn server and automatically opens localhost dashboard."""
    url = f"http://localhost:{port}"
    print(f"\n========================================================")
    print(f"  🚀 Youth Ideathon Web GUI Running on {url}")
    print(f"========================================================\n")
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    start_server(port=8000, open_browser=True)
