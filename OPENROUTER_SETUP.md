# OpenRouter setup: SynthLab on a $4.64 balance

OpenRouter gives this educational project access to an OpenAI-compatible API without requiring separate OpenAI API credits. We recommend the known structured-output-capable model **`openai/gpt-4o-mini`**.

## Budget policy
- The account screenshot on Oct 23, 2026 shows **$4.64 remaining**. Do not enable Auto Top-Up.
- Generate a NEW, dedicated project key at https://openrouter.ai/keys; name it **SynthLab MSAI-630**.
- Set a **$2 USD total key credit limit**, with **no automatic reset** when the UI offers that. This is the actual spend-control boundary. The account's full $4.64 must not be exposed to one unlimited key.
- Use a single model: `openai/gpt-4o-mini`. The app locks the model selection whenever an OpenRouter key is configured. The generator also caps completion tokens at 1,200 per API batch.
- Approximate October 2026 price shown by OpenRouter for this model: **$0.15/1M input tokens; $0.60/1M output tokens**. For example, **100,000 input + 50,000 output tokens** would cost around **$0.045**, excluding any additional platform fees or pricing changes. This is an *illustration*, not a quote or measured experiment price.
- The exact 120-row cost will depend on prompt size, returned tokens, retries, and usage. Monitor the OpenRouter Activity/Credits page, especially with a small balance.
- No automatic fallbacks to costly models. Avoid free model auto-routing for formal evaluation: the same named model is needed for reproducibility.

Pricing source: https://openrouter.ai/openai/gpt-4o-mini
API compatibility: https://openrouter.ai/docs/community/frameworks
Key limit documentation: https://openrouter.ai/docs/api/api-reference/api-keys/create-keys

## Configure Streamlit Community Cloud
Open **share.streamlit.io → My apps → SynthLab → Settings → Secrets** and paste TOML, using your real values *only inside the Streamlit secrets editor*:

```toml
OPENROUTER_API_KEY = "sk-or-v1-REPLACE-IN-STREAMLIT-ONLY"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
SYNTHLAB_GENERATION_PASSWORD = "USE-YOUR-OWN-LONG-TEAM-ONLY-PASSWORD"
```

Delete old `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_BASE_URL` if you previously configured them only for this demo; SynthLab prioritizes OpenRouter when an `OPENROUTER_API_KEY` is present. Root-level Streamlit secrets are exported to environment variables.

**Never paste the actual key into GitHub, a screenshot, or ChatGPT.**

After saving the secrets, reboot or refresh the app if necessary. The sidebar should now display **Provider: OpenRouter** and a disabled `openai/gpt-4o-mini` model selector. Enter the private team password within the running app to unlock live generation.

## Smoke test with minimal spend
1. Set two BANKING77 intent categories (rather than all six).
2. Set four generated messages per category, for an eight-record smoke test.
3. Choose **Controlled live demo**, tone `frustrated`, length `short`.
4. Click **Generate real LLM records**; verify **eight requested** and record any shortfall.
5. Select **Quality dashboard → Evaluate current generated records**. Some fidelity metrics may say not measured for very small sample sizes, which is correct.
6. Check **OpenRouter → Activity/Credits** to verify charged usage.
7. Run the formal study (six intents × twenty messages) after the smoke test passes, ideally through the command-line experiment runner, which saves CSV, metrics, failure rows, and a manifest.

## Optional higher-quality generator

For a modest upgrade while keeping OpenAI-compatible structured output and the existing temperature setting, change the Streamlit secret **`OPENROUTER_MODEL = "openai/gpt-4.1-mini"`** and reboot the app. Its listed OpenRouter price is approximately **$0.40 per 1M input** and **$1.60 per 1M output** tokens, compared with GPT-4o mini's $0.15/$0.60. This is roughly 2.7× per token, but the small 120-text study may remain inexpensive in absolute dollars. Do a 2-category × 4-text smoke test before committing to a larger run. Source: https://openrouter.ai/openai/gpt-4.1-mini .

Other models, including GPT-5 Mini, may require different decoding parameters and may not accept the project's current `temperature` setting. Do **not** assume arbitrary model IDs are compatible merely because OpenRouter exposes them. Model quality must be tested by actual downstream intent and diversity metrics, not by the name or family alone.

Generation v3 rotates prompt examples and adds lexical duplicate rejection, with one controlled repair call at most per batch. A Streamlit session remembers the last 240 generated texts but a browser refresh/new session clears that history. A dedicated API-key spending cap remains the reliable budget ceiling.

## Important limits
- **Hosting is free**, not the API. OpenRouter models consume prepaid credits.
- One Streamlit session's generated records are temporary; refresh/restarts can clear them. Save CSV and metrics downloads. For the final presentation, review and version approved `results/latest/` artifacts to make dashboard loading reproducible.
- The team password discourages casual misuse, but it is not per-user authentication or a billing guarantee. The **OpenRouter API key credit limit** is the budget guardrail.
- No live call has been made by ChatGPT: actual generation needs your key saved in Streamlit.
- If API returns a 400 error about structured outputs, verify the model string and available providers instead of switching to an unverified model or dropping evaluation requirements.
