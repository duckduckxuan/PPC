import random
import socket
import json
import threading

# Manage status of info tokens and fuse tokens
class TokenManager:
    def __init__(self, num_players):
        self.info_tokens = num_players + 3
        self.fuse_tokens = 3

    def use_info_token(self):
        if self.info_tokens > 0:
            self.info_tokens -= 1
            return True
        return False

    def get_info_token(self, num_players):
        # Maximum number of info tokens: initial number + number of card colors
        if self.info_tokens < 2 * num_players + 3:
            self.info_tokens += 1

    def use_fuse_token(self):
        if self.fuse_tokens > 0:
            self.fuse_tokens -= 1
            return self.fuse_tokens > 0
        return False

    # All fuse tokens are used -> fail
    def is_game_fail(self):
        return self.fuse_tokens == 0
    

# Manage the process of game
class GameManager:
    def __init__(self, num_players):
        self.deck = []
        self.num_players = num_players
        self.current_player = 0
        self.played_cards = {color: [] for color in ['Red', 'Blue', 'Green', 'Yellow', 'Purple'][:num_players]}
        self.discarded_cards = []
        self.player_hands = {f'Player {i+1}': [] for i in range(num_players)}

    def initialise_deck(num_players, deck):
        # Define card colors
        colors = ['Red', 'Blue', 'Green', 'Yellow', 'Purple'][:num_players]

        # Generate cards
        for color in colors:
            deck.extend([color + ' 1'] * 3)  # three cards 1
            deck.extend([color + ' 2'] * 2)  # two cards 2
            deck.extend([color + ' 3'] * 2)  # three cards 3
            deck.extend([color + ' 4'] * 2)  # four cards 4
            deck.append(color + ' 5')        # one card 5

        random.shuffle(deck)  # Shuffle cards in the deck
        return deck

    # Distribute 5 cards to each player
    def distribute_cards(deck, player_hands):
        for _ in range(5):
            for player in player_hands:
                card = deck.pop()  # Delete distributed card from deck
                player_hands[player].append(card)
        return player_hands

    # Every turn of game distribute a card to each player
    def deal_card(self, player_handcard):
        if self.deck:
            card = self.deck.pop()
            player_handcard.append(card)
            return card
        return None

    # A player's turn
    def play_card(self, card, player_handcard, token_manager):
        color, number = card.split()
        number = int(number)
        
        # Check if the card can be successfully played
        if self.can_play_card(color, number):
            self.played_cards[color].append(number)
            player_handcard.remove(card)

            # Check if it's a 5 to add an info token
            if number == 5:
                token_manager.get_info_token(self.num_players)
            return True
        
        # Discard this card and use a fuse token
        else:
            player_handcard.remove(card)
            self.discarded_cards.append(card)
            token_manager.use_fuse_token()
            return False

    # Conditions of playing a card successfully
    def can_play_card(self, color, number):
        if number == 1 and len(self.played_cards[color]) == 0:
            return True
        if number > 1 and self.played_cards[color] and number == self.played_cards[color][-1] + 1:
            return True
        return False

    # All cards 5 are played -> win
    def is_game_win(self):
        return all(5 in self.played_cards[color] for color in self.played_cards)

    # Game is over if all fuse tokens are used or all cards 5 are played
    def is_game_over(self, token_manager):
        return token_manager.is_game_fail() or self.is_game_win()





# Network communication functions
def send_message(conn, message):
    try:
        serialized_message = json.dumps(message).encode('utf-8')
        conn.sendall(serialized_message)
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")

def receive_message(conn):
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        if data:
            return json.loads(data.decode('utf-8'))
        else:
            # Connection closed
            return None
    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
        return None
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

def handle_player_connection(conn, player_hands, player_id, game_manager, token_manager):
    while not game_manager.is_game_over(token_manager):
        if game_manager.current_player == player_id:
            # 发送手牌信息给当前玩家
            send_message(conn, game_manager.player_hands[f'Player {player_id+1}'])

            # 接收玩家动作
            action = receive_message(conn)
            if action['action'] == 'play_card':
                card_index = action['card_index']
                chosen_card = player_hands[card_index]
                play_successful = game_manager.play_card(chosen_card, player_hands, token_manager)
                
                # 发一张新牌给玩家
                new_card = game_manager.deal_card(player_hands[f'Player {player_id+1}'])
                send_message(conn, {'play_successful': play_successful, 'new_hand': player_hands})

            # 更新当前玩家
            game_manager.current_player = (game_manager.current_player + 1) % game_manager.num_players

    # 游戏结束，发送结果给所有玩家
    send_message(conn, {'game_over': True, 'game_won': game_manager.is_game_win()})


def main():
    host = 'localhost'  # Adjust as needed
    port = 12345        # Adjust as needed

    # 初始化游戏管理器等
    num_players = 2  # 假设有两名玩家
    game_manager = GameManager(num_players)
    token_manager = TokenManager(num_players)

    # 设置套接字等待玩家连接
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print("Waiting for player connection...")
        connections = []

        # 等待两个玩家连接
        for player_id in range(2):
            conn, _ = s.accept()
            connections.append(conn)
            threading.Thread(target=handle_player_connection, args=(conn, game_manager.player_hands, player_id, game_manager, token_manager)).start()

        # 等待所有线程结束
        for conn in connections:
            conn.join()

if __name__ == "__main__":
    main()