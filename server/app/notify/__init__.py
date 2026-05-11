"""LISTEN/NOTIFY plumbing for real-time vault events (D-07/D-08)."""

from app.notify.listener import IndexEventListener
from app.notify.publisher import publish_index_event

__all__ = ["IndexEventListener", "publish_index_event"]
