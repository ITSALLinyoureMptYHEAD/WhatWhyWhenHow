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
        elif command.startswith("type ") or command.startswith("type"):
                args = command.split("type ", 1) or args = command.split("type", 1)
                command_name = args[1]
                if args[1] in ("echo", "exit", "type"):
                    print(f"{args[1]} is a shell builtin")
                    continue
                elif not builtins:
                        found = False
                        path = os.environ.get("PATH", "")
                        path_separator = os.pathsep
                        os.access(path, os.X_OK)
                        for directory in path.split(path_separator):
                            full_path = os.path.join(directory, command_name)
                            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                                print(f"{command_name} is {full_path}")
                                found = True
                                continue
                            if not os.path.isdir(directory):
                                print(f"{args[1]}: not found")
                                continue
                            elif OSError:
                                print(f"OSError, FIX ME!")
                                continue
                else:
                            print(f"{command}: command not found")
                            continue

if __name__ == "__main__":
    main()
