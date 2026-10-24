# START HERE — Team handoff bundle

1. **Read `MASTER_PLAN.md`** as the source of truth for schedule, five owners, research-backed model/data/hosting choices, and Sunday requirements.
2. **Read `AGENTS.md`** before assigning tasks to coding agents; paste the role instructions into each agent task.
3. **Create GitHub Issues** from `GITHUB_ISSUES.md`; name an actual owner for each, add to GitHub Project board.
4. **Run existing starter** using instructions in `README.md`; this bundle includes a functional Streamlit prototype and automated test code, NOT real generated data or performance results.
5. **Deploy** with provided `Dockerfile` on Railway (link main, configure OPENAI_API_KEY and OPENAI_MODEL=gpt-4o-mini as variables). Test the app; do not claim successful deployment until it is actually reachable.
6. **Generate and measure real examples** (planned 6 intents × 20 each) and add documented results before Sunday.
7. **Note needed code upgrade**: current evaluation.py only uses TF-IDF cosine; add MiniLM sentence-embedding-based diversity/copy checks offline to more directly satisfy the professor's embedding-space language.
8. **Database**: none needed for MVP. Supabase is optional only if persistence becomes necessary and does not threaten the Saturday checkpoint.