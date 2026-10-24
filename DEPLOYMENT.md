# Railway deployment and runbook (Oct 2026)

## Prerequisites

- GitHub repository: `abhay8046/synthlab-msai630-project4` (private)
- Railway account with access to that repository
- An OpenAI **API** key with billing/quota available; a ChatGPT Plus plan by itself does not grant API credits
- Team-only password, kept private
- No Supabase, PostgreSQL, Redis, vector DB, or separate frontend service for the MVP

## Connect Railway

1. Visit https://railway.com/new and sign in.
2. Choose **Deploy from GitHub Repo** and authorize Railway's GitHub access to the private SynthLab repository.
3. Choose the repository and the `main` branch. Railway automatically recognizes the root `Dockerfile`.
4. In service **Variables**, add `OPENAI_API_KEY` (secret), `OPENAI_MODEL=gpt-4o-mini`, and `SYNTHLAB_GENERATION_PASSWORD` (long random password).
5. In **Settings → Networking**, generate a public Railway domain.
6. Configure **Settings → Healthcheck path** as `/_stcore/health` and leave the default timeout unless real logs justify a change.
7. Inspect build and startup logs; verify an HTTPS URL loads in an incognito window.
8. In the site, verify real BANKING77 counts and the public attribution link. Enter the password and generate only 4 examples per category for a smoke test.
9. Verify the Generation and Evaluation tabs report actual counts and scores. Use the saved evaluated 120-row run as the presentation's reproducible reference.

Official docs:
- Dockerfiles: https://docs.railway.com/builds/dockerfiles
- Variables: https://docs.railway.com/variables
- Healthchecks: https://docs.railway.com/deployments/healthchecks
- GitHub deployments: https://docs.railway.com/guides/github-autodeploys

**Oct 2026 note:** Railway now recommends Infrastructure as Code instead of its deprecated `railway.toml`/`railway.json` config-as-code for *new* projects. We use dashboard settings and the Dockerfile; do not add a new `railway.toml` for this service.

## Operational caveats

- The site is public but repository private. The team's API key is only on the server.
- No database: Streamlit session state is not persistent through container restarts. A reviewed `results/latest/` fixture committed to GitHub is the reliable Sunday dashboard.
- MiniLM model download / embedding evaluation happens locally or in Colab, not at every page request.
- Public live generation must remain locked unless the password is configured. Restrict session size via app controls and do not share the team password publicly.
- A "2xx" healthcheck only means the web process is listening. You must separately verify BANKING77 fetch and API generation.
- If raw.githubusercontent.com is blocked, surface an explicit error; do not silently swap datasets.
- If API fails, the app should display errors; inspect Railway Variables, outbound connectivity, model name, billing and quota.
- If Railway refuses to load after the Docker build, verify `PORT` and logs. Start command in Dockerfile listens on `0.0.0.0` and `$PORT`.
- Uploading a locally generated study's CSV/metrics to this codebase is a controlled team review step; never upload `.env` or private blind-study answer keys.

## Sunday checklist

- [ ] GitHub Actions green on frozen commit
- [ ] Real 6×20 API study run; disclose actual successful count / shortfalls
- [ ] Eval CSV, metrics JSON, manifest produced and reviewed
- [ ] MiniLM offline audit (if time allows)
- [ ] Human audit rating counts and method recorded (if done)
- [ ] HTTPS page loads and sample generation works
- [ ] All four rubric properties shown with denominators
- [ ] Failure cases, limitations and ethics are honest
- [ ] Slides 10–12; timed demo 10 minutes; 5-minute Q&A prep
- [ ] Backup demo video saved offline; individual contribution statements prepared

## What the assistant cannot do without user setup

The repository integration can edit source and Issues. Railway cannot be provisioned or assigned secrets through the currently connected tools. The project owner must link Railway and enter the API key/password **within Railway**, not in the chat.
