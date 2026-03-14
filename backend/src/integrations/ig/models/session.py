from pydantic import BaseModel


class IgOAuthToken(BaseModel):
    access_token: str
    refresh_token: str
    scope: str
    token_type: str
    expires_in: str


class IgSession(BaseModel):
    account_id: str
    client_id: str
    lightstreamer_endpoint: str
    oauth_token: IgOAuthToken | None = None
