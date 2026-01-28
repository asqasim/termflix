import sys
import time
import random
from collections import deque
from blessed import Terminal

term = Terminal()
DIGITS = ["🯰", "🯱", "🯲", "🯳", "🯴", "🯵", "🯶", "🯷", "🯸", "🯹"]

# Tetris Definitions
# Shapes defined as lists of (row, col) coordinates relative to pivot
TETRIS_SHAPES = {
    'I': [[(0, -1), (0, 0), (0, 1), (0, 2)], [( -1, 1), (0, 1), (1, 1), (2, 1)]],
    'J': [[(-1, -1), (0, -1), (0, 0), (0, 1)], [(-1, 1), (0, 1), (1, 1), (1, 0)], [(0, -1), (0, 0), (0, 1), (1, 1)]], 
    'L': [[(-1, 1), (0, -1), (0, 0), (0, 1)], [(-1, 0), (0, 0), (1, 0), (1, 1)], [(0, -1), (0, 0), (0, 1), (1, -1)], [(-1, -1), (-1, 0), (0, 0), (1, 0)]],
    'O': [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    'S': [[(0, -1), (0, 0), (-1, 0), (-1, 1)], [(-1, 0), (0, 0), (0, 1), (1, 1)]],
    'T': [[(0, -1), (0, 0), (0, 1), (-1, 0)], [(-1, 0), (0, 0), (1, 0), (0, 1)], [(0, -1), (0, 0), (0, 1), (1, 0)], [(-1, 0), (0, 0), (1, 0), (0, -1)]],
    'Z': [[(-1, -1), (-1, 0), (0, 0), (0, 1)], [(-1, 1), (0, 1), (0, 0), (1, 0)]]
}

TETRIS_COLORS = {
    'I': term.cyan,
    'J': term.blue,
    'L': term.white, 
    'O': term.yellow,
    'S': term.green,
    'T': term.magenta,
    'Z': term.red
}

class ArcadeSystem:
    def __init__(self):
        self.running = True
        self.selection = 0 # 0=Match4, 1=TicTacToe, 2=Snake, 3=Tetris
        self.m4_red_score = 0
        self.m4_blue_score = 0
        self.snake_score = 0
        self.tetris_score = 0
        self.ai_mode = False 

    def draw_box(self, x, y, w, h, title="", style="default"):
        # Define border character sets
        styles = {
            "default": {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
            "dotted":  {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "╌", "v": "╎"},
            "filled":  {"tl": "🮘", "tr": "🮘", "bl": "🮘", "br": "🮘", "h": "🮘", "v": "🮘"},
            "curved":  {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│"},
            "double":  {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
        }
    
        b = styles.get(style, styles["default"])

        if style == "filled":
            if title:
                clean_title = term.strip(title)
                display_title = f" {title} "
                clean_display_len = len(clean_title) + 2
                avail_space = w - 4
                if clean_display_len > avail_space: 
                    display_title = " " + clean_title[:avail_space-2] + " "
                    clean_display_len = len(display_title)
                padding = max(0, (avail_space - clean_display_len) // 2)
                right_padding = max(0, avail_space - clean_display_len - padding)
                top_line = (b["tl"]*2) + b["h"] + (b["h"] * padding) + display_title + (b["h"] * right_padding) + (b["tr"]*2)
            else:
                top_line = (b["tl"]*2) + b["h"] * (w - 4) + (b["tr"]*2)
            
            print(term.move_xy(x, y) + top_line)
            for i in range(1, h - 1):
                middle_line = (b["v"]*2) + " " * (w - 4) + (b["v"]*2)
                print(term.move_xy(x, y + i) + middle_line)
            bottom_line = (b["bl"]*2) + b["h"] * (w - 4) + (b["br"]*2)
            print(term.move_xy(x, y + h - 1) + bottom_line)

        else:
            if title:
                clean_title = term.strip(title)
                if len(clean_title) > w-2:
                    clean_title = clean_title[:w-2]
                display_title = title if len(term.strip(title)) == len(title) else clean_title
                top_line = b["tl"] + b["h"] + display_title + b["h"] * (w - 3 - len(clean_title)) + b["tr"]
            else:
                top_line = b["tl"] + b["h"] * (w - 2) + b["tr"]
        
            print(term.move_xy(x, y) + top_line)
            for i in range(1, h - 1):
                middle_line = b["v"] + " " * (w - 2) + b["v"]
                print(term.move_xy(x, y + i) + middle_line)
            bottom_line = b["bl"] + b["h"] * (w - 2) + b["br"]
            print(term.move_xy(x, y + h - 1) + bottom_line)

    def draw_footer(self, rules):
        y = term.height - 8
        w_half = term.width // 2
        print(term.move_xy(0, y) + "░" * term.width)
        print(term.move_xy(2, y+1) + term.bold_yellow("GAME RULES:"))
        for i, rule in enumerate(rules):
            print(term.move_xy(2, y+2+i) + f"⊱ {rule}")
        cx = w_half + 2
        print(term.move_xy(cx, y+1) + term.bold_yellow("CONTROLS:"))
        print(term.move_xy(cx, y+2) + "Move        │ ⇦ ⇧ ⇨    ")
        print(term.move_xy(cx, y+3) + "Select/Pause│ ↲ Enter  ")
        print(term.move_xy(cx, y+4) + "Restart     │ R        ")
        print(term.move_xy(cx, y+5) + "Main Menu   │ Q        ")

    def score_glyphs(self, n):
        try:
            n = int(n)
        except:
            n = 0
        n = max(0, min(n, 9999)) # Increased limit for tetris
        s = str(n)
        return ''.join(DIGITS[int(d)] for d in s)

    def draw_scores(self, x, y):
        r_glyphs = self.score_glyphs(self.m4_red_score)
        b_glyphs = self.score_glyphs(self.m4_blue_score)
        print(term.move_xy(x, y) + term.red("RED ") + term.red(r_glyphs) + "   " + term.blue("BLUE ") + term.blue(b_glyphs))

    def main_menu(self):
        print(term.clear + term.hide_cursor)
        title = " ARCADE LAUNCHER "
        print(term.move_xy(term.width//2 - len(title)//2, 2) + term.bold(title))

        # Adjusted layout to 2x2 grid to fit 4 games nicely
        # Row 1: Match 4 (Left), TTT (Right)
        # Row 2: Snake (Left), Tetris (Right)
        
        c1_x, c2_x = 15, 60
        r1_y, r2_y = 5, 17

        # --- Match 4 Preview ---
        self.draw_box(c1_x, r1_y, 30, 10, "MATCH 4", style = "curved")
        if self.selection == 0:
            print(term.move_xy(c1_x+2, r1_y) + term.bold_green("MATCH 4"))
        
        bx, by = c1_x+8, r1_y+2
        print(term.move_xy(bx, by)   + term.white("○") + " " + term.white("○") + " " + term.white("○") + " " + term.white("○") + " " + term.white("○"))
        print(term.move_xy(bx, by+1) + term.white("○") + " " + term.blue("⬤") + " " + term.red("⬤") + " " + term.white("○") + " " + term.white("○"))
        print(term.move_xy(bx, by+2) + term.white("○") + " " + term.red("⬤") + " " + term.blue("⬤") + " " + term.white("○") + " " + term.white("○"))
        print(term.move_xy(bx, by+3) + term.red("⬤") + " " + term.red("⬤") + " " + term.blue("⬤") + " " + term.blue("⬤") + " " + term.white("○"))
        print(term.move_xy(bx, by+4) + term.blue("⬤") + " " + term.red("⬤") + " " + term.blue("⬤") + " " + term.red("⬤") + " " + term.red("⬤"))

        # --- Tic Tac Toe Preview ---
        self.draw_box(c2_x, r1_y, 30, 10, "VANISHING TTT")
        if self.selection == 1:
            print(term.move_xy(c2_x+2, r1_y) + term.bold_green("VANISHING TTT"))

        bx, by = c2_x+10, r1_y+3
        print(term.move_xy(bx, by)    + " "+ term.red("⬤") +" │   │   ")
        print(term.move_xy(bx, by+1)  + "───┼───┼───")
        print(term.move_xy(bx, by+2) + " "+ term.blue("⬤") +" │ "+ term.red("⬤") +" │   ")
        print(term.move_xy(bx, by+3) + "───┼───┼───")
        print(term.move_xy(bx, by+4) + " "+ term.blue("⬤") +" │   │ "+ term.blue("⬤") +" ")

        # --- Classic Snake Preview ---
        self.draw_box(c1_x, r2_y, 30, 10, "CLASSIC SNAKE")
        if self.selection == 2:
            print(term.move_xy(c1_x+2, r2_y) + term.bold_green("CLASSIC SNAKE"))

        bx, by = c1_x+4, r2_y+4
        print(term.move_xy(bx, by) + term.red("░░") + term.blue("▒▒")+ term.red("🮐🮐") + term.blue("🮐🮐")+ term.red("🮐🮐") + term.blue("🮐🮐") + "ᐸ")
        print(term.move_xy(bx, by+1) + term.blue("🮐🮐"))
        print(term.move_xy(bx, by+2) + term.red("🮐🮐")+ term.blue("🮐🮐")+ term.red("🮐🮐") + "        " + term.green("⬤"))

        # --- Tetris Preview ---
        self.draw_box(c2_x, r2_y, 30, 10, "TETRIS BLOCKS")
        if self.selection == 3:
            print(term.move_xy(c2_x+2, r2_y) + term.bold_green("TETRIS BLOCKS"))
        
        bx, by = c2_x+7, r2_y+2
        # T shape
        print(term.move_xy(bx+4, by) + term.magenta("  🮐🮐  "))
        print(term.move_xy(bx+4, by+1) + term.magenta("🮐🮐🮐🮐🮐🮐"))
        # Z shape falling
        print(term.move_xy(bx-2, by+3) + term.red("🮐🮐🮐🮐"))
        print(term.move_xy(bx, by+4) + term.red("🮐🮐🮐🮐"))
        # L shape
        print(term.move_xy(bx+10, by+3) + term.white("🮐🮐"))
        print(term.move_xy(bx+10, by+4) + term.white("🮐🮐"))
        print(term.move_xy(bx+10, by+5) + term.white("🮐🮐🮐🮐"))

        print(term.move_xy(20, term.height-2) + "Use ARROWS to Select, ENTER to Play, Q to Quit")

    def select_opponent(self):
        options = ["VS FRIEND", "VS AI BOT"]
        sel = 0
        while True:
            print(term.clear)
            self.draw_box(30, 8, 30, 8, " SELECT MODE ")
            for i, opt in enumerate(options):
                prefix = term.white(" > ") if i == sel else "   "
                print(term.move_xy(32, 11+i) + prefix + opt)
            val = term.inkey()
            if val.code == term.KEY_UP: sel = (sel-1)%2
            elif val.code == term.KEY_DOWN: sel = (sel+1)%2
            elif val.code == term.KEY_ENTER:
                self.ai_mode = (sel == 1)
                return True
            elif val.lower() == 'q':
                return False

    def select_snake_mode(self):
        options = ["Single Player", "VS Friend (Coming Soon)"]
        sel = 0
        while True:
            print(term.clear)
            self.draw_box(30, 8, 30, 8, " SNAKE MODE ")
            for i, opt in enumerate(options):
                prefix = " > " if i == sel else "   "
                color = term.bold_green if i == sel else term.white
                print(term.move_xy(32, 11+i) + color + prefix + opt)
            val = term.inkey()
            if val.code == term.KEY_UP: sel = (sel-1)%len(options)
            elif val.code == term.KEY_DOWN: sel = (sel+1)%len(options)
            elif val.code == term.KEY_ENTER:
                if sel == 1: continue 
                return True
            elif val.lower() == 'q':
                return False

    def select_snake_skin(self):
        colors = [("Red", term.red), ("Blue", term.blue), ("Yellow", term.yellow), ("Green", term.green), ("Cyan", term.cyan)]
        sel = 0
        while True:
            print(term.clear)
            self.draw_box(25, 6, 40, 11, " SELECT SNAKE ", style="double")
            for i, (name, col_func) in enumerate(colors):
                prefix = " > " if i == sel else "   "
                preview = col_func(name.ljust(8)) + col_func("🮐🮐") + term.white("🮐🮐🮐🮐🮐🮐")
                print(term.move_xy(28, 9+i) + prefix + preview)
            val = term.inkey()
            if val.code == term.KEY_UP: sel = (sel-1) % len(colors)
            elif val.code == term.KEY_DOWN: sel = (sel+1) % len(colors)
            elif val.code == term.KEY_ENTER: return colors[sel][1]
            elif val.lower() == 'q': return None

    def select_snake_dimension(self):
        max_h = term.height - 6
        options = [("Small  (15x15)", 20), ("Medium (20x20)", 30), (f"Large  (Max Height)", max_h)]
        sel = 0
        while True:
            print(term.clear)
            self.draw_box(25, 8, 40, 9, " GRID SIZE ", style="double")
            for i, (text, size) in enumerate(options):
                color = term.bold_green if i == sel else term.white
                prefix = " > " if i == sel else "   "
                print(term.move_xy(28, 11+i) + color + prefix + text)
            val = term.inkey()
            if val.code == term.KEY_UP: sel = (sel-1) % len(options)
            elif val.code == term.KEY_DOWN: sel = (sel+1) % len(options)
            elif val.code == term.KEY_ENTER: return options[sel][1]
            elif val.lower() == 'q': return None

    def run(self):
        with term.cbreak(), term.hidden_cursor():
            self.main_menu()
            while self.running:
                val = term.inkey()
                if val.code == term.KEY_LEFT:
                    self.selection = (self.selection-1) % 4
                    self.main_menu()
                elif val.code == term.KEY_RIGHT:
                    self.selection = (self.selection+1) % 4
                    self.main_menu()
                # Also support Up/Down for 2x2 grid feel
                elif val.code == term.KEY_UP:
                    self.selection = (self.selection-2) % 4
                    self.main_menu()
                elif val.code == term.KEY_DOWN:
                    self.selection = (self.selection+2) % 4
                    self.main_menu()
                elif val.code == term.KEY_ENTER:
                    if self.selection == 2: # Snake
                        if self.select_snake_mode():
                            skin_col = self.select_snake_skin()
                            if skin_col:
                                size = self.select_snake_dimension()
                                if size: self.play_snake(size, skin_col)
                        self.main_menu()
                    elif self.selection == 3: # Tetris
                         self.play_tetris()
                         self.main_menu()
                    else:
                        if self.select_opponent():
                            if self.selection == 0: self.play_match4()
                            else: self.play_tictactoe()
                        self.main_menu()
                elif val.lower() == 'q':
                    self.running = False

    # --- TETRIS GAME ---
    def play_tetris(self):
        grid_w, grid_h = 10, 20
        grid = [[None for _ in range(grid_w)] for _ in range(grid_h)]
        
        # Calculate centering
        board_pixel_w = grid_w * 2 
        bx = (term.width - board_pixel_w) // 2
        by = 2
        
        # Side panel for Next Piece and Score
        panel_x = bx + board_pixel_w + 2
        
        score = 0
        level = 1
        speed = 0.5
        
        def new_piece():
            shape_key = random.choice(list(TETRIS_SHAPES.keys()))
            return {'key': shape_key, 'rot': 0, 'row': 0, 'col': grid_w // 2 - 1, 'color': TETRIS_COLORS[shape_key]}

        current_piece = new_piece()
        next_piece = new_piece()
        
        paused = True # Start paused as requested
        game_over = False
        last_drop_time = time.time()

        print(term.clear)
        self.draw_box(bx, by-1, board_pixel_w+2, grid_h+2, " TETRIS ", style="double")
        
        # Draw Side Panel
        self.draw_box(panel_x, by-1, 16, 12, " INFO ", style="dotted")

        def draw_next_piece_preview():
            # Clear preview area
            for r in range(4):
                print(term.move_xy(panel_x+2, by+3+r) + "            ")
            
            # Draw next piece
            shape = TETRIS_SHAPES[next_piece['key']][0] # Default rotation
            col = next_piece['color']
            for dr, dc in shape:
                # Center somewhat in the box (approx offset 4, 2)
                px = panel_x + 6 + (dc * 2)
                py = by + 4 + dr
                print(term.move_xy(px, py) + col("🮐🮐"))

        def draw_ui():
            # Score
            print(term.move_xy(panel_x+2, by+1) + "SCORE:")
            print(term.move_xy(panel_x+2, by+2) + self.score_glyphs(score))
            # Next label
            print(term.move_xy(panel_x+2, by+8) + "NEXT:")
            draw_next_piece_preview()
            
            # Controls help
            print(term.move_xy(panel_x, by+12) + "CONTROLS:")
            print(term.move_xy(panel_x, by+13) + "Arrows: Move")
            print(term.move_xy(panel_x, by+14) + "Up/Dn: Rotate")
            print(term.move_xy(panel_x, by+15) + "Enter: Drop")
            print(term.move_xy(panel_x, by+16) + "Space: Pause")
        
        draw_ui()

        # Render full board
        def render_board(blink_lines=None):
            for r in range(grid_h):
                line_str = ""
                for c in range(grid_w):
                    if blink_lines and r in blink_lines:
                        line_str += term.white("██") # Flash white
                    elif grid[r][c]:
                        line_str += grid[r][c]("🮐🮐")
                    else:
                        line_str += "  " # Overwrite with spaces to clear previous trails
                print(term.move_xy(bx+1, by+r) + line_str)
                
        def get_ghost_piece():
             # Calculate ghost position (hard drop position)
            ghost = current_piece.copy()
            while is_valid_move(ghost, 1, 0):
                ghost['row'] += 1
            return ghost

        def render_current_piece():
            # Draw ghost first (dimmed)
            ghost = get_ghost_piece()
            rots = TETRIS_SHAPES[ghost['key']]
            shape = rots[ghost['rot'] % len(rots)]
            for dr, dc in shape:
                r, c = ghost['row'] + dr, ghost['col'] + dc
                if 0 <= r < grid_h and 0 <= c < grid_w:
                     # Use a dim char or just dots for ghost
                     if not grid[r][c]: # Don't overwrite locked blocks
                        print(term.move_xy(bx+1 + c*2, by+r) + term.dimgray("::"))

            # Draw actual piece
            rots = TETRIS_SHAPES[current_piece['key']]
            shape = rots[current_piece['rot'] % len(rots)]
            col = current_piece['color']
            for dr, dc in shape:
                r, c = current_piece['row'] + dr, current_piece['col'] + dc
                if 0 <= r < grid_h and 0 <= c < grid_w:
                    print(term.move_xy(bx+1 + c*2, by+r) + col("🮐🮐"))
        
        def is_valid_move(piece, dr=0, dc=0, drot=0):
            rots = TETRIS_SHAPES[piece['key']]
            new_rot = (piece['rot'] + drot) % len(rots)
            shape = rots[new_rot]
            for r_off, c_off in shape:
                r = piece['row'] + dr + r_off
                c = piece['col'] + dc + c_off
                if c < 0 or c >= grid_w or r >= grid_h: return False
                if r >= 0 and grid[r][c] is not None: return False
            return True

        def lock_piece():
            nonlocal score, speed
            rots = TETRIS_SHAPES[current_piece['key']]
            shape = rots[current_piece['rot'] % len(rots)]
            for dr, dc in shape:
                r, c = current_piece['row'] + dr, current_piece['col'] + dc
                if 0 <= r < grid_h and 0 <= c < grid_w:
                    grid[r][c] = current_piece['color']
            
            # Check lines
            full_lines = []
            for r in range(grid_h):
                if all(grid[r][c] is not None for c in range(grid_w)):
                    full_lines.append(r)
            
            if full_lines:
                # Blink animation
                for _ in range(3):
                    render_board(blink_lines=full_lines)
                    sys.stdout.flush()
                    time.sleep(0.1)
                    render_board(blink_lines=[]) # Hide
                    sys.stdout.flush()
                    time.sleep(0.1)

                # Remove lines
                for r in full_lines:
                    del grid[r]
                    grid.insert(0, [None for _ in range(grid_w)])
                
                # Scoring
                score += (100 * len(full_lines)) * len(full_lines) # 100, 400, 900, 1600
                speed = max(0.05, 0.5 - (score // 500) * 0.05) # Speed up
                draw_ui()
                render_board()

        render_board()
        if paused:
             print(term.move_xy(bx + board_pixel_w // 2 - 3, by + grid_h // 2) + term.bold_yellow("PAUSED"))

        while not game_over:
            # Input
            val = term.inkey(timeout=0.05) # Fast polling
            
            if val.lower() == 'q':
                return
            elif val == ' ':
                paused = not paused
                render_board() # clear/restore board
                if paused:
                    print(term.move_xy(bx + board_pixel_w // 2 - 3, by + grid_h // 2) + term.bold_yellow("PAUSED"))
                else:
                    render_current_piece()
            
            if paused:
                continue

            # Controls
            moved = False
            if val.code == term.KEY_LEFT:
                if is_valid_move(current_piece, 0, -1):
                    current_piece['col'] -= 1
                    moved = True
            elif val.code == term.KEY_RIGHT:
                if is_valid_move(current_piece, 0, 1):
                    current_piece['col'] += 1
                    moved = True
            elif val.code == term.KEY_UP: # Cycle Rotation CW
                if is_valid_move(current_piece, 0, 0, 1):
                    current_piece['rot'] += 1
                    moved = True
            elif val.code == term.KEY_DOWN: # Cycle Rotation CCW
                if is_valid_move(current_piece, 0, 0, -1):
                    current_piece['rot'] -= 1
                    moved = True
            elif val.code == term.KEY_ENTER: # Hard Drop
                while is_valid_move(current_piece, 1, 0):
                    current_piece['row'] += 1
                lock_piece()
                current_piece = next_piece
                next_piece = new_piece()
                draw_next_piece_preview()
                if not is_valid_move(current_piece):
                    game_over = True
                last_drop_time = time.time()
                moved = True 

            # Gravity
            if time.time() - last_drop_time > speed:
                if is_valid_move(current_piece, 1, 0):
                    current_piece['row'] += 1
                    moved = True
                else:
                    lock_piece()
                    current_piece = next_piece
                    next_piece = new_piece()
                    draw_next_piece_preview()
                    if not is_valid_move(current_piece):
                        game_over = True
                last_drop_time = time.time()

            if moved:
                render_board()
                render_current_piece()

        # Game Over Screen
        print(term.move_xy(bx + 4, by + grid_h // 2) + term.on_red(term.bold_white(" GAME OVER ")))
        term.inkey()

    # --- MATCH 4 GAME ---
    def check_m4_win(self, grid, rows, cols):
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 0: continue
                p = grid[r][c]
                for dr, dc in [(0,1), (1,0), (1,1), (1,-1)]:
                    line = [(r,c)]
                    for i in range(1,4):
                        nr, nc = r+(dr*i), c+(dc*i)
                        if 0<=nr<rows and 0<=nc<cols and grid[nr][nc]==p:
                            line.append((nr,nc))
                        else: break
                    if len(line) == 4: return line
        return None

    def play_match4(self):
        rows, cols = 6, 7
        grid = [[0]*cols for _ in range(rows)]
        bx, by = 10, 5
        turn = 1
        curr_col = 0
        print(term.clear)
        self.draw_scores(bx, 2)
        self.draw_box(bx-2, by-1, 17, rows+2)
        for r in range(rows):
            for c in range(cols):
                print(term.move_xy(bx + c*2, by + r) + '○')
        self.draw_footer(["Connect 4 circles in a row", "Horizontal, Vertical, Diagonal", "Red goes first"])
        while True:
            if self.ai_mode and turn == 2:
                time.sleep(0.5)
                valid_cols = [c for c in range(cols) if grid[0][c] == 0]
                if valid_cols:
                    curr_col = random.choice(valid_cols)
                    val = " "
                else:
                    return
            else:
                col_func = term.red if turn == 1 else term.blue
                print(term.move_xy(bx + curr_col*2, by - 2) + col_func('▼'))
                val = term.inkey()
                print(term.move_xy(bx + curr_col*2, by - 2) + " ")
                if val.lower() == 'q': return
                if val.lower() == 'r': return self.play_match4()
                if val.code == term.KEY_LEFT and curr_col > 0: curr_col -= 1
                elif val.code == term.KEY_RIGHT and curr_col < cols - 1: curr_col += 1
            if val.code == term.KEY_ENTER or val == " ":
                target = -1
                for r in range(rows-1, -1, -1):
                    if grid[r][curr_col] == 0:
                        target = r
                        break
                if target != -1:
                    col_func = term.red if turn == 1 else term.blue
                    for r in range(target + 1):
                        print(term.move_xy(bx + curr_col*2, by + r) + col_func('⬤'))
                        if r > 0: print(term.move_xy(bx + curr_col*2, by + r - 1) + '○')
                        time.sleep(0.04); sys.stdout.flush()
                    grid[target][curr_col] = turn
                    win = self.check_m4_win(grid, rows, cols)
                    if win:
                        if turn == 1:
                            self.m4_red_score += 1
                        else:
                            self.m4_blue_score += 1
                        winner_label = term.bold_red("Red") if turn == 1 else term.bold_blue("Blue")
                        while True:
                            self.draw_scores(bx, 2)
                            print(term.move_xy(bx, by+rows+2) + (f"{winner_label} WINS!"))
                            for r, c in win:
                                print(term.move_xy(bx + c*2, by + r) + term.bold_white('⬤'))
                            time.sleep(0.3)
                            for r, c in win:
                                col_func2 = term.red if turn == 1 else term.blue
                                print(term.move_xy(bx + c*2, by + r) + col_func2('⬤'))
                            time.sleep(0.3)
                            k = term.inkey(timeout=0.1)
                            if k.lower() == 'r': return self.play_match4()
                            if k.lower() == 'q': return
                    turn = 2 if turn == 1 else 1

    # --- VANISHING TIC TAC TOE GAME ---
    def play_tictactoe(self):
        grid = [[0]*3 for _ in range(3)]
        moves = {1: deque(), 2: deque()}
        turn = 1
        cx, cy = 1, 1
        bx, by = 30, 6
        print(term.clear)
        self.draw_scores(bx-5, 2)
        print(term.move_xy(bx-5, 3) + term.bold_green("VANISHING TIC TAC TOE"))
        print(term.move_xy(bx, by+0)   + "   │   │   ")
        print(term.move_xy(bx, by+1)   + "───┼───┼───")
        print(term.move_xy(bx, by+2)   + "   │   │   ")
        print(term.move_xy(bx, by+3)   + "───┼───┼───")
        print(term.move_xy(bx, by+4)   + "   │   │   ")
        self.draw_footer(["Max 3 pieces per player", "4th piece removes your 1st", "Connect 3 to win"])
        while True:
            if self.ai_mode and turn == 2:
                time.sleep(0.5)
                empty_cells = [(r,c) for r in range(3) for c in range(3) if grid[r][c] == 0]
                if empty_cells:
                    cy, cx = random.choice(empty_cells)
                    val = " "
                else: val = ""
            else:
                for r in range(3):
                    for c in range(3):
                        sx, sy = bx + 1 + (c * 4), by + (r * 2)
                        char = " "
                        if grid[r][c] == 1: char = term.red("⬤")
                        elif grid[r][c] == 2: char = term.blue("⬤")
                        if r == cy and c == cx and not (self.ai_mode and turn==2):
                            if grid[r][c] != 0: char = term.white("⬤")
                            else: char = term.white("○")
                        print(term.move_xy(sx, sy) + char)
                name = term.red("Red") if turn == 1 else term.blue("Blue")
                print(term.move_xy(bx, by+6) + f"{name}'s TURN   ")
                val = term.inkey()
                if val.lower() == 'q': return
                if val.lower() == 'r': return self.play_tictactoe()
                if val.code == term.KEY_LEFT: cx = max(0, cx-1)
                elif val.code == term.KEY_RIGHT: cx = min(2, cx+1)
                elif val.code == term.KEY_UP: cy = max(0, cy-1)
                elif val.code == term.KEY_DOWN: cy = min(2, cy+1)
            if val.code == term.KEY_ENTER or val == " ":
                if grid[cy][cx] == 0:
                    if len(moves[turn]) == 3:
                        old_r, old_c = moves[turn].popleft()
                        grid[old_r][old_c] = 0
                        print(term.move_xy(bx + 1 + (old_c * 4), by + (old_r * 2)) + term.bold_yellow("*"))
                        time.sleep(0.2)
                    grid[cy][cx] = turn
                    moves[turn].append((cy, cx))
                    win_line = None
                    for i in range(3):
                        if grid[i][0]==turn and grid[i][1]==turn and grid[i][2]==turn: win_line=[(i,0),(i,1),(i,2)]
                        if grid[0][i]==turn and grid[1][i]==turn and grid[2][i]==turn: win_line=[(0,i),(1,i),(2,i)]
                    if grid[0][0]==turn and grid[1][1]==turn and grid[2][2]==turn: win_line=[(0,0),(1,1),(2,2)]
                    if grid[0][2]==turn and grid[1][1]==turn and grid[2][0]==turn: win_line=[(0,2),(1,1),(2,0)]
                    if win_line:
                        if turn == 1:
                            self.m4_red_score += 1
                        else:
                            self.m4_blue_score += 1
                        for r in range(3):
                            for c in range(3):
                                sx, sy = bx + 1 + (c * 4), by + (r * 2)
                                if grid[r][c] == 1: print(term.move_xy(sx, sy) + term.red("⬤"))
                                elif grid[r][c] == 2: print(term.move_xy(sx, sy) + term.blue("⬤"))
                        self.draw_scores(bx-5, 2)
                        t_col = term.red if turn == 1 else term.blue
                        while True:
                            winner = term.bold_blue("Blue") if turn == 2 else term.bold_red("Red")
                            print(term.move_xy(bx, by+7) + winner + (" WINS!"))
                            for r, c in win_line:
                                print(term.move_xy(bx+1+(c*4), by+(r*2)) + term.bold_white("⬤"))
                            time.sleep(0.3)
                            for r, c in win_line:
                                print(term.move_xy(bx+1+(c*4), by+(r*2)) + t_col("⬤"))
                            time.sleep(0.3)
                            k = term.inkey(timeout=0.1)
                            if k.lower() == 'r': return self.play_tictactoe()
                            if k.lower() == 'q': return
                    turn = 2 if turn == 1 else 1

    # --- CLASSIC SNAKE GAME ---
    def play_snake(self, dim_size=12, skin_func=term.white):
        play_h = dim_size
        play_w = dim_size
        total_visual_w = (play_w * 2) + 4
        bx = (term.width - total_visual_w) // 2
        by = 2
        
        init_r, init_c = play_h//2, 4
        snake = [(init_r, init_c), (init_r, init_c+1), (init_r, init_c+2), (init_r, init_c+3)]
        direction = 'right'
        dir_delta = {'up':(-1,0), 'down':(1,0), 'left':(0,-1), 'right':(0,1)}
        
        body_glyph = '🮐🮐' 
        head_glyph = '🮐🮐'
        
        def random_food():
            empties = [(r,c) for r in range(play_h) for c in range(play_w) if (r,c) not in snake]
            return random.choice(empties) if empties else None
        food = random_food()
        score = 0

        print(term.clear)
        self.draw_box(bx, by-1, (play_w * 2) + 4, play_h+2, " CLASSIC SNAKE ", style="filled")
        
        if food:
            print(term.move_xy(bx + 2 + (food[1]*2), by + food[0]) + term.red('⬤ '))
        for seg in snake[:-1]:
            print(term.move_xy(bx + 2 + (seg[1]*2), by + seg[0]) + term.white(body_glyph))
        h = snake[-1]
        print(term.move_xy(bx + 2 + (h[1]*2), by + h[0]) + skin_func(head_glyph))
        
        glyph_score = self.score_glyphs(score)
        print(term.move_xy(bx + (play_w*2) + 6, by + 2) + term.bold_yellow("SCORE:") + " " + term.bold_white(glyph_score))
        print(term.move_xy(bx, by+play_h+2) + "Press ARROW/SPACE to Start")

        paused = False
        started = False
        tick = 0.12
        
        while True:
            k = term.inkey(timeout=tick)
            if k:
                if not started:
                    if k.code in [term.KEY_UP, term.KEY_DOWN, term.KEY_LEFT, term.KEY_RIGHT] or k == " ":
                        started = True
                        print(term.move_xy(bx, by+play_h+2) + "                        ")
                    else:
                        if k.lower() == 'q': return
                        continue

                if k.code == term.KEY_UP and direction != 'down': direction = 'up'
                elif k.code == term.KEY_DOWN and direction != 'up': direction = 'down'
                elif k.code == term.KEY_LEFT and direction != 'right': direction = 'left'
                elif k.code == term.KEY_RIGHT and direction != 'left': direction = 'right'
                elif k.lower() == 'q': return
                elif k.lower() == 'r': return self.play_snake(dim_size, skin_func)
                elif k.lower() == 'p': paused = not paused

            if not started:
                continue

            if paused:
                print(term.move_xy(bx + (play_w*2) + 6, by) + term.bold_yellow("PAUSED"))
                continue
            else:
                print(term.move_xy(bx + (play_w*2) + 6, by) + "      ")

            dr, dc = dir_delta[direction]
            head_r, head_c = snake[-1]
            new_head = (head_r + dr, head_c + dc)

            if not (0 <= new_head[0] < play_h and 0 <= new_head[1] < play_w):
                print(term.move_xy(bx, by+play_h+2) + term.bold_red("Game Over - Hit wall"))
                time.sleep(0.3)
                self.snake_score = max(self.snake_score, score)
                while True:
                    k2 = term.inkey(timeout=0.1)
                    if k2.lower() == 'r': return self.play_snake(dim_size, skin_func)
                    if k2.lower() == 'q': return

            if new_head in snake:
                print(term.move_xy(bx, by+play_h+2) + term.bold_red("Game Over - Self collision"))
                time.sleep(0.3)
                self.snake_score = max(self.snake_score, score)
                while True:
                    k2 = term.inkey(timeout=0.1)
                    if k2.lower() == 'r': return self.play_snake(dim_size, skin_func)
                    if k2.lower() == 'q': return

            snake.append(new_head)
            ate = (food is not None and new_head == food)
            if ate:
                score += 1
                food = random_food()
            else:
                tail = snake.pop(0)
                print(term.move_xy(bx + 2 + (tail[1]*2), by + tail[0]) + '  ')

            if food:
                print(term.move_xy(bx + 2 + (food[1]*2), by + food[0]) + term.red('⬤ '))

            for seg in snake[:-1]:
                print(term.move_xy(bx + 2 + (seg[1]*2), by + seg[0]) + term.white(body_glyph))
            h = snake[-1]
            print(term.move_xy(bx + 2 + (h[1]*2), by + h[0]) + skin_func(head_glyph))

            glyph_score = self.score_glyphs(score)
            print(term.move_xy(bx + (play_w*2) + 6, by + 2) + term.bold_yellow("SCORE:") + " " + term.bold_white(glyph_score))

if __name__ == "__main__":
    sys.stdout.write("\033[?1049h")
    try:
        app = ArcadeSystem()
        app.run()
    finally:
        sys.stdout.write("\033[?1049l")