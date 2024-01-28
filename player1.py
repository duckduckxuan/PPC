import socket
import json

def send_message(conn, message):
    try:
        print(f"Sending message: {message}")
        serialized_message = json.dumps(message).encode('utf-8')
        conn.sendall(serialized_message)
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")

# 在 receive_message 函数中，修改接收消息长度信息的方式
def receive_messages(conn):
    try:
        buffer = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                print("Connection closed by the server.")
                break
            buffer += chunk

            while b'\n' in buffer:
                msg, buffer = buffer.split(b'\n', 1)
                try:
                    decoded_msg = json.loads(msg.decode('utf-8'))
                    print(f"Received message from server: {decoded_msg}")
                    yield decoded_msg
                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")

        if buffer:
            decoded_msg = json.loads(buffer.decode('utf-8'))
            print(f"Received message from server: {decoded_msg}")
            yield decoded_msg
        else:
            print("Connection closed.")
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
    host = 'localhost'
    port = 8888
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connection OK")
        
        while True:
            response = s.recv(4096).decode('utf-8')
            if response is None:
                print("No response received. Exiting.")
                break

            print(f"Received message from server: {response}")

            # 解析为Python对象
            print("Received response:", response)
            parsed_response = json.loads(response)


            if parsed_response and 'game_over' in parsed_response:
                print("Game Over. You", "won!" if response['game_won'] else "lost.")
                break


            if parsed_response and 'action_required' in parsed_response and parsed_response['action_required'] == 'play_card':
                print("Server is requesting action: play_card")
                # Receive hand
                """
                hand = parsed_response.get('hand', [])
                if not hand:
                    print("No hand received. Exiting.")
                    break
                print("Received hand:", hand)
                print("Your hand:", display_hand(hand))
                """

                # 提示用户选择一张牌
                card_index = choose_card_to_play(5)
                print(f"Sending play_card action with card index: {card_index}")
                

                send_message(s, {'action': 'play_card', 'card_index': card_index})

                # Receive game update
                response = s.recv(4096).decode('utf-8')
                if response is None:
                    print("No response2 received. Exiting.")
                    break
                print("Played card pile:", response.get('played_pile', []))
                print("Play was successful!" if response['play_successful'] else "Play failed.")
                print("\n" + "-"*30)  # Add a separator for better readability

if __name__ == "__main__":
    main()
