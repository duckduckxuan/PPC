import random
import multiprocessing

# Constants
NUM_COLORS = 2  # Red and Blue for 2 players
DECK = {'Red': [1, 1, 1, 2, 2, 3, 3, 4, 4, 5], 'Blue': [1, 1, 1, 2, 2, 3, 3, 4, 4, 5]}
INFO_TOKENS = 5  # Number of players + 3
FUSE_TOKENS = 3

def game_process(queue):
    # Initialize game state
    deck = {color: cards.copy() for color, cards in DECK.items()}
    random.shuffle(deck['Red'])
    random.shuffle(deck['Blue'])
    hands = [[], []]  # Two players
    played_cards = {'Red': [], 'Blue': []}
    info_tokens = INFO_TOKENS
    fuse_tokens = FUSE_TOKENS

    # Deal cards
    for _ in range(5):
        for hand in hands:
            hand.append(deck['Red'].pop() if len(deck['Red']) > len(deck['Blue']) else deck['Blue'].pop())

    # Game loop
    current_player = 0
    while True:
        # Send game state to players
        queue.put(('state', (played_cards, hands[1 - current_player], info_tokens, fuse_tokens)))

        # Wait for player action
        action, data = queue.get()
        if action == 'play':
            # Handle play card action
            pass  # Implement play card logic
        elif action == 'info':
            # Handle give information action
            pass  # Implement give information logic

        # Check for game end
        pass  # Implement game end check

        # Switch to next player
        current_player = 1 - current_player

def player_process(player_id, queue):
    while True:
        # Receive game state
        msg, state = queue.get()
        if msg == 'state':
            played_cards, other_hand, info_tokens, fuse_tokens = state
            print(f"Player {player_id} sees:", other_hand, info_tokens, fuse_tokens)

            # Decide on action
            action = input("Choose action (play/info): ")
            data = None
            if action == 'play':
                data = int(input("Enter card index to play: "))
            elif action == 'info':
                data = input("Enter information to give: ")

            # Send action to game process
            queue.put((action, data))

if __name__ == "__main__":
    queue = multiprocessing.Queue()

    # Start game process
    game_proc = multiprocessing.Process(target=game_process, args=(queue,))
    game_proc.start()

    # Start player processes
    players = []
    for i in range(2):
        player_proc = multiprocessing.Process(target=player_process, args=(i, queue,))
        player_proc.start()
        players.append(player_proc)

    # Wait for all processes to finish
    game_proc.join()
    for p in players:
        p.join()
 