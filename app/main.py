import sys


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        if command == "echo"(input()):
            print(input())
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
