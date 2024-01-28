import socket
import json
import queue
import threading

def send_message(conn, message):
    try:
        print(f"Sending message: {message}")
        serialized_message = json.dumps(message).encode('utf-8')
        conn.sendall(serialized_message)
    except json.JSONDecodeError as e:
        print(f"Error encoding message: {e}")


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

def handle_server_connection(socket, info_queue):
    while True:
        response = socket.recv(4096).decode('utf-8')
        if response is None:
            print("No response received. Exiting.")
            break

        parsed_response = json.loads(response)
        recipient_id = parsed_response.get('recipient', None)

        if parsed_response and 'game_over' in parsed_response and recipient_id == 1:
            print("Received response:", parsed_response)
            print("Game Over. You", "won!" if parsed_response['game_over'] else "lost.")
            break

        if parsed_response and 'action_required' in parsed_response and recipient_id == 1:
            print("Received response:", parsed_response)
            action_required = parsed_response['action_required']

            if action_required == 'give_info':
                hand = parsed_response.get('hand', [])
                if not hand:
                    print("No hand received. Exiting.")
                    break
                print("Received hand:", hand)

                # 用户输入
                user_input = input("Give a tip to the other player? (y/n): ")

                if user_input.lower() == 'y':
                    # 让玩家输入想发送的信息
                    info_message = input("Enter the information you want to send: ")

                    # 向队列中添加信息，用于与另一个玩家通信
                    info_queue.put(info_message)

                    # 向游戏进程告知消耗一个引信令牌
                    send_message(socket, {'action': 'give_info', 'consume': True})

                elif user_input.lower() == 'n':
                    # 向另一玩家自动发送消息
                    info_message = "This player will not provide information this round."

                    # 向队列中添加信息，用于与另一个玩家通信
                    info_queue.put(info_message)

                    send_message(socket, {'action': 'give_info', 'consume': False})

                else:
                    print("Invalid input. Please enter 'y' or 'n'.")

            elif action_required == 'play_card':
                print("Server is requesting action: play_card")

                # 提示用户选择一张牌
                card_index = choose_card_to_play(5)
                print(f"Sending play_card action with card index: {card_index}")

                send_message(socket, {'action': 'play_card', 'card_index': card_index})

                # Receive game update
                response = socket.recv(4096).decode('utf-8')
                if response is None:
                    print("No response received. Exiting.")
                    break
                print(f"Received message from server: {response}")

                print("Received response:", response)
                parsed_response = json.loads(response)
                recipient_id = parsed_response.get('recipient', None)

                if parsed_response and recipient_id == 1:
                    print("Played card pile:", parsed_response.get('played_pile', []))
                    print("Play was successful!" if parsed_response['play_successful'] else "Play failed.")
                    print("\n" + "-"*30)  # Add a separator for better readability

def main():
    host = 'localhost'
    port = 8888
    info_queue = queue.Queue()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connection OK")

        # 在一个线程中处理与服务器的通信
        server_thread = threading.Thread(target=handle_server_connection, args=(s, info_queue))
        server_thread.start()

        """
        # 在主线程中等待用户输入
        while True:
            user_input = input("Main thread is waiting. Type 'exit' to quit: ")
            if user_input.lower() == 'exit':
                break
        """

        # 等待服务器线程结束
        server_thread.join()

if __name__ == "__main__":
    main()
