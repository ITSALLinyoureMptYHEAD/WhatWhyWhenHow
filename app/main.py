import sys
import os


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        builtins = {"echo", "exit", "type"}
        if command == "exit":
            break
        elif command.startswith("echo "):
            args = command.split("echo ", 1)
            print(args[1])
        elif command == "echo":
            print("")
        elif command.startswith("type"):
            args = command.split("type ", 1)
            command_name = args[1]
            if args[1] in ("echo", "exit", "type"):
                print(f"{args[1]} is a shell builtin")
                continue
            elif command_name not in builtins:
                found = False
                path = os.environ.get("PATH", "")
                full_path = os.path.join(directory, command_name)
                path_separator = os.pathsep
                os.access(full_path, os.X_OK)
                for directory in path.split(path_separator):
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{command_name} is {full_path}")
                        found = True
                        break
                    if not os.path.isdir(directory):
                        try:
                            found = False
                            print(f"{command_name}: not found")
                        except OSError:
                            break
        else:
            print(f"{command}: command not found")
            break


if __name__ == "__main__":
    main()
