"""Duquesne Light Company (DLC)."""

from html.parser import HTMLParser
import re
from typing import Optional

import aiohttp

from ..const import USER_AGENT
from ..exceptions import InvalidAuth
from .base import UtilityBase


class DLCUsageParser(HTMLParser):
    """HTML parser to extract OPower bearer token from DLC Usage page."""

    _regexp = re.compile(r'"OPowerToken":\s*"(?P<token>[^"]+)"')

    def __init__(self) -> None:
        """Initialize."""
        super().__init__()
        self.opower_access_token: Optional[str] = None
        self._in_inline_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        """Recognizes inline scripts."""
        if (
            tag == "script"
            and next(filter(lambda attr: attr[0] == "src", attrs), None) is None
        ):
            self._in_inline_script = True

    def handle_data(self, data: str) -> None:
        """Try to extract the access token from the inline script."""
        if self._in_inline_script:
            result = self._regexp.search(data)
            if result and result.group("token"):
                self.opower_access_token = result.group("token")

    def handle_endtag(self, tag: str) -> None:
        """Recognizes the end of inline scripts."""
        if tag == "script":
            self._in_inline_script = False


class DLC(UtilityBase):
    """Duquesne Light Company (DLC)."""

    @staticmethod
    def name() -> str:
        """Distinct recognizable name of the utility."""
        return "Duquesne Light Company (DLC)"

    @staticmethod
    def subdomain() -> str:
        """Return the opower.com subdomain for this utility."""
        return "duq"

    @staticmethod
    def timezone() -> str:
        """Return the timezone."""
        return "America/New_York"

    @staticmethod
    async def async_login(
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        optional_mfa_secret: Optional[str]
    ) -> str:
        """Login to the utility website."""
        async with session.post(
            "https://www.duquesnelight.com/login/login",
            json={
                "Username": username,
                "Password": password
            },
            headers={"User-Agent": USER_AGENT},
            raise_for_status=True,
        ) as resp:
            result = await resp.json()
            if "errorMsg" in result:
                raise InvalidAuth(result["errorMsg"])
        
        usage_parser = DLCUsageParser()

        async with session.get(
            "https://www.duquesnelight.com/energy-money-savings/my-electric-usage",
            headers={"User-Agent": USER_AGENT},
            raise_for_status=True,
        ) as resp:
            usage_parser.feed(await resp.text())

            assert (
                usage_parser.opower_access_token
            ), "Failed to parse OPower bearer token"

        return usage_parser.opower_access_token
