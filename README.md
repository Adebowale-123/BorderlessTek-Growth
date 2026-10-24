# BorderlessTek Growth — Lead Finder

A private tool that finds parents asking where their child (ages 6–16) can learn coding, animation, design and other
digital skills. It drafts a helpful reply for each, and tracks every family from first contact to their onboarding
call and enrolment.

## How it works

1. **Search.** Every few hours (`/tick/`, called by cron-job.org) it reads public parent communities on Reddit, your
   Google Alerts, and any RSS feeds you add.
2. **Score.** Each post gets a score out of 100, based on:
   - a parent talking about their child;
   - the child's age (6–16);
   - the topic (coding, Scratch, Python, game design, animation, design, robotics, AI, STEM);
   - whether they're asking for recommendations;
   - interest in classes;
   - a target country.

   Posts that look like adult learners, ads, or something else entirely are filtered out.
3. **Draft.** Each reply gives useful, age-appropriate advice and free resources first. It ends with an honest
   disclosure ("I work with BorderlessTek…") and a tracked link to book the onboarding call.
4. **Review.** On **Parents to reply**, a team member opens the post, edits and copies the reply, posts it as
   themselves, and clicks **I replied**. About 2 minutes per post.
5. **Track.** Interested parents become **Leads** (New → Contacted → In conversation → Call booked → Enrolled /
   Not now). Follow-ups are scheduled at 2, 5 and 10 days, with a ready-to-send message for each.
6. **Daily summary.** A morning message goes to Telegram and/or email: parents to reply to, follow-ups due, calls
   booked.

### Why a person posts the replies

Automated posting and unsolicited DMs are banned by Reddit, Facebook, Instagram and WhatsApp, and fall foul of
UK/EU marketing law (PECR, GDPR). Accounts that do it get shut down, and for a children's education brand trust is
everything. So the tool finds the conversations and does the writing; a person presses send.

Facebook groups can't be read automatically. Paste posts you find there into **Add a post you found** to get a
score and a draft.

### Children's data

The tool records only what parents share publicly or tell you, and the child's age, never children's names. Only
email or WhatsApp a parent who agreed to it (the **consent** box on each lead).

## Running locally (Windows)

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_growth
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

## Deploying (free)

1. Create a free **Neon** project and copy its connection string.
2. Render → **New → Blueprint** → this repository. Fill in `DATABASE_URL`, `ADMIN_USERNAME` and
   `ADMIN_PASSWORD`. Use a separate Render workspace: each workspace gets its own 750 free hours.
3. Set up **cron-job.org** to open `https://<app>.onrender.com/tick/?key=<TICK_KEY>` every 30 minutes. Write any
   `+` in the key as `%2B`.
4. In the app's **Settings**, add the onboarding call booking link (e.g. Calendly), the name to sign replies with,
   and the Telegram details for the daily summary.

## Tests

```powershell
.venv\Scripts\python manage.py test apps
```
