""" Stats Request models """
from pydantic import BaseModel, Field

class StatsResetRequest(BaseModel):
    """
    Request model for resetting stats.
    """
    confirm: bool = Field(
        default=True,
        description="Must be true to confirm resetting stats",
        example=True
    )

    class Config:
        json_schema_extra = {
            "example": {
                "confirm": True
            }
        }
