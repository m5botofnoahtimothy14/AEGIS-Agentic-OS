                           
from .speech import SpeechManager
from .voice_command_router import VoiceCommandRouter
from .notification_router import NotificationRouter
from .sentiment_engine import SentimentEngine
from .autoreply_engine import AutoReplyEngine
from .whatsapp_navigator import WhatsAppNavigator
from .insta_navigator import InstaNavigator
from .email_navigator import EmailNavigator
from .google_calendar import CalendarManager
try:
    from .call_agent import CallAgent
except ImportError:
    # Phone support is optional; it must not prevent the local voice stack from
    # starting when LiveKit is not installed.
    CallAgent = None

__all__ = [
    "SpeechManager",
    "VoiceCommandRouter",
    "NotificationRouter",
    "SentimentEngine",
    "AutoReplyEngine",
    "WhatsAppNavigator",
    "InstaNavigator",
    "EmailNavigator",
    "CalendarManager",
    "CallAgent",
]
