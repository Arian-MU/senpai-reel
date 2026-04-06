"""
Curated list of Jobs-in-Australia competitor Instagram accounts to track.
Edit this list to add/remove accounts from the scraping target list.

Categories:
  - Resume & Career Coaches
  - Recruitment Agencies
  - HR & ATS Tips
  - Interview Prep
  - LinkedIn / Job Search Strategy
"""

# fmt: off
COMPETITOR_ACCOUNTS = [
    # ── Resume & Career Coaches ──────────────────────────────────────────────
    "resumeworded",          # AI-powered resume + LinkedIn feedback
    "careersidekick",        # Career advice, job search tips
    "the.career.strategist", # Australian career coach
    "iamhannah.co",          # Resume + job search for AU/NZ
    "careerwithsam",         # Interview + resume AU-focused
    "jobsearchcoach",        # General job search advice
    "theresumewriter",       # Professional resume tips
    "careercoachmelbourne",  # Melbourne-based career coach

    # ── Recruitment & HR ─────────────────────────────────────────────────────
    "hays.australia",        # Hays Recruitment AU
    "robertwaltersau",       # Robert Walters Australia
    "michaelpageaustralia",  # Michael Page AU
    "reedrecruitment",       # Reed Recruitment
    "seek.com.au",           # SEEK Australia (main job board)
    "hrmonline",             # HR news and insights AU

    # ── ATS & Resume Tips ────────────────────────────────────────────────────
    "tealau",                # Teal – resume builder / ATS
    "kickresume",            # Resume / cover letter builder
    "resumetricks",          # ATS resume hacks

    # ── Interview Prep ───────────────────────────────────────────────────────
    "interviewguru",         # Interview tips
    "theinterviewcoach",     # STAR method + behavioural tips
    "lindseypollak",         # Workplace + career advice

    # ── LinkedIn & Job Strategy ──────────────────────────────────────────────
    "linkedinau",            # LinkedIn Australia official
    "joshuafluke",           # LinkedIn personal branding
    "austinbelcak",          # Job search strategy, networking
]
# fmt: on

# Default max reels to scrape per account in batch mode
DEFAULT_MAX_ITEMS = 30

# Higher limits for key competitor deep-dives
PRIORITY_ACCOUNTS = {
    "resumeworded": 50,
    "seek.com.au": 50,
    "hays.australia": 50,
}


def get_accounts_with_limits() -> list[tuple[str, int]]:
    """Return list of (username, max_items) tuples for batch scraping."""
    return [
        (username, PRIORITY_ACCOUNTS.get(username, DEFAULT_MAX_ITEMS))
        for username in COMPETITOR_ACCOUNTS
    ]
