import json

GAME_OVER_SCORE = 10000
LOG_TO_FILE = False

INITIAL_WEIGHTS = {
    'saved_bonuses': {0:0, 1:18, 2:20, 3:22, 4:24, 5:26, 6:28},
    'goal_bonuses': {0:0, 1:38, 2:40, 3:42, 4:44, 5:46, 6:48},
    'near_goal_bonuses': {0:0, 1:18, 2:20, 3:22, 4:24, 5:26, 6:28},
    'game_stage_bonuses': {'midgame': 50, 'endgame': 100},
    'captured_bonuses': {0:0, 1:4, 2:6, 3:8, 4:10, 5:12, 6:14},
    'loose_piece_penalties': {0:0, 1:-18, 2:-20, 3:-22, 4:-24, 5:-26, 6:-28},
    'blocked_piece_penalties': {0:0, 1:-16, 2:-18, 3:-20, 4:-22, 5:-24, 6:-26},
    'saved_piece': 60,
    'goal_piece': 36,
    'near_goal_piece': 4,
    'nearer_goal_piece': 3,
    'captured_opponent_piece': 5,
    'unentered_piece': -14,
    'loose_piece': -4,
    'blocked_piece': -6,
    'distance_penalty': -.2,
    'high_goal_penalty': -.3,
    'dice_roll_utilization': -2
}
class Agent():
    def __init__(self, board=None, weights=INITIAL_WEIGHTS, log_file='game_log.json'):
        self.board = board
        self.weights = weights
        self.log = []
        self.log_file = log_file


    def evaluate_player(self, board, player):
        opponent = 'white' if player == 'black' else 'black'
        save_rack = board.get_save_rack(player)
        unentered_rack = board.get_unentered_rack(player)
        opponent_unentered = board.get_unentered_rack(opponent)

        # Precompute shortest routes for all pieces
        distances = {}
        for piece in board.pieces:
            distances[piece] = board.shortest_route_to_goal(piece)


        # Saved pieces and bonus
        saved_pieces = len(save_rack)
        saved_bonus = sum(self.weights['saved_bonuses'].get(piece.number, 0) for piece in save_rack)

        # Goal pieces and bonus
        goal_pieces = [piece for piece in board.pieces if piece.player == player and piece.can_be_saved()]
        goal_bonus = sum(self.weights['goal_bonuses'].get(piece.number, 0) for piece in goal_pieces if piece.number <= 6)

        # High goal penalty
        occupied_goals = [piece.tile for piece in goal_pieces if piece.tile and piece.number > 6]
        high_goal_penalty = sum(self.weights['goal_bonuses'].get(goal.number, 0) * self.weights['high_goal_penalty']
                                for goal in occupied_goals)

        # Pieces near goal and nearer goal with bonus
        board_pieces = [piece for piece in board.pieces if piece.player == player and piece.tile]
        pieces_near_goal = [piece for piece in board_pieces if 1 <= distances[piece] <= 6]
        pieces_nearer_goal = [piece for piece in board_pieces if piece.number > 6 and 1 <= distances[piece] <= 4]
        near_goal_bonus = sum(self.weights['near_goal_bonuses'].get(piece.number, 0) for piece in pieces_near_goal if piece.number <= 6)

        # Off-goal and far-from-goal penalties
        numbered_off_goal = [piece for piece in board.pieces if piece.player == player and piece.number <= 6 and not piece.can_be_saved()]
        off_goal_penalty = -sum(self.weights['goal_bonuses'].get(piece.number, 0) for piece in numbered_off_goal)
        numbered_far_from_goal = [piece for piece in numbered_off_goal if distances[piece] > 6 and piece.tile and piece.tile.type in ['field', 'save']]
        far_from_goal_penalty = -sum(self.weights['goal_bonuses'].get(piece.number, 0) for piece in numbered_far_from_goal)

        # Total distance component
        pieces_not_near_goal = [piece for piece in board.pieces if piece.player == player and distances[piece] > 6]
        total_distance = min(sum(distances[piece] for piece in pieces_not_near_goal), 100)
        total_distance += sum(self.weights['goal_bonuses'].get(piece.number, 0)
                            for piece in pieces_not_near_goal if piece.number <= 6) / 10

        # Blocked pieces bonus
        blocked_pieces = [piece for piece in board.pieces if piece.player == player and distances[piece] > 1000]
        blocked_piece_bonus = sum(self.weights['blocked_piece_penalties'].get(piece.number, 0)
                                for piece in blocked_pieces if piece.number <= 6)

        # Loose pieces bonus
        loose_pieces = [piece for piece in board_pieces if piece.tile.type == 'field' and len(piece.tile.pieces) == 1]
        loose_piece_bonus = sum(self.weights['loose_piece_penalties'].get(piece.number, 0)
                                for piece in loose_pieces if piece.number <= 6)
        opponent_board_pieces = (len([piece for piece in board.pieces if piece.player == opponent and piece.tile and piece.tile.type in ['field', 'home']])
                                + min(1, len(opponent_unentered)))
        loose_piece_bonus *= (opponent_board_pieces / 14)
        if board.game_stages[opponent] == 'endgame':
            loose_piece_bonus *= -1

        # Captured opponent pieces bonus
        captured_pieces = [piece for piece in board.pieces if piece.player == opponent and piece.tile and piece.tile.type == 'home']
        captured_bonus = sum(self.weights['captured_bonuses'].get(piece.number, 0)
                            for piece in captured_pieces if piece.number <= 6)

        # Game stage bonus
        game_stage = board.game_stages[player]
        game_stage_bonus = self.weights['game_stage_bonuses'].get(game_stage, 0)

        # Massive penalty for leaving a captured piece home
        penalty = 10000 if len([piece for piece in board.pieces if board.current_player == player and piece.player == player and piece.tile and piece.tile.type == 'home']) > 0 else 0

        score_components = {
            'saved_pieces': saved_pieces * self.weights['saved_piece'],
            'saved_bonus': saved_bonus,
            'goal_pieces': len(goal_pieces) * self.weights['goal_piece'],
            'goal_bonus': goal_bonus,
            'captured_pieces': len(captured_pieces) * self.weights['captured_opponent_piece'],
            'captured_bonus': captured_bonus,
            'pieces_near_goal': len(pieces_near_goal) * self.weights['near_goal_piece'],
            'pieces_nearer_goal': len(pieces_nearer_goal) * self.weights['nearer_goal_piece'],
            'near_goal_bonus': near_goal_bonus,
            'blocked_pieces': len(blocked_pieces) * self.weights['blocked_piece'],
            'blocked_piece_bonus': blocked_piece_bonus,
            'loose_pieces': len(loose_pieces) * self.weights['loose_piece'],
            'loose_piece_bonus': loose_piece_bonus,
            'total_distance': total_distance * self.weights['distance_penalty'],
            'unentered_pieces': len(unentered_rack) * self.weights['unentered_piece'],
            'off_goal_penalty': off_goal_penalty,
            'far_from_goal_penalty': far_from_goal_penalty,
            'high_goal_penalty': high_goal_penalty,
            'game_stage_bonus': game_stage_bonus
        }
        total_score = sum(score_components.values()) - penalty
        score_components['_total_score'] = total_score
        score_components['_player'] = player
        score_components['_goal_pieces'] = [(piece.number, piece.player, board.shortest_route_to_goal(piece)) for piece in pieces_near_goal]

        return total_score, score_components


    def evaluate(self, board, player):
        winner, score = board.check_game_over()
        if winner:
            factor = 1 if winner == player else -1
            return factor * score * GAME_OVER_SCORE, {}

        player_eval, player_components = self.evaluate_player(board, player)
        opponent = 'white' if player == 'black' else 'black'
        opponent_eval, opponent_components = self.evaluate_player(board, opponent)

        total_score = player_eval - opponent_eval
        score_components = {
            'player': player_components,
            'opponent': opponent_components,
            'total_score': f'{player}: {player_eval} - {opponent_eval} = {total_score}'
        }

        return total_score, score_components

    def select_move_pair(self, moves, board, player):
        move_scores = dict()

        # Ensure moves is a set and does not contain integers
        if not isinstance(moves, (list, set)) or not all(isinstance(m, tuple) for m in moves):
            raise ValueError('Invalid moves format: expected a list or set of tuples.')

        # Evaluate the pass move
        move_scores[((0, 0, 0), (0, 0, 0))] = self.evaluate(board, player)

        # Create a set of moves without the pass move
        moves = set(moves)
        moves.discard((0, 0, 0))

        for move in moves:
            if not isinstance(move, tuple) or len(move) != 3:
                raise ValueError('Invalid move format: each move should be a tuple of length 3.')

            board.apply_move(move, switch_turn = False)
            move_scores[(move, (0, 0, 0))] = self.evaluate(board, player)  # make one move then pass
            next_moves = set(board.get_valid_moves())
            if not next_moves:
                continue
            next_moves.discard((0, 0, 0))

            for next_move in next_moves:
                if not isinstance(next_move, tuple) or len(next_move) != 3:
                    raise ValueError('Invalid next move format: each move should be a tuple of length 3.')

                board.apply_move(next_move, switch_turn = False)
                move_scores[(move, next_move)] = self.evaluate(board, player)
                board.undo_last_move()

            board.undo_last_move()

        best_move_pair = max(move_scores, key=lambda k: move_scores[k][0])
        best_move_score, best_move_components = move_scores[best_move_pair]

        self.log.append({
            'move': best_move_pair,
            'score': best_move_score,
            'components': best_move_components
        })

        if LOG_TO_FILE:
            with open(self.log_file, 'w') as file:
                file.write(json.dumps(self.log, indent=4))
            print(f"Log updated with move: {best_move_pair}")

        print(best_move_components)

        return best_move_pair



    def save_log_to_file(self):
        return json.dumps(self.log, indent=4)


# agent tried to save a numbered piece when it wasn't in the midgame (but was one piece away from midgame)
# agent doesn't bring out its second captured piece but passes instead
# in endgame agent tries to save a piece that can't be saved when it can save a piece on a lower goal
# add "distance from endgame bonus"