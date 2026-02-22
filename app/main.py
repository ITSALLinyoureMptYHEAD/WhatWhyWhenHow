import sys
import os
import subprocess

BUILTINS = {
    "exit": lambda: sys.exit(),
    "echo": lambda *args: sys.stdout.write(" ".join(args) + "\n"),
    "type": lambda *args: _get_type(args),
    "pwd": lambda: sys.stdout.write(os.getcwd() + "\n"),
}


def _find_exec_path(file):
    PATH = os.environ.get("PATH")
    for directory in PATH.split(":"):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
            return file_path
        return None


def _get_type(commands):
    for command in commands:
        if command in BUILTINS:
            sys.stdout.write(f"{command} is a shell builtin\n")
        elif file_path := _find_exec_path(command):
            sys.stdout.write(f"{command} is {file_path}\n")
        else:
            sys.stdout.write(f"{command}: not found\n")


def main():
    while True:
        sys.stdout.write("$ ")
        cmd = input()
        first = cmd.split(" ")[0]
        rest = cmd.split(" ")[1:]

        if first in BUILTINS:
            BUILTINS[first](*rest)
        elif _find_exec_path(first):
            subprocess.run(cmd.split(" "), check=True)
        else:
            sys.stdout.write(f"{cmd}: command not found\n")


if __name__ == "__main__":
    main()
