from typing import Dict, Any


def get_behavior_journal_status() -> Dict[str, Any]:
    """
    Behavior journal is explicitly disabled by design.
    Bot must NEVER write or modify behavior/character journals.
    """
    return {
        "touched": False,
        "action": "SKIP",
        "message": "🚫 Jurnal Perilaku tidak disentuh."
    }
