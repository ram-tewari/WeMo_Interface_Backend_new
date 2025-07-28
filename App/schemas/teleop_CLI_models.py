#schemas/teleop_CLI_models.py
from pydantic import BaseModel, Field

#defines data schemas expected from HTTP payloads

class BotId(BaseModel):
    bot_id: int = Field(..., gt=0, description="Bot ID to control") # ... as the field is required, and must be greater than 0

class SpeedChangeReq(BaseModel):
    bot_id: int = Field(..., gt=0, description="Robot ID to control")
    action: str = Field(
        ...,
        pattern="^(increase|decrease)$",
        description="Speed action: 'increase' maps to '+', 'decrease' to '-'"
    )

class MoveReq(BotId):
    direction: str = Field(..., pattern = "^(up|down|left|right)$", description="MoveDirection") #Required field that must be up, down, left or right

class RotateReq(BotId):
    direction: str = Field(..., pattern = "^(left|right)$", description="Rotate Direction") #Required field that must be left or right