# Multimodal Construction Intelligence Platform

A Streamlit capstone application for visual site-safety review, concrete crack triage, indicative project planning and a weather-aware construction assistant.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL printed by Streamlit (normally http://localhost:8501).

## Gemini API key

The app works in demonstration mode without a key. For live image analysis and chat, paste a Google Gemini API key into the sidebar at runtime. The key is held in Streamlit session state / the active app process and is not written to a database or file by this app. For a deployed private instance, prefer Streamlit secrets or an approved secret manager rather than sharing keys.

Model configured: `gemini-2.5-flash`. Change `MODEL_NAME` in `app.py` if your Google AI account uses a different supported model.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and add `app.py`, `requirements.txt`, and this README.
2. In Streamlit Community Cloud, create an app pointing to `app.py`.
3. Deploy. No database, Dockerfile or external server is required.
4. Users can add their own Gemini key in the sidebar. For a centrally managed key, configure `GEMINI_API_KEY` in the app's Streamlit secrets and update the app to read it from `st.secrets`.

## Modules

- **Site Safety & PPE Audit:** image-based visible-evidence checklist, hazard severity and JSON report.
- **Crack Diagnostics:** visual defect triage, approximate width (when supportable), possible causes, repair considerations and urgency.
- **Planning & Valuation:** transparent thumb-rule rates, contingency, completion-based expenditure, indicative asset value and material quantities.
- **Site Assistant:** weather-specific alerts and multi-turn Gemini chat.

## Important limitations

- This is a capstone / decision-support prototype, not a certified safety inspection, structural assessment, BOQ, quantity survey, valuation or engineering approval.
- A photograph cannot reliably establish PPE certification, boot toe protection, harness anchorage, crack depth, crack activity or structural capacity. Unseen / occluded items should be treated as unverifiable.
- **IS 456:2000 is a concrete design code, not a PPE standard.** PPE recommendations should be checked against applicable Indian occupational safety requirements, project rules and relevant OSHA principles where applicable.
- Planning rates, market multipliers, steel factors and cement factors are illustrative defaults. Replace them with project BOQ, local rates, approved drawings, specifications and qualified quantity-surveyor / valuer input.
- Pollinations AI is a third-party conceptual image service. It is not a CAD/BIM tool and generated images must not be used for construction.
- Demo-mode results are explicitly sample outputs and do not analyze the uploaded image.
- Uploaded photos and prompts may be sent to Google Gemini when a user supplies an API key. Obtain authorization and avoid sensitive site data unless the service is approved for it.

## Suggested production hardening

Before real project deployment, add role-based authentication, server-side secret management, upload size limits, audit logging, retention controls, human review/approval, model-output schema validation, rate limiting, unit tests, and organization-approved privacy controls.
