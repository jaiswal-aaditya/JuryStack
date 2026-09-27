from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.auth.roles import Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        normalized = email.strip().casefold()
        if normalized.count("@") != 1 or normalized.startswith("@"):
            raise ValueError("Enter a valid email address.")
        return normalized


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: Role
