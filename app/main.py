import sys


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command == "exit":
            break
        elif command.startswith("echo "):
            args = command.split(" ", 1)
            print(args[1])
        elif command.startswith("type "):
            args = command.split(" ", 1)
            if args[1] in ("echo", "exit", "type"):
            print(f"{args[1]} is a shell builtin! :D")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
