from typing import List
from .urlextract_patched import URLExtractPatched


class URLExtrator:
    def __init__(self, blacklist: set = set(), whitelist: set = set()) -> 'URLExtrator':
        """URLExtrator

        Args:
            blacklist (set, optional): 
                URLs among which will be found. Defaults to set().

            whitelist (set, optional): 
                URLs that will be ignored. 
                Will be applied after the `blacklist`. Defaults to set().
        """
        self._url_extract = URLExtractPatched()
        self._url_extract.ignore_list = whitelist
        self._url_extract.permit_list = blacklist

    def find(self, text: str) -> List[str]:
        """Finds URLs within text

        Args:
            text (str): Source text

        Returns:
            List[Result]: Found URLs
        """
        return self._url_extract.find_urls(text, only_unique=True)

    def has_urls(self, text: str) -> bool:
        """Checks if text has URLs

        Args:
            text (str): Source text

        Returns:
            bool: Indicates that text has URLs
        """
        return self._url_extract.has_urls(text)
