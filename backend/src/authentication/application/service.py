from datetime import datetime, timedelta, timezone
from typing import Optional

from shared.config.settings import Settings, get_settings
from shared.errors.base import ApplicationError, AuthenticationError, NotAuthenticatedError

from authentication.application.dto import (
    BrokerSessionHealthResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SessionStatusResponse,
    StreamingTokensResponse,
)
from authentication.domain.models import UserSession
from integrations.ig.models.account import AccountSnapshot
from integrations.ig.rest.accounts_client import IgAccountsClient
from integrations.ig.rest.session_client import IgLoginCommand, IgSessionClient


class SessionManager:
    def __init__(self) -> None:
        self._current_session: Optional[UserSession] = None
        self._stream_cst: Optional[str] = None
        self._stream_xst: Optional[str] = None
        self._stream_tokens_expire_at: Optional[datetime] = None

    def set_session(self, session: UserSession) -> None:
        self._current_session = session
        # Clear streaming tokens on new session
        self._stream_cst = None
        self._stream_xst = None
        self._stream_tokens_expire_at = None

    def get_session(self) -> Optional[UserSession]:
        return self._current_session

    def clear_session(self) -> None:
        self._current_session = None
        self._stream_cst = None
        self._stream_xst = None
        self._stream_tokens_expire_at = None

    def is_authenticated(self) -> bool:
        if self._current_session is None:
            return False
        return datetime.now(timezone.utc) < self._current_session.expires_at

    def require_session(self) -> UserSession:
        if not self.is_authenticated() or self._current_session is None:
            raise NotAuthenticatedError()
        return self._current_session

    def cache_stream_tokens(self, cst: str, xst: str) -> None:
        self._stream_cst = cst
        self._stream_xst = xst
        # Session tokens usually valid for 12+ hours, let's cache for 8 hours
        self._stream_tokens_expire_at = datetime.now(timezone.utc) + timedelta(hours=8)

    def get_cached_stream_tokens(self) -> tuple[Optional[str], Optional[str]]:
        if self._stream_tokens_expire_at and datetime.now(timezone.utc) < self._stream_tokens_expire_at:
            return self._stream_cst, self._stream_xst
        return None, None


session_manager = SessionManager()


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._client = IgSessionClient(settings)
        self._accounts_client = IgAccountsClient(settings)
        self._settings = settings

    async def login(self, request: LoginRequest) -> LoginResponse:
        self._validate_requested_account_type(request.account_type)
        ig_response = await self._client.login(
            IgLoginCommand(identifier=request.identifier, password=request.password)
        )

        oauth = _require_mapping(ig_response, "oauthToken")

        account_id = _extract_account_id(ig_response)

        expires_in = _coerce_int(oauth.get("expires_in"), default=3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        session = UserSession(
            account_id=account_id,
            client_id=str(ig_response.get("clientId", "")),
            lightstreamer_endpoint=str(ig_response.get("lightstreamerEndpoint", "")),
            access_token=str(oauth.get("access_token", "")),
            refresh_token=str(oauth.get("refresh_token", "")),
            expires_at=expires_at,
            is_demo=request.account_type == "demo",
        )
        session_manager.set_session(session)

        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=expires_in,
            account_id=session.account_id,
            account_type="demo" if session.is_demo else "live",
            lightstreamer_endpoint=session.lightstreamer_endpoint,
        )

    async def logout(self) -> None:
        session_manager.clear_session()

    async def refresh(self, request: RefreshRequest) -> RefreshResponse:
        session = session_manager.require_session()
        ig_response = await self._client.refresh_token(request.refresh_token)

        oauth = ig_response
        expires_in = _coerce_int(oauth.get("expires_in"), default=3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        session.access_token = str(oauth.get("access_token", ""))
        session.refresh_token = str(oauth.get("refresh_token", ""))
        session.expires_at = expires_at

        return RefreshResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=expires_in,
        )

    async def get_session_tokens(self) -> StreamingTokensResponse:
        session = session_manager.require_session()
        
        cst, xst = session_manager.get_cached_stream_tokens()
        if cst and xst:
            return StreamingTokensResponse(
                cst=cst,
                x_security_token=xst,
                account_id=session.account_id,
            )

        tokens = await self._client.fetch_session_tokens(session.access_token)
        session_manager.cache_stream_tokens(tokens["cst"], tokens["x_security_token"])

        return StreamingTokensResponse(
            cst=tokens["cst"],
            x_security_token=tokens["x_security_token"],
            account_id=session.account_id,
        )

    def get_status(self) -> SessionStatusResponse:
        if not session_manager.is_authenticated():
            return SessionStatusResponse(authenticated=False)

        session = session_manager.require_session()

        return SessionStatusResponse(
            authenticated=True,
            account_id=session.account_id,
            account_type="demo" if session.is_demo else "live",
            lightstreamer_endpoint=session.lightstreamer_endpoint,
        )

    def get_access_token(self) -> str:
        session = session_manager.require_session()
        if not session.access_token:
            raise NotAuthenticatedError("No access token provided")
        return session.access_token

    async def is_session_alive(self) -> BrokerSessionHealthResponse:
        session = session_manager.get_session()
        if session is None or not session_manager.is_authenticated():
            return BrokerSessionHealthResponse(alive=False, detail="No active session")

        try:
            tokens = await self.get_session_tokens()
            if not tokens.cst or not tokens.x_security_token:
                return BrokerSessionHealthResponse(alive=False, detail="Missing IG session tokens", account_id=session.account_id)
            return BrokerSessionHealthResponse(alive=True, detail="IG session is healthy", account_id=session.account_id)
        except ApplicationError as exc:
            return BrokerSessionHealthResponse(alive=False, detail=exc.detail, account_id=session.account_id)

    async def ensure_session_valid(self) -> None:
        health = await self.is_session_alive()
        if not health.alive:
            raise NotAuthenticatedError(health.detail)

    async def get_account_balance(self) -> AccountSnapshot:
        session = session_manager.require_session()
        tokens = await self.get_session_tokens()
        payload = await self._accounts_client.fetch_accounts(
            {
                "Authorization": f"Bearer {session.access_token}",
                "CST": tokens.cst,
                "X-SECURITY-TOKEN": tokens.x_security_token,
                "IG-ACCOUNT-ID": tokens.account_id,
            }
        )
        raw_accounts = payload.get("accounts")
        if not isinstance(raw_accounts, list) or not raw_accounts:
            raise ApplicationError("IG account snapshot is unavailable", status_code=502)

        for item in raw_accounts:
            if not isinstance(item, dict):
                continue
            if str(item.get("accountId", "")) != session.account_id:
                continue
            balance = _as_float(item.get("balance", {}), "balance")
            available_cash = _as_optional_float(item.get("balance", {}), "available")
            return AccountSnapshot(
                account_id=session.account_id,
                balance=balance,
                available_cash=available_cash,
                account_name=_as_str(item.get("accountName")),
                account_type=_as_str(item.get("accountType")),
            )

        first = raw_accounts[0]
        if not isinstance(first, dict):
            raise ApplicationError("IG account snapshot is unavailable", status_code=502)
        return AccountSnapshot(
            account_id=_as_str(first.get("accountId")) or session.account_id,
            balance=_as_float(first.get("balance", {}), "balance"),
            available_cash=_as_optional_float(first.get("balance", {}), "available"),
            account_name=_as_str(first.get("accountName")),
            account_type=_as_str(first.get("accountType")),
        )

    def _validate_requested_account_type(self, account_type: str) -> None:
        expected = self._settings.ig_environment
        if account_type != expected:
            raise ApplicationError(
                f"This backend is configured for IG {expected} accounts only",
                status_code=409,
            )
        if expected == "live" and not self._settings.allow_live_trading:
            raise ApplicationError(
                "Live IG trading is blocked by configuration",
                status_code=409,
            )


def get_auth_service() -> AuthService:
    return AuthService(get_settings())


def _require_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    raise AuthenticationError(f"IG response missing '{key}'")


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise AuthenticationError("IG returned an invalid token expiry") from exc
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("IG returned an invalid token expiry") from exc


def _extract_account_id(ig_response: dict[str, object]) -> str:
    if "accountInfo" in ig_response and isinstance(ig_response.get("accountInfo"), dict):
        account_info = ig_response["accountInfo"]
        if isinstance(account_info, dict) and "accountId" in account_info:
            return str(account_info["accountId"])
    
    if "accountId" in ig_response:
        return str(ig_response["accountId"])
    
    if "accounts" in ig_response and isinstance(ig_response.get("accounts"), list):
        accounts = ig_response["accounts"]
        if len(accounts) > 0 and isinstance(accounts[0], dict):
            first_account = accounts[0]
            if "accountId" in first_account:
                return str(first_account["accountId"])
    
    raise AuthenticationError("IG response missing account information")


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: object, key: str) -> float:
    if isinstance(value, dict):
        raw = value.get(key)
    else:
        raw = value
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ApplicationError("IG account balance is invalid", status_code=502)


def _as_optional_float(value: object, key: str) -> float | None:
    if isinstance(value, dict):
        raw = value.get(key)
    else:
        raw = value
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
