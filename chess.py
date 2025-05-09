import pygame
import copy
import sys
from enum import Enum, auto

# Initialize pygame
pygame.init()

# Constants
BOARD_SIZE = 8
SQUARE_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * SQUARE_SIZE
IMAGES = {}

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_SQUARE = (118, 150, 86)
LIGHT_SQUARE = (238, 238, 210)
HIGHLIGHT = (186, 202, 68)
MOVE_HIGHLIGHT = (119, 149, 86, 150)  # Green with transparency

class PieceType(Enum):
    KING = auto()
    QUEEN = auto()
    ROOK = auto()
    BISHOP = auto()
    KNIGHT = auto()
    PAWN = auto()

class PieceColor(Enum):
    WHITE = auto()
    BLACK = auto()

class GameState(Enum):
    ACTIVE = auto()
    CHECK = auto()
    CHECKMATE = auto()
    STALEMATE = auto()

class Move:
    def __init__(self, start_pos, end_pos, piece_moved, piece_captured=None, is_castle=False, 
                is_promotion=False, is_en_passant=False, promotion_piece=None):
        self.start_row, self.start_col = start_pos
        self.end_row, self.end_col = end_pos
        self.piece_moved = piece_moved
        self.piece_captured = piece_captured
        self.is_castle = is_castle
        self.is_promotion = is_promotion
        self.is_en_passant = is_en_passant
        self.promotion_piece = promotion_piece

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            # piece_moved and piece_captured are Piece objects, which already have custom __deepcopy__
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class Piece:
    def __init__(self, color, piece_type):
        self.color = color
        self.piece_type = piece_type
        self.has_moved = False
        self.image = None
        self.load_image()
        
    def load_image(self):
        color_str = "w" if self.color == PieceColor.WHITE else "b"
        piece_str = ""
        
        if self.piece_type == PieceType.KING:
            piece_str = "k"
        elif self.piece_type == PieceType.QUEEN:
            piece_str = "q"
        elif self.piece_type == PieceType.ROOK:
            piece_str = "r"
        elif self.piece_type == PieceType.BISHOP:
            piece_str = "b"
        elif self.piece_type == PieceType.KNIGHT:
            piece_str = "n"
        elif self.piece_type == PieceType.PAWN:
            piece_str = "p"
            
        piece_key = color_str + piece_str
        if piece_key not in IMAGES:
            try:
                IMAGES[piece_key] = pygame.transform.scale(
                    pygame.image.load(f"resources/{piece_key}.png"), 
                    (SQUARE_SIZE, SQUARE_SIZE)
                )
            except:
                # Create a basic shape if image not found
                surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                color = WHITE if self.color == PieceColor.WHITE else BLACK
                pygame.draw.circle(surf, color, (SQUARE_SIZE//2, SQUARE_SIZE//2), SQUARE_SIZE//3)
                IMAGES[piece_key] = surf
                
        self.image = IMAGES[piece_key]
    
    def get_possible_moves(self, board, position, for_attack=False):
        # This method should be overridden by specific piece classes
        return []
    
    def is_valid_move(self, board, start_pos, end_pos):
        # Check if the move is in the list of possible moves
        possible_moves = self.get_possible_moves(board, start_pos)
        return end_pos in [(move.end_row, move.end_col) for move in possible_moves]

    def __deepcopy__(self, memo):
        # Create a new instance without calling __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        
        # Only copy essential attributes
        result.color = self.color
        result.piece_type = self.piece_type
        result.has_moved = self.has_moved
        result.image = self.image  # Shallow copy for image
        
        return result

class King(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.KING)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dr, dc in directions:
            end_row, end_col = row + dr, col + dc
            if 0 <= end_row < BOARD_SIZE and 0 <= end_col < BOARD_SIZE:
                end_piece = board.get_piece((end_row, end_col))
                if end_piece is None or end_piece.color != self.color:
                    moves.append(Move((row, col), (end_row, end_col), self, end_piece))
        
        # Only add castling moves if not for attack
        if not for_attack and not self.has_moved and not board.is_in_check(self.color):
            # Kingside castle
            if (board.get_piece((row, col+1)) is None and 
                board.get_piece((row, col+2)) is None and 
                isinstance(board.get_piece((row, col+3)), Rook) and 
                not board.get_piece((row, col+3)).has_moved):
                # Check if king passes through check
                if not board.is_position_under_attack((row, col+1), self.color) and not board.is_position_under_attack((row, col+2), self.color):
                    moves.append(Move((row, col), (row, col+2), self, is_castle=True))
            
            # Queenside castle
            if (board.get_piece((row, col-1)) is None and 
                board.get_piece((row, col-2)) is None and 
                board.get_piece((row, col-3)) is None and 
                isinstance(board.get_piece((row, col-4)), Rook) and 
                not board.get_piece((row, col-4)).has_moved):
                # Check if king passes through check
                if not board.is_position_under_attack((row, col-1), self.color) and not board.is_position_under_attack((row, col-2), self.color):
                    moves.append(Move((row, col), (row, col-2), self, is_castle=True))
        
        return moves

class Queen(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.QUEEN)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        
        # Queen moves like a rook and bishop combined
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dr, dc in directions:
            for i in range(1, BOARD_SIZE):
                end_row, end_col = row + dr * i, col + dc * i
                if not (0 <= end_row < BOARD_SIZE and 0 <= end_col < BOARD_SIZE):
                    break
                
                end_piece = board.get_piece((end_row, end_col))
                if end_piece is None:
                    moves.append(Move((row, col), (end_row, end_col), self))
                elif end_piece.color != self.color:
                    moves.append(Move((row, col), (end_row, end_col), self, end_piece))
                    break
                else:
                    break
                    
        return moves

class Rook(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.ROOK)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        
        # Rook moves horizontally and vertically
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for dr, dc in directions:
            for i in range(1, BOARD_SIZE):
                end_row, end_col = row + dr * i, col + dc * i
                if not (0 <= end_row < BOARD_SIZE and 0 <= end_col < BOARD_SIZE):
                    break
                
                end_piece = board.get_piece((end_row, end_col))
                if end_piece is None:
                    moves.append(Move((row, col), (end_row, end_col), self))
                elif end_piece.color != self.color:
                    moves.append(Move((row, col), (end_row, end_col), self, end_piece))
                    break
                else:
                    break
                    
        return moves

class Bishop(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.BISHOP)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        
        # Bishop moves diagonally
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        for dr, dc in directions:
            for i in range(1, BOARD_SIZE):
                end_row, end_col = row + dr * i, col + dc * i
                if not (0 <= end_row < BOARD_SIZE and 0 <= end_col < BOARD_SIZE):
                    break
                
                end_piece = board.get_piece((end_row, end_col))
                if end_piece is None:
                    moves.append(Move((row, col), (end_row, end_col), self))
                elif end_piece.color != self.color:
                    moves.append(Move((row, col), (end_row, end_col), self, end_piece))
                    break
                else:
                    break
                    
        return moves

class Knight(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.KNIGHT)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        
        # Knight L-shaped moves
        knight_moves = [
            (-2, -1), (-2, 1),
            (-1, -2), (-1, 2),
            (1, -2),  (1, 2),
            (2, -1),  (2, 1)
        ]
        
        for dr, dc in knight_moves:
            end_row, end_col = row + dr, col + dc
            if 0 <= end_row < BOARD_SIZE and 0 <= end_col < BOARD_SIZE:
                end_piece = board.get_piece((end_row, end_col))
                if end_piece is None:
                    moves.append(Move((row, col), (end_row, end_col), self))
                elif end_piece.color != self.color:
                    moves.append(Move((row, col), (end_row, end_col), self, end_piece))
                    
        return moves

class Pawn(Piece):
    def __init__(self, color):
        super().__init__(color, PieceType.PAWN)
        
    def get_possible_moves(self, board, position, for_attack=False):
        row, col = position
        moves = []
        
        # Direction based on pawn color
        direction = -1 if self.color == PieceColor.WHITE else 1
        
        # Forward one square
        if 0 <= row + direction < BOARD_SIZE:
            if board.get_piece((row + direction, col)) is None:
                # Check for promotion
                if (row + direction == 0 and self.color == PieceColor.WHITE) or (row + direction == 7 and self.color == PieceColor.BLACK):
                    # Add promotion moves for all possible pieces
                    for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                        moves.append(Move((row, col), (row + direction, col), self, is_promotion=True, promotion_piece=piece_type))
                else:
                    moves.append(Move((row, col), (row + direction, col), self))
                
                # Forward two squares from starting position
                start_row = 6 if self.color == PieceColor.WHITE else 1
                if row == start_row and board.get_piece((row + 2*direction, col)) is None:
                    moves.append(Move((row, col), (row + 2*direction, col), self))
        
        # Diagonal captures
        for dc in [-1, 1]:
            if 0 <= row + direction < BOARD_SIZE and 0 <= col + dc < BOARD_SIZE:
                end_piece = board.get_piece((row + direction, col + dc))
                if end_piece is not None and end_piece.color != self.color:
                    # Check for promotion
                    if (row + direction == 0 and self.color == PieceColor.WHITE) or (row + direction == 7 and self.color == PieceColor.BLACK):
                        for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                            moves.append(Move((row, col), (row + direction, col + dc), self, end_piece, is_promotion=True, promotion_piece=piece_type))
                    else:
                        moves.append(Move((row, col), (row + direction, col + dc), self, end_piece))
                
                # En passant
                if board.en_passant_target == (row, col + dc):
                    captured_pawn = board.get_piece((row, col + dc))
                    moves.append(Move((row, col), (row + direction, col + dc), self, captured_pawn, is_en_passant=True))
                    
        return moves

class Board:
    def __init__(self, setup=True):
        self.board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = PieceColor.WHITE
        self.game_state = GameState.ACTIVE
        self.move_history = []
        self.en_passant_target = None
        if setup:
            self.setup_board()
        
    def setup_board(self):
        # Setup pawns
        for col in range(BOARD_SIZE):
            self.board[1][col] = Pawn(PieceColor.BLACK)
            self.board[6][col] = Pawn(PieceColor.WHITE)
        
        # Setup other pieces
        back_row_order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, piece_class in enumerate(back_row_order):
            self.board[0][col] = piece_class(PieceColor.BLACK)
            self.board[7][col] = piece_class(PieceColor.WHITE)
    
    def get_piece(self, position):
        row, col = position
        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
            return self.board[row][col]
        return None
    
    def make_move(self, move, update_state=True):
        # Get the pieces
        piece = self.get_piece((move.start_row, move.start_col))
        
        # Check if it's a valid piece and player's turn
        if piece is None or piece.color != self.current_player:
            return False
        
        # For now, we'll implement a simplified version for testing
        if move.is_castle:
            # Kingside castle
            if move.end_col - move.start_col == 2:
                rook = self.get_piece((move.start_row, 7))
                self.board[move.start_row][5] = rook
                self.board[move.start_row][7] = None
                rook.has_moved = True
            # Queenside castle
            elif move.end_col - move.start_col == -2:
                rook = self.get_piece((move.start_row, 0))
                self.board[move.start_row][3] = rook
                self.board[move.start_row][0] = None
                rook.has_moved = True
        
        # Handle en passant capture
        if move.is_en_passant:
            self.board[move.start_row][move.end_col] = None
        
        # Move the piece
        self.board[move.start_row][move.start_col] = None
        
        # Handle promotion
        if move.is_promotion and move.promotion_piece:
            if move.promotion_piece == PieceType.QUEEN:
                self.board[move.end_row][move.end_col] = Queen(piece.color)
            elif move.promotion_piece == PieceType.ROOK:
                self.board[move.end_row][move.end_col] = Rook(piece.color)
            elif move.promotion_piece == PieceType.BISHOP:
                self.board[move.end_row][move.end_col] = Bishop(piece.color)
            elif move.promotion_piece == PieceType.KNIGHT:
                self.board[move.end_row][move.end_col] = Knight(piece.color)
        else:
            self.board[move.end_row][move.end_col] = piece
        
        # Update piece's move status
        piece.has_moved = True
        
        # Set en passant target if pawn moved two squares
        self.en_passant_target = None
        if isinstance(piece, Pawn) and abs(move.start_row - move.end_row) == 2:
            self.en_passant_target = (move.start_row + (1 if piece.color == PieceColor.BLACK else -1), move.start_col)
        
        # Add move to history
        self.move_history.append(move)
        
        # Switch player
        self.current_player = PieceColor.BLACK if self.current_player == PieceColor.WHITE else PieceColor.WHITE
        
        # Update game state
        if update_state:
            self.update_game_state()
        
        return True
    
    def is_position_under_attack(self, position, color):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece((row, col))
                if piece and piece.color != color:
                    # Pass for_attack=True to avoid recursion
                    moves = piece.get_possible_moves(self, (row, col), for_attack=True)
                    for move in moves:
                        if (move.end_row, move.end_col) == position:
                            return True
        return False
    
    def is_in_check(self, color):
        # Find the king
        king_position = None
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece((row, col))
                if piece and piece.color == color and piece.piece_type == PieceType.KING:
                    king_position = (row, col)
                    break
            if king_position:
                break
        
        # Check if the king is under attack
        if king_position:
            return self.is_position_under_attack(king_position, color)
        return False
    
    def update_game_state(self):
        # Check if current player is in check
        if self.is_in_check(self.current_player):
            self.game_state = GameState.CHECK
            
            # Check if it's checkmate (no valid moves)
            if self.is_checkmate():
                self.game_state = GameState.CHECKMATE
        else:
            self.game_state = GameState.ACTIVE
            
            # Check for stalemate
            if self.is_stalemate():
                self.game_state = GameState.STALEMATE
    
    def is_checkmate(self):
        return self.has_no_valid_moves()
    
    def is_stalemate(self):
        return self.has_no_valid_moves()
    
    def has_no_valid_moves(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece((row, col))
                if piece and piece.color == self.current_player:
                    moves = piece.get_possible_moves(self, (row, col))
                    for move in moves:
                        # Try the move and see if it gets us out of check
                        temp_board = self.copy()
                        temp_board.make_move(move, update_state=False)
                        if not temp_board.is_in_check(self.current_player):
                            return False
        return True
    
    def copy(self):
        new_board = Board(setup=False)
        new_board.board = copy.deepcopy(self.board)
        new_board.current_player = self.current_player
        new_board.game_state = self.game_state
        # Don't deep copy move history, just create a new empty list
        new_board.move_history = []
        new_board.en_passant_target = self.en_passant_target
        return new_board
    
    def get_valid_moves(self, position):
        piece = self.get_piece(position)
        if piece is None or piece.color != self.current_player:
            return []
        
        all_moves = piece.get_possible_moves(self, position)
        valid_moves = []
        
        for move in all_moves:
            # Try the move and see if it leaves the king in check
            temp_board = self.copy()
            temp_board.make_move(move, update_state=False)
            if not temp_board.is_in_check(self.current_player):
                valid_moves.append(move)
                
        return valid_moves

class ChessGame:
    def __init__(self):
        self.board = Board()
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Chess Game")
        self.selected_piece = None
        self.selected_pos = None
        self.valid_moves = []
        self.clock = pygame.time.Clock()
        self.is_promotion_menu_active = False
        self.promotion_move = None
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(event.pos)
            
            self.draw_board()
            self.draw_pieces()
            
            if self.selected_pos:
                self.highlight_selected()
                self.highlight_valid_moves()
            
            if self.is_promotion_menu_active:
                self.draw_promotion_menu()
            
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()
    
    def draw_board(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                pygame.draw.rect(self.screen, color, rect)
    
    def draw_pieces(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board.get_piece((row, col))
                if piece:
                    self.screen.blit(piece.image, pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    
    def highlight_selected(self):
        row, col = self.selected_pos
        rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        pygame.draw.rect(self.screen, HIGHLIGHT, rect, 4)
    
    def highlight_valid_moves(self):
        for move in self.valid_moves:
            end_row, end_col = move.end_row, move.end_col
            highlight_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surf.fill(MOVE_HIGHLIGHT)
            self.screen.blit(highlight_surf, (end_col * SQUARE_SIZE, end_row * SQUARE_SIZE))
    
    def handle_mouse_click(self, pos):
        if self.is_promotion_menu_active:
            self.handle_promotion_click(pos)
            return
            
        col = pos[0] // SQUARE_SIZE
        row = pos[1] // SQUARE_SIZE
        
        if self.selected_pos:  # A piece is already selected
            move_made = False
            for move in self.valid_moves:
                if (move.end_row, move.end_col) == (row, col):
                    if move.is_promotion:
                        self.promotion_move = move
                        self.is_promotion_menu_active = True
                        return
                    else:
                        self.board.make_move(move)
                        move_made = True
                        break
            
            if move_made:
                self.selected_pos = None
                self.valid_moves = []
            elif self.board.get_piece((row, col)) and self.board.get_piece((row, col)).color == self.board.current_player:
                self.selected_pos = (row, col)
                self.valid_moves = self.board.get_valid_moves(self.selected_pos)
            else:
                self.selected_pos = None
                self.valid_moves = []
        else:  # No piece selected yet
            piece = self.board.get_piece((row, col))
            if piece and piece.color == self.board.current_player:
                self.selected_pos = (row, col)
                self.valid_moves = self.board.get_valid_moves(self.selected_pos)
    
    def draw_promotion_menu(self):
        menu_width = SQUARE_SIZE * 4
        menu_height = SQUARE_SIZE
        menu_x = (WINDOW_SIZE - menu_width) // 2
        menu_y = (WINDOW_SIZE - menu_height) // 2
        
        # Draw background
        pygame.draw.rect(self.screen, WHITE, (menu_x, menu_y, menu_width, menu_height))
        pygame.draw.rect(self.screen, BLACK, (menu_x, menu_y, menu_width, menu_height), 2)
        
        # Draw piece options
        color = self.board.current_player
        pieces = [Queen(color), Rook(color), Bishop(color), Knight(color)]
        
        for i, piece in enumerate(pieces):
            x = menu_x + i * SQUARE_SIZE
            self.screen.blit(piece.image, (x, menu_y))
    
    def handle_promotion_click(self, pos):
        menu_width = SQUARE_SIZE * 4
        menu_height = SQUARE_SIZE
        menu_x = (WINDOW_SIZE - menu_width) // 2
        menu_y = (WINDOW_SIZE - menu_height) // 2
        
        if not (menu_x <= pos[0] <= menu_x + menu_width and menu_y <= pos[1] <= menu_y + menu_height):
            self.is_promotion_menu_active = False
            return
        
        piece_index = (pos[0] - menu_x) // SQUARE_SIZE
        promotion_pieces = [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]
        
        if 0 <= piece_index < len(promotion_pieces):
            self.promotion_move.promotion_piece = promotion_pieces[piece_index]
            self.board.make_move(self.promotion_move)
            self.is_promotion_menu_active = False
            self.selected_pos = None
            self.valid_moves = []

if __name__ == "__main__":
    game = ChessGame()
    game.run()