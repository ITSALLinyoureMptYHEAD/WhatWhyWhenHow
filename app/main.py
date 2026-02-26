import sys
import os
import termios
import tty


def parse_arguments(command):
    args = []
    current_arg = ""
    in_single_quotes = False
    in_double_quotes = False
    escape_next = False
    for char in command:
        if escape_next:
            if in_double_quotes and char not in ['"', "\\", "$", "`", "\n"]:
                current_arg += "\\"
            current_arg += char
            escape_next = False
            continue
        if char == "'" and not in_double_quotes:
            in_single_quotes = not in_single_quotes
        elif char == '"' and not in_single_quotes:
            in_double_quotes = not in_double_quotes
        elif char == " " and not in_single_quotes and not in_double_quotes:
            if current_arg:
                args.append(current_arg)
                current_arg = ""
        elif char == "\\" and not in_single_quotes:
            escape_next = True
        else:
            current_arg += char
    if current_arg:
        args.append(current_arg)
    return args


def get_input(builtins, history_log):
    command = ""
    hist_idx = len(history_log)
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin)
    try:
        while True:
            char = sys.stdin.read(1)
            if char == "\x1b":
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                if next1 == "[" and next2 == "A":
                    if hist_idx > 0:
                        hist_idx -= 1
                        command = history_log[hist_idx]
                        sys.stdout.write("\r\x1b[K$ " + command)
                elif next1 == "[" and next2 == "B":
                    if hist_idx < len(history_log) - 1:
                        hist_idx += 1
                        command = history_log[hist_idx]
                        sys.stdout.write("\r\x1b[K$ " + command)
                    else:
                        hist_idx = len(history_log)
                        command = ""
                        sys.stdout.write("\r\x1b[K$ ")
                sys.stdout.flush()
                continue
            if char in ("\n", "\r"):
                sys.stdout.write("\r\n")
                return command
            elif char == "\x7f":
                if len(command) > 0:
                    command = command[:-1]
                    sys.stdout.write("\b \b")
            elif char == "\x03":
                sys.exit(0)
            else:
                sys.stdout.write(char)
                command += char
            sys.stdout.flush()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def execute_command(command_str, builtins_list, history_log):
    parts = parse_arguments(command_str)
    if not parts:
        return
    cmd_name = parts[0]

    if cmd_name == "echo":
        sys.stdout.write(" ".join(parts[1:]) + "\n")
    elif cmd_name == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
    elif cmd_name == "type":
        if len(parts) > 1:
            target = parts[1]
            if target in builtins_list:
                sys.stdout.write(f"{target} is a shell builtin\n")
            else:
                paths = os.environ.get("PATH", "").split(":")
                found = False
                for path in paths:
                    full_path = os.path.join(path, target)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        sys.stdout.write(f"{target} is {full_path}\n")
                        found = True
                        break
                if not found:
                    sys.stdout.write(f"{target}: not found\n")
    elif cmd_name == "history":
        limit = len(history_log)
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except ValueError:
                pass
        start_index = max(0, len(history_log) - limit)
        for i in range(start_index, len(history_log)):
            sys.stdout.write(f"{i + 1:>5}  {history_log[i]}\n")
    else:
        try:
            os.execvp(cmd_name, parts)
        except FileNotFoundError:
            sys.stderr.write(f"{cmd_name}: not found\n")
            os._exit(1)


def main():
    history_log = []
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        builtins_list = ["echo", "exit", "type", "pwd", "cd", "history"]

        command = get_input(builtins_list, history_log)
        if not command:
            continue

        if command.startswith("!"):
            try:
                idx = int(command[1:]) - 1
                if 0 <= idx < len(history_log):
                    command = history_log[idx]
                    sys.stdout.write(command + "\n")
                else:
                    sys.stdout.write(f"{command}: event not found\n")
                    continue
            except ValueError:
                pass

        if command.strip() == "exit":
            break

        parts = parse_arguments(command)
        if not parts:
            continue

        if parts[0] == "cd":
            dest = parts[1] if len(parts) > 1 else os.environ.get("HOME")
            try:
                os.chdir(os.path.expanduser(dest))
            except Exception as e:
                print(f"cd: {dest}: {e}")
            history_log.append(command)
            continue
        elif parts[0] == "history" and len(parts) > 1 and parts[1] == "-r":
            history_log.append(command)
            if len(parts) > 2 and os.path.exists(parts[2]):
                with open(parts[2], "r") as f:
                    for line in f:
                        history_log.append(line.strip())
            continue

        history_log.append(command)

        pid = os.fork()
        if pid == 0:
            execute_command(command, builtins_list, history_log)
            os._exit(0)
        else:
            os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
