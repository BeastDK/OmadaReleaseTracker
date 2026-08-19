# Omada Release Tracker

Lille, selvkørende projekt der:

1. Henter Omadas offentlige release-kalender fra Google Calendar (.ics-feed).
2. Kategoriserer hver event som **Cloud**, **Private Cloud** eller **On-Premises**
   ud fra titlen.
3. Bygger en statisk hjemmeside (`docs/index.html`) med releases grupperet
   pr. kategori, hostet gratis via **GitHub Pages**.
4. Fører en **changelog** (`changelog.json`), så det fremgår hvis en dato
   flyttes (fx "August Cloud Release: 5. → 19.").
5. Sender dig en **mail**, hvis der er sket ændringer siden sidste kørsel.

Alt sammen kører automatisk hver dag via GitHub Actions — du behøver ikke
gøre noget efter opsætningen.

## 1. Opret repo

Opret et nyt (gerne public) GitHub-repo og læg alle filerne fra dette
projekt ind i det (bevar mappestrukturen, særligt `.github/workflows/`).

## 2. Find den korrekte kalender-URL

Standard-URL'en i scriptet peger på:

```
https://calendar.google.com/calendar/ical/kinga.kostrzewa%40omadaidentity.com/public/basic.ics
```

Det er den offentlige iCal-udgave af den kalender, du linkede til. Vil du
selv verificere/finde den:

1. Åbn kalenderen i Google Calendar.
2. Klik de tre prikker → **Indstillinger og deling**.
3. Under **Integrer kalender** finder du **Offentlig adresse i iCal-format**
   — det er den URL, scriptet skal bruge.

Hvis linket ændrer sig, kan du overskrive det uden at røre koden (se
punkt 4).

## 3. Aktivér GitHub Pages

Repo → **Settings → Pages** → under "Build and deployment" vælg
**Source: GitHub Actions**. Workflowet deployer automatisk indholdet af
`docs/`.

## 4. Sæt variabler og secrets op

Repo → **Settings → Secrets and variables → Actions**.

**Variables** (kan være offentlige):
| Navn | Værdi |
|---|---|
| `CALENDAR_ICS_URL` | (valgfrit) overskriver standard-kalenderlinket |

**Secrets** (til mail-afsendelse, brug fx Gmail med en "app-adgangskode",
eller enhver anden SMTP-udbyder):
| Navn | Værdi |
|---|---|
| `SMTP_SERVER` | fx `smtp.gmail.com` |
| `SMTP_PORT` | fx `465` |
| `SMTP_USERNAME` | din afsender-mailadresse |
| `SMTP_PASSWORD` | app-adgangskode / SMTP-password |
| `MAIL_TO` | din modtager-mailadresse |

> Bruger du Gmail, skal du oprette en "App Password" (kræver 2-trins
> bekræftelse aktiveret) — dit almindelige password virker ikke.

## 5. Kør det

Workflowet kører automatisk hver dag kl. 06:00 UTC (kan justeres i
`.github/workflows/update-releases.yml` under `cron:`), men du kan også
trigge det manuelt:

Repo → **Actions** → "Update Omada release calendar" → **Run workflow**.

Efter første kørsel:
- Siden ligger på `https://<dit-brugernavn>.github.io/<repo-navn>/`
- `data.json` indeholder de seneste kendte events
- `changelog.json` indeholder historikken over ændringer
- Du får en mail, hvis noget ændrer sig

## Lokalt test

```bash
pip install -r requirements.txt
python fetch_releases.py
open docs/index.html   # eller "start docs/index.html" på Windows
```

## Sådan virker kategoriseringen

Scriptet kigger på event-titlen og matcher (i denne rækkefølge):

1. "Private Cloud" → **Private Cloud**
2. "On-Prem" / "On-Premises" → **On-Premises**
3. "Cloud" → **Cloud**
4. Alt andet → **Andet**

Passer Omadas navngivning ikke præcis med dette, kan du justere
`CATEGORY_PATTERNS` i `fetch_releases.py`.

## Filer

```
fetch_releases.py                  # hovedscript
templates/index.html.jinja         # skabelon til hjemmesiden
data.json                          # seneste kendte events (auto-genereret)
changelog.json                     # historik over ændringer (auto-genereret)
docs/index.html                    # den bygget hjemmeside (auto-genereret, Pages)
.github/workflows/update-releases.yml
```
