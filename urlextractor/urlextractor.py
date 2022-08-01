import re
import uritools
from typing import NamedTuple, List

class Span(NamedTuple):
    start: int
    end: int

class Result(NamedTuple):
    span: Span
    text: str

class URLExtrator:
    _URL_RE = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")

    def __init__(self, blacklist: set = set(), whitelist: set = set()) -> 'URLExtrator':
        """URLExtrator

        Args:
            blacklist (set, optional): URLs among which will be found. Defaults to set().
            whitelist (set, optional): URLs that will be ignored. Defaults to set().
        """
        self._black_list = blacklist
        self._white_list = whitelist

    def find(self, text: str) -> List[Result]:
        """Finds URLs within text

        Args:
            text (str): Source text

        Returns:
            List[Result]: Found URLs
        """

        urls: List[Result] = []

        for url_match in self._URL_RE.finditer(text):

            url_span = Span(url_match.start(0), url_match.end(0))
            url = text[url_span.start:url_span.end]

            scheme_pos = url.find("://")
            if scheme_pos == -1:
                schemed_url = "http://" + url
            else:
                schemed_url = url

            url_host = uritools.urisplit(schemed_url).gethost()

            if url_host in self._white_list or (self._black_list and url_host not in self._black_list):
                continue
            
            urls.append(Result(url_span, url))
            
        return urls
    
    def has_urls(self, text: str) -> bool:
        """Checks if text has URLs

        Args:
            text (str): Source text

        Returns:
            bool: Indicates that text has URLs
        """
        return len(self.find(text)) > 0