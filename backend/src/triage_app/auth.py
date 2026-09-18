"""Chapter 22: the same real bearer-token verification chapter 6 already
built and proved, against a real Auth0 tenant, real JWKS endpoint,
real RS256 signature check. `triage-app` doesn't need a second tenant
or a rebuilt mechanism, only its own API resource in the same tenant
(audience `https://triage-app.dev/api`), so an existing reorder-app
token can never be replayed against this API, and vice versa.

There is no session, no cookie, no password stored anywhere in this
repo. The identity of every caller is exactly what its bearer token
proves, nothing this API manages itself.
"""

import os

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


def _auth0_domain() -> str:
    return os.environ.get("AUTH0_DOMAIN", "")


def _auth0_audience() -> str:
    return os.environ.get("AUTH0_AUDIENCE", "")


_bearer_scheme = HTTPBearer()
_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"https://{_auth0_domain()}/.well-known/jwks.json")
    return _jwks_client


class Principal(BaseModel):
    subject: str


class UnauthorizedError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Principal:
    token = credentials.credentials
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_auth0_audience(),
            issuer=f"https://{_auth0_domain()}/",
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(detail=str(exc)) from exc
    return Principal(subject=payload["sub"])


def register_auth_exception_handlers(app) -> None:
    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(request: Request, exc: UnauthorizedError) -> JSONResponse:
        from triage_app.api import ProblemDetail

        problem = ProblemDetail(
            type="https://triage-app.dev/problems/unauthorized",
            title="Unauthorized",
            status=401,
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=401,
            content=problem.model_dump(),
            media_type="application/problem+json",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        from triage_app.api import ProblemDetail

        problem = ProblemDetail(
            type="https://triage-app.dev/problems/unauthorized",
            title="Unauthorized",
            status=exc.status_code,
            detail=str(exc.detail),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=problem.model_dump(),
            media_type="application/problem+json",
        )
