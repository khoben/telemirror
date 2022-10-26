import collections


class LimitedDict(collections.OrderedDict):
    """
    Dict with a limited length, ejecting LRUs as needed.
    """

    def __init__(self, *args, capacity, free_factor=0.5, **kwargs):
        assert capacity > 0
        assert free_factor > 0.1 and free_factor <= 1.0
        self.capacity = capacity
        self.keep_last = max(1.0, capacity * (1.0 - free_factor))

        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().move_to_end(key)

        if len(self) > self.capacity:
            while len(self) > self.keep_last:
                oldkey = next(iter(self))
                super().__delitem__(oldkey)

    def __getitem__(self, key):
        val = super().__getitem__(key)
        super().move_to_end(key)

        return val
