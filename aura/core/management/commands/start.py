from .command import Action
from .command import BaseActionCommand


class Command(BaseActionCommand):
    help = "Start services"
    action = Action.start.value
