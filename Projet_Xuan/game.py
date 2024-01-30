import random
import socket
import json
from multiprocessing import Process
import time
import sysv_ipc

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





# Send messages to client
def send_message(conn, message):
    try:
        print(f"Sending message: {message}")
        serialized_message = (json.dumps(message)).encode('utf-8')
        conn.sendall(serialized_message)
        print("Send message successfully")
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")

# Logic of the game
def handle_player_connection(conn, player_id, game_manager, token_manager, shm):
    while not game_manager.is_game_over(token_manager):
        shm.write(f"Rest info token: {token_manager.info_tokens}\nRest fuse token: {token_manager.fuse_tokens}".encode())
        time.sleep(1)
        shm.remove()

        if game_manager.current_player == player_id:
            # Send a message to the player who plays card
            send_message(conn, {'action_required': 'play_card'})

            # Receive player's action
            action_str = conn.recv(4096).decode('utf-8')
            print(f"Received action from Player {player_id+1}: {action_str}")

            try:
                action = json.loads(action_str)
                if action and action['action'] == 'play_card':
                    card_index = action['card_index']
                    chosen_card = game_manager.player_hands[f'Player {player_id+1}'][card_index]
                    play_successful = game_manager.play_card(chosen_card, game_manager.player_hands[f'Player {player_id+1}'], token_manager)
                    
                    # Distribute a new card to player
                    game_manager.deal_card(game_manager.player_hands[f'Player {player_id+1}'])
                    played_pile = game_manager.played_cards
                    send_message(conn, {'played_pile': played_pile, 'play_successful': play_successful})

            except json.JSONDecodeError as e:
                print(f"Error decoding action: {e}")
                send_message(conn, {'error': f"Invalid action format: {action_str}"})

            # Update players' infomation
            game_manager.current_player = (game_manager.current_player + 1) % game_manager.num_players
            print(f"Current player: Player {game_manager.current_player+1}")

        else:
            # Find the other player's ID
            next_player_id = (player_id + 1) % game_manager.num_players
            print(f"Sending hand to Player {player_id+1}: {game_manager.player_hands[f'Player {next_player_id+1}']}")

            # Send a message to the player who gives infomation to the other
            send_message(conn, {'hand': game_manager.player_hands[f'Player {next_player_id+1}'], 'action': 'give_info'})
            print(f"Waiting for action give_info from Player {player_id+1}...")

            # Receive player's action
            response = conn.recv(4096).decode('utf-8')
            print(f"Received action give_info from Player {player_id+1}: {response}")


            try:
                parsed_response = json.loads(response)
                if parsed_response and parsed_response['action'] == 'give_info':
                    consume = parsed_response['consume']
                    if consume and token_manager.info_tokens > 0:
                        info_statu = token_manager.use_info_token
                        print(f"Info token available status: {info_statu}")
                    else:
                        print(f"There's no info to Player {next_player_id+1}")

            except json.JSONDecodeError as e:
                print(f"Error decoding action: {e}")
                send_message(conn, {'error': f"Invalid action format: {response}"})

    # Game over, send result to player
    send_message(conn, {'game_over': True, 'game_won': game_manager.is_game_win()})


def main():
    host = 'localhost'
    port = 12345

    num_players = 2
    game_manager = GameManager(num_players)
    token_manager = TokenManager(num_players)

    shm = sysv_ipc.SharedMemory(888, sysv_ipc.IPC_CREAT, size=1024)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print("Waiting for player connection...")

        connections = []
        processes = []
        connected_players = 0

        while connected_players < num_players:
            conn, _ = s.accept()
            connections.append(conn)
            connected_players += 1
            print(f"Player {connected_players} connected.")

        for player_id in range(num_players):
            p = Process(target=handle_player_connection, args=(connections[player_id], player_id, game_manager, token_manager, shm))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()


if __name__ == "__main__":
    main()
