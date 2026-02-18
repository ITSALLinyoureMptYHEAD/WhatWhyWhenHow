import sys
import os


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
                print(f"{args[1]} is a shell builtin")
                path_dirs = os.environ.get("PATH", "").split(os.pathsep)
                for dir in path_dirs:
                    full_path = os.path.join(dir, args[1])
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{arg[1]} is {full_path}")
                        break
                else:
                print(f"{args[1]}: not found")


        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
