"""
job_report.py
-------------
Morning job listing report for quant/finance/tech internship roles.

SETUP:
  1. pip install requests
  2. Sign up for a free RapidAPI account at https://rapidapi.com
  3. Subscribe to the JSearch API (free tier): https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
  4. Copy your RapidAPI key into RAPIDAPI_KEY below
  5. (Optional) Set your Gmail credentials to receive the report by email

USAGE:
  python job_report.py              # prints report to terminal
  python job_report.py --email      # also sends report to your email

SCHEDULING (Windows Task Scheduler):
  - Open Task Scheduler > Create Basic Task
  - Trigger: Daily at your preferred morning time
  - Action: Start a program
      Program: C:\path\to\your\python.exe (or "python" if on PATH)
      Arguments: C:\path\to\job_report.py --email
"""

import sys
import requests
import smtplib
import argparse
import datetime
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Make console output robust to non-UTF-8 environments (e.g. Windows Task
# Scheduler, which often runs with a cp1252/OEM codepage). Without this, the
# arrow/box-drawing characters in our progress output raise UnicodeEncodeError
# and crash the whole run before the email is sent.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# ─────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────

# Loads variables from a .env file sitting in the same folder as this script.
# Your .env file should contain: RAPIDAPI_KEY=your_key_here
# Keep .env off GitHub and out of shared folders — never hardcode keys here.
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_env()
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")  # set in .env

# Email settings — set these in your .env file:
#   SENDER_EMAIL=yourname@gmail.com
#   SENDER_PASSWORD=your16characterapppassword
# RECIPIENT_EMAIL defaults to the same address but can be overridden in .env
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", SENDER_EMAIL)

# How many days back to look for postings.
# Set to 8 for a weekly run (7 days + 1 day of headroom in case the run is late).
DAYS_BACK = 8

# ─────────────────────────────────────────
#  SEARCH PARAMETERS
# ─────────────────────────────────────────

# Role keywords — a posting must match at least one
ROLE_KEYWORDS = [
    # ── Quant Research & Analysis ──────────────────────────────
    "quantitative research",
    "quant research",
    "quantitative researcher",
    "quant researcher",
    "quantitative analyst",
    "quant analyst",
    "quantitative intern",
    "quant intern",
    "quantitative research intern",
    "quantitative analyst intern",
    "alpha research",
    "signal research",
    "systematic research",
    "systematic investing",
    "macro research",
    "investment research intern",
    "research intern",

    # ── Trading ────────────────────────────────────────────────
    "quantitative trader",
    "quant trader",
    "quantitative trading",
    "quantitative trading intern",
    "systematic trading",
    "algorithmic trading",
    "algo trading",
    "electronic trading",
    "automated trading",
    "statistical arbitrage",
    "stat arb",
    "market making",
    "high frequency trading",
    "HFT",
    "trading intern",
    "trading analyst intern",
    "commodities trading",

    # ── Quant Development ──────────────────────────────────────
    "quantitative developer",
    "quant developer",
    "quant dev",
    "financial engineering",
    "financial engineering intern",

    # ── Data Science & ML ──────────────────────────────────────
    "data science intern",
    "machine learning intern",
    "ML intern",
    "AI research intern",
    "predictive modeling",
    "time series",
    "optimization",

    # ── Strats & Analytics ─────────────────────────────────────
    "strats",
    "strategic analytics",
    "markets analytics",
    "portfolio analytics",
    "portfolio construction",
    "risk analytics",
    "model risk",

    # ── Pricing & Fixed Income ─────────────────────────────────
    "pricing models",
    "derivatives pricing",
    "options pricing",
    "fixed income analytics",
    "equities analytics",

    # ── General Finance (broader net) ──────────────────────────
    "software engineer intern finance",
    "investment banking intern",
    "capital markets intern",
    "risk analyst intern",
    "equity research intern",
]

# Target firms — combined from spreadsheet + supplemental list
TARGET_FIRMS = [
    # ── Prop Trading / Market Making ──────────────────────────
    "SIG", "Susquehanna", "Susquehanna International Group",
    "Jane Street",
    "Optiver",
    "Citadel", "Citadel Securities",
    "Jump Trading",
    "IMC Trading", "IMC",
    "DRW",
    "Hudson River Trading", "HRT",
    "Two Sigma",
    "DE Shaw",
    "Five Rings",
    "Akuna Capital",
    "Chicago Trading Company",
    "Belvedere Trading",
    "Flow Traders",
    "Maven Securities",
    "G Research", "G-Research",
    "Tower Research Capital",
    "Radix", "Radix Trading",
    "Headlands Tech", "Headlands Technologies",
    "Vatic Labs",
    "Voloridge", "Voloridge Investment Management",
    "XTX Markets",
    "Qube Research & Technologies", "Qube RT",
    "QuantLab", "Quantlab",
    "XR Trading",
    "TransMarket Group",
    "Geneva Trading",
    "Valkyrie Trading",
    "Group One Trading", "Group 1 Trading",
    "Wolverine Trading",
    "GTS", "Global Trading Systems",
    "Old Mission Capital", "Old Mission",
    "Hudson Bay Capital",
    "Bluefin Trading", "Bluefin Capital",
    "DV Trading",
    "PEAK6", "Peak6",
    "Tanius", "Tanius Technology",
    "Teza Technologies",
    "Virtu Financial",
    "TrexQuant",
    "Arrowstreet Capital",
    "Trillium Trading",
    "Kernal Trading",
    "Consolidated Trading",
    "Freestone Grove",
    "Highbridge Capital",
    "HAP Capital",
    "Simplex Trading",
    "SquarePoint Capital",
    "Aquatic Capital",
    "Epoch Capital",
    "QuantBot",
    "Jain Global",
    "Edgestream Partners",

    # ── Quant Hedge Funds / Systematic Asset Managers ─────────
    "Renaissance Technologies",
    "AQR Capital", "AQR Capital Management",
    "Man Group", "Man AHL",
    "Winton Group", "Winton",
    "Marshall Wace",
    "Cubist", "Cubist Systematic Strategies",
    "Point72",
    "Millennium Management",
    "Balyasny", "Balyasny Asset Management",
    "Schonfeld", "Schonfeld Strategic Advisors",
    "WorldQuant",
    "Engineers Gate",
    "PDT Partners",
    "Graham Capital", "Graham Capital Management",
    "Tudor", "Tudor Investment Corporation",
    "Bridgewater Associates",
    "Capula", "Capula Investment Management",
    "Aspect Capital",
    "Brevan Howard",
    "Caxton Associates",
    "ExodusPoint", "ExodusPoint Capital Management",
    "Verition", "Verition Fund Management",
    "Systematica Investments",
    "Squarepoint Capital",
    "Quantitative Investment Management",
    "PanAgora", "PanAgora Asset Management",
    "Acadian Asset Management",
    "Research Affiliates",
    "Magnetar Capital",
    "The Voleon Group",
    "Moore Capital",
    "GSA Capital",
    "Walleye Capital",
    "Garda Capital",
    "Capstone Investment Advisors",
    "Weiss Asset Management",
    "Millburn Ridgefield",
    "HBK Capital",
    "Quadrature",
    "Ansatz Capital",
    "Bracebridge Capital",
    "AlphaTaraxia",
    "Joccassee Quantitative",
    "Stevens Capital",
    "Bayview Asset Management",
    "Quantitative Brokers",
    "QMS Capital",

    # ── Bulge Bracket & Investment Banks ──────────────────────
    "Goldman Sachs",
    "Morgan Stanley",
    "JPMorgan", "JPMorgan Chase", "J.P. Morgan",
    "Bank of America", "BofA",
    "Citi", "Citibank", "Citigroup",
    "Barclays",
    "UBS",
    "Deutsche Bank",
    "BNP Paribas",
    "Societe Generale",
    "HSBC",
    "RBC Capital Markets", "RBC",
    "TD Securities",
    "Jefferies",
    "Nomura",
    "Mizuho",
    "Wells Fargo Securities", "Wells Fargo",
    "Santander Corporate & Investment Banking", "Santander",
    "Macquarie Group", "Macquarie",
    "Standard Chartered",

    # ── Asset Managers / Other Finance & Tech ─────────────────
    "BlackRock",
    "Vanguard",
    "Fidelity Investments", "Fidelity",
    "State Street", "State Street Global Advisors",
    "PIMCO",
    "T. Rowe Price",
    "Capital Group",
    "Dimensional Fund Advisors", "DFA",
    "Bloomberg",
    "CME Group",
    "Cboe",
    "Wellington Management",
    "Geode Capital",
    "Alliance Bernstein",
    "MFS Investment Management",
    "Lord Abbett",
    "Voya Financial",
    "Wolfe Research",
    "StoneX",
    "Fannie Mae",
    "National Futures Association",
    "TradeWeb",
    "Instinet",
]

# Greenhouse job boards — these firms use Greenhouse and expose a free JSON API.
# Format: firm name → Greenhouse board token (the slug that appears in the URL)
# These are unmetered and free; they do NOT count against the JSearch quota.
GREENHOUSE_BOARDS = {
    # ── Originally configured ──────────────────────────────────
    "Walleye Capital":              "walleyecapital",
    "Radix":                        "radixuniversity",
    "Simplex Trading":              "simplextrading",
    "Garda Capital":                "gardacp",
    "Weiss Asset Mgmt":             "weissassetmanagement",
    "AlphaTaraxia":                 "alphataraxia",
    "Bracebridge Capital":          "bracebridgecapital",

    # ── Prop trading / market making ───────────────────────────
    "Jane Street":                  "janestreet",
    "IMC Trading":                  "imc",
    "Jump Trading":                 "jumptrading",
    "Optiver":                      "optiver",
    "Akuna Capital":                "akunacapital",
    "Flow Traders":                 "flowtraders",
    "Tower Research Capital":       "towerresearchcapital",
    "DV Trading":                   "dvtrading",
    "Old Mission Capital":          "oldmissioncapital",
    "Geneva Trading":               "genevatrading",
    "TransMarket Group":            "transmarketgroup",
    "Vatic Labs":                   "vaticlabs",
    "Tanius Technology":            "tanius",
    "Trillium Trading":             "trillium",

    # ── Quant hedge funds / systematic managers ────────────────
    "Point72":                      "point72",
    "WorldQuant":                   "worldquant",
    "SquarePoint Capital":          "squarepointcapital",
    "Schonfeld":                    "schonfeld",
    "Man Group":                    "mangroup",
    "AQR Capital Management":       "aqr",
    "PDT Partners":                 "pdtpartners",
    "Capstone Investment Advisors": "capstoneinvestmentadvisors",
    "Graham Capital Management":    "grahamcapitalmanagement",
    "Engineers Gate":               "engineersgate",
    "Winton":                       "winton",
    "GSA Capital":                  "gsacapital",
    "Edgestream Partners":          "edgestream",
    "Magnetar Capital":             "magnetar",
    "ExodusPoint Capital":          "exoduspoint",
    "Marshall Wace":                "marshallwace",
    "Epoch Capital":                "epochcapital",
}

# Lever job boards — these firms use Lever and expose a free JSON API.
# Format: firm name → Lever company slug
LEVER_COMPANIES = {
    "Ansatz Capital":    "ansatzcapital",
    "Belvedere Trading": "belvederetrading",
    "Valkyrie Trading":  "valkyrietrading",
    "HAP Capital":       "hap-capital",
    "The Voleon Group":  "voleon",
}

# NOTE: Citadel, Two Sigma, and DE Shaw use Workday / custom ATS platforms that
# do not expose a free JSON API, so they remain dependent on the JSearch queries
# above. Jane Street, IMC, Jump Trading, Optiver, and Akuna Capital — previously
# assumed JSearch-only — were found to have free Greenhouse boards and are now
# covered directly above.

# ─────────────────────────────────────────
#  JSEARCH API QUERY
# ─────────────────────────────────────────

def _within_window(job: dict, cutoff: datetime.datetime) -> bool:
    """Keep jobs posted on/after the cutoff. Jobs with no posting date are kept
    (better to include an undated posting than to silently drop it)."""
    ts = job.get("job_posted_at_datetime_utc")
    if not ts:
        return True
    try:
        posted = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    return posted >= cutoff


def fetch_jsearch_listings(query: str, num_pages: int = 1) -> list[dict]:
    """Query the JSearch API (via RapidAPI) for job listings."""
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    # JSearch's date_posted filter only supports today / 3days / week / month —
    # there is no exact 8-day option. For windows longer than a week we ask the
    # API for "month" and trim to DAYS_BACK ourselves below (no extra quota cost).
    if DAYS_BACK == 1:
        date_posted = "today"
    elif DAYS_BACK <= 3:
        date_posted = "3days"
    elif DAYS_BACK <= 7:
        date_posted = "week"
    else:
        date_posted = "month"

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_BACK)

    results = []
    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "date_posted": date_posted,
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            results.extend(job for job in data.get("data", []) if _within_window(job, cutoff))
        except requests.RequestException as e:
            print(f"  [JSearch] Error fetching '{query}': {e}")
    return results


def is_relevant(job: dict) -> bool:
    """Return True if the job posting is relevant based on keywords and firm names."""
    title       = (job.get("job_title") or "").lower()
    employer    = (job.get("employer_name") or "").lower()
    description = (job.get("job_description") or "").lower()

    role_match = any(kw.lower() in title or kw.lower() in description for kw in ROLE_KEYWORDS)
    firm_match = any(firm.lower() in employer or firm.lower() in title for firm in TARGET_FIRMS)

    # Accept if it matches a target firm regardless of title, or if it matches
    # a role keyword in an obvious finance/tech context
    finance_context = any(word in employer + " " + description for word in [
        "capital", "trading", "asset management", "investment", "financial",
        "securities", "hedge", "quant", "bank", "finance"
    ])

    return firm_match or (role_match and finance_context)


def format_job(job: dict, source: str = "JSearch") -> str:
    title    = job.get("job_title", "N/A")
    employer = job.get("employer_name", "N/A")
    location = (job.get("job_city") or "") + (", " + (job.get("job_state") or "") if job.get("job_state") else "")
    link     = job.get("job_apply_link") or job.get("job_google_link") or ""
    posted   = job.get("job_posted_at_datetime_utc", "")[:10] if job.get("job_posted_at_datetime_utc") else "N/A"
    return f"  [{employer}] {title} — {location}\n  Posted: {posted} | Source: {source}\n  {link}"


# ─────────────────────────────────────────
#  GREENHOUSE & LEVER API FETCHERS
# ─────────────────────────────────────────

INTERN_TERMS = ["intern", "internship", "summer", "co-op"]


def _is_intern_title(title: str) -> bool:
    return any(t in title.lower() for t in INTERN_TERMS)


def fetch_greenhouse_jobs(firm: str, board_token: str) -> list[dict]:
    """Fetch intern listings from a Greenhouse board via their public JSON API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    results = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        for job in resp.json().get("jobs", []):
            if _is_intern_title(job.get("title", "")):
                location = job.get("location", {}).get("name", "")
                city, _, state = location.partition(", ")
                results.append({
                    "job_title":                   job["title"],
                    "employer_name":               firm,
                    "job_city":                    city,
                    "job_state":                   state,
                    "job_apply_link":              job.get("absolute_url", ""),
                    "job_posted_at_datetime_utc":  job.get("updated_at", ""),
                })
    except requests.RequestException as e:
        print(f"  [Greenhouse] Could not fetch {firm}: {e}")
    return results


def fetch_lever_jobs(firm: str, company_slug: str) -> list[dict]:
    """Fetch intern listings from a Lever board via their public JSON API."""
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    results = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        for job in resp.json():
            if _is_intern_title(job.get("text", "")):
                loc = job.get("categories", {}).get("location", "")
                city, _, state = loc.partition(", ")
                results.append({
                    "job_title":                   job["text"],
                    "employer_name":               firm,
                    "job_city":                    city,
                    "job_state":                   state,
                    "job_apply_link":              job.get("hostedUrl", ""),
                    "job_posted_at_datetime_utc":  "",
                })
    except requests.RequestException as e:
        print(f"  [Lever] Could not fetch {firm}: {e}")
    return results


# ─────────────────────────────────────────
#  REPORT BUILDER
# ─────────────────────────────────────────

def build_report() -> str:
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    lines = [
        "=" * 60,
        f"  MORNING INTERNSHIP REPORT — {today}",
        "=" * 60,
        "",
    ]

    # ── JSearch queries ──────────────────────────────────────
    all_jsearch_jobs = []
    seen_ids = set()

    queries = [
        "quantitative intern summer 2026",
        "quant research intern finance 2026",
        "data science intern finance 2026",
        "machine learning intern finance 2026",
        "algorithmic trading intern 2026",
        "investment banking intern summer 2026",
        "software engineer intern trading firm 2026",
    ]

    print("Querying JSearch API...")
    for q in queries:
        print(f"  → {q}")
        jobs = fetch_jsearch_listings(q, num_pages=1)
        for job in jobs:
            job_id = job.get("job_id") or job.get("job_apply_link") or job.get("job_title", "")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            if is_relevant(job):
                all_jsearch_jobs.append(job)

    lines.append(f"── JSearch Results ({len(all_jsearch_jobs)} relevant listings) ──")
    lines.append("")
    if all_jsearch_jobs:
        for job in all_jsearch_jobs:
            lines.append(format_job(job, source="JSearch"))
            lines.append("")
    else:
        lines.append("  No relevant listings found via JSearch today.")
        lines.append("")

    # ── Greenhouse & Lever board queries ─────────────────────
    all_scraped = []
    print("\nQuerying Greenhouse boards...")
    for firm, token in GREENHOUSE_BOARDS.items():
        print(f"  → {firm}")
        all_scraped.extend(fetch_greenhouse_jobs(firm, token))

    print("Querying Lever boards...")
    for firm, slug in LEVER_COMPANIES.items():
        print(f"  → {firm}")
        all_scraped.extend(fetch_lever_jobs(firm, slug))

    lines.append(f"── Greenhouse / Lever Results ({len(all_scraped)} listings found) ──")
    lines.append("")
    if all_scraped:
        for job in all_scraped:
            lines.append(format_job(job, source="Direct"))
            lines.append("")
    else:
        lines.append("  No intern listings found on direct career pages today.")
        lines.append("")

    lines.append("=" * 60)
    lines.append("End of report. Good luck out there.")
    lines.append("=" * 60)

    return "\n".join(lines)


# ─────────────────────────────────────────
#  EMAIL DELIVERY (optional)
# ─────────────────────────────────────────

def send_email(report: str):
    subject = f"Internship Report — {datetime.date.today().strftime('%b %d, %Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(report, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("\nReport emailed successfully.")
    except Exception as e:
        print(f"\nFailed to send email: {e}")


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Morning internship report")
    parser.add_argument("--email", action="store_true", help="Send report via email in addition to printing")
    args = parser.parse_args()

    report = build_report()
    print("\n" + report)

    if args.email:
        send_email(report)
