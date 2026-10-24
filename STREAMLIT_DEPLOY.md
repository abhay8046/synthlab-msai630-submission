# Deploy SynthLab free on Streamlit Community Cloud

**Source code:** Private GitHub repository: `abhay8046/synthlab-msai630-project4`. **Entrypoint:** `app.py`. **Branch:** `main`.

## Create app
1. Open https://share.streamlit.io/ and sign in.
2. Connect the `abhay8046` GitHub account. For private repos: workspace **Settings → Linked accounts → Source control → Connect here**, and authorize private repository access.
3. **Create app → Yup, I have an app**.
4. Use repository `abhay8046/synthlab-msai630-project4`, branch `main`, main file `app.py`.
5. Optionally choose subdomain `synthlab-msai630` if available.
6. **Advanced settings:** Python 3.11; configure secrets only in Streamlit Cloud, never GitHub.
7. Start deployment. If a fatal error appears, open **Manage app → Logs** and inspect the traceback.

## Secrets
Streamlit Cloud's Secrets editor uses **TOML** syntax. Root-level entries are also exported as environment variables accessible with `os.environ`. Paste this *template* into Advanced settings → Secrets, replacing the placeholders with real values **privately**:

```toml
OPENROUTER_API_KEY = "sk-or-v1-REPLACE-IN-STREAMLIT-ONLY"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
SYNTHLAB_GENERATION_PASSWORD = "replace-with-long-random-team-only-password"
```

Leave `OPENROUTER_API_KEY` out if you only want a read-only preview of the public dataset dashboard. Your $4.64 OpenRouter balance is enough for a low-cost pilot, but all actual token usage draws down those credits. Set a dedicated $2 total key spending limit at OpenRouter and leave Auto Top-Up disabled. See [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md).

**Generation is disabled unless both API credentials and the team password are configured.** An OpenRouter key takes precedence over legacy OpenAI credentials. On public deployments, visitors must know that password to make API calls; do not share it in the slide deck.

## Private repo vs public app
Streamlit Cloud can host an app backed by a private repository. The deployed app is private by default; to let a professor or audience view it without login, go to app Settings → **Sharing** and switch the app to public. This does **not** change GitHub repository visibility.

## No-terminal experiment collection (recommended for Sunday)

1. Open the deployed Streamlit app and enter the team generation password.
2. Under sidebar **Customer question categories**, select only two; set **Generate per category = 4**.
3. On **Generate**, click **Generate real LLM records** and download the generated CSV.
4. On **Quality dashboard**, click **Evaluate current generated records**.
5. Click **Download complete experiment evidence ZIP**. This saves the real CSV, evaluations, failures, metrics, batch log (where available), and a provenance manifest.
6. For the formal study, select **all six categories**, keep **Balanced evaluation**, and choose **20 per category**. Generate once, evaluate, download the ZIP before you close the browser or restart the server.
7. Review the ZIP for flagged near-copies or potential identifiers. **Upload the ZIP to this ChatGPT conversation** and ask for the real results to be committed to the private GitHub repository; the deployed app can then display frozen results.
8. Make sure your OpenRouter project key has a fixed $2 total limit and no automatic reset. A Streamlit password is not a reliable billing limit.

The UI starts with only four records per category to avoid accidental large spending. For Sunday's live demo, reopen the website, choose the same categories and seed count as the saved study, then use **Generate → Restore a saved study** to import your evidence ZIP. This restores real metrics and examples without another LLM charge. A downloaded evidence ZIP is critical: free Streamlit hosting has ephemeral sessions and does not persist local files between restarts.

## Experiment
The site can generate and evaluate a small live batch. For a reproducible 120-record study, run:

```bash
python run_experiment.py --per-intent 20 --output-dir results/latest
```

Review output manually, then commit the *approved* `results/latest/` CSV/JSON files to the private repo if you want the deployed dashboard to load frozen results at startup. Do not commit real bank customer data, API keys, or blind-study answer keys.

## Troubleshooting
- Repository not shown: complete private repository GitHub authorization in Streamlit Cloud workspace settings.
- App loads but generation is disabled: check root-level Secrets keys and save; refresh/reboot app if necessary.
- Dataset checksum failure: verify outbound access to `raw.githubusercontent.com` and the pinned source rather than bypassing validation.
- OpenRouter authentication or quota error: verify the OpenRouter account/key credit limit, model ID, available credits and private key spelling.
- On cold start, Community Cloud may need to wake an idle app; test the demo link from another browser in advance.

Reference: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
