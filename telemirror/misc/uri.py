import re
from typing import Optional, Set


class UriGuard:
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

    # RFC 3986 2.2 gen-delims
    COLON, AT = (
        ":",
        "@"
    )

    DIGITS = "0123456789"

    def __init__(self, blacklist: Set[str] = set(), whitelist: Set[str] = set()):
        """UriGuard

        Args:
            blacklist (set, optional): 
                URLs that will be filtered. Defaults to set().

            whitelist (set, optional): 
                URLs that will be ignored. 
                Will be applied after the `blacklist`. Defaults to set().
        """
        self._blacklist = blacklist
        self._whitelist = whitelist

    def is_should_filtered(self, url: str) -> bool:
        """Checks if URL should be filtered
        Args:
            url (str): URL
        Returns:
            bool: Indicates that URL should be filtered
        """
        host = self._get_host(url)

        if not host:
            return False

        if self._blacklist and host not in self._blacklist:
            return False

        if host in self._whitelist:
            return False

        return True

    def _get_host(self, url: str) -> Optional[str]:
        scheme_pos = url.find("://")
        if scheme_pos == -1:
            # prepend temp http scheme
            url = "http://" + url
        authority: Optional[str] = self.RE.match(
            url).group(self.AUTHORITY_GROUP_INDEX)
        if authority is None:
            return None
        _, _, hostinfo = authority.rpartition(self.AT)
        host, _, port = hostinfo.rpartition(self.COLON)
        if port.lstrip(self.DIGITS):
            return hostinfo
        else:
            return host
