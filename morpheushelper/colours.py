from PyDrocsid.material_colours import MaterialColours, NestedInt
from discord import Colour


class Colours(MaterialColours):
    # General
    default = MaterialColours.teal
    error = MaterialColours.red
    warning = MaterialColours.yellow[700]

    # Cogs
    AllowedInvites = MaterialColours.lightgreen["a700"]
    AutoMod = MaterialColours.blue["a700"]
    CleverBot = 0x8EBBF6  # clever bot color
    CodeBlocks = MaterialColours.grey[900]
    DiscordPy = Colour.blurple()  # discord colour
    Logging = NestedInt(
        MaterialColours.blue["a700"], {"edit": MaterialColours.yellow[800], "delete": MaterialColours.red[900]}
    )
    MediaOnly = MaterialColours.yellow["a200"]
    MetaQuestions = MaterialColours.purple["a400"]
    MiniGamesCog = MaterialColours.green
    ModTools = MaterialColours.blue["a700"]
    News = MaterialColours.orange
    Permissions = MaterialColours.blue["a700"]
    Polls = MaterialColours.orange[800]
    ReactionPin = MaterialColours.blue["a700"]
    ReactionRole = MaterialColours.blue["a700"]
    Reddit = 0xFF4500  # Reddit color
    RuleCommands = MaterialColours.blue["a700"]
    BeTheProfessional = MaterialColours.yellow["a200"]
    ServerInformation = MaterialColours.indigo
    Verification = MaterialColours.green["a100"]
    Voice = NestedInt(
        MaterialColours.blue["a700"],
        {"public": MaterialColours.lightgreen["a700"], "private": MaterialColours.blue["a700"]},
    )

    # Commands
    changelog = NestedInt(
        MaterialColours.teal,
        {
            "report": MaterialColours.yellow[800],
            "warn": MaterialColours.yellow["a200"],
            "mute": MaterialColours.yellow[600],
            "unmute": MaterialColours.green["a700"],
            "kick": MaterialColours.orange[700],
            "ban": MaterialColours.red[500],
            "unban": MaterialColours.green["a700"],
        },
    )
    github = MaterialColours.teal[800]
    info = MaterialColours.indigo
    ping = MaterialColours.green["a700"]
    prefix = MaterialColours.indigo
    stats = MaterialColours.green
    userlog = MaterialColours.green["a400"]
    version = MaterialColours.indigo
