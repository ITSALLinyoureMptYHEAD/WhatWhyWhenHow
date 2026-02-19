import sys
import os


def main():
    while True:
        os.environ.get("PATH")
        os.pathsep
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
                print(f"{args[1]} is a shell builtin")
            else:
                print(f"{args[1]}: not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
