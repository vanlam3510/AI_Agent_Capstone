# SecureFolio AI

SecureFolio AI is a permission-aware personal portfolio and Gemini 4 Hydrogen-powered assistant. It
filters portfolio records through four deterministic visibility tiers before rendering them
or passing them to the language model.

## Features

- Public, signed-in, selected-visitor, and owner-only data tiers
- Permission-scoped visitor Q&A using Google AI Studio
- Pre-LLM Unicode, hidden-comment, length, and prompt-injection checks
- Owner workflow: upload notes, sanitize, draft, preview, approve, and publish
- Streamlit role preview for demonstrating all four tiers

> The role selector is a classroom demo control, not production authentication. Connect and
> verify Beagle identity before deploying protected content.

## Local setup (Windows 11)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Add your Google AI Studio key to the ignored `.env` file:

```dotenv
GEMINI_API_KEY=your_key_here
```

Run the app:

```powershell
streamlit run app.py
```

Use `selected@example.com` in the selected-visitor preview to see the sample selected-tier
record.

