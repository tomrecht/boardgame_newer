import unittest
from game import Board, Piece, Tile, Die, NUM_PIECES

class TestGameLogic(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.board = Board()
        # Helper to quickly find tiles, assuming they are loaded from json
        self.save_tiles = {t.number: t for t in self.board.tiles if t.type == 'save' and t.number is not None}
        self.field_tiles = [t for t in self.board.tiles if t.type == 'field']
        if not self.field_tiles: # Ensure there's at least one field tile for placing pieces
            # Add a generic field tile if none are loaded (shouldn't happen with tile_neighbors.json)
            self.board.add_tile(Tile('field', 1, 0, self.board)) # Ring 1, Sector 0
            self.field_tiles = [t for t in self.board.tiles if t.type == 'field']


    def _get_player_piece(self, player_name, piece_identifier, by_id=False):
        """Helper to get a specific piece for a player by number or ID."""
        for piece in self.board.pieces:
            if piece.player == player_name:
                if by_id and piece.id == piece_identifier:
                    return piece
                elif not by_id and piece.number == piece_identifier: # Find by number
                    return piece
        return None

    def _create_and_place_piece(self, player_name, number, tile, piece_id=None):
        """Creates a piece, assigns an ID, adds to board.pieces, and places it."""
        if piece_id is None:
            piece_id = self.board.next_piece_id
            self.board.next_piece_id += 1
        
        piece = Piece(player_name, number, self.board, piece_id)
        
        # Ensure piece is tracked by the board
        # Remove if already exists by ID (e.g. re-creating for a test)
        self.board.pieces = [p for p in self.board.pieces if p.id != piece.id]
        self.board.pieces.append(piece)

        self._place_piece_on_tile(piece, tile)
        return piece

    def _place_piece_on_tile(self, piece, tile):
        """Helper to place a piece on a tile, removing from old location."""
        if piece.tile and piece.tile.pieces and piece in piece.tile.pieces:
            piece.tile.pieces.remove(piece)
        
        if piece.rack: 
            if piece in piece.rack:
                 piece.rack.remove(piece)
            piece.rack = None

        piece.tile = tile
        if tile:
            if piece not in tile.pieces: # Avoid duplicates if already there
                tile.pieces.append(piece)
        else: # Piece is removed from board (e.g. going to a rack conceptually, or just off-board)
            piece.tile = None


    def _clear_player_pieces_from_board_and_racks(self, player_name):
        """Clears pieces for a player to allow specific test setups."""
        # Remove from tiles
        for tile in self.board.tiles:
            tile.pieces = [p for p in tile.pieces if p.player != player_name]

        # Remove from board's main list
        self.board.pieces = [p for p in self.board.pieces if p.player != player_name]
        
        # Clear from racks
        if player_name == 'white':
            self.board.white_unentered.clear()
            self.board.white_saved.clear()
        else: # black
            self.board.black_unentered.clear()
            self.board.black_saved.clear()
        
        # Note: This doesn't reset self.board.next_piece_id to avoid ID clashes
        # if pieces are re-added without specific ID management in tests.
        # Tests creating pieces should use _create_and_place_piece or manage IDs.

    def test_piece_initialization_unique_ids(self):
        expected_next_id = 1 + (NUM_PIECES * len(self.board.players))
        self.assertEqual(self.board.next_piece_id, expected_next_id)
        piece_ids = set()
        for piece in self.board.pieces:
            self.assertIsNotNone(piece.id)
            self.assertGreaterEqual(piece.id, 1) 
            self.assertLess(piece.id, expected_next_id) 
            self.assertNotIn(piece.id, piece_ids)
            piece_ids.add(piece.id)
        self.assertEqual(len(piece_ids), len(self.board.pieces))
        self.assertEqual(len(self.board.pieces), NUM_PIECES * len(self.board.players))

    def test_update_state_piece_ids(self):
        board = Board() 
        game_state_details = {
            'currentTurn': 'white',
            'dice': [{'value': 1, 'used': False}, {'value': 2, 'used': False}],
            'racks': {
                'whiteUnentered': [{'id': 101, 'number': 1, 'color': 'white'}],
                'whiteSaved': [{'id': 102, 'number': 2, 'color': 'white'}],
                'blackUnentered': [{'id': 201, 'number': 1, 'color': 'black'}],
                'blackSaved': [{'id': 202, 'number': 2, 'color': 'black'}]
            },
            'boardPieces': [
                {'id': 103, 'number': 3, 'color': 'white', 'tile': {'ring': 1, 'sector': 1}},
                {'id': 203, 'number': 3, 'color': 'black', 'tile': {'ring': 1, 'sector': 2}}
            ]
        }
        if not board.get_tile(1,1): board.add_tile(Tile('field', 1, 1, board))
        if not board.get_tile(1,2): board.add_tile(Tile('field', 1, 2, board))
        board.update_state(game_state_details)
        self.assertEqual(board.white_unentered[0].id, 101)
        self.assertEqual(board.white_saved[0].id, 102)
        self.assertEqual(board.black_unentered[0].id, 201)
        self.assertEqual(board.black_saved[0].id, 202)
        board_piece_ids_on_tiles = {p.id for p in board.pieces if p.tile is not None}
        self.assertIn(103, board_piece_ids_on_tiles)
        self.assertIn(203, board_piece_ids_on_tiles)
        all_loaded_ids = [101, 102, 201, 202, 103, 203]
        expected_next_id = max(all_loaded_ids) + 1
        self.assertEqual(board.next_piece_id, expected_next_id)

    def test_unnumbered_piece_can_be_saved(self):
        player = self.board.current_player
        unnumbered_piece = self._create_and_place_piece(player, 0, None)
        save_tile = self.save_tiles.get(list(self.save_tiles.keys())[0])
        self.assertIsNotNone(save_tile)
        non_save_tile = self.field_tiles[0]
        self.assertIsNotNone(non_save_tile)
        self._place_piece_on_tile(unnumbered_piece, save_tile)
        self.assertTrue(unnumbered_piece.can_be_saved())
        self._place_piece_on_tile(unnumbered_piece, non_save_tile)
        self.assertFalse(unnumbered_piece.can_be_saved())
        self._place_piece_on_tile(unnumbered_piece, None)

    def test_get_saving_die_unnumbered_midgame(self):
        player = 'white'
        self.board.current_player = player
        self.board.game_stages[player] = 'midgame'
        piece = self._create_and_place_piece(player, 0, None)
        save_tile_3 = self.save_tiles.get(3)
        self.assertIsNotNone(save_tile_3)
        self._place_piece_on_tile(piece, save_tile_3)
        self.board.dice[0].number = 3; self.board.dice[0].used = False
        self.board.dice[1].number = 4; self.board.dice[1].used = False
        self.assertEqual(self.board.get_saving_die(piece), 3)
        self.board.dice[0].number = 4; self.board.dice[1].number = 5
        self.assertFalse(self.board.get_saving_die(piece))
        self._place_piece_on_tile(piece, None)

    def test_get_saving_die_unnumbered_endgame_exact_roll(self):
        player = 'white'
        self.board.current_player = player
        self.board.game_stages[player] = 'endgame'
        piece = self._create_and_place_piece(player, 0, None)
        save_tile_3 = self.save_tiles.get(3)
        self.assertIsNotNone(save_tile_3)
        self._place_piece_on_tile(piece, save_tile_3)
        self.board.dice[0].number = 3; self.board.dice[0].used = False
        self.board.dice[1].number = 4; self.board.dice[1].used = False
        self.assertEqual(self.board.get_saving_die(piece), 3)
        self._place_piece_on_tile(piece, None)

    def test_endgame_rule_piece_becomes_unnumbered(self):
        player_name = 'white'
        self.board.current_player = player_name
        self.board.game_stages[player_name] = 'endgame'
        self._clear_player_pieces_from_board_and_racks(player_name)

        # Ensure no unentered pieces for this player
        if player_name == 'white': self.board.white_unentered.clear()
        else: self.board.black_unentered.clear()


        p3 = self._create_and_place_piece(player_name, 3, self.field_tiles[0])
        p5 = self._create_and_place_piece(player_name, 5, self.field_tiles[1])
        p6 = self._create_and_place_piece(player_name, 6, self.field_tiles[2])
        
        # Verify all are numbered and on field tiles (unsaved)
        self.assertTrue(all(p.number != 0 for p in [p3, p5, p6]))
        self.assertTrue(all(p.tile is not None and p.tile.type == 'field' for p in [p3, p5, p6]))

        self.board.apply_move((0, 0, 0)) # Pass move

        self.assertEqual(p6.number, 0, "Highest piece (6) should become unnumbered (0).")
        self.assertEqual(p5.number, 5, "Piece 5 should retain its number.")
        self.assertEqual(p3.number, 3, "Piece 3 should retain its number.")
        # The rule should have re-evaluated the game stage.
        # Depending on whether p6 becoming unnumbered makes all pieces saveable, it might stay endgame or revert.
        # For this test, we mainly care that the number changed.
        # self.assertEqual(self.board.game_stages[player_name], 'endgame') # Or 'midgame'

    def test_no_save_moves_in_opening_stage(self):
        player_name = 'white'
        self.board.current_player = player_name
        self._clear_player_pieces_from_board_and_racks(player_name)
        
        # Re-initialize to get pieces in unentered racks, ensuring 'opening' stage
        # Board.initialize_pieces() is complex, so manually set up one piece in unentered
        # and one to test on a save tile.
        
        # Piece that stays in unentered rack to ensure 'opening' stage
        unentered_id = self.board.next_piece_id; self.board.next_piece_id += 1
        unentered_piece = Piece(player_name, 1, self.board, unentered_id)
        self.board.pieces.append(unentered_piece)
        self.board.white_unentered.append(unentered_piece)
        unentered_piece.rack = self.board.white_unentered
        
        self.board.game_stages[player_name] = self.board.get_game_stage(player_name)
        self.assertEqual(self.board.game_stages[player_name], 'opening')

        # Piece to test for saving
        piece_to_test_id = self.board.next_piece_id; self.board.next_piece_id += 1
        piece_to_test = Piece(player_name, 3, self.board, piece_to_test_id)
        self.board.pieces.append(piece_to_test)
        
        save_tile_3 = self.save_tiles.get(3)
        self.assertIsNotNone(save_tile_3, "Save tile 3 not found.")
        self._place_piece_on_tile(piece_to_test, save_tile_3)

        self.board.dice[0].number = 3; self.board.dice[0].used = False
        self.board.dice[1].number = 1; self.board.dice[1].used = False

        valid_moves = self.board.get_valid_moves()
        found_save_move = any(move[0] == piece_to_test.id and move[1] == 'save' for move in valid_moves)
        self.assertFalse(found_save_move, "Save move should not be available in opening stage.")

    def test_get_saving_die_unnumbered_endgame_higher_roll_logic(self):
        player_name = 'white'
        self.board.current_player = player_name
        self.board.game_stages[player_name] = 'endgame'
        self._clear_player_pieces_from_board_and_racks(player_name)
        
        save_tile_3 = self.save_tiles.get(3)
        self.assertIsNotNone(save_tile_3)
        save_tile_5 = self.save_tiles.get(5)
        self.assertIsNotNone(save_tile_5)

        u1 = self._create_and_place_piece(player_name, 0, save_tile_3) # Unnumbered on save tile 3

        # Scenario 1: Blocked by higher occupied goal
        n1 = self._create_and_place_piece(player_name, 5, save_tile_5) # Numbered piece on save tile 5
        self.board.dice[0].number = 4; self.board.dice[0].used = False
        self.board.dice[1].number = 2; self.board.dice[1].used = False
        self.assertFalse(self.board.get_saving_die(u1), 
                         "S1: Should be False. U1 on ST3 (val 3), N1 on ST5 (val 5). HOGN=5. Dice 4,2. Roll 4 > 3 but 3 < HOGN(5).")

        # Scenario 2: Higher roll allowed (N1 removed)
        self._place_piece_on_tile(n1, None) # Move N1 off ST5
        self.board.pieces = [p for p in self.board.pieces if p.id != n1.id] # Remove N1 from board.pieces
        
        self.board.dice[0].number = 4; self.board.dice[0].used = False
        self.board.dice[1].number = 2; self.board.dice[1].used = False
        # Now HOGN for u1 on ST3 would be 3 (from u1 itself, or 0 if no other pieces).
        # get_saving_die logic: die(4) > tile(3) AND tile(3) >= HOGN(3, or 0 if u1 is only one). This should be true.
        self.assertEqual(self.board.get_saving_die(u1), 4,
                         "S2: Should be 4. U1 on ST3. N1 removed. Dice 4,2. HOGN based on U1 or 0. Roll 4 is valid.")

        # Scenario 3: Exact roll preferred
        self.board.dice[0].number = 3; self.board.dice[0].used = False
        self.board.dice[1].number = 4; self.board.dice[1].used = False
        self.assertEqual(self.board.get_saving_die(u1), 3,
                         "S3: Should be 3. U1 on ST3. N1 removed. Dice 3,4. Exact roll 3 preferred.")

        # Scenario 4: No valid roll
        self.board.dice[0].number = 2; self.board.dice[0].used = False
        self.board.dice[1].number = 1; self.board.dice[1].used = False
        self.assertFalse(self.board.get_saving_die(u1),
                         "S4: Should be False. U1 on ST3. N1 removed. Dice 2,1. No valid roll.")

if __name__ == '__main__':
    unittest.main()
