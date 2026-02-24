import sys
import os
import subprocess
import termios
import tty


def parse_arguments(command):
    args = []  # Fixed: Removed non-printable character U+00A0
    current_arg = ""
    in_single_quotes = False
    in_double_quotes = False
    escape_next = False

    for char in command:
        if escape_next:
            current_arg += char
            escape_next = False
            continue
        if char == "\\" and not in_single_quotes:
            escape_next = True
            continue
        if char == "'" and not in_double_quotes:
            in_single_quotes = not in_single_quotes
            continue
        if char == '"' and not in_single_quotes:
            in_double_quotes = not in_double_quotes
            continue
        if char == " " and not in_single_quotes and not in_double_quotes:
            if current_arg:
                args.append(current_arg)
                current_arg = ""
        else:
            current_arg += char
    if current_arg:
        args.append(current_arg)
    return args


def execute_command(args):
    # 1. Handle Redirection (>)
    if ">" in args:
        idx = args.index(">")
        left_cmd = args[:idx]
        file_path = args[idx + 1]

        # Ensure directory exists for /tmp/fox/file-13
        (
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if os.path.dirname(file_path)
            else None
        )

        with open(file_path, "w") as f:
            return subprocess.run(left_cmd, stdout=f)

    # 2. Handle Pipeline (|)
    if "|" in args:
        idx = args.index("|")
        cmd1 = args[:idx]
        cmd2 = args[idx + 1 :]

        p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(cmd2, stdin=p1.stdout)
        p1.stdout.close()
        return p2.communicate()

    # 3. Handle Built-ins
    if args[0] == "exit":
        sys.exit(0)
    elif args[0] == "cd":
        path = args[1] if len(args) > 1 else os.path.expanduser("~")
        try:
            os.chdir(path)
        except FileNotFoundError:
            print(f"cd: {path}: No such file or directory")
        return

    # 4. Standard Executables
    try:
        subprocess.run(args)
    except FileNotFoundError:
        print(f"{args[0]}: command not found")


def get_lcp(matches):
    if not matches:
        return ""
    # Sort them and compare the first and last
    matches.sort()
    s1, s2 = matches[0], matches[-1]
    for i, c in enumerate(s1):
        if i >= len(s2) or c != s2[i]:
            return s1[:i]
    return s1


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        line = sys.stdin.readline()
        if not line:
            break

        command = line.strip()
        if not command:
            continue

        args = parse_arguments(command)
        if args:
            execute_command(args)


if __name__ == "__main__":
    main()
