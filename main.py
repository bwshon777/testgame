# main.py (pygbag/pygame-web friendly)
import pygame
import random
import time
import asyncio

GRID_SIZE = 4
TILE_SIZE = 110
GAP = 12
PADDING = 20
WIDTH = PADDING * 2 + GRID_SIZE * TILE_SIZE + (GRID_SIZE - 1) * GAP
HEIGHT = WIDTH + 120
BG_COLOR = (250, 248, 239)
BOARD_BG = (187, 173, 160)
EMPTY_COLOR = (205, 193, 180)
TEXT_COLOR = (119, 110, 101)
WHITE = (255, 255, 255)
ANIM_TIME = 0.10  # a touch longer for browsers

TILE_COLORS = {
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}

def new_board():
    b = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
    add_random_tile(b); add_random_tile(b)
    return b

def add_random_tile(board):
    empties = [(r,c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if board[r][c]==0]
    if not empties: return False
    r,c = random.choice(empties)
    board[r][c] = 4 if random.random() < 0.1 else 2
    return True

def can_move(board):
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if board[r][c] == 0: return True
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            v = board[r][c]
            for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                nr,nc = r+dr, c+dc
                if 0<=nr<GRID_SIZE and 0<=nc<GRID_SIZE and board[nr][nc]==v:
                    return True
    return False

def won(board):
    return any(board[r][c] >= 2048 for r in range(GRID_SIZE) for c in range(GRID_SIZE))

def move_and_merge_line(line):
    arr = [v for v in line if v != 0]
    out, gain, i = [], 0, 0
    while i < len(arr):
        if i+1 < len(arr) and arr[i] == arr[i+1]:
            nv = arr[i]*2
            out.append(nv); gain += nv; i += 2
        else:
            out.append(arr[i]); i += 1
    out += [0]*(len(line)-len(out))
    return out, gain

def rotate_board(board):
    N = len(board)
    return [[board[N-1-r][c] for r in range(N)] for c in range(N)]

def move_board(board, direction):
    b = [row[:] for row in board]
    rot = {'left':0,'down':1,'right':2,'up':3}[direction]
    for _ in range(rot): b = rotate_board(b)

    moved, gain = False, 0
    before_rows = [row[:] for row in b]
    for r in range(GRID_SIZE):
        nr, g = move_and_merge_line(b[r])
        if nr != b[r]: moved = True
        b[r] = nr; gain += g

    for _ in range((4-rot)%4): b = rotate_board(b)

    # very simple movement map: map each non-zero source to a same-valued destination (approx)
    move_map, after_positions = {}, {}
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            v = b[r][c]
            if v: after_positions.setdefault(v, []).append((r,c))
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            v = board[r][c]
            if v:
                if v in after_positions and after_positions[v]:
                    nr, nc = after_positions[v].pop(0)
                    move_map[(r,c)] = (nr,nc, False)
                else:
                    if v*2 in after_positions and after_positions[v*2]:
                        nr, nc = after_positions[v*2][0]
                        move_map[(r,c)] = (nr,nc, True)
                    else:
                        move_map[(r,c)] = (r,c, False)
    return b, moved, gain, move_map

def draw_rounded_rect(surf, rect, color, radius=12):
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def tile_rect(r, c):
    x = PADDING + c*(TILE_SIZE+GAP)
    y = PADDING + r*(TILE_SIZE+GAP) + 100
    return pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

def draw_board(screen, font_big, font_small, board, score, best, message=None):
    screen.fill(BG_COLOR)
    title = font_big.render("2048", True, TEXT_COLOR)
    screen.blit(title, (PADDING, 20))

    score_box = pygame.Rect(WIDTH - PADDING - 140, 20, 140, 60)
    best_box  = pygame.Rect(WIDTH - PADDING - 300, 20, 140, 60)
    for box, label, value in [(best_box,"BEST",best),(score_box,"SCORE",score)]:
        draw_rounded_rect(screen, box, (187,173,160), 8)
        screen.blit(font_small.render(label, True, (238,228,218)), (box.x+10, box.y+6))
        screen.blit(font_big.render(str(value), True, WHITE), (box.x+10, box.y+22))

    board_rect = pygame.Rect(PADDING, 100, WIDTH - 2*PADDING, WIDTH - 2*PADDING)
    draw_rounded_rect(screen, board_rect, BOARD_BG, 12)

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            rect = tile_rect(r,c)
            v = board[r][c]
            if not v:
                draw_rounded_rect(screen, rect, EMPTY_COLOR, 8)
            else:
                color = TILE_COLORS.get(v, (60,58,50))
                draw_rounded_rect(screen, rect, color, 8)
                text_col = TEXT_COLOR if v <= 4 else (249,246,242)
                txt = font_big.render(str(v), True, text_col)
                screen.blit(txt, txt.get_rect(center=rect.center))

    if message:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,120))
        screen.blit(overlay, (0,0))
        msg = font_big.render(message, True, WHITE)
        sub = font_small.render("R to restart • U to undo", True, WHITE)
        screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 10)))
        screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 30)))

async def animate_move(screen, font_big, font_small, before, after, score, best, move_map):
    start = time.time()
    # simple per-frame limiter (pygbag hates long tight loops)
    while True:
        t = (time.time() - start) / ANIM_TIME
        if t >= 1.0: break
        screen.fill(BG_COLOR)
        draw_board(screen, font_big, font_small, before, score, best, None)
        # draw moving tiles
        for (r,c), (nr,nc,merged) in move_map.items():
            v = before[r][c]
            if not v: continue
            sr = tile_rect(r,c); er = tile_rect(nr,nc)
            ix = sr.x + (er.x - sr.x) * t
            iy = sr.y + (er.y - sr.y) * t
            rect = pygame.Rect(ix, iy, TILE_SIZE, TILE_SIZE)
            color = TILE_COLORS.get(v, (60,58,50))
            draw_rounded_rect(screen, rect, color, 8)
            text_col = TEXT_COLOR if v <= 4 else (249,246,242)
            txt = font_big.render(str(v), True, text_col)
            screen.blit(txt, txt.get_rect(center=rect.center))
        pygame.display.flip()
        pygame.event.pump()         # keep browser responsive
        await asyncio.sleep(0)      # yield to the event loop

async def main():
    pygame.init()
    pygame.display.set_caption("2048 (Web)")
    # SCALED helps on high-DPI; RESIZABLE avoids some canvas issues
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # fonts: use default to avoid missing system fonts in the browser
    font_big = pygame.font.SysFont(None, 42, bold=True)
    font_small = pygame.font.SysFont(None, 18, bold=True)

    board = new_board()
    score = 0
    best = 0
    won_flag = False
    history = []

    running = True
    while running:
        # normal draw
        msg = None
        if won(board) and not won_flag:
            won_flag = True
        if won_flag: msg = "You made 2048! Keep going!"
        if not can_move(board): msg = "Game Over!"

        draw_board(screen, font_big, font_small, board, score, best, msg)
        pygame.display.flip()

        # handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                # keep canvas responsive
                screen = pygame.display.set_mode(event.size, pygame.SCALED | pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                direction = None
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    board = new_board(); score = 0; won_flag = False; history.clear(); continue
                elif event.key == pygame.K_u and history:
                    board, score = history.pop(); continue
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    direction = 'left'
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    direction = 'right'
                elif event.key in (pygame.K_UP, pygame.K_w):
                    direction = 'up'
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    direction = 'down'

                if direction and can_move(board):
                    before = [row[:] for row in board]
                    new_board_state, did_move, gain, move_map = move_board(board, direction)
                    if did_move:
                        history.append((before, score))
                        board = new_board_state
                        score += gain
                        best = max(best, score)
                        await animate_move(screen, font_big, font_small, before, board, score, best, move_map)
                        add_random_tile(board)
                        won_flag = won_flag or won(board)

        # yield every frame
        clock.tick(60)
        await asyncio.sleep(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # pygbag may already run an event loop; fall back to create_task
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()