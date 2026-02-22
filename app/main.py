import sys
import os


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        builtins = {"echo", "exit", "type", "pwd"}
        if command == "exit":
            break
        elif command.startswith("echo "):
            args = command.split("echo ", 1)
            print(args[1])
        elif command == "echo":
            print("")
        elif command.startswith("type"):
            found = False
            args = command.split("type ", 1)
            command_name = args[1]
            if args[1] in ("echo", "exit", "type", "pwd"):
                print(f"{args[1]} is a shell builtin")
                continue
            elif command_name not in builtins:
                path = os.environ.get("PATH", "")
                path_separator = os.pathsep
                for directory in path.split(path_separator):
                    full_path = os.path.join(directory, command_name)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{command_name} is {full_path}")
                        found = True
                        break
                if not found:
                    try:
                        print(f"{command_name}: not found")
                    except OSError:
                        break

        elif command not in builtins:
            found = False
            path = os.environ.get("PATH", "")
            path_separator = os.pathsep
            parts = command.split()
            command_name = parts[0]
            for directory in path.split(path_separator):
                full_path = os.path.join(directory, command_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found = True
                    break
            if found:
                pid = os.fork()
                if pid == 0:
                    os.execvp(command_name, parts)
                else:
                    os.waitpid(pid, 0)
            if not found:
                try:
                    print(f"{command_name}: not found")
                except OSError:
                    break

        elif command == ("pwd"):
            print(os.getcwd())


if __name__ == "__main__":
    main()
