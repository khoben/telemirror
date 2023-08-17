import re
from typing import Optional, Set, Tuple


class UrlMatcher:
    """https://github.com/tkem/uritools/"""

    # RFC 3986 Appendix B
    RE = re.compile(
        r"""
    (?:([A-Za-z][A-Za-z0-9+.-]*):)?  # scheme (RFC 3986 3.1)
    (?://([^/?#]*))?                 # authority
    ([^?#]*)                         # path
    (?:\?([^#]*))?                   # query
    (?:\#(.*))?                      # fragment
    """,
        flags=re.VERBOSE,
    )

    AUTHORITY_GROUP_INDEX = 2
    PATH_GROUP_INDEX = 3

    # RFC 3986 2.2 gen-delims
    COLON, AT = (":", "@")

    DIGITS = "0123456789"

    def __init__(self, blacklist: Set[str] = set(), whitelist: Set[str] = set()):
        """UrlMatcher

        Args:
            blacklist (set, optional):
                URLs that will be matched. Defaults to set().

            whitelist (set, optional):
                URLs that will be NOT matched.
                Will be applied after the `blacklist`. Defaults to set().
        """
        self._blacklist = blacklist
        self._whitelist = whitelist

    def match(self, url: str) -> bool:
        """Checks if URL matched
        Args:
            url (str): URL
        Returns:
            bool: Indicates that URL matched
        """
        if url is None:
            return False

        host, path = self._get_url_components(url)

        if not host:
            return False

        host = host.lower()

        if not path:
            path = ""
            full_url = path
        else:
            # ///path -> /path
            path = f"/{path.lstrip('/').lower()}"
            full_url = f"{host}{path}"

        if (
            self._blacklist
            and host not in self._blacklist
            and full_url not in self._blacklist
        ):
            return False

        if self._whitelist and (host in self._whitelist or full_url in self._whitelist):
            return False

        return True

    def _get_url_components(self, url: str) -> Tuple[Optional[str]]:
        """Get host and path from [url]"""
        # prepend default http scheme
        url = f"http://{url.rpartition('://')[2]}"
        url_parts = self.RE.match(url)
        if url_parts is None:
            return None, None

        authority: Optional[str] = url_parts.group(self.AUTHORITY_GROUP_INDEX)
        if authority is None:
            return None, None

        path: Optional[str] = url_parts.group(self.PATH_GROUP_INDEX)

        _, _, hostinfo = authority.rpartition(self.AT)
        host, _, port = hostinfo.rpartition(self.COLON)

        if port.lstrip(self.DIGITS):
            return hostinfo, path
        else:
            return host, path
