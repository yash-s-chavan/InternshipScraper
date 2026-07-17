/*
  app.js
  ------
  Client-side logic for the Internship Scraper dashboard.
  Communicates with Flask backend via fetch() calls.

  TODO: On page load → GET /api/listings → render listing cards
  TODO: On page load → GET /api/stats   → update header stats bar

  TODO: renderListingCard(listing) — build card HTML from listing object
  TODO: renderMatchBadge(tier, score) — colored badge with emoji + percentage
  TODO: renderSkillChips(skills_matched, all_skills) — green matched / grey unmatched

  TODO: handleApprove(listing_id) → POST /api/approve → show success toast + remove card
  TODO: handleSkip(listing_id)    → POST /api/skip    → show skip toast + remove card

  TODO: Filter bar logic — filter cards client-side by tier / location / repo

  TODO: "Add Repo" modal — open/close, POST /api/add-repo, show loading state

  TODO: Pipeline panel — GET /api/pipeline → render approved listings table
  TODO: Tab switching between Pipeline and Stats views

  TODO: Toast notification system (success / error / info, auto-dismiss 3s)

  TODO: Auto-open browser on app start (handled by app.py via webbrowser.open)
*/
