# Omada Release Tracker

A small, self-running project that:

1. Fetches Omada's public release calendar from Google Calendar (.ics feed).
2. Categorizes each event as **Cloud**, **Private Cloud**, or **On-Premises**
   based on its title.
3. Builds a static website (`docs/index.html`) with releases grouped
   by category, hosted for free via **GitHub Pages**.
4. Keeps a **changelog** (`changelog.json`), so you can see if a date
   has moved (e.g. "August Cloud Release: 5th → 19th").
5. Sends you an **email** if anything has changed since the last run.

Everything runs automatically once a day via GitHub Actions — no manual
steps needed after the initial setup.

## 1. Create the repo

Create a new (public or private) GitHub repo and add all the files from
this project (keep the folder structure, especially `.github/workflows/`).

## 2. Find the correct calendar URL

The default URL in the script points to:

```
https://calendar.google.com/calendar/ical/kinga.kostrzewa%40omadaidentity.com/public/basic.ics
```

That's the public iCal version of the calendar you linked to. To verify
or find it yourself:

1. Open the calendar in Google Calendar.
2. Click the three dots → **Settings and sharing**.
3. Under **Integrate calendar**, find **Public URL to this calendar**
   in iCal format — that's the URL the script needs.

If the link ever changes, you can override it without touching the code
(see step 4).

## 3. Enable GitHub Pages

Repo → **Settings → Pages** → under "Build and deployment" choose
**Source: GitHub Actions**. The workflow automatically deploys the
contents of `docs/`.

## 4. Set up variables and secrets

Repo → **Settings → Secrets and variables → Actions**.

**Variables** (can be public):
| Name | Value |
|---|---|
| `CALENDAR_ICS_URL` | (optional) overrides the default calendar link |

**Secrets** (for sending email, e.g. via Gmail with an "app password",
or any other SMTP provider):
| Name | Value |
|---|---|
| `SMTP_SERVER` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | e.g. `465` |
| `SMTP_USERNAME` | your sender email address |
| `SMTP_PASSWORD` | app password / SMTP password |
| `MAIL_TO` | your recipient email address |

> If you use Gmail, you'll need to create an "App Password" (requires
> 2-step verification to be enabled) — your regular password won't work.

## 5. Run it

The workflow runs automatically every day at 06:00 UTC (adjustable in
`.github/workflows/update-releases.yml` under `cron:`), but you can also
trigger it manually:

Repo → **Actions** → "Update Omada release calendar" → **Run workflow**.

After the first run:
- The site is available at `https://<your-username>.github.io/<repo-name>/`
- `data.json` contains the latest known events
- `changelog.json` contains the history of changes
- You'll get an email if anything changes

## Local testing

```bash
pip install -r requirements.txt
python fetch_releases.py
open docs/index.html   # or "start docs/index.html" on Windows
```

## How categorization works

The script looks at the event title and matches (in this order):

1. Both "private" and "cloud" appear (in any order) → **Private Cloud**
2. "On-Prem" / "On-Premises" → **On-Premises**
3. "Cloud" → **Cloud**
4. Anything else → **Other**

If Omada's naming doesn't match this exactly, adjust the regex patterns
(`RE_PRIVATE`, `RE_CLOUD`, `RE_ONPREM`) in `fetch_releases.py`.

## Files

```
fetch_releases.py                  # main script
templates/index.html.jinja         # website template
data.json                          # latest known events (auto-generated)
changelog.json                     # change history (auto-generated)
docs/index.html                    # the built website (auto-generated, Pages)
.github/workflows/update-releases.yml
```
