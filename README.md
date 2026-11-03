# 🚀 Youth Ideathon Bot

A lightweight Windows installer for a local dashboard that batch-submits ideas to the [Youth Ideathon portal](https://youthideathon.in/submit-your-idea/) with live logs, an ETA, and screenshot proof.

<p align="center">
  <a href="https://github.com/rKyzen/Youth-Ideathon-Bot/releases/download/v1_exe/YouthIdeathon_Setup_v2.1.0.exe">
    <img src="https://img.shields.io/badge/Download-Installer_v2.1.0-f97316?style=for-the-badge&logo=windows&logoColor=white" alt="Download the installer">
  </a>
  <a href="https://github.com/rKyzen/Youth-Ideathon-Bot/releases">
    <img src="https://img.shields.io/github/downloads/rKyzen/Youth-Ideathon-Bot/total?style=for-the-badge&label=downloads&color=2ea44f" alt="Total downloads">
  </a>
</p>

---

## Why does this exist?

Submitting dozens of ideas by hand means repeating the same form, mentor lookup, and dropdown selections over and over. This tool makes that process reliable and auditable:

- Submits ideas **sequentially** with human-like delays
- Streams **live logs** and shows an **ETA** in a local dashboard
- Saves a **full-page screenshot** of every submission as proof
- Supports a **dry run** that fills the form without clicking Submit
- Works offline and keeps everything on your machine

---

## Who made it?

Made by [@rKyzen](https://github.com/rKyzen), built with Python, FastAPI, and Playwright.

---

## How to use it (installer)

1. Click the **Download Installer** box above.
2. Run **`YouthIdeathon_Setup_v2.1.0.exe`** (no administrator rights needed).
3. Follow the setup wizard. It automatically:
   - installs **Python 3.12** if it is missing,
   - installs the required Python packages and **Playwright Chromium**,
   - detects Google Chrome, and falls back to Chromium if Chrome is absent.
4. Launch **Youth Ideathon Bot** from the Start Menu or desktop shortcut.
5. Your browser opens **`http://localhost:8000`**. Enter the SIDs and mentor, click **Run dry-run test** to verify the form, then **Start full submission**.
6. To reinstall dependencies later, use **Start Menu → Install / Repair Dependencies**. Uninstall from **Settings → Apps**.
