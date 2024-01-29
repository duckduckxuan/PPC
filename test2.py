import sysv_ipc
import json
from multiprocessing import Process
import socket

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


def handle_server_connection(socket, message_queue):
    while True:
        try:
            response = socket.recv(4096).decode('utf-8')
            if not response:
                print("Connection closed by the server. Exiting.")
                break

            parsed_response = json.loads(response)
            print(f"Received message:", parsed_response)

            if 'game_over' in parsed_response:
                print("Game Over. You", "won!" if parsed_response['game_over'] else "lost.")
                break

            if 'action_required' in parsed_response:
                action_required = parsed_response['action_required']
                print("required")
                if action_required == 'give_info':
                    """
                    hand = parsed_response.get('hand', [])
                    if not hand:
                        print("No hand received. Exiting.")
                        break
                    print("Received hand:", hand)
                    """

                    user_input = input("Give a tip to the other player? (y/n): ")

                    if user_input.lower() == 'y':
                        info_message = input("Enter the information you want to send: ")

                        # Use sysv_ipc message_queue to send information
                        message_queue.send(info_message.encode(), type=1)

                        # Notify the game process that an info token is consumed
                        send_message(socket, {'action': 'give_info', 'consume': True})

                    elif user_input.lower() == 'n':
                        info_message = "This player will not provide information this round."

                        # Use sysv_ipc message_queue to send information
                        message_queue.send(info_message.encode(), type=1)

                        send_message(socket, {'action': 'give_info', 'consume': False})

                    else:
                        print("Invalid input. Please enter 'y' or 'n'.")

                if action_required == 'play_card':
                    print("Server is requesting action: play_card")

                    card_index = choose_card_to_play(5)
                    print(f"Sending play_card action with card index: {card_index}")

                    send_message(socket, {'action': 'play_card', 'card_index': card_index})

                    # Receive game update
                    response = socket.recv(4096).decode('utf-8')
                    if not response:
                        print("Connection closed by the server. Exiting.")
                        break
                    print(f"Received message from server: {response}")

                    parsed_response = json.loads(response)

                    if parsed_response:
                        print("Played card pile:", parsed_response.get('played_pile', []))
                        print("Play was successful!" if parsed_response['play_successful'] else "Play failed.")
                        print("\n" + "-"*30)  # Add a separator for better readability

        except Exception as e:
            print(f"Error handling server connection: {e}")


def main():
    host = 'localhost'
    port = 8888

    # 创建 sysv_ipc 消息队列
    mq_key = 1234
    message_queue = sysv_ipc.MessageQueue(mq_key, sysv_ipc.IPC_CREAT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        print("Connection OK")

        # 在一个进程中处理与服务器的通信
        p = Process(target=handle_server_connection, args=(s, message_queue))
        p.start()

        # 关闭消息队列
        message_queue.remove()

        # 等待服务器线程结束
        p.join()

if __name__ == "__main__":
    main()