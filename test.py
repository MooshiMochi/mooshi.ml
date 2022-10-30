board = [1, 2, 3, 4, 5, 6, 7, 8, 9]


def get_choice():
    print("1. X\n2. O\n")
    user_choice = int(input())
    return user_choice


def choice(user_choice):
    odg = int(input())
    c = "X" if user_choice == 1 else "O"
    index = odg - 1
    if board[index] != "X" and board[index] != "O":
        board[index] = c
    else:
        print("Mjesto je vec iskoristeno")


def all_x_or_o():
    w = True
    while w:
        if (
            board[0]
            and board[1]
            and board[2] == "X"
            or board[0]
            and board[1]
            and board[2] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[3]
            and board[4]
            and board[5] == "X"
            or board[3]
            and board[4]
            and board[5] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[6]
            and board[7]
            and board[8] == "X"
            or board[6]
            and board[7]
            and board[8] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[0]
            and board[3]
            and board[6] == "X"
            or board[0]
            and board[3]
            and board[6] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[1]
            and board[4]
            and board[7] == "X"
            or board[1]
            and board[4]
            and board[7] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[2]
            and board[5]
            and board[8] == "X"
            or board[2]
            and board[5]
            and board[8] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[0]
            and board[4]
            and board[8] == "X"
            or board[0]
            and board[4]
            and board[8] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False
        elif (
            board[2]
            and board[4]
            and board[6] == "X"
            or board[2]
            and board[4]
            and board[6] == "O"
        ):
            print("You won") if user_choice == 1 else print("You lost")
            w = False


def draw():
    print(board[0], "|", board[1], "|", board[2])
    print("---------")
    print(board[3], "|", board[4], "|", board[5])
    print("---------")
    print(board[6], "|", board[7], "|", board[8])


user_choice = get_choice()
while all_x_or_o():
    draw()
    choice(user_choice)
