import threading
import sysv_ipc
import socket
import json

def send_message(conn, message):
    try:
        print(f"Sending message: {message}")
        serialized_message = json.dumps(message).encode('utf-8')
        conn.sendall(serialized_message)
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")

def receive_message(socket):
    try:
        response = socket.recv(4096).decode('utf-8')
        if not response:
            print("Connection closed by the server. Exiting.")
            return None
        return json.loads(response)
    except json.JSONDecodeError as json_error:
        print(f"Error decoding server response: {json_error}")
        return None
    except Exception as e:
        print(f"Error receive message from server: {e}")
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

def handle_server_socket(socket):
    try:
        while True:
            parsed_response = receive_message(socket)
            if parsed_response is None:
                break

            if 'game_over' in parsed_response:
                print("Game Over. You", "won!" if parsed_response['game_over'] else "lost.")
                break

            elif parsed_response['action_required'] == 'give_info':
                user_input = input("Give a tip to the other player? (y/n): ")

                if user_input == 'y':
                    send_message(socket, {'action': 'give_info', 'consume': True})

                elif user_input == 'n':
                    send_message(socket, {'action': 'give_info', 'consume': False})

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

            elif parsed_response['action_required'] == 'play_card':
                    print("Server is requesting action: play_card")
                    card_index = choose_card_to_play(5)
                    print(f"Sending play_card action with card index: {card_index}")
                    send_message(socket, {'action': 'play_card', 'card_index': card_index})

                    # Receive game update
                    parsed_response = receive_message(socket)
                    if parsed_response:
                        print("Played card pile:", parsed_response.get('played_pile', []))
                        print("Play was successful!" if parsed_response['play_successful'] else "Play failed.")
                        print("\n" + "-"*30)  # Add a separator for better readability

    except Exception as e:
        print(f"Error handling server socket connection: {e}")


if __name__ == "__main__":
    # Set socket connection
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect(('localhost', 12345))

    shm = sysv_ipc.SharedMemory(888)

    # Start Game-Player connection
    handle_server_socket(server_socket)

    # Close socket connection
    server_socket.close()