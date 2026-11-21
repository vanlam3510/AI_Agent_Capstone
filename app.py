"""SecureFolio AI Streamlit application."""

import base64
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

from core.llm_agent import answer_visitor_question, draft_project_update
from core.models import PortfolioItem, PortfolioStore, VisibilityTier, filter_items_for_visitor
from core.sanitizer import sanitize_untrusted_text


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "portfolio.json"
BACKGROUND_PATH = BASE_DIR / "assets" / "images" / "portfolio-background.jpeg"
SECURITY_REVIEW_VERSION = 3

CATEGORY_ICONS = {
    "about": ":material/person:",
    "project": ":material/rocket_launch:",
    "skills": ":material/terminal:",
    "experience": ":material/work_history:",
    "education": ":material/school:",
    "case study": ":material/analytics:",
    "contact": ":material/alternate_email:",
}
load_dotenv(BASE_DIR / ".env")


@st.cache_data
def load_store(path: str, modified_at: float) -> PortfolioStore:
    del modified_at
    return PortfolioStore.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_store(store: PortfolioStore) -> None:
    DATA_PATH.write_text(store.model_dump_json(indent=2), encoding="utf-8")
    load_store.clear()


def clear_owner_workflow_state() -> None:
    """Clear results that belong to the previously selected source file."""
    st.session_state["owner_security_review"] = None
    st.session_state["owner_draft"] = None
    st.session_state["owner_draft_error"] = None


def read_upload(uploaded_file) -> str:
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return uploaded_file.getvalue().decode("utf-8", errors="replace")


@st.cache_data(show_spinner=False)
def encode_image(path: str, modified_at: float) -> str:
    """Return a cached Base64 representation of a local background image."""
    del modified_at
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def set_background(image_path: Path) -> None:
    """Apply the local portfolio artwork as a fixed full-page background."""
    encoded = encode_image(str(image_path), image_path.stat().st_mtime)
    st.html(
        f"""
        <style>
        .stApp {{
            background-image:
                linear-gradient(rgba(248, 251, 255, 0.18), rgba(248, 251, 255, 0.18)),
                url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """
    )


st.set_page_config(page_title="SecureFolio AI", page_icon=":material/security:", layout="wide")
st.html(BASE_DIR / "styles.css")
set_background(BACKGROUND_PATH)
st.session_state.setdefault("visitor_messages", [])
st.session_state.setdefault("owner_draft", None)
st.session_state.setdefault("owner_draft_error", None)
st.session_state.setdefault("owner_security_review", None)
st.session_state.setdefault("access_mode", "Public")
existing_security_review = st.session_state.get("owner_security_review")
if existing_security_review and existing_security_review.get("version") != SECURITY_REVIEW_VERSION:
    st.session_state["owner_security_review"] = None
    st.session_state["owner_draft"] = None
    st.session_state["owner_draft_error"] = None
store = load_store(str(DATA_PATH), DATA_PATH.stat().st_mtime)

with st.sidebar:
    with st.container(key="sidebar_molecules"):
        st.html(
            """
            <svg class="sidebar-molecule-field" viewBox="0 0 320 900"
                 preserveAspectRatio="xMidYMid slice" aria-hidden="true">
              <g class="molecule-layer molecule-layer-a">
                <g class="molecule-bonds">
                  <line x1="18" y1="90" x2="104" y2="42" />
                  <line x1="104" y1="42" x2="178" y2="118" />
                  <line x1="178" y1="118" x2="286" y2="72" />
                  <line x1="36" y1="248" x2="122" y2="190" />
                  <line x1="122" y1="190" x2="222" y2="260" />
                  <line x1="222" y1="260" x2="306" y2="205" />
                  <line x1="122" y1="190" x2="178" y2="118" />
                </g>
                <g class="molecule-nodes">
                  <circle cx="18" cy="90" r="5" /><circle cx="104" cy="42" r="8" />
                  <circle cx="178" cy="118" r="6" /><circle cx="286" cy="72" r="4" />
                  <circle cx="36" cy="248" r="6" /><circle cx="122" cy="190" r="5" />
                  <circle cx="222" cy="260" r="8" /><circle cx="306" cy="205" r="5" />
                </g>
              </g>
              <g class="molecule-layer molecule-layer-b">
                <g class="molecule-bonds">
                  <line x1="4" y1="430" x2="82" y2="356" />
                  <line x1="82" y1="356" x2="170" y2="420" />
                  <line x1="170" y1="420" x2="294" y2="370" />
                  <line x1="28" y1="610" x2="116" y2="540" />
                  <line x1="116" y1="540" x2="210" y2="624" />
                  <line x1="210" y1="624" x2="314" y2="550" />
                  <line x1="170" y1="420" x2="116" y2="540" />
                  <line x1="54" y1="790" x2="150" y2="724" />
                  <line x1="150" y1="724" x2="274" y2="800" />
                  <line x1="210" y1="624" x2="150" y2="724" />
                </g>
                <g class="molecule-nodes molecule-nodes-delayed">
                  <circle cx="4" cy="430" r="5" /><circle cx="82" cy="356" r="8" />
                  <circle cx="170" cy="420" r="5" /><circle cx="294" cy="370" r="7" />
                  <circle cx="28" cy="610" r="4" /><circle cx="116" cy="540" r="7" />
                  <circle cx="210" cy="624" r="6" /><circle cx="314" cy="550" r="4" />
                  <circle cx="54" cy="790" r="7" /><circle cx="150" cy="724" r="5" />
                  <circle cx="274" cy="800" r="8" />
                </g>
              </g>
            </svg>
            """
        )
    st.title(":material/shield_lock: SecureFolio AI")
    st.caption("A permission-aware portfolio and AI assistant")
    st.subheader("Preview access")
    st.caption("Choose a visitor tier to preview its authorized content.")
    tier_options = (
        ("Public", ":material/public:", "tier_public"),
        ("Signed in", ":material/account_circle:", "tier_signed_in"),
        ("Selected visitor", ":material/verified_user:", "tier_selected"),
        ("Owner", ":material/admin_panel_settings:", "tier_owner"),
    )
    for tier_label, tier_icon, tier_key in tier_options:
        if st.button(
            tier_label,
            icon=tier_icon,
            key=tier_key,
            type="primary" if st.session_state["access_mode"] == tier_label else "secondary",
            width="stretch",
        ):
            st.session_state["access_mode"] = tier_label
            st.rerun()
    access_mode = st.session_state["access_mode"]
    active_tier_key = next(key for label, _icon, key in tier_options if label == access_mode)
    st.html(
        f"""
        <style>
        .st-key-{active_tier_key} button {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 58%, #3B82F6 100%) !important;
            border-color: #1E40AF !important;
            box-shadow: 0 9px 26px rgba(37, 99, 235, .38), inset 0 1px 0 rgba(255, 255, 255, .28) !important;
            transform: translateY(-1px);
        }}
        .st-key-{active_tier_key} button * {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }}
        </style>
        """
    )
    st.divider()
    default_emails = {
        "Public": "",
        "Signed in": "visitor@example.com",
        "Selected visitor": "selected@example.com",
        "Owner": "owner@example.com",
    }
    visitor_email = st.text_input(
        "Visitor email",
        value=default_emails[access_mode],
        disabled=access_mode == "Public",
        key=f"visitor_email_{access_mode}",
        icon=":material/mail:",
    )
    is_owner = access_mode == "Owner"
    effective_email = None if access_mode == "Public" else visitor_email
    st.info(
        "This preview demonstrates authorization logic; it is not production authentication.",
        icon=":material/info:",
    )

allowed_items = filter_items_for_visitor(store, effective_email, is_owner)
portfolio_tab, chat_tab, owner_tab = st.tabs(
    ["Portfolio", "Visitor Q&A", "Owner Agent Studio"],
    key="main_navigation_tabs",
)

with portfolio_tab:
    st.title(store.owner_name)
    st.subheader("AI developer · Security-minded builder")
    st.write(
        "A living portfolio where every record is filtered by authorization before it reaches "
        "the interface or the AI assistant."
    )
    st.caption(f"Showing {len(allowed_items)} authorized item(s) for the current preview identity.")
    for item in allowed_items:
        with st.container(border=True, key=f"portfolio_card_{item.id}"):
            st.caption(f"{item.category.upper()} · {item.visibility.value.replace('_', ' ').title()}")
            st.subheader(
                item.title,
                icon=CATEGORY_ICONS.get(item.category.lower(), ":material/article:"),
            )
            st.write(item.content)
            links = []
            if item.repo_url:
                links.append(f"[Repository]({item.repo_url})")
            if item.demo_url:
                links.append(f"[Live demo]({item.demo_url})")
            if links:
                st.markdown(" · ".join(links))

with chat_tab:
    st.header("Ask about this portfolio")
    st.write("Answers are grounded only in the portfolio records authorized for your identity.")
    for message in st.session_state["visitor_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask about Van's authorized portfolio", submit_mode="disable")
    if not st.session_state["visitor_messages"]:
        starter_questions = {
            ":blue[:material/security:] AI architecture & guardrails": (
                "What AI architectures and guardrails has Van built in production?"
            ),
            ":violet[:material/account_tree:] Enterprise system design": (
                "Tell me about Van's system design experience at Intel and GlobalFoundries."
            ),
            ":green[:material/contact_mail:] Contact & availability": (
                "What is Van's contact info or availability?"
            ),
        }
        suggestion_slot = st.empty()
        selected_question = suggestion_slot.pills(
            "Suggested questions",
            tuple(starter_questions),
            label_visibility="collapsed",
            key="visitor_question_suggestions",
        )
        if selected_question:
            question = starter_questions[selected_question]
        if question:
            suggestion_slot.empty()
    if question:
        st.session_state["visitor_messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        cleaned_question, flagged, alerts = sanitize_untrusted_text(question, max_chars=2_000)
        if flagged:
            answer = "The question was blocked by the pre-LLM security gate. " + " ".join(alerts)
        else:
            try:
                with st.spinner("Reviewing authorized portfolio data…"):
                    answer = answer_visitor_question(cleaned_question, allowed_items)
            except Exception as exc:
                answer = f"The AI request could not be completed: {exc}"
        st.session_state["visitor_messages"].append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
    st.divider()
    st.link_button(
        "Open Beagle messaging documentation",
        "https://beagle.chat/en/docs/",
        icon=":material/open_in_new:",
    )

with owner_tab:
    st.header("Owner Agent Studio")
    if not is_owner:
        st.warning("Switch the demo access tier to Owner to use the drafting and publishing workflow.")
    else:
        st.write("Upload notes → sanitize → draft → preview → approve and publish")
        uploaded_file = st.file_uploader(
            "Project notes or README",
            type=("txt", "md", "pdf"),
            key="owner_source_file",
            on_change=clear_owner_workflow_state,
        )
        pasted_notes = st.text_area("Or paste project notes", height=180)
        if st.button("Sanitize and draft", type="primary", icon=":material/auto_awesome:"):
            raw_notes = read_upload(uploaded_file) if uploaded_file else pasted_notes
            cleaned_notes, flagged, alerts = sanitize_untrusted_text(raw_notes)
            if not cleaned_notes:
                st.session_state["owner_security_review"] = None
                st.session_state["owner_draft"] = None
                st.session_state["owner_draft_error"] = None
                st.error("Add project notes before creating a draft.")
            elif flagged:
                st.session_state["owner_security_review"] = {
                    "version": SECURITY_REVIEW_VERSION,
                    "status": "blocked",
                    "alerts": alerts,
                    "cleaned_source": None,
                }
                st.session_state["owner_draft"] = None
                st.session_state["owner_draft_error"] = None
            else:
                st.session_state["owner_security_review"] = {
                    "version": SECURITY_REVIEW_VERSION,
                    "status": "passed",
                    "alerts": alerts,
                    "cleaned_source": cleaned_notes,
                }
                st.session_state["owner_draft_error"] = None
                try:
                    with st.spinner("Drafting an update for owner review…"):
                        st.session_state["owner_draft"] = draft_project_update(cleaned_notes)
                except Exception as exc:
                    st.session_state["owner_draft"] = None
                    st.session_state["owner_draft_error"] = str(exc)

        security_review = st.session_state.get("owner_security_review")
        if security_review:
            if security_review["status"] == "blocked":
                st.error(
                    "Security review failed. The source was blocked before reaching the LLM."
                )
                for alert in security_review["alerts"]:
                    st.warning(alert)
            elif st.session_state.get("owner_draft_error"):
                st.warning(
                    "Security scan passed, but draft generation failed. "
                    "No draft was created."
                )
                st.error(
                    "The AI request could not be completed: "
                    f"{st.session_state['owner_draft_error']}"
                )
                with st.expander("Review sanitized source"):
                    st.code(security_review["cleaned_source"], language=None)
            else:
                st.success(
                    "Security scan passed and the draft was created successfully."
                )
                for alert in security_review["alerts"]:
                    st.info(alert)
                with st.expander("Review sanitized source"):
                    st.code(security_review["cleaned_source"], language=None)

        if st.session_state.get("owner_draft"):
            edited_draft = st.text_area(
                "Preview and edit",
                value=st.session_state["owner_draft"],
                height=240,
            )
            title = st.text_input("Portfolio title", value="New project update")
            visibility = st.selectbox(
                "Visibility",
                tuple(VisibilityTier),
                format_func=lambda tier: tier.value.replace("_", " ").title(),
            )
            if st.button("Approve and publish", icon=":material/publish:"):
                store.items.append(
                    PortfolioItem(
                        id=f"project-{uuid4().hex[:10]}",
                        category="project",
                        title=title,
                        content=edited_draft,
                        visibility=visibility,
                    )
                )
                save_store(store)
                st.session_state.pop("owner_draft", None)
                st.session_state.pop("owner_draft_error", None)
                st.session_state.pop("owner_security_review", None)
                st.success("Approved update published to the local portfolio store.")
                st.rerun()

