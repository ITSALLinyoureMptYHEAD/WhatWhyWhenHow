import sys
import os


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        if command.startswith("type "):
            args = command.split(" ", 1)
            command_name = args[1]
        if not builtin:
        path = os.environ.get("PATH", "")
        path_separator = os.pathsep
        os.access(path, os.X_OK)
        for directory in path.split(path_separator):
            full_path = os.path.join(directory, command_name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                print(f"{command_name} is {full_path}")
                return
        try:
        if not os.path.isdir(directory):
            OSError:
            continue

        if command == "exit":
            break
        elif command.startswith("echo "):
            args = command.split(" ", 1)
            print(args[1])
            if args[1] in ("echo", "exit", "type"):
                print(f"{args[1]} is a shell builtin")
            else:
                print(f"{args[1]}: not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
