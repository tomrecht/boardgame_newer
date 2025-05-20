import os
import copy
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from game import Board
from agent import Agent

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)
CORS(app)

board = Board()
agent = Agent()

@app.route('/select_moves', methods=['POST'])
def select_moves():
    try:
        state = request.json
        board.update_state(state)
        moves = board.get_valid_moves(mask_offgoals=True)
        if moves:
            chosen = agent.select_move_pair(moves, board, board.current_player)
            return jsonify({"move": chosen}), 200
        return jsonify({"message": "No valid moves"}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 500

@app.route('/evaluate_board', methods=['POST'])
def evaluate_board():
    try:
        state = request.json
        newb = copy.deepcopy(board)
        newb.update_state(state)
        _, val = agent.evaluate(newb, newb.current_player)
        return jsonify({"eval": val}), 200
    except Exception as e:
        logger.error(e)
        return jsonify({"error": str(e)}), 500

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve(path):
    return send_from_directory(BASE_DIR, path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
