from pydantic import BaseModel, field_validator


class SessionData(BaseModel):
    username: str
    role: str
    mail: str
    display_name: str

    @field_validator('role')
    @classmethod
    def trim_role(cls, value: str) -> str:
        if '_' in value:
            return value.split('_')[-1]
        return value
