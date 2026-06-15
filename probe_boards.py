"""
probe_boards.py — throwaway probe to find which target firms expose
free Greenhouse / Lever JSON boards. Not part of the main app.
"""

import requests
import re
import concurrent.futures as cf

# Unique firm names worth probing (deduped, primary names only).
FIRMS = [
    "SIG", "Susquehanna", "Jane Street", "Optiver", "Citadel", "Citadel Securities",
    "Jump Trading", "IMC Trading", "DRW", "Hudson River Trading", "Two Sigma",
    "DE Shaw", "Five Rings", "Akuna Capital", "Chicago Trading Company",
    "Belvedere Trading", "Flow Traders", "Maven Securities", "G Research",
    "Tower Research Capital", "Radix Trading", "Headlands Technologies", "Vatic Labs",
    "Voloridge", "XTX Markets", "Qube Research Technologies", "Quantlab", "XR Trading",
    "TransMarket Group", "Geneva Trading", "Valkyrie Trading", "Group One Trading",
    "Wolverine Trading", "GTS", "Old Mission Capital", "Hudson Bay Capital",
    "Bluefin", "DV Trading", "PEAK6", "Tanius Technology", "Teza Technologies",
    "Virtu Financial", "TrexQuant", "Arrowstreet Capital", "Trillium Trading",
    "Consolidated Trading", "Freestone Grove", "Highbridge Capital", "HAP Capital",
    "Simplex Trading", "SquarePoint Capital", "Aquatic Capital", "Epoch Capital",
    "Jain Global", "Edgestream Partners",
    "Renaissance Technologies", "AQR Capital Management", "Man Group", "Winton",
    "Marshall Wace", "Cubist Systematic Strategies", "Point72", "Millennium Management",
    "Balyasny Asset Management", "Schonfeld", "WorldQuant", "Engineers Gate",
    "PDT Partners", "Graham Capital Management", "Tudor Investment Corporation",
    "Bridgewater Associates", "Capula Investment Management", "Aspect Capital",
    "Brevan Howard", "Caxton Associates", "ExodusPoint Capital Management",
    "Verition Fund Management", "Systematica Investments", "PanAgora Asset Management",
    "Acadian Asset Management", "Research Affiliates", "Magnetar Capital",
    "The Voleon Group", "Moore Capital", "GSA Capital", "Walleye Capital",
    "Garda Capital", "Capstone Investment Advisors", "Weiss Asset Management",
    "Millburn Ridgefield", "HBK Capital", "Quadrature", "Ansatz Capital",
    "Bracebridge Capital", "Stevens Capital", "Bayview Asset Management",
    "Quantitative Brokers", "QMS Capital",
    "Goldman Sachs", "Morgan Stanley", "JPMorgan", "Bank of America", "Citi",
    "Barclays", "UBS", "Deutsche Bank", "BNP Paribas", "Societe Generale", "HSBC",
    "RBC Capital Markets", "TD Securities", "Jefferies", "Nomura", "Mizuho",
    "Wells Fargo", "Santander", "Macquarie", "Standard Chartered",
    "BlackRock", "Vanguard", "Fidelity", "State Street", "PIMCO", "T. Rowe Price",
    "Capital Group", "Dimensional Fund Advisors", "Bloomberg", "CME Group", "Cboe",
    "Wellington Management", "Geode Capital", "Alliance Bernstein",
    "MFS Investment Management", "Lord Abbett", "Voya Financial", "Wolfe Research",
    "StoneX", "Fannie Mae", "Tradeweb", "Instinet",
]


def slug_candidates(firm: str) -> list[str]:
    """Generate plausible board slugs/tokens from a firm name."""
    name = firm.strip()
    lower = name.lower()
    # strip common corporate suffixes for a shorter variant
    short = re.sub(
        r"\b(capital|management|group|trading|securities|technologies|technology|"
        r"partners|associates|investments?|investment|advisors|asset|fund|llc|inc|"
        r"corporation|corp|the)\b",
        "", lower,
    )
    def norm(s, sep=""):
        return sep.join(re.findall(r"[a-z0-9]+", s))
    cands = {
        norm(lower),            # janestreet
        norm(short),            # jane
        norm(lower, "-"),       # jane-street
        norm(short, "-"),       # jane
    }
    return [c for c in cands if len(c) >= 3]


def probe_greenhouse(slug: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            n = len(r.json().get("jobs", []))
            return ("greenhouse", slug, n)
    except requests.RequestException:
        pass
    return None


def probe_lever(slug: str):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200 and isinstance(r.json(), list):
            return ("lever", slug, len(r.json()))
    except requests.RequestException:
        pass
    return None


def probe_firm(firm: str):
    hits = []
    for slug in slug_candidates(firm):
        for fn in (probe_greenhouse, probe_lever):
            res = fn(slug)
            if res:
                hits.append(res)
    return firm, hits


if __name__ == "__main__":
    print(f"Probing {len(FIRMS)} firms on Greenhouse + Lever...\n")
    found = {}
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        for firm, hits in ex.map(probe_firm, FIRMS):
            if hits:
                found[firm] = hits

    print("=" * 60)
    print(f"FIRMS WITH WORKING BOARDS ({len(found)}):\n")
    for firm in sorted(found):
        for platform, slug, n in found[firm]:
            print(f"  {firm:35s} {platform:11s} {slug:30s} {n} jobs")
