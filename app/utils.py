import re
from urlextract import URLExtract
from settings import REMOVE_URLS_WL_DATA as WHITELIST

url_extractor = URLExtract()


def remove_urls(text, limit_not_remove=0, placeholder='***'):
    """Removes URLs from given text

    Args:
        text (str): Text
        limit_not_remove (int, optional): If text has less
        than 'limit_not_remove' symbols then dont process it. Defaults to 140.
        placeholder (str, optional): Placeholder for URL. Defaults to '***'.

    Returns:
        str: Text
    """
    if len(text) < limit_not_remove:
        return text

    urls = url_extractor.find_urls(text)
    for url in urls:
        allowed = False
        for white_listed in WHITELIST:
            if url.find(white_listed) != -1:
                allowed = True
                break
        if allowed is False:
            text = text.replace(url, placeholder)

    # @test => placeholder
    text = re.sub(r'@[\d\w]*', placeholder, text)

    return text
