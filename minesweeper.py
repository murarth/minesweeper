#!/usr/bin/python3
# -*- coding: utf-8

__all__ = [
    'Grid',
]

class Grid(object):

    def __init__(self, w, h, default = lambda: None):
        assert w > 0 and h > 0, 'Invalid grid dimensions'
        self.grid = [default() for i in range(w * h)]
        self.w = w
        self.h = h

    def __contains__(self, key):
        x, y = key
        return 0 <= x < self.w and 0 <= y < self.h

    def __iter__(self):
        return iter(self.grid)

    def __getitem__(self, key):
        idx = self._get_index(key)
        return self.grid[idx]

    def __setitem__(self, key, value):
        idx = self._get_index(key)
        self.grid[idx] = value

    def _get_index(self, key):
        assert key in self, \
            'key {} out of bounds for grid {}'.format(key, (self.w, self.h))
        x, y = key
        return x * self.h + y

    def neighbors(self, key):
        x, y = key

        for (rx, ry) in (
                    (-1, -1), ( 0, -1), ( 1, -1),
                    (-1,  0),           ( 1,  0),
                    (-1,  1), ( 0,  1), ( 1,  1),
                ):
            pos = (x + rx, y + ry)
            if pos in self:
                yield pos
