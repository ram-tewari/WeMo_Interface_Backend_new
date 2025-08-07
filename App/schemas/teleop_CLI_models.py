#schemas/teleop_CLI_models.py

"""Data schemas for teleop CLI models using Pydantic.

Defines expected structures for HTTP payloads related to bot control.
"""

from pydantic import BaseModel, Field


class BotId(BaseModel):
    bot_id: int = Field(..., gt=0, description="Bot ID to control")


class SpeedChangeReq(BotId):
    action: str = Field(
        ...,
        pattern="^(increase|decrease)$",
        description="Speed action: 'increase' maps to '+', 'decrease' to '-'"
    )


class MoveReq(BotId):
    direction: str = Field(
        ...,
        pattern="^(up|down|left|right)$",
        description="Move direction"
    )


class RotateReq(BotId):
    direction: str = Field(
        ...,
        pattern="^(left|right)$",
        description="Rotate direction"
    )
