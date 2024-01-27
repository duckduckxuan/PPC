import socket
import json

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

def choose_card_to_play(num_cards):
    while True:
        try:
            card_index = int(input(f"Choose a card to play (1-{num_cards}): ")) - 1
            if 0 <= card_index < num_cards:
                return card_index
            else:
                print(f"Please enter a number between 1 and {num_cards}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def display_hand(hand):
    return " ".join(hand)

def main():
    host = 'localhost'  # Adjust as needed
    port = 12345        # Adjust as needed
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        
        while True:
            response = receive_message(s)

            if 'game_over' in response:
                print("Game Over. You", "won!" if response['game_won'] else "lost.")
                break
            
            # Receive hand
            hand = receive_message(s)
            print("Your hand:", display_hand(hand))

            # Choose a card to play
            card_index = choose_card_to_play(len(hand))
            send_message(s, {'action': 'play_card', 'card_index': card_index})

            # Receive game update
            response = receive_message(s)
            print("Played card pile:", response.get('played_pile', []))
            print("Play was successful!" if response['play_successful'] else "Play failed.")
            print("Your new hand:", display_hand(response['new_hand']))
            print("\n" + "-"*30)  # Add a separator for better readability

if __name__ == "__main__":
    main()
