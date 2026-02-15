from .channels import router as channels_router
from .contents import router as contents_router
from .dashboard import router as dashboard_router
from .jobs import router as jobs_router
from .logs import router as logs_router
from .source_channel_bindings import router as source_channel_bindings_router
from .sources import router as sources_router
from .system import router as system_router

__all__ = [
    "sources_router",
    "channels_router",
    "contents_router",
    "logs_router",
    "source_channel_bindings_router",
    "jobs_router",
    "dashboard_router",
    "system_router",
]
