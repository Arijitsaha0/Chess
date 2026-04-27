from flask import Flask, jsonify, request, send_file
import copy
import os

app = Flask(__name__)

# ─── BOARD SETUP ─────────────────────────────────────────────
def fresh_board():
    return [
        ['bR','bN','bB','bQ','bK','bB','bN','bR'],
        ['bP','bP','bP','bP','bP','bP','bP','bP'],
        ['--','--','--','--','--','--','--','--'],
        ['--','--','--','--','--','--','--','--'],
        ['--','--','--','--','--','--','--','--'],
        ['--','--','--','--','--','--','--','--'],
        ['wP','wP','wP','wP','wP','wP','wP','wP'],
        ['wR','wN','wB','wQ','wK','wB','wN','wR'],
    ]

# ─── GAME STATE ──────────────────────────────────────────────
game_state = {
    'board': fresh_board(),
    'turn': 'w',
    'captured_w': [],
    'captured_b': [],
    'move_count': 0,
    'game_over': False,
    'status': ''
}

# ─── MOVE LOGIC ──────────────────────────────────────────────
def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def get_raw_moves(board, row, col):
    piece = board[row][col]
    color, kind = piece[0], piece[1]
    enemy = 'b' if color == 'w' else 'w'
    moves = []

    def slide(dirs):
        for dr, dc in dirs:
            r, c = row + dr, col + dc
            while in_bounds(r, c):
                if board[r][c] == '--':
                    moves.append([r, c])
                elif board[r][c][0] == enemy:
                    moves.append([r, c])
                    break
                else:
                    break
                r += dr; c += dc

    def step(dirs):
        for dr, dc in dirs:
            r, c = row + dr, col + dc
            if in_bounds(r, c) and board[r][c][0] != color:
                moves.append([r, c])

    if kind == 'P':
        direction = -1 if color == 'w' else 1
        start_row = 6 if color == 'w' else 1
        if in_bounds(row + direction, col) and board[row + direction][col] == '--':
            moves.append([row + direction, col])
            if row == start_row and board[row + 2 * direction][col] == '--':
                moves.append([row + 2 * direction, col])
        for dc in [-1, 1]:
            r, c = row + direction, col + dc
            if in_bounds(r, c) and board[r][c][0] == enemy:
                moves.append([r, c])
    elif kind == 'R': slide([[-1,0],[1,0],[0,-1],[0,1]])
    elif kind == 'B': slide([[-1,-1],[-1,1],[1,-1],[1,1]])
    elif kind == 'Q': slide([[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[-1,1],[1,-1],[1,1]])
    elif kind == 'N': step([[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]])
    elif kind == 'K': step([[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]])

    return moves

def find_king(board, color):
    for r in range(8):
        for c in range(8):
            if board[r][c] == color + 'K':
                return [r, c]
    return None

def is_in_check(board, color):
    king = find_king(board, color)
    if not king: return False
    enemy = 'b' if color == 'w' else 'w'
    for r in range(8):
        for c in range(8):
            if board[r][c][0] == enemy:
                if king in get_raw_moves(board, r, c):
                    return True
    return False

def get_valid_moves(board, row, col):
    color = board[row][col][0]
    legal = []
    for move in get_raw_moves(board, row, col):
        tmp = copy.deepcopy(board)
        tmp[move[0]][move[1]] = tmp[row][col]
        tmp[row][col] = '--'
        if not is_in_check(tmp, color):
            legal.append(move)
    return legal

def has_any_moves(board, color):
    for r in range(8):
        for c in range(8):
            if board[r][c][0] == color:
                if get_valid_moves(board, r, c):
                    return True
    return False

# ─── ROUTES ──────────────────────────────────────────────────
@app.route('/')
def index():
    folder = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(folder, 'index.html'))

@app.route('/state', methods=['GET'])
def get_state():
    return jsonify(game_state)

@app.route('/moves', methods=['POST'])
def get_moves():
    data = request.json
    row, col = data['row'], data['col']
    board = game_state['board']
    piece = board[row][col]
    if piece == '--' or piece[0] != game_state['turn']:
        return jsonify({'moves': []})
    moves = get_valid_moves(board, row, col)
    return jsonify({'moves': moves})

@app.route('/move', methods=['POST'])
def make_move():
    if game_state['game_over']:
        return jsonify({'error': 'Game over'}), 400

    data = request.json
    fr, fc = data['from_row'], data['from_col']
    tr, tc = data['to_row'], data['to_col']
    board = game_state['board']
    piece = board[fr][fc]

    if piece == '--' or piece[0] != game_state['turn']:
        return jsonify({'error': 'Invalid piece'}), 400

    valid = get_valid_moves(board, fr, fc)
    if [tr, tc] not in valid:
        return jsonify({'error': 'Invalid move'}), 400

    captured = board[tr][tc]
    if captured != '--':
        if captured[0] == 'b':
            game_state['captured_w'].append(captured[1])
        else:
            game_state['captured_b'].append(captured[1])

    board[tr][tc] = piece
    board[fr][fc] = '--'
    game_state['move_count'] += 1

    next_turn = 'b' if game_state['turn'] == 'w' else 'w'
    game_state['turn'] = next_turn

    if is_in_check(board, next_turn):
        if not has_any_moves(board, next_turn):
            winner = 'White Wins!' if next_turn == 'b' else 'Black Wins!'
            game_state['status'] = winner
            game_state['game_over'] = True
        else:
            game_state['status'] = 'CHECK!'
    else:
        if not has_any_moves(board, next_turn):
            game_state['status'] = 'Stalemate!'
            game_state['game_over'] = True
        else:
            game_state['status'] = ''

    return jsonify(game_state)

@app.route('/reset', methods=['POST'])
def reset():
    game_state['board'] = fresh_board()
    game_state['turn'] = 'w'
    game_state['captured_w'] = []
    game_state['captured_b'] = []
    game_state['move_count'] = 0
    game_state['game_over'] = False
    game_state['status'] = ''
    return jsonify(game_state)

if __name__ == '__main__':
    print("")
    print("  ♟  Chess server is running!")
    print("  👉 Open your browser and go to: http://localhost:5000")
    print("")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)