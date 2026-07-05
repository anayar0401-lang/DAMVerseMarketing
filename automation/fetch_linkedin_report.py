#!/usr/bin/env python3
"""
DAMVerse — LinkedIn Campaign Manager report fetcher.

Downloads the campaign/creative performance CSV from LinkedIn Campaign Manager
using a real logged-in browser session (Playwright, persistent profile), then
saves it locally and/or uploads it to the portal's Google Drive folder.

The portal's "Refresh Data" button picks the file up from Drive.

Usage:
  python3 fetch_linkedin_report.py --login
      One-time: opens a visible browser. Log in to LinkedIn manually
      (including 2FA). Close the browser window when you see your feed.
      The session is saved in ./.profile and reused by later runs.

  python3 fetch_linkedin_report.py
      Fetch the report. Add --headed the first few times to watch it work.

  python3 fetch_linkedin_report.py --drive
      Also upload the CSV to the Drive folder (needs credentials.json,
      see README "Automated fetch" section).

Options:
  --account-id ID   Campaign Manager account id (from the URL:
                    linkedin.com/campaignmanager/accounts/<ID>/...).
                    If omitted, the first account on your accounts page is used.
  --out DIR         Where to save the CSV (default: ./downloads).
                    Tip: point this at a Google Drive for desktop synced folder
                    and you don't need --drive at all.
  --headed          Show the browser window (recommended until trusted).
  --login           Interactive login mode (see above).
  --drive           Upload the downloaded CSV to the Drive folder via OAuth.

Scheduling (runs daily at 06:30):
  crontab -e
  30 6 * * * cd /Users/archeetnayar/ClaudeCode/DAMVerse1/automation && /usr/bin/env python3 fetch_linkedin_report.py --drive >> fetch.log 2>&1

NOTE: LinkedIn's User Agreement prohibits automated access. This script exists
as a stopgap while Marketing API developer access is pending. Run it at most
once or twice a day, from your own machine, on your own account.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HERE = Path(__file__).resolve().parent
PROFILE_DIR = HERE / ".profile"
DEBUG_SHOT = HERE / "debug.png"

DRIVE_FOLDER_ID = "1vCBU1cDadEoChmsnN9NtJ6g5f9xWm_D6"  # portal reports folder

CM_HOME = "https://www.linkedin.com/campaignmanager/"


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def fail(page, msg: str) -> None:
    """Screenshot the page so selector problems are easy to diagnose, then exit."""
    try:
        page.screenshot(path=str(DEBUG_SHOT), full_page=True)
        log(f"Saved screenshot of the stuck page to {DEBUG_SHOT}")
    except Exception:
        pass
    sys.exit(f"ERROR: {msg}")


def do_login(pw) -> None:
    ctx = pw.chromium.launch_persistent_context(str(PROFILE_DIR), headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.linkedin.com/login")
    log("Log in manually in the browser window (finish any 2FA).")
    log("When you can see your LinkedIn feed, close the browser window.")
    try:
        ctx.wait_for_event("close", timeout=0)
    except Exception:
        pass
    log("Session saved. You can now run the script without --login.")


def first_visible(page, locators):
    """Return the first locator in the list that is visible, else None."""
    for loc in locators:
        try:
            if loc.first.is_visible(timeout=2000):
                return loc.first
        except Exception:
            continue
    return None


def fetch_report(pw, account_id: str | None, out_dir: Path, headed: bool) -> Path:
    ctx = pw.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=not headed,
        accept_downloads=True,
        viewport={"width": 1440, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.set_default_timeout(30000)

    # 1. Reach Campaign Manager (bounces to /login if the session expired).
    target = f"{CM_HOME}accounts/{account_id}/campaigns" if account_id else CM_HOME
    log(f"Opening {target}")
    page.goto(target, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    if "/login" in page.url or "checkpoint" in page.url:
        fail(page, "Not logged in (or LinkedIn raised a checkpoint). Run with --login first.")

    # 2. If we landed on the account list, open the first account.
    if account_id is None and "/accounts/" not in page.url:
        acct = first_visible(page, [page.locator("a[href*='/accounts/']")])
        if not acct:
            fail(page, "Could not find an ad account link on the Campaign Manager page.")
        acct.click()
        page.wait_for_timeout(4000)
        m = re.search(r"/accounts/(\d+)", page.url)
        if m:
            log(f"Using ad account {m.group(1)} (pass --account-id {m.group(1)} to skip this step).")

    # 3. Open the export dialog.
    export_open = first_visible(page, [
        page.get_by_role("button", name=re.compile(r"^export$", re.I)),
        page.get_by_role("button", name=re.compile(r"export", re.I)),
        page.locator("button:has-text('Export')"),
    ])
    if not export_open:
        fail(page, "Could not find the Export button. LinkedIn may have changed the UI — "
                   "send debug.png back to Claude to update the selectors.")
    export_open.click()
    page.wait_for_timeout(2000)

    # 4. In the export panel: prefer a daily time breakdown so the portal's
    #    trend chart gets per-day rows. Selector names vary; all are optional.
    for label in ["Daily", "Day"]:
        opt = first_visible(page, [
            page.get_by_role("radio", name=re.compile(label, re.I)),
            page.get_by_label(re.compile(label, re.I)),
            page.locator(f"label:has-text('{label}')"),
        ])
        if opt:
            try:
                opt.click()
                log(f"Selected '{label}' time breakdown.")
                break
            except Exception:
                pass

    # 5. Confirm the export and capture the download.
    confirm = first_visible(page, [
        page.get_by_role("dialog").get_by_role("button", name=re.compile(r"export|download", re.I)),
        page.locator("[role=dialog] button:has-text('Export')"),
        page.get_by_role("button", name=re.compile(r"^download$", re.I)),
    ])
    if not confirm:
        fail(page, "Export dialog opened but no confirm button found — send debug.png back to Claude.")

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with page.expect_download(timeout=120000) as dl:
            confirm.click()
        download = dl.value
    except PWTimeout:
        fail(page, "Clicked export but no file downloaded within 2 minutes.")

    stamp = datetime.date.today().isoformat()
    dest = out_dir / f"linkedin_report_{stamp}.csv"
    download.save_as(str(dest))
    log(f"Downloaded report → {dest}")
    ctx.close()
    return dest


def upload_to_drive(csv_path: Path) -> None:
    """Upload (or update) the CSV in the portal's Drive folder via OAuth.

    Needs automation/credentials.json (OAuth client, Desktop app type) from the
    same Google Cloud project as the portal's API key. First run opens a
    browser consent screen once; the token is cached in token.json.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    scopes = ["https://www.googleapis.com/auth/drive"]
    token_file = HERE / "token.json"
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(HERE / "credentials.json"), scopes)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    svc = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(str(csv_path), mimetype="text/csv")

    # Replace a same-named file if it exists, so the folder stays tidy.
    existing = svc.files().list(
        q=f"name = '{csv_path.name}' and '{DRIVE_FOLDER_ID}' in parents and trashed = false",
        fields="files(id)").execute().get("files", [])
    if existing:
        svc.files().update(fileId=existing[0]["id"], media_body=media).execute()
        log(f"Updated existing Drive file {csv_path.name}")
    else:
        svc.files().create(
            body={"name": csv_path.name, "parents": [DRIVE_FOLDER_ID]},
            media_body=media, fields="id").execute()
        log(f"Uploaded {csv_path.name} to the Drive reports folder")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--login", action="store_true", help="interactive login mode")
    ap.add_argument("--account-id", help="Campaign Manager account id")
    ap.add_argument("--out", default=str(HERE / "downloads"), help="download directory")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--drive", action="store_true", help="upload the CSV to the Drive folder")
    args = ap.parse_args()

    with sync_playwright() as pw:
        if args.login:
            do_login(pw)
            return
        csv_path = fetch_report(pw, args.account_id, Path(args.out), args.headed)

    if args.drive:
        upload_to_drive(csv_path)
    log("Done. Open the portal and click 'Refresh Data' (or wait for the next scheduled visit).")


if __name__ == "__main__":
    main()
