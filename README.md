# Internship Scraper 🚀

A daily web dashboard that scrapes GitHub internship repos, scores listings against your skills, and pushes approved ones to Google Sheets.

## Project Structure

```
InternshipScraper/
├── app.py                        # Flask server + pipeline orchestrator
├── config.json                   # Repos, API keys, thresholds, locations
├── requirements.txt              # Python dependencies
├── resume.pdf                    # ← Drop your resume here
├── credentials.json              # ← Google Sheets service account key (after GCP setup)
│
├── scraper/
│   ├── github_scraper.py         # Fetches READMEs from GitHub API
│   └── parser.py                 # Parses markdown tables → structured dicts
│
├── engine/
│   ├── skill_extractor.py        # PDF → skill list
│   └── matcher.py                # Scores listings against your skills
│
├── sheets/
│   └── google_sheets.py          # Pushes approved listings to Google Sheet
│
├── db/
│   └── database.py               # SQLite: seen/approved/skipped tracking
│
├── templates/
│   └── index.html                # Dashboard HTML
│
└── static/
    ├── style.css                 # Premium dark-mode styles
    └── app.js                    # Dashboard interactivity
```

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Add Your Resume
Drop `resume.pdf` into the project root. Skills are auto-extracted on first run.

### 3. Add GitHub PAT
In `config.json`, replace `YOUR_GITHUB_PAT_HERE` with your token.
Create one at: https://github.com/settings/tokens (needs only `public_repo` scope)

### 4. Google Sheets Setup (one-time)
1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable the **Google Sheets API**
4. Create a **Service Account** → download `credentials.json` → place in project root
5. Create a new Google Sheet → share it with the service account email
6. Copy the Sheet ID from the URL into `config.json`

### 5. Run
```bash
python app.py
```
Opens at http://localhost:5000 automatically.

## Morning Workflow
1. Run `python app.py`
2. Browser opens — new listings are already scored and sorted
3. Hit ✅ to add to your sheet, ❌ to skip forever
4. Done in 5–10 minutes

## Adding a New Repo
Click **"+ Add Repo"** in the dashboard, paste any GitHub URL (e.g. `https://github.com/owner/repo`), hit Add.
