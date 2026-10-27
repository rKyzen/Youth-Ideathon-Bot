"""
Youth Ideathon Idea Submission Automation Script
------------------------------------------------
Automates sequential submission of ideas to https://youthideathon.in/submit-your-idea/
using Playwright with robust Cloudflare bypass, interactive startup configuration,
markdown/JSON/CSV idea loading, human-like delays, idempotency, and comprehensive logging.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from playwright.async_api import BrowserContext, Page, async_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("YouthIdeathonAutomation")

# Constants & Configuration
TARGET_URL = "https://youthideathon.in/submit-your-idea/"
LOG_CSV_FILE = "submission_log.csv"
SCREENSHOTS_DIR = "screenshots"
USER_DATA_DIR = "chrome_user_data"


def parse_markdown_ideas(text: str) -> List[Dict]:
    """Parse ideas catalog from a Markdown file (e.g. Idea.md)."""
    # Regex pattern to match idea blocks
    # Supports ### IDEA-XX: Title or ### Title
    idea_blocks = re.split(r'\n(?=###\s+)', '\n' + text)
    ideas = []

    for block in idea_blocks:
        block = block.strip()
        if not block.startswith("###"):
            continue

        # Extract title and optional ID
        header_match = re.match(r'###\s+(?:(IDEA-\d+):\s+)?([^\n]+)', block)
        if not header_match:
            continue

        idea_id = header_match.group(1) or ""
        title = header_match.group(2).strip()

        # Extract fields using regex
        theme_m = re.search(r'-\s+\*\*Theme:\*\*\s+([^\n]+)', block, re.IGNORECASE)
        irctc_sub_m = re.search(r'-\s+\*\*(?:Sub-Theme|IRCTC Sub-theme):\*\*\s+([^\n]+)', block, re.IGNORECASE)
        origin_m = re.search(r'-\s+\*\*Origin:\*\*\s+([^\n]+)', block, re.IGNORECASE)
        stage_m = re.search(r'-\s+\*\*Stage:\*\*\s+([^\n]+)', block, re.IGNORECASE)
        reach_m = re.search(r'-\s+\*\*(?:3-Year Projected Users|Projected Reach|Projected Users):\*\*\s+([^\n]+)', block, re.IGNORECASE)
        why_great_m = re.search(r'-\s+\*\*Why Great:\*\*\s+([^\n]+)', block, re.IGNORECASE)
        desc_m = re.search(r'-\s+\*\*Description[^\*]*\*\*\s*\n+((?:>?[^\n]+\n?)+)', block, re.IGNORECASE)

        theme_raw = theme_m.group(1).strip() if theme_m else ""
        theme = theme_raw
        irctc_theme = irctc_sub_m.group(1).strip() if irctc_sub_m else ""

        # Handle inline IRCTC format: Theme: IRCTC challenge (Sub-theme)
        if not irctc_theme and "IRCTC challenge" in theme_raw:
            inline_irctc = re.match(r'IRCTC challenge\s*\((.+?)\)', theme_raw, re.IGNORECASE)
            if inline_irctc:
                theme = "IRCTC challenge"
                irctc_theme = inline_irctc.group(1).strip()

        origin = origin_m.group(1).strip() if origin_m else ""
        stage = stage_m.group(1).strip() if stage_m else ""
        projected_reach = reach_m.group(1).strip() if reach_m else ""
        why_great = why_great_m.group(1).strip() if why_great_m else ""

        # Clean description (strip markdown blockquote '>' and extra whitespace)
        description = ""
        if desc_m:
            raw_desc = desc_m.group(1)
            desc_lines = []
            for line in raw_desc.splitlines():
                cleaned = line.strip()
                if cleaned.startswith('>'):
                    cleaned = cleaned[1:].strip()
                if cleaned and not cleaned.startswith('#') and not cleaned.startswith('-'):
                    desc_lines.append(cleaned)
            description = " ".join(desc_lines).strip()

        if not idea_id:
            idea_id = f"IDEA-{len(ideas)+1:02d}"

        ideas.append({
            "id": idea_id,
            "title": title,
            "theme": theme,
            "irctc_theme": irctc_theme,
            "origin": origin,
            "stage": stage,
            "projected_reach": projected_reach,
            "why_great": why_great,
            "description": description
        })

    return ideas


def load_ideas(data_path: Optional[str] = None) -> List[Dict]:
    """Load ideas from Idea.md, ideas.json, or ideas.csv."""
    # If no data path provided, detect available files
    if not data_path:
        for candidate in ["Idea.md", "ideas.json", "ideas.csv"]:
            if Path(candidate).exists():
                data_path = candidate
                break

    if not data_path or not Path(data_path).exists():
        raise FileNotFoundError(f"Idea data file not found: {data_path or 'Idea.md / ideas.json / ideas.csv'}")

    path = Path(data_path)
    ideas = []

    if path.suffix.lower() == ".md":
        with open(path, "r", encoding="utf-8") as f:
            ideas = parse_markdown_ideas(f.read())
    elif path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            ideas = json.load(f)
    elif path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8-sig") as f:
            ideas = list(csv.DictReader(f))
    else:
        # Fallback detection
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if path.suffix.lower() == ".md" or "###" in content:
                ideas = parse_markdown_ideas(content)
            else:
                ideas = json.loads(content)
        except Exception:
            with open(path, "r", encoding="utf-8-sig") as f:
                ideas = list(csv.DictReader(f))

    logger.info(f"Loaded {len(ideas)} ideas from {data_path}")
    return ideas


def get_successful_idea_ids(log_path: str = LOG_CSV_FILE) -> Set[str]:
    """Read submission_log.csv and return set of idea IDs marked SUCCESS."""
    path = Path(log_path)
    if not path.exists():
        return set()

    successful_ids = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "").strip().upper()
            idea_id = row.get("idea_id", "").strip()
            if status == "SUCCESS" and idea_id:
                successful_ids.add(idea_id)
    return successful_ids


def log_result(
    idea_id: str,
    title: str,
    status: str,
    screenshot_path: str = "",
    log_path: str = LOG_CSV_FILE,
    notes: str = ""
):
    """Append a submission record to submission_log.csv."""
    path = Path(log_path)
    file_exists = path.exists()

    fieldnames = ["idea_id", "title", "status", "timestamp", "screenshot_path", "notes"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "idea_id": idea_id,
            "title": title,
            "status": status,
            "timestamp": now_str,
            "screenshot_path": screenshot_path,
            "notes": notes
        })
    logger.info(f"Logged result for [{idea_id}] -> Status: {status}")


async def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    """Simulate human reading and interaction pause."""
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


async def select_dropdown_by_text(
    page: Page,
    selector: str,
    target_text: str,
    field_name: str = "",
    timeout: float = 10.0
) -> bool:
    """
    Robustly select an option in a <select> element by its visible text.
    Handles exact match, case-insensitive match, and value attribute matching.
    """
    logger.debug(f"Selecting '{target_text}' for {field_name or selector}")
    loc = page.locator(selector)
    await loc.wait_for(state="attached", timeout=timeout * 1000)

    # First attempt: standard Playwright label selection
    try:
        await loc.select_option(label=target_text, timeout=2000)
        await loc.dispatch_event("change")
        return True
    except Exception:
        pass

    # Second attempt: inspect option texts and values manually
    options = await loc.locator("option").all()
    target_norm = target_text.strip().lower()

    for opt in options:
        opt_text = (await opt.inner_text()).strip()
        opt_val = await opt.get_attribute("value") or ""
        if opt_text.lower() == target_norm or opt_val.lower() == target_norm:
            await loc.select_option(value=opt_val)
            await loc.dispatch_event("change")
            return True

    # Partial substring fallback
    for opt in options:
        opt_text = (await opt.inner_text()).strip()
        opt_val = await opt.get_attribute("value") or ""
        if target_norm in opt_text.lower() and opt_val:
            await loc.select_option(value=opt_val)
            await loc.dispatch_event("change")
            return True

    raise ValueError(f"Could not find matching option '{target_text}' in {field_name or selector}")


async def ensure_page_ready(page: Page, timeout: float = 30.0):
    """Wait for Cloudflare check to clear and the main form to be interactable."""
    logger.info("Navigating to form page...")
    await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=timeout * 1000)

    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < timeout:
        title = await page.title()
        if "Just a moment" not in title and await page.locator("#participation-type").count() > 0:
            logger.info(f"Page loaded and form detected: '{title}'")
            return
        await asyncio.sleep(1.0)

    if await page.locator("#participation-type").count() == 0:
        raise TimeoutError("Form element #participation-type not found. Cloudflare or page failed to load.")


async def fill_form_for_idea(
    page: Page,
    idea: Dict,
    config: Dict,
    dry_run: bool = False,
    input_delay_min: float = 1.0,
    input_delay_max: float = 3.0
) -> str:
    """
    Populates all form fields for a given idea following the exact specification.
    Returns path to the screenshot captured.
    """
    idea_id = idea.get("id", "UNKNOWN")
    title = idea.get("title", "Untitled")

    logger.info(f"Starting form population for Idea [{idea_id}]: '{title}'")
    Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)

    # 1. Participation Type: Select "Team" or "Individual"
    part_type = config.get("participation_type", "Team")
    logger.info(f"Step 1: Selecting Participation Type -> {part_type}")
    await select_dropdown_by_text(
        page,
        "#participation-type",
        part_type,
        field_name="Participation Type"
    )
    await human_delay(input_delay_min, input_delay_max)

    # 2. Primary Student ID (SID 1)
    primary_sid = config.get("primary_sid", "YI26-11860")
    logger.info(f"Step 2: Entering Primary SID (SID 1) -> {primary_sid}")
    sid_input = page.locator("#primary-sid")
    await sid_input.click()
    await sid_input.fill("")
    await sid_input.fill(primary_sid)
    await sid_input.blur()

    # Trigger jQuery change/blur event explicitly to guarantee AJAX trigger
    await page.evaluate("""
        const sid = document.getElementById('primary-sid');
        if (window.jQuery) {
            window.jQuery(sid).trigger('change').trigger('blur');
        } else {
            sid.dispatchEvent(new Event('change', { bubbles: true }));
            sid.dispatchEvent(new Event('blur', { bubbles: true }));
        }
    """)
    await human_delay(input_delay_min, input_delay_max)

    # 3. Select Mentor: From dynamically populated dropdown
    mentor_target = config.get("mentor_target", "Umesh Verma (ATL)")
    logger.info(f"Step 3: Awaiting dynamic mentor dropdown population for -> '{mentor_target}'")
    mentor_select = page.locator("#idea-mentor-select")

    # Poll up to 15 seconds for mentor options to load via AJAX
    mentor_found = False
    for _ in range(15):
        options = await mentor_select.locator("option").all_inner_texts()
        if any(mentor_target.lower() in opt.lower() for opt in options):
            mentor_found = True
            break
        await asyncio.sleep(1.0)

    if not mentor_found:
        raise RuntimeError(f"Dynamic mentor options failed to load '{mentor_target}' within timeout.")

    await select_dropdown_by_text(
        page,
        "#idea-mentor-select",
        mentor_target,
        field_name="Mentor Dropdown"
    )
    await human_delay(input_delay_min, input_delay_max)

    # 4. Teammate SIDs (if Team)
    if part_type == "Team":
        t1_sid = config.get("teammate_1_sid", "")
        t2_sid = config.get("teammate_2_sid", "")
        logger.info(f"Step 4: Entering Teammate SIDs: T1 (SID 2)='{t1_sid}', T2 (SID 3)='{t2_sid}'")
        if t1_sid:
            t1_input = page.locator("#teammate-1-sid")
            await t1_input.fill(t1_sid)
            await human_delay(input_delay_min, input_delay_max)

        if t2_sid:
            t2_input = page.locator("#teammate-2-sid")
            await t2_input.fill(t2_sid)
            await human_delay(input_delay_min, input_delay_max)

    # 5. Idea Origin: Where did you get this idea?
    origin = idea.get("origin", "").strip()
    if origin:
        logger.info(f"Step 5: Selecting Idea Origin -> '{origin}'")
        await select_dropdown_by_text(page, "#idea-origin", origin, field_name="Idea Origin")
        await human_delay(input_delay_min, input_delay_max)

    # 6. Idea Stage: What is the stage of your idea?
    stage = idea.get("stage", "").strip()
    if stage:
        logger.info(f"Step 6: Selecting Idea Stage -> '{stage}'")
        await select_dropdown_by_text(page, "#idea-stage", stage, field_name="Idea Stage")
        await human_delay(input_delay_min, input_delay_max)

    # 7. Projected Reach: 3 years from now users
    projected_reach = idea.get("projected_reach", "").strip()
    if projected_reach:
        logger.info(f"Step 7: Selecting Projected Reach -> '{projected_reach}'")
        await select_dropdown_by_text(page, "#idea-impact", projected_reach, field_name="Projected Reach")
        await human_delay(input_delay_min, input_delay_max)

    # 8. Why Great
    why_great = idea.get("why_great", "").strip()
    if why_great:
        logger.info(f"Step 8: Selecting Why Great -> '{why_great}'")
        await select_dropdown_by_text(page, "#idea-great", why_great, field_name="Why Great")
        await human_delay(input_delay_min, input_delay_max)

    # 9. Theme
    theme = idea.get("theme", "").strip()
    if theme:
        logger.info(f"Step 9: Selecting Theme -> '{theme}'")
        await select_dropdown_by_text(page, "#idea-theme", theme, field_name="Main Theme")
        await human_delay(input_delay_min, input_delay_max)

    # 10. IRCTC Theme (if applicable)
    irctc_theme = idea.get("irctc_theme", "").strip()
    if theme == "IRCTC challenge" or irctc_theme:
        if irctc_theme:
            logger.info(f"Step 10: Selecting IRCTC Sub-theme -> '{irctc_theme}'")
            irctc_selector = "#idea-irctc-theme, #idea-IRCTC-theme, select[id='idea-irctc-theme' i]"
            await select_dropdown_by_text(page, irctc_selector, irctc_theme, field_name="IRCTC Theme")
            await human_delay(input_delay_min, input_delay_max)

    # 11. Idea Description (Max 500 characters)
    description = idea.get("description", "").strip()
    logger.info(f"Step 11: Entering Idea Description ({len(description)} characters)")
    desc_area = page.locator("#idea-description")
    await desc_area.fill(description)
    await human_delay(input_delay_min, input_delay_max)

    # 12. Awards Won: Ensure all are unchecked
    logger.info("Step 12: Verifying all Awards Won checkboxes remain unchecked")
    award_boxes = await page.locator('input[name="awards[]"]').all()
    for box in award_boxes:
        if await box.is_checked():
            await box.uncheck()

    # 13. User Agreement: Check "I agree"
    logger.info("Step 13: Checking User Agreement checkbox")
    agree_box = page.locator('input[name="agreement[]"][value="I agree"]')
    if not await agree_box.is_checked():
        await agree_box.check()
    await human_delay(input_delay_min, input_delay_max)

    # Capture state screenshot
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_prefix = "dry_run" if dry_run else "pre_submit"
    screenshot_filename = f"{mode_prefix}_{idea_id}_{timestamp}.png"
    screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_filename)

    await page.screenshot(path=screenshot_path, full_page=True)
    logger.info(f"Captured screenshot: {screenshot_path}")

    return screenshot_path


async def submit_and_verify(page: Page, idea_id: str) -> bool:
    """Clicks Submit and waits for success confirmation or failure message."""
    logger.info(f"Clicking 'Submit Idea' for [{idea_id}]...")
    submit_btn = page.locator('input[type="submit"][value="Submit Idea"]')
    await submit_btn.click()

    # Wait for either URL change to thank-you or contact form 7 response message
    start_time = asyncio.get_event_loop().time()
    timeout = 30.0

    while asyncio.get_event_loop().time() - start_time < timeout:
        current_url = page.url
        if "thank-you" in current_url:
            logger.info(f"Redirected to confirmation page: {current_url}")
            return True

        # Check form response output container
        resp_output = page.locator(".wpcf7-response-output")
        if await resp_output.count() > 0:
            text = (await resp_output.inner_text()).strip()
            form_status = await page.locator("form.wpcf7-form").get_attribute("data-status")
            if form_status == "sent" or "thank you" in text.lower():
                logger.info(f"Form submission succeeded: '{text}'")
                return True
            elif form_status in ["invalid", "failed"]:
                logger.error(f"Form submission failed with status '{form_status}': {text}")
                return False

        await asyncio.sleep(1.0)

    logger.warning("Timed out waiting for submission confirmation redirect/output.")
    return False


async def process_idea(
    page: Page,
    idea: Dict,
    config: Dict,
    dry_run: bool,
    input_delay_min: float,
    input_delay_max: float
) -> tuple[str, str, str]:
    """
    Validates, fills, and optionally submits a single idea with single retry logic.
    Returns: (status, screenshot_path, notes)
    """
    idea_id = idea.get("id", "UNKNOWN")
    title = idea.get("title", "Untitled")
    description = idea.get("description", "").strip()

    # Pre-validation Requirement: Description length must be strictly <= 500 chars
    desc_len = len(description)
    if desc_len > 500:
        err_msg = f"Validation Failed: Description length {desc_len} exceeds 500 characters."
        logger.error(f"[{idea_id}] {err_msg}")
        return "VALIDATION_ERROR", "", err_msg

    max_attempts = 2  # 1 initial try + 1 retry
    last_error = ""
    screenshot_path = ""

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Processing [{idea_id}] (Attempt {attempt}/{max_attempts})")
            await ensure_page_ready(page)
            screenshot_path = await fill_form_for_idea(
                page=page,
                idea=idea,
                config=config,
                dry_run=dry_run,
                input_delay_min=input_delay_min,
                input_delay_max=input_delay_max
            )

            if dry_run:
                logger.info(f"Dry-run active. Bypassing final Submit click for [{idea_id}].")
                return "DRY_RUN", screenshot_path, "Inputs populated and screenshot captured in dry-run mode."

            # Real submission
            success = await submit_and_verify(page, idea_id)
            if success:
                post_shot = os.path.join(
                    SCREENSHOTS_DIR,
                    f"success_{idea_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                await page.screenshot(path=post_shot, full_page=True)
                return "SUCCESS", post_shot, "Submission confirmed successfully."
            else:
                raise RuntimeError("Form submit failed or returned invalid response.")

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} failed for [{idea_id}]: {last_error}")
            err_shot = os.path.join(
                SCREENSHOTS_DIR,
                f"error_{idea_id}_attempt{attempt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            try:
                await page.screenshot(path=err_shot, full_page=True)
                screenshot_path = err_shot
            except Exception:
                pass

            if attempt < max_attempts:
                logger.info(f"Retrying [{idea_id}] after 3 seconds...")
                await asyncio.sleep(3.0)

    return "FAILED", screenshot_path, f"Failed after {max_attempts} attempts. Error: {last_error}"


def prompt_user_configuration(args: argparse.Namespace) -> Dict:
    """
    Prompt user interactively for team/individual, SIDs, and mentor details.
    Allows bypassing with --non-interactive.
    """
    if args.non_interactive:
        return {
            "participation_type": args.participation_type or "Team",
            "primary_sid": args.primary_sid or "YI26-11860",
            "mentor_target": args.mentor or "Umesh Verma (ATL)",
            "teammate_1_sid": args.sid_2 or "YI26-08461",
            "teammate_2_sid": args.sid_3 or "YI26-09892",
            "awards": [],
            "agreement": True,
        }

    print("\n" + "=" * 62)
    print("      YOUTH IDEATHON 2026 - SUBMISSION CONFIGURATION")
    print("=" * 62)
    print("Press [Enter] to accept the suggested default value in [brackets].\n")

    # 1. Team or Individual
    default_type = args.participation_type or "Team"
    raw_type = input(f"1. Participation Type (Team / Individual) [{default_type}]: ").strip()
    if not raw_type:
        part_type = default_type
    elif raw_type.lower().startswith("i"):
        part_type = "Individual"
    else:
        part_type = "Team"

    # 2. SID 1 (Primary SID)
    default_sid1 = args.primary_sid or "YI26-11860"
    raw_sid1 = input(f"2. SID 1 (Primary Student ID) [{default_sid1}]: ").strip()
    primary_sid = raw_sid1 if raw_sid1 else default_sid1

    # 3. Teammate SIDs (if Team)
    t1_sid = ""
    t2_sid = ""
    if part_type == "Team":
        default_sid2 = args.sid_2 or "YI26-08461"
        raw_sid2 = input(f"3. SID 2 (Teammate 1 SID) [{default_sid2}]: ").strip()
        t1_sid = raw_sid2 if raw_sid2 else default_sid2

        default_sid3 = args.sid_3 or "YI26-09892"
        raw_sid3 = input(f"4. SID 3 (Teammate 2 SID) [{default_sid3}]: ").strip()
        t2_sid = raw_sid3 if raw_sid3 else default_sid3

    # 4. Mentor (exact detail)
    default_mentor = args.mentor or "Umesh Verma (ATL)"
    raw_mentor = input(f"5. Mentor Name (exact detail, e.g. Name (Stream)) [{default_mentor}]: ").strip()
    mentor_target = raw_mentor if raw_mentor else default_mentor

    config = {
        "participation_type": part_type,
        "primary_sid": primary_sid,
        "mentor_target": mentor_target,
        "teammate_1_sid": t1_sid,
        "teammate_2_sid": t2_sid,
        "awards": [],
        "agreement": True,
    }

    print("\n--- Active Submission Parameters ---")
    print(f"Participation Type : {config['participation_type']}")
    print(f"Primary SID (SID 1): {config['primary_sid']}")
    if part_type == "Team":
        print(f"Teammate 1 (SID 2) : {config['teammate_1_sid']}")
        print(f"Teammate 2 (SID 3) : {config['teammate_2_sid']}")
    print(f"Mentor (Exact)     : {config['mentor_target']}")
    print("=" * 62 + "\n")

    return config


async def run_automation(args: argparse.Namespace):
    """Main orchestration loop."""
    config = prompt_user_configuration(args)
    ideas = load_ideas(args.data_file)
    successful_ids = get_successful_idea_ids(args.log_file)
    logger.info(f"Previously successful idea IDs ({len(successful_ids)}): {list(successful_ids)}")

    # Filter ideas if a specific ID is requested
    if args.idea_id:
        ideas = [i for i in ideas if i.get("id") == args.idea_id]
        if not ideas:
            logger.error(f"Requested idea ID '{args.idea_id}' not found in dataset.")
            return

    # Filter ideas by max count if requested
    if args.max_ideas and args.max_ideas > 0:
        ideas = ideas[:args.max_ideas]

    logger.info(f"Total ideas scheduled for this run: {len(ideas)}")

    user_data_path = os.path.abspath(args.user_data_dir)

    async with async_playwright() as p:
        logger.info(f"Launching persistent Chrome context (headless={args.headless})...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            channel="chrome",
            headless=args.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation"],
            no_viewport=True
        )
        page = context.pages[0] if context.pages else await context.new_page()

        total_processed = 0
        for idx, idea in enumerate(ideas):
            idea_id = idea.get("id", f"IDEA-{idx+1:02d}")
            title = idea.get("title", "Untitled")

            # Idempotency check: Skip if already marked SUCCESS
            if idea_id in successful_ids:
                logger.info(f"Skipping [{idea_id}] '{title}': Already marked SUCCESS in log.")
                continue

            total_processed += 1
            logger.info(f"\n==================================================")
            logger.info(f"Processing ({total_processed}/{len(ideas)}): [{idea_id}] {title}")
            logger.info(f"==================================================")

            status, shot_path, notes = await process_idea(
                page=page,
                idea=idea,
                config=config,
                dry_run=args.dry_run,
                input_delay_min=args.delay_inputs_min,
                input_delay_max=args.delay_inputs_max
            )

            # Log to CSV
            log_result(
                idea_id=idea_id,
                title=title,
                status=status,
                screenshot_path=shot_path,
                log_path=args.log_file,
                notes=notes
            )

            # In dry-run, if user only wanted to test one idea or if exiting is desired:
            if args.dry_run and args.single_dry_run:
                logger.info("Single dry run completed. Exiting as requested.")
                break

            # Human-like delay between submissions (8-12 seconds)
            if idx < len(ideas) - 1:
                wait_time = random.uniform(args.delay_submit_min, args.delay_submit_max)
                logger.info(f"Waiting {wait_time:.1f}s before next idea...")
                await asyncio.sleep(wait_time)

        await context.close()
        logger.info("Automation completed successfully.")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Youth Ideathon Idea Submission Automation")
    parser.add_argument(
        "--data-file",
        type=str,
        default=None,
        help="Path to Markdown (Idea.md), JSON, or CSV file containing ideas (default: auto-detect Idea.md)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Populate inputs, take screenshot, and exit before clicking Submit"
    )
    parser.add_argument(
        "--single-dry-run",
        action="store_true",
        default=False,
        help="In dry-run mode, stop after the first idea"
    )
    parser.add_argument(
        "--idea-id",
        type=str,
        default=None,
        help="Process only a specific idea ID (e.g. IDEA-01)"
    )
    parser.add_argument(
        "--max-ideas",
        type=int,
        default=None,
        help="Maximum number of ideas to process in this run"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False for optimal Cloudflare bypass)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=LOG_CSV_FILE,
        help="Path to CSV log file (default: submission_log.csv)"
    )
    parser.add_argument(
        "--user-data-dir",
        type=str,
        default=USER_DATA_DIR,
        help="Chrome user profile directory for session persistence"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Skip startup interactive prompt and use command line / default parameters"
    )
    parser.add_argument(
        "--participation-type",
        type=str,
        default=None,
        choices=["Team", "Individual"],
        help="Participation Type (Team or Individual)"
    )
    parser.add_argument(
        "--primary-sid",
        type=str,
        default=None,
        help="Primary Student ID (SID 1)"
    )
    parser.add_argument(
        "--sid-2",
        type=str,
        default=None,
        help="Teammate 1 SID (SID 2)"
    )
    parser.add_argument(
        "--sid-3",
        type=str,
        default=None,
        help="Teammate 2 SID (SID 3)"
    )
    parser.add_argument(
        "--mentor",
        type=str,
        default=None,
        help="Exact mentor option text (e.g. 'Umesh Verma (ATL)')"
    )
    parser.add_argument(
        "--delay-inputs-min",
        type=float,
        default=1.0,
        help="Minimum delay between field inputs in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--delay-inputs-max",
        type=float,
        default=3.0,
        help="Maximum delay between field inputs in seconds (default: 3.0)"
    )
    parser.add_argument(
        "--delay-submit-min",
        type=float,
        default=8.0,
        help="Minimum delay between submissions in seconds (default: 8.0)"
    )
    parser.add_argument(
        "--delay-submit-max",
        type=float,
        default=12.0,
        help="Maximum delay between submissions in seconds (default: 12.0)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_arguments()
    asyncio.run(run_automation(cli_args))
