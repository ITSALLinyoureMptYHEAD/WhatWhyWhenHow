import sys


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        else command == "echo":
            print(input())
        elif print(f"{command}: command not found")


if __name__ == "__main__":
    main()
