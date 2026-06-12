import streamlit as st


def render_metric_card(title: str, value: str | int, help_text: str | None = None) -> None:
    st.metric(
        label=title,
        value=value,
        help=help_text,
    )


def render_section_header(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def render_status_badge(status: str) -> str:
    status_map = {
        "draft": "🟡 draft",
        "ready": "🟢 ready",
        "running": "🔵 running",
        "paused": "🟠 paused",
        "completed": "✅ completed",
        "cancelled": "⛔ cancelled",
        "pending": "🟡 pending",
        "dry_run": "🔵 dry_run",
        "sent": "✅ sent",
        "failed": "❌ failed",
        "skipped": "⚪ skipped",
        "blocked": "⛔ blocked",
        "unsubscribed": "🚫 unsubscribed",
        "bounced": "📭 bounced",
        "consented": "✅ consented",
        "unknown": "⚪ unknown",
    }

    return status_map.get(status, status)