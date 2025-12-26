from config import registry


def get_system_status() -> str:
    """
    Get the current health and status of external services (Qdrant, API keys).
    Returns a formatted description of the system status.
    """
    try:
        qdrant_ok = registry.check_qdrant()
        keys_ok = registry.check_api_keys()

        q_status = "READY" if qdrant_ok else "UNAVAILABLE (Keyword search fallback)"
        status_lines = [
            "### System Status",
            f"- **Qdrant Vector DB**: {q_status}",
            f"- **API Keys**: {'CONFIGURED' if keys_ok else 'MISSING'}",
        ]

        # Add more details if possible
        if qdrant_ok:
            status_lines.append("- **Search Mode**: Semantic (Hybrid)")
        else:
            status_lines.append("- **Search Mode**: Keyword only")

        return "\n".join(status_lines)
    except Exception as e:
        return f"Error retrieving system status: {str(e)}"
