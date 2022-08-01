import string
from urlextract import URLExtract

class URLExtractPatched(URLExtract):

    def _complete_url(
        self, text, tld_pos, tld, check_dns=False, with_schema_only=False
    ):
        """
        Patched from URLExtract._complete_url:
        1. Optimize start_pos/end_pos index calculation
        2. Expand only to printable symbols

        Expand string in both sides to match whole URL.

        :param str text: text where we want to find URL
        :param int tld_pos: position of TLD
        :param str tld: matched TLD which should be in text
        :param bool check_dns: filter results to valid domains
        :param bool with_schema_only: get domains with schema only
            (e.g. https://janlipovsky.cz but not example.com)
        :return: returns URL
        :rtype: str
        """

        max_len = len(text) - 1
        end_pos = tld_pos
        start_pos = tld_pos

        while start_pos > 0 and \
            text[start_pos - 1] not in self._stop_chars_left \
                 and text[start_pos - 1] in string.printable:
            start_pos -= 1

        while end_pos < max_len and \
             text[end_pos + 1] not in self._stop_chars_right and \
                 text[start_pos + 1] in string.printable:
            end_pos += 1

        complete_url = text[start_pos : end_pos + 1].lstrip("/")
        # remove last character from url
        # when it is allowed character right after TLD (e.g. dot, comma)
        temp_tlds = {tld + c for c in self._after_tld_chars}
        # get only dot+tld+one_char and compare
        extended_tld = complete_url[len(complete_url) - len(tld) - 1 :]
        if extended_tld in temp_tlds:
            # We do not want o change found URL
            if not extended_tld.endswith("/"):
                complete_url = complete_url[:-1]

        complete_url = self._split_markdown(complete_url, tld_pos - start_pos)
        complete_url = self._remove_enclosure_from_url(
            complete_url, tld_pos - start_pos, tld
        )

        # search for enclosures before URL ignoring space character " "
        # when URL contains right enclosure character (issue #77)
        enclosure_map = {
            left_char: right_char for left_char, right_char in self._enclosure
        }
        if any(
            enclosure in complete_url[tld_pos - start_pos :]
            for enclosure in enclosure_map.values()
        ):
            enclosure_space_char = True
            enclosure_found = False
            tmp_start_pos = start_pos
            while enclosure_space_char:
                if tmp_start_pos <= 0:
                    break
                if text[tmp_start_pos - 1] == " ":
                    tmp_start_pos -= 1
                elif text[tmp_start_pos - 1] in enclosure_map.keys():
                    tmp_start_pos -= 1
                    enclosure_found = True
                else:
                    enclosure_space_char = False

            if enclosure_found:
                pre_url = text[tmp_start_pos:start_pos]
                extended_complete_url = pre_url + complete_url
                complete_url = self._remove_enclosure_from_url(
                    extended_complete_url, tld_pos - tmp_start_pos, tld
                )
        # URL should not start/end with whitespace
        complete_url = complete_url.strip()
        # URL should not start with two backslashes
        if complete_url.startswith("//"):
            complete_url = complete_url[2:]
        if not self._is_domain_valid(
            complete_url, tld, check_dns=check_dns, with_schema_only=with_schema_only
        ):
            return ""

        return complete_url