"""Create Discord bots with readable command definitions."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("discord-bot-maker")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .command import Command
from .dbot import Bot, DBot

__all__ = ["Bot", "Command", "DBot", "__version__"]

from .definition import BotDefinition
from .engine import Context, Engine, ExecutionError
from .flow import FlowBot

__all__ += ["BotDefinition", "Context", "Engine", "ExecutionError", "FlowBot"]

from .interactions import CommandContext
from .responses import Button, Embed, Message, Poll, Response, UserError
from .storage import Store

__all__ += ["Button", "CommandContext", "Embed", "Message", "Poll", "Response", "Store", "UserError"]

from .config import BotConfig
from .policies import Checks

__all__ += ["BotConfig", "Checks"]

from .responses import Attachment, Modal, Select, TextInput
__all__ += ["Attachment", "Modal", "Select", "TextInput"]

from .simulator import Simulator, SimulationResult
__all__ += ["Simulator", "SimulationResult"]

from .settings import Settings, ServerSettings
__all__ += ["Settings", "ServerSettings"]

from .operations import configure_logging
__all__ += ["configure_logging"]
