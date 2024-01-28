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
        self.initialise_deck(num_players, self.deck)
        self.distribute_cards(self.deck, self.player_hands)

    def initialise_deck(self, num_players, deck):
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
    def distribute_cards(self, deck, player_hands):
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
        print(f"Sending message: {message}")
        serialized_message = (json.dumps(message) + "\n").encode('utf-8')
        conn.sendall(serialized_message)
        print("Send message successfully")
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")


def handle_player_connection(conn, player_id, game_manager, token_manager):
    while not game_manager.is_game_over(token_manager):
        if game_manager.current_player == player_id:
            # 发送手牌信息给另一玩家
            next_player_id = (player_id + 1) % game_manager.num_players
            print(f"Player1: {game_manager.player_hands[f'Player 1']}")
            print(f"Player2: {game_manager.player_hands[f'Player 2']}")
            print(f"Sending hand to Player {next_player_id+1}: {game_manager.player_hands[f'Player {player_id+1}']}")
            send_message(conn, {'action': 'give_info', 'hand': game_manager.player_hands[f'Player {player_id+1}'], 'recipient': next_player_id})
            print(f"Waiting for action from Player {next_player_id+1}...")

            response = conn.recv(4096).decode('utf-8')
            print(f"Received action from Player {next_player_id+1}: {response}")

            try:
                parsed_response = json.loads(response)

                if parsed_response and parsed_response['action'] == 'give_info':
                    consume = parsed_response['consume']
                    if consume and token_manager.info_tokens > 0:
                        info_statu = token_manager.use_info_token
                        print(f"Info token available status: {info_statu}")
                    else:
                        print(f"There's no info to Player {player_id+1}")

            except json.JSONDecodeError as e:
                print(f"Error decoding action: {e}")
                send_message(conn, {'error': f"Invalid action format: {action_str}", 'recipient': next_player_id})


            # 向客户端发送指示需要出牌的消息
            send_message(conn, {'action_required': 'play_card', 'recipient': player_id})

            # 接收玩家动作
            action_str = conn.recv(4096).decode('utf-8')
            print(f"Received action from Player {player_id+1}: {action_str}")

            try:
                action = json.loads(action_str)
                if action and action['action'] == 'play_card':
                    card_index = action['card_index']
                    chosen_card = game_manager.player_hands[f'Player {player_id+1}'][card_index]
                    play_successful = game_manager.play_card(chosen_card, game_manager.player_hands[f'Player {player_id+1}'], token_manager)
                    
                    # 发一张新牌给玩家
                    game_manager.deal_card(game_manager.player_hands[f'Player {player_id+1}'])
                    played_pile = game_manager.played_cards
                    send_message(conn, {'played_pile': played_pile, 'play_successful': play_successful, 'recipient': player_id})
                    send_message(conn, {'played_pile': played_pile, 'play_successful': play_successful, 'recipient': next_player_id})

            except json.JSONDecodeError as e:
                print(f"Error decoding action: {e}")
                send_message(conn, {'error': f"Invalid action format: {action_str}", 'recipient': player_id})
            # 更新当前玩家
            game_manager.current_player = (game_manager.current_player + 1) % game_manager.num_players
            print(f"Current player: Player {game_manager.current_player+1}")
    # 游戏结束，发送结果给所有玩家
    send_message(conn, {'game_over': True, 'game_won': game_manager.is_game_win(), 'recipient': player_id})
    send_message(conn, {'game_over': True, 'game_won': game_manager.is_game_win(), 'recipient': next_player_id})



def main():
    host = 'localhost'
    port = 8888

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
        threads = []

        # 等待两个玩家连接
        for player_id in range(num_players):
            conn, _ = s.accept()
            connections.append(conn)
            thread = threading.Thread(target=handle_player_connection, args=(conn, player_id, game_manager, token_manager))
            threads.append(thread)
            thread.start()

        # 等待所有线程结束
        for thread in threads:
            thread.join()

if __name__ == "__main__":
    main()
