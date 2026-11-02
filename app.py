import json
import math
import os
import re
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

import streamlit as st
from PIL import Image

# Optional AI dependency is imported lazily so demo mode works without a key.
APP_TITLE = "Multimodal Construction Intelligence Platform"
MODEL_NAME = "gemini-2.5-flash"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Styling --------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#17243a; --muted:#64748b; --line:#e5eaf1; --blue:#2356d8; --teal:#0f9f8f; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:linear-gradient(180deg,#f7f9fc 0%,#f2f5fa 100%); color:var(--ink); }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.03em; }
h1 { font-size:2.15rem !important; }
.block-container { padding-top:1.5rem; padding-bottom:3rem; max-width:1450px; }
[data-testid="stSidebar"] { background:#101c31; }
[data-testid="stSidebar"] * { color:#edf3ff !important; }
[data-testid="stSidebar"] .stTextInput input { background:#1d2b43; color:white; }
.hero { padding:1.5rem 1.7rem; border-radius:20px; color:white;
        background:linear-gradient(115deg,#142747,#2457a7 68%,#0f9488);
        box-shadow:0 12px 35px rgba(27,57,102,.16); margin-bottom:1.1rem; }
.hero p { color:#dbeafe; margin-bottom:0; }
.eyebrow { font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; font-weight:700; opacity:.8; }
.panel { background:white; border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem; }
.metric { background:white; border:1px solid var(--line); border-radius:15px; padding:1rem; min-height:108px; }
.metric-label { color:#64748b; font-size:.78rem; font-weight:600; }
.metric-value { color:#17243a; font-family:'Space Grotesk'; font-size:1.55rem; font-weight:700; margin-top:.25rem; }
.pill { display:inline-block; border-radius:999px; padding:.28rem .7rem; font-size:.76rem; font-weight:700; }
.pill-green { color:#087443; background:#dcfce7; }
.pill-yellow { color:#92400e; background:#fef3c7; }
.pill-red { color:#b42318; background:#fee4e2; }
.pill-blue { color:#1d4ed8; background:#dbeafe; }
.small-muted { color:#64748b; font-size:.83rem; }
div.stButton > button { border-radius:10px; font-weight:700; }
div[data-testid="stFileUploader"] { background:white; border:1px dashed #b8c6da; border-radius:14px; padding:.6rem; }
hr { border-color:#e5eaf1; }
</style>
""", unsafe_allow_html=True)


# ----------------------------- Utilities ------------------------------------
def safe_json_from_text(text):
    """Parse JSON even if a model wraps it in a Markdown code fence."""
    if not text:
        raise ValueError("The model returned an empty response.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def gemini_client(api_key):
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        st.warning(f"Gemini client could not be initialized; using demonstration mode. Details: {exc}")
        return None


def call_gemini_json(client, prompt, image=None):
    """Call Gemini and require JSON output. Image is optional."""
    from google.genai import types
    contents = [prompt]
    if image is not None:
        contents.append(image)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return safe_json_from_text(response.text)


def image_for_gemini(uploaded):
    image = Image.open(uploaded).convert("RGB")
    # Keep image payloads manageable while preserving inspection detail.
    image.thumbnail((1800, 1800))
    return image


def download_json(data, filename):
    payload = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    st.download_button(
        "⬇ Download JSON report",
        data=payload.encode("utf-8"),
        file_name=filename,
        mime="application/json",
        use_container_width=False,
    )


def status_pill(status):
    s = str(status).lower()
    cls = "pill-green" if any(x in s for x in ["safe", "low", "good", "normal", "minor"]) else (
        "pill-red" if any(x in s for x in ["critical", "high", "unsafe", "urgent", "immediate"]) else "pill-yellow"
    )
    st.markdown(f'<span class="pill {cls}">{status}</span>', unsafe_allow_html=True)


def show_metric(label, value, sub=None):
    st.markdown(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="small-muted">{sub or ""}</div></div>',
        unsafe_allow_html=True,
    )


def demo_safety():
    return {
        "safety_score": 72,
        "overall_status": "Needs Improvement",
        "ppe_detection": {
            "helmet": {"detected": True, "compliant": True, "notes": "Hard hat visible on the primary worker."},
            "high_visibility_vest": {"detected": True, "compliant": True, "notes": "Reflective vest appears visible."},
            "steel_toe_boots": {"detected": False, "compliant": None, "notes": "Footwear is not sufficiently visible to verify."},
            "safety_harness": {"detected": False, "compliant": None, "notes": "Harness use cannot be confirmed from this view."}
        },
        "hazards": [
            {"hazard": "Unverified fall-protection equipment near elevated work area", "severity": "High",
             "evidence": "Harness connection is not visible; confirm whether the worker is exposed to a fall hazard.",
             "corrective_remedy": "Stop exposed work until a competent person verifies compliant fall protection, anchorage and tie-off."},
            {"hazard": "Foot protection not verifiable", "severity": "Medium",
             "evidence": "Boot type is obscured.",
             "corrective_remedy": "Verify approved protective footwear before entry to the active work zone."}
        ],
        "limitations": ["Demonstration-mode sample only; not an analysis of the uploaded image."]
    }


def demo_crack():
    return {
        "defect_type": "Hairline",
        "estimated_crack_width_mm": 0.3,
        "confidence": "Low (demonstration mode)",
        "root_causes": ["Possible drying shrinkage", "Possible thermal movement"],
        "recommended_repairs": [
            {"method": "Monitor and seal", "details": "Record crack length and width; use a compatible flexible sealant if non-structural status is confirmed."},
            {"method": "Engineering review", "details": "Obtain site measurements and assess whether the crack is active or associated with movement."}
        ],
        "urgency": "Routine monitoring",
        "limitations": ["Demonstration-mode sample only; not an analysis of the uploaded image."]
    }


def render_hazards(hazards):
    if not hazards:
        st.success("No hazards were identified in the model output. This does not prove the site is hazard-free.")
        return
    for item in hazards:
        sev = item.get("severity", "Unspecified")
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{item.get('hazard', 'Unspecified hazard')}**")
            c2.markdown(f'<span class="pill {"pill-red" if sev in ["High","Critical"] else "pill-yellow" if sev=="Medium" else "pill-green"}">{sev}</span>', unsafe_allow_html=True)
            if item.get("evidence"):
                st.caption(f"Evidence: {item['evidence']}")
            st.markdown(f"**Corrective action:** {item.get('corrective_remedy', 'Refer to site safety officer.')}")


def format_inr(value):
    if value >= 1e7:
        return f"₹{value / 1e7:,.2f} Cr"
    return f"₹{value / 1e5:,.2f} L"


# ----------------------------- Sidebar --------------------------------------
with st.sidebar:
    st.markdown("## 🏗️ MCI Platform")
    st.caption("Skill Wallet · Capstone Project 1")
    api_key = st.text_input("Google Gemini API key", type="password", placeholder="Paste key for live AI analysis")
    client = gemini_client(api_key.strip()) if api_key.strip() else None
    if client:
        st.success("Gemini connected")
        ai_mode = "Live Gemini"
    else:
        st.info("Demonstration mode active")
        ai_mode = "Demo mode"
    st.markdown("---")
    st.markdown("### Architecture")
    st.markdown("""
    <div class="small-muted">
    <b>Streamlit UI</b><br>↓<br><b>Validation & image preprocessing</b><br>↓<br>
    <b>Gemini multimodal / demo engine</b><br>↓<br><b>JSON normalization & reports</b><br>
    <br><b>State:</b> browser session only<br><b>Storage:</b> no external database
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Navigate")
    st.caption("Use the module tabs in the main workspace.")
    st.markdown("---")
    st.caption(f"Engine: {ai_mode}")
    st.caption("Do not enter confidential project information unless approved for the chosen AI service.")

st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Construction intelligence · India-ready workflow</div>
  <h1>{APP_TITLE}</h1>
  <p>Visual site checks, early defect triage, project planning and weather-aware field guidance.</p>
</div>
""", unsafe_allow_html=True)

st.warning(
    "Engineering and safety disclaimer: AI outputs are preliminary decision support, not a statutory inspection, "
    "structural assessment, certified valuation or substitute for a competent person / licensed engineer. "
    "IS 456 is a concrete design code, not a PPE checklist; PPE checks should be aligned with applicable OSHA "
    "requirements and Indian site rules. Verify every finding on site."
)

safety_tab, crack_tab, planning_tab, assistant_tab = st.tabs([
    "🦺 Site Safety & PPE Audit",
    "🧱 Crack Diagnostics",
    "📐 Planning & Valuation",
    "🌦️ Site Assistant"
])

# ----------------------------- Tab 1 ----------------------------------------
with safety_tab:
    st.subheader("Site Safety & PPE Audit")
    st.write("Upload a clear site photograph. The audit identifies visible PPE evidence and observable hazards.")
    safety_file = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="safety_upload")
    if safety_file:
        try:
            preview = image_for_gemini(safety_file)
            left, right = st.columns([1, 1.35])
            with left:
                st.image(preview, caption="Uploaded site image", use_container_width=True)
            with right:
                st.markdown("**Audit scope**")
                st.markdown("- Hard hats / helmets\n- High-visibility vests\n- Steel-toe footwear (only if visible)\n- Fall-arrest harnesses and visible tie-off\n- Observable housekeeping, access and work-at-height hazards")
                st.caption("A hidden or occluded item is reported as unverifiable, not automatically non-compliant.")
            if st.button("Run PPE & hazard audit", type="primary", key="run_safety"):
                prompt = """
You are a construction site safety visual-assessment assistant. Inspect the attached image only.
Return valid JSON with exactly these top-level keys:
{
 "safety_score": integer 0-100,
 "overall_status": string,
 "ppe_detection": {
   "helmet": {"detected": boolean, "compliant": boolean|null, "notes": string},
   "high_visibility_vest": {"detected": boolean, "compliant": boolean|null, "notes": string},
   "steel_toe_boots": {"detected": boolean, "compliant": boolean|null, "notes": string},
   "safety_harness": {"detected": boolean, "compliant": boolean|null, "notes": string}
 },
 "hazards": [{"hazard": string, "severity": "Low|Medium|High|Critical", "evidence": string, "corrective_remedy": string}],
 "limitations": [string]
}
Use null for compliance when an item cannot be verified visually. Do not infer unseen PPE. Identify only hazards supported by visible evidence. Give practical corrective remedies.
Use OSHA construction safety principles and applicable Indian construction-site rules as references. Important: IS 456:2000 is a plain/reinforced concrete design code, not a PPE standard; do not claim it specifies helmets, vests, boots or harnesses. Mention any structural/concrete observations only as limitations or referrals. Score reflects visible evidence only and must not imply legal certification. If the image is ambiguous, say so.
"""
                with st.spinner("Inspecting image..."):
                    try:
                        result = call_gemini_json(client, prompt, preview) if client else demo_safety()
                        st.session_state["safety_result"] = result
                    except Exception as exc:
                        st.error(f"AI analysis failed: {exc}. Showing demonstration output instead.")
                        st.session_state["safety_result"] = demo_safety()
            result = st.session_state.get("safety_result")
            if result:
                st.markdown("---")
                st.markdown("### Audit summary")
                m1, m2 = st.columns(2)
                with m1:
                    show_metric("Visible-evidence safety score", f"{result.get('safety_score', '—')}/100", "Indicative, not a compliance certificate")
                with m2:
                    st.markdown("**Overall status**")
                    status_pill(result.get("overall_status", "Not assessed"))
                st.markdown("### PPE detection checklist")
                ppe = result.get("ppe_detection", {})
                labels = [("helmet", "Helmet"), ("high_visibility_vest", "High-visibility vest"),
                          ("steel_toe_boots", "Steel-toe boots"), ("safety_harness", "Safety harness")]
                for key, label in labels:
                    item = ppe.get(key, {})
                    detected = item.get("detected")
                    compliant = item.get("compliant")
                    state = "Compliant evidence visible" if compliant is True else (
                        "Not compliant / absent" if compliant is False else "Unable to verify")
                    icon = "✅" if compliant is True else ("⚠️" if compliant is False else "❔")
                    st.markdown(f"**{icon} {label}:** {state} — {item.get('notes', '')}")
                st.markdown("### Identified hazards & corrective remedies")
                render_hazards(result.get("hazards", []))
                for note in result.get("limitations", []):
                    st.caption(f"Limitation: {note}")
                download_json(result, f"site_safety_audit_{datetime.now():%Y%m%d_%H%M%S}.json")
        except Exception as exc:
            st.error(f"Could not read the image: {exc}")

# ----------------------------- Tab 2 ----------------------------------------
with crack_tab:
    st.subheader("Crack Diagnostics & Structural Integrity")
    st.write("Upload a close, well-lit image with a scale reference where possible.")
    crack_file = st.file_uploader("Concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_upload")
    if crack_file:
        try:
            crack_image = image_for_gemini(crack_file)
            a, b = st.columns([1, 1.35])
            with a:
                st.image(crack_image, caption="Uploaded surface image", use_container_width=True)
            with b:
                st.info("Image-only width estimates are approximate. For meaningful measurement, include a ruler / crack comparator in the same plane.")
                if st.button("Diagnose visible defect", type="primary", key="run_crack"):
                    prompt = """
Act as a cautious concrete-defect triage assistant. Inspect the attached surface image.
Return valid JSON:
{
 "defect_type": "Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling|Unclear",
 "estimated_crack_width_mm": number|null,
 "confidence": "Low|Medium|High",
 "root_causes": [string],
 "recommended_repairs": [{"method": string, "details": string}],
 "urgency": "Routine monitoring|Schedule engineering review|Urgent engineering assessment|Immediate make-safe action",
 "limitations": [string]
}
Classify only what the image supports. Do not diagnose structural safety from a photo. State width is visual estimate and use null if no scale is present or measurement is unreliable. Distinguish crack pattern from confirmed cause. Discuss epoxy injection only if appropriate after engineer confirms an active structural crack; mention structural re-grouting only where technically suitable, not as a universal fix. For spalling, include removal of unsound concrete, reinforcement corrosion assessment and compatible repair mortar only as engineer-directed options. Recommend an on-site structural engineer for significant, diagonal, widening, through-cracks, exposed/corroded reinforcement or deformation.
"""
                    with st.spinner("Assessing surface defect..."):
                        try:
                            result = call_gemini_json(client, prompt, crack_image) if client else demo_crack()
                            st.session_state["crack_result"] = result
                        except Exception as exc:
                            st.error(f"AI analysis failed: {exc}. Showing demonstration output instead.")
                            st.session_state["crack_result"] = demo_crack()
            result = st.session_state.get("crack_result")
            if result:
                st.markdown("---")
                x, y, z = st.columns(3)
                with x:
                    show_metric("Defect classification", result.get("defect_type", "Unclear"))
                with y:
                    width = result.get("estimated_crack_width_mm")
                    show_metric("Estimated width", f"{width} mm" if width is not None else "Not measurable")
                with z:
                    st.markdown("**Urgency**")
                    status_pill(result.get("urgency", "Review required"))
                st.markdown("### Possible root causes")
                for cause in result.get("root_causes", []):
                    st.markdown(f"- {cause}")
                st.markdown("### Recommended engineering actions")
                for repair in result.get("recommended_repairs", []):
                    with st.container(border=True):
                        st.markdown(f"**{repair.get('method', 'Engineering review')}**")
                        st.write(repair.get("details", ""))
                st.caption(f"Confidence: {result.get('confidence', 'Not stated')}. Photo-based triage only.")
                for note in result.get("limitations", []):
                    st.caption(f"Limitation: {note}")
                download_json(result, f"crack_diagnostics_{datetime.now():%Y%m%d_%H%M%S}.json")
        except Exception as exc:
            st.error(f"Could not read the image: {exc}")

# ----------------------------- Tab 3 ----------------------------------------
with planning_tab:
    st.subheader("Planning & Real Estate Valuation")
    st.write("Indicative planning model using editable assumptions. Replace unit rates with a project BOQ / local schedule of rates.")
    c1, c2 = st.columns(2)
    with c1:
        structure = st.selectbox("Structure type", ["Residential RCC", "Commercial RCC", "Industrial shed", "Institutional RCC"])
        area = st.number_input("Built-up area (sqft)", min_value=100, max_value=2_000_000, value=1800, step=100)
        tier = st.selectbox("Location tier", ["Tier 1", "Tier 2", "Tier 3"])
    with c2:
        completion = st.slider("Construction completion", 0, 100, 35, 1, format="%d%%")
        contingency = st.slider("Contingency allowance", 0.0, 20.0, 5.0, 0.5, format="%.1f%%")
        custom_rate = st.number_input("Optional custom base rate (₹/sqft; 0 = use indicative rate)", min_value=0, max_value=50000, value=0, step=100)

    base_rates = {
        "Residential RCC": {"Tier 1": 2600, "Tier 2": 2200, "Tier 3": 1900},
        "Commercial RCC": {"Tier 1": 3300, "Tier 2": 2800, "Tier 3": 2400},
        "Industrial shed": {"Tier 1": 1800, "Tier 2": 1550, "Tier 3": 1350},
        "Institutional RCC": {"Tier 1": 3100, "Tier 2": 2650, "Tier 3": 2300},
    }
    market_multipliers = {"Tier 1": 1.25, "Tier 2": 1.12, "Tier 3": 1.00}
    material_factors = {
        "Residential RCC": (3.8, 0.40),
        "Commercial RCC": (4.5, 0.45),
        "Industrial shed": (2.5, 0.22),
        "Institutional RCC": (4.2, 0.43),
    }
    rate = custom_rate or base_rates[structure][tier]
    base_budget = area * rate
    total_budget = base_budget * (1 + contingency / 100)
    incurred = total_budget * completion / 100
    asset_value = area * rate * market_multipliers[tier]
    steel_kg = area * material_factors[structure][0]
    cement_bags = area * material_factors[structure][1]
    remaining = max(0, total_budget - incurred)

    st.markdown("---")
    k1, k2, k3 = st.columns(3)
    with k1: show_metric("Estimated total project budget", format_inr(total_budget), f"₹{rate:,.0f}/sqft base rate + {contingency:.1f}% contingency")
    with k2: show_metric("Capital expenditure incurred", format_inr(incurred), f"{completion}% completion assumption")
    with k3: show_metric("Indicative current asset value", format_inr(asset_value), f"{tier} location multiplier; excludes title / market due diligence")
    k4, k5, k6 = st.columns(3)
    with k4: show_metric("Estimated steel requirement", f"{steel_kg:,.0f} kg", f"Approx. {steel_kg/1000:,.2f} tonnes")
    with k5: show_metric("Estimated cement requirement", f"{cement_bags:,.0f} bags", "Assumes 50 kg bags")
    with k6: show_metric("Indicative balance budget", format_inr(remaining), "Total budget less assumed expenditure")
    st.markdown("### Project milestone")
    st.progress(completion / 100, text=f"{completion}% complete · {100-completion}% remaining")
    st.caption("Planning quantities are thumb-rule estimates, not a structural design, quantity take-off or procurement schedule. Actual consumption depends on drawings, spans, foundation, specifications, wastage and site conditions.")

    st.markdown("---")
    st.markdown("### Conceptual 3D architectural visualization")
    st.write("Generate a visual concept prompt and optionally open the Pollinations image endpoint. This is an illustrative concept, not a construction drawing.")
    style = st.selectbox("Rendering style", ["Photorealistic architectural visualization", "Modern minimalist", "Sustainable tropical design", "Industrial contemporary"])
    floors = st.selectbox("Indicative floors", ["G+1", "G+2", "G+3", "G+4 or more"])
    prompt = (f"{style} of a {structure.lower()} building, {floors}, approximately {area:,} square feet built-up area, "
              f"located in an Indian {tier} city, realistic Indian urban context, detailed facade, landscaped entrance, "
              "daylight, professional architectural visualization, wide-angle exterior view, no text, no watermark")
    st.text_area("Generated image prompt", value=prompt, height=110, key="render_prompt")
    image_url = "https://image.pollinations.ai/prompt/" + quote(prompt, safe="")
    st.link_button("Open conceptual rendering (Pollinations AI)", image_url, use_container_width=False)
    st.caption("Pollinations is a third-party service. Availability, moderation and image quality are controlled by that service.")

# ----------------------------- Tab 4 ----------------------------------------
with assistant_tab:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    weather = st.selectbox("Current / forecast weather condition", ["Normal", "High Wind", "Heavy Rain", "Extreme Heat"])
    alerts = {
        "Normal": ("Routine controls", "Continue work under the approved method statement. Maintain housekeeping, hydration, PPE checks and daily toolbox talks."),
        "High Wind": ("Wind exposure alert", "Suspend crane / hoist lifts when wind exceeds the equipment manufacturer's or lift-plan limits. Secure loose materials, formwork and edge protection; restrict work at height and reassess before restart."),
        "Heavy Rain": ("Rain and electrical hazard alert", "Stop work in flooded or lightning-exposed areas. Isolate and inspect temporary electrical systems, protect distribution boards, check excavations / slopes for instability, and provide safe drainage. Reassess access before resuming."),
        "Extreme Heat": ("Heat-stress alert", "Implement work-rest cycles, shaded recovery, drinking water and electrolyte access. Acclimatize workers, monitor for heat illness, adjust strenuous tasks to cooler hours and follow approved concrete placement / curing procedures to limit rapid moisture loss.")
    }
    alert_title, alert_body = alerts[weather]
    alert_class = "pill-green" if weather == "Normal" else "pill-red" if weather in ["High Wind", "Heavy Rain"] else "pill-yellow"
    st.markdown(f'<div class="panel"><span class="pill {alert_class}">{alert_title}</span><p style="margin-top:.8rem">{alert_body}</p></div>', unsafe_allow_html=True)
    st.caption("Apply project-specific weather thresholds, equipment manuals, local forecasts and the site emergency plan. This advisory is not a live weather feed.")

    st.markdown("### Ask the construction engineering assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    user_prompt = st.chat_input("Ask about concrete, site planning, safety, materials or construction methods...")
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Preparing guidance..."):
                try:
                    if client:
                        from google.genai import types
                        history = []
                        for item in st.session_state.chat_history[-12:]:
                            role = "user" if item["role"] == "user" else "model"
                            history.append(types.Content(role=role, parts=[types.Part.from_text(text=item["content"])]))
                        response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=history,
                            config=types.GenerateContentConfig(
                                system_instruction=(
                                    "You are a cautious construction engineering site assistant for Indian projects. "
                                    "Give practical, structured educational guidance. Ask for missing context when needed. "
                                    "Do not certify structural safety, approve designs, replace a licensed engineer, or invent code clauses. "
                                    "Flag high-risk work and recommend a competent person. Consider the selected weather condition: " + weather
                                ),
                                temperature=0.3,
                            ),
                        )
                        answer = response.text or "I could not generate a response. Please try again."
                    else:
                        answer = (
                            "Demo mode response: I can help outline a safe workflow, but live project-specific reasoning "
                            "requires a Gemini API key. For this question, first confirm the approved drawings, method statement, "
                            "site conditions and applicable Indian codes. Escalate structural or high-risk decisions to the "
                            "project's qualified engineer / safety officer."
                        )
                except Exception as exc:
                    answer = f"I couldn't reach the AI service ({exc}). Please retry or check the API key and network connection."
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    if st.session_state.chat_history and st.button("Clear chat", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

st.markdown("---")
st.caption("Multimodal Construction Intelligence Platform · Skill Wallet Capstone Project 1 · No external database required")
