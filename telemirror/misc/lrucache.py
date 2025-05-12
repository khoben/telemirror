import collections
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V], collections.OrderedDict[K, V]):
    """
    Dict with a limited length, ejecting LRUs as needed.

    Args:
        capacity (int): Maximum number of items the cache can hold.
        free_factor (float, optional): Fraction of items to keep when purging (default: 0.5).
    """

    def __init__(self, *args, capacity: int, free_factor: float = 0.5, **kwargs):
        assert capacity > 0
        assert free_factor > 0.1 and free_factor <= 1.0
        self.capacity = capacity
        self.keep_last = max(1.0, capacity * (1.0 - free_factor))

        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V):
        super().__setitem__(key, value)
        super().move_to_end(key)

        if len(self) > self.capacity:
            while len(self) > self.keep_last:
                oldkey = next(iter(self))
                super().__delitem__(oldkey)

    def __getitem__(self, key: K):
        val = super().__getitem__(key)
        super().move_to_end(key)

        return val
