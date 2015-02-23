#!/usr/bin/python3
# -*- coding: utf-8

import curses
from functools import partial
import random
import time

from game import *
from minesweeper import *

# TODO: Configurable field size
GRID_SIZE = (32, 16)
GRID_MINES = 100

class Item(object):
    __slots__ = 'mine', 'clear', 'flag', 'adjacent_mines'

    def __init__(self):
        # Whether the cell contains a mine
        self.mine = False
        # Whether the user has cleared the cell
        self.clear = False
        # Whether the user has flagged the cell
        self.flag = False
        # Number of adjacent mines (remains 0 when self.mine is True)
        self.adjacent_mines = 0

class MinesweeperGame(Game):

    GAME_TITLE = 'Minesweeper'

    def __init__(self, stdscr):
        super().__init__(stdscr)

        self.key_callbacks = {
            ord('w'): lambda: self.move_cursor(0, -1),
            ord('a'): lambda: self.move_cursor(-1, 0),
            ord('s'): lambda: self.move_cursor(0, 1),
            ord('d'): lambda: self.move_cursor(1, 0),

            ord('n'): self.confirm_new_game,
            ord('p'): self.toggle_pause,
            ord('q'): self.confirm_quit_game,
            ord('?'): self.show_help,

            ord('j'): lambda: self.clear_cell(self.cursor),
            ord('k'): lambda: self.flag_cell(self.cursor),
        }

    def init_colors(self):
        super().init_colors()
        curses.init_pair(1, curses.COLOR_BLUE, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_CYAN, -1)
        # TODO: curses doesn't have enough colors. :/
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_CYAN, -1)
        curses.init_pair(8, curses.COLOR_CYAN, -1)
        # Flag or mine color
        curses.init_pair(9, curses.COLOR_RED, -1)

    def draw_field(self, y, x):
        self.draw_flag_count(y, x)

        grid = self.grid
        w, h = grid.w, grid.h

        y_off = 3
        x_off = (x - w) // 2

        self.stdscr.subwin(h + 2, w + 2, y_off - 1, x_off - 1).border()
        stopped = self.stopped

        for py in range(h):
            for px in range(w):
                pos = (px, py)
                item = grid[pos]

                attr, content = self.render_cell(item, pos, stopped)

                self.stdscr.addstr(py + y_off, px + x_off, content, attr)

    def render_cell(self, item, pos, stopped):
        attr = 0
        content = ' '

        if pos == self.cursor or pos in self.highlighted_cells:
            attr |= curses.A_REVERSE

        if item.clear:
            attr |= curses.color_pair(item.adjacent_mines)
            content = '•' if item.adjacent_mines == 0 else str(item.adjacent_mines)
        elif item.flag:
            if stopped and not item.mine:
                content = 'x'
            else:
                attr |= curses.color_pair(9)
                attr |= curses.A_BOLD
                content = '!'
        elif stopped and item.mine:
            attr |= curses.color_pair(9)
            content = '*'

        return attr, content

    def highlight_cells(self, cells, timeout = 0.5):
        self.highlighted_cells = set(cells)
        self.highlight_timeout = time.time() + timeout
        self.queue_redraw = True

    def draw_flag_count(self, y, x):
        s = '!: {:>3}/{}'.format(self.flags_placed, self.total_mines)
        self.stdscr.addstr(0, x - len(s) - 8, s, curses.A_REVERSE)

    def draw_stopped(self, y, x):
        self.draw_field(y, x)
        if self.won:
            self.draw_centered(1, x, 'You won!')
        else:
            self.draw_centered(1, x, 'You lose')

    def draw_help(self, y, x):
        '''Draw help screen'''

        lines = [
            '?           Show this help screen',
            'Q           Quit the game (requires confirmation)',
            'P           Pause the game',
            'N           Start a new game',
            '',
            'W, A, S, D  Move the cursor',
            'J           Clear a cell',
            'K           Flag a cell',
        ]

        starty = max(1, (y - (len(lines) + 2)) // 2)
        startx = (x - max(map(len, lines))) // 2

        self.draw_centered(starty, x, 'HELP', curses.A_BOLD)

        for i, s in enumerate(lines, 2):
            self.draw_line(starty + i, startx, s)

    def help_callback(self, ch):
        if ch in { ord('p'), ord(' '), ctrl('[') }:
            self.unpause_game()
            return False
        elif ch == ord('q'):
            self.confirm_quit_game()

        return True
    def game_over(self):
        self.stopped = True
        self.won = False
        self.grab_input(self.stopped_callback)
        self.queue_redraw = True

    def game_won(self):
        self.stopped = True
        self.won = True
        self.grab_input(self.stopped_callback)

        for item in self.grid:
            if item.mine:
                item.flag = True

        self.queue_redraw = True

    def new_game(self):
        self.start_game()
        self.queue_redraw = True

    def start_game(self):
        self.paused = False
        self.stopped = False
        self.grid = grid = Grid(*GRID_SIZE, default = Item)
        self.cursor = (grid.w // 2, grid.h // 2)
        self.flags_placed = 0
        self.total_mines = GRID_MINES
        self.placed_mines = False
        self.time_offset = time.time()
        self.highlighted_cells = set()
        self.highlight_timeout = None

    def after_tick(self):
        if self.highlight_timeout is not None and \
                self.highlight_timeout < time.time():
            self.highlighted_cells.clear()
            self.highlight_timeout = None
            self.queue_redraw = True

    def clear_cell(self, pos):
        if not self.placed_mines:
            self.place_mines(pos, self.total_mines)

        item = self.grid[pos]

        if item.flag:
            return
        if item.clear:
            self.clear_neighbors(pos)
            return
        if item.mine:
            self.game_over()
        else:
            self.do_clear_cell(pos)

            if all(item.clear or item.mine for item in self.grid):
                self.game_won()
            self.queue_redraw = True

    def clear_neighbors(self, pos):
        '''
        Attempts to clear the given cell's neighbors.
        
        If the given cell is cleared and the number of flags placed in adjacent
        cells is equal to the number of mines in adjacent cells, all unflagged
        neighbors will be cleared.
        '''
        grid = self.grid
        item = grid[pos]
        if not item.clear:
            return

        flags = sum(1 for p in grid.neighbors(pos) if grid[p].flag)

        if flags == item.adjacent_mines:
            for n in grid.neighbors(pos):
                # Break out if a clear attempt has caused a game over
                if self.stopped:
                    break
                if not (grid[n].clear or grid[n].flag):
                    self.clear_cell(n)
        elif flags < item.adjacent_mines:
            self.highlight_cells(
                { p for p in grid.neighbors(pos)
                    if not grid[p].flag and not grid[p].clear })
        else: # flags > item.adjacent_mines
            self.highlight_cells(
                { p for p in grid.neighbors(pos)
                    if grid[p].flag and not grid[p].clear })

    def do_clear_cell(self, pos):
        item = self.grid[pos]

        assert item.mine is False, 'item with mine passed to do_clear_mine'

        if item.clear:
            return

        item.clear = True
        if item.flag:
            self.flags_placed -= 1
            item.flag = False

        if item.adjacent_mines == 0:
            for n in self.grid.neighbors(pos):
                self.do_clear_cell(n)

    def flag_cell(self, pos):
        item = self.grid[pos]

        if item.clear:
            return

        if item.flag:
            self.flags_placed -= 1
        else:
            self.flags_placed += 1

        item.flag = not item.flag
        self.queue_redraw = True

    def place_mines(self, pos, n):
        grid = self.grid
        w, h = grid.w, grid.h

        possible = { (px, py) for px in range(w) for py in range(h) }

        possible.remove(pos)
        [possible.remove(n) for n in grid.neighbors(pos)]

        if len(possible) < n:
            raise Exception('cannot place {} mines in {} slots'
                .format(n, len(possible)))

        plist = list(possible)
        random.shuffle(plist)

        for ipos in plist[:n]:
            grid[ipos].mine = True

        for nx in range(w):
            for ny in range(h):
                npos = (nx, ny)
                item = grid[npos]
                if not item.mine:
                    item.adjacent_mines = sum(
                        1 for n in grid.neighbors(npos) if grid[n].mine)

        self.placed_mines = True

    def move_cursor(self, rel_x, rel_y):
        x, y = self.cursor
        x += rel_x
        y += rel_y
        if (x, y) in self.grid:
            self.cursor = (x, y)
            self.queue_redraw = True

    def stopped_callback(self, ch):
        if ch == ord('n'):
            self.new_game()
            return False
        elif ch == ord('q'):
            self.confirm_quit_game()
        return True

    def show_help(self):
        self.pause_game(self.help_callback, self.draw_help)

if __name__ == '__main__':
    main(MinesweeperGame)
