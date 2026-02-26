import sys
import os
import termios
import tty


# Handles quotes and escaped characters for all shell commands
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


# Custom input handler to support Arrow Key navigation
def get_input(builtins, history_log):
    command = ""
    hist_idx = len(history_log)
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin)
    try:
        while True:
            char = sys.stdin.read(1)
            if char == "\x1b":  # Detect Arrows
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                if next1 == "[" and next2 == "A":  # UP ARROW
                    if hist_idx > 0:
                        hist_idx -= 1
                        command = history_log[hist_idx]
                        sys.stdout.write("\r\x1b[K$ " + command)
                elif next1 == "[" and next2 == "B":  # DOWN ARROW
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
            elif char == "\x7f":  # Backspace
                if len(command) > 0:
                    command = command[:-1]
                    sys.stdout.write("\b \b")
            elif char == "\x03":  # Ctrl+C
                sys.exit(0)
            else:
                sys.stdout.write(char)
                command += char
            sys.stdout.flush()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def load_history():
    history_file = os.path.expanduser("~/.shell_history")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return [line.strip() for line in f.readlines()]
    return []


def append_to_history(command):
    history_file = os.path.expanduser("~/.shell_history")
    with open(history_file, "a") as f:
        f.write(command + "\n")


# Logic for builtins and external programs
def execute_command(command_str, builtins_list, history_log):
    parts = parse_arguments(command_str)
    if not parts:
        return
    cmd_name = parts[0]

    if cmd_name == "echo":
        sys.stdout.write(" ".join(parts[1:]) + "\n")
    elif cmd_name == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
    elif cmd_name == "history":
        limit = len(history_log)
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except ValueError:
                pass
        # Use precise formatting for Listing stage
        start_index = max(0, len(history_log) - limit)
        for i in range(start_index, len(history_log)):
            sys.stdout.write(f"  {i + 1}  {history_log[i]}\n")
    else:
        try:
            os.execvp(cmd_name, parts)
        except FileNotFoundError:
            sys.stderr.write(f"{cmd_name}: not found\n")
            os._exit(1)


def main():
    # Load history on startup
    history_log = load_history()
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        builtins_list = ["echo", "exit", "type", "pwd", "cd", "history"]

        command = get_input(builtins_list, history_log)
        if not command:
            continue

        # Expansion: !number logic MUST be in parent
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

        # State-Changing commands MUST run in parent to update memory
        if parts[0] == "cd":
            dest = parts[1] if len(parts) > 1 else os.environ.get("HOME")
            try:
                os.chdir(os.path.expanduser(dest))
            except Exception as e:
                print(f"cd: {dest}: {e}")
            history_log.append(command)
            append_to_history(command)
            continue
        elif parts[0] == "history" and len(parts) > 1 and parts[1] == "-r":
            history_log.append(command)
            append_to_history(command)

            if len(parts) > 2 and os.path.exists(parts[2]):
                with open(parts[2], "r") as f:
                    for line in f:
                        history_log.append(line.strip())
            continue

        history_log.append(command)
        append_to_history(command)

        # Standard execution via Forking
        pid = os.fork()
        if pid == 0:
            execute_command(command, builtins_list, history_log)
            os._exit(0)
        else:
            os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
