import sys
import os
import termios
import tty


# This automatically handles single quotes, double quotes, and escaped characters
def parse_arguments(command):
    args = []
    current_arg = ""
    # """switches""" eg. b_l_a_h = False
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
        # Check for single quote (ONLY if we aren't inside double quotes)
        if char == "'" and not in_double_quotes:
            # Toggle the quote state; do not add the quote character itself
            in_single_quotes = not in_single_quotes
        # Check for double quote (ONLY if we aren't inside single quotes)
        elif char == '"' and not in_single_quotes:
            # A space outside of quotes means the argument is complete
            in_double_quotes = not in_double_quotes
        # Check for space (ONLY if BOTH switches are off)
        #
        # A single = is a command: "Make the thing on the left equal to the thing on the right."
        # A double == is a question: "Are these two things exactly the same?"
        #
        elif char == " " and not in_single_quotes and not in_double_quotes:
            if current_arg:
                args.append(current_arg)
                current_arg = ""
        # Normal letters (or spaces/quotes trapped inside the other quote type)
        elif char == "\\" and not in_single_quotes:
            escape_next = True
        else:
            # Add any other character (or spaces inside quotes) to the argument
            # now we do current_arg = current_arg + char, but faster
            current_arg += char
    #
    # Imagine you have a piece of paper.
    #    Without +=:
    # You take a new blank paper. You look at your old paper (which says "ec"), copy "ec" onto the new paper,
    #  and then write "h" at the end. Then you throw away the old paper.
    # current_arg = current_arg + char
    #    With +=:
    # You just take your pen and write "h" at the end of the paper you already have.
    # current_arg += char
    # It is just a shortcut that means "stick this onto the end of what is already there."
    #
    # Add the final argument after the loop finishes
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

            if char == "\x1b":  # Detect Arrow Keys
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                if next1 == "[" and next2 == "A":  # UP
                    if hist_idx > 0:
                        hist_idx -= 1
                        command = history_log[hist_idx]
                        sys.stdout.write("\r\x1b[K$ " + command)
                elif next1 == "[" and next2 == "B":  # DOWN
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


def execute_command(command_str, builtins_list, history_log):
    parts = parse_arguments(command_str)
    if not parts:
        return

    # Handle Redirections
    redirect_out = None
    redirect_err = None
    append_out = False
    append_err = False

    # Check for Error Redirection first
    if "2>>" in parts:
        idx = parts.index("2>>")
        redirect_err = parts[idx + 1]
        append_err = True
        parts = parts[:idx]
    elif "2>" in parts:
        idx = parts.index("2>")
        redirect_err = parts[idx + 1]
        parts = parts[:idx]

    # Check for Output Redirection
    if ">>" in parts or "1>>" in parts:
        op = ">>" if ">>" in parts else "1>>"
        idx = parts.index(op)
        redirect_out = parts[idx + 1]
        append_out = True
        parts = parts[:idx]
    elif ">" in parts or "1>" in parts:
        op = ">" if ">" in parts else "1>"
        idx = parts.index(op)
        redirect_out = parts[idx + 1]
        parts = parts[:idx]

    # Apply the Redirections (inside the child process)
    if redirect_out:
        flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append_out else os.O_TRUNC)
        fd = os.open(redirect_out, flags, 0o644)
        os.dup2(fd, sys.stdout.fileno())
        os.close(fd)
    if redirect_err:
        flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append_err else os.O_TRUNC)
        fd = os.open(redirect_err, flags, 0o644)
        os.dup2(fd, sys.stderr.fileno())
        os.close(fd)

    # translation for redirections:
    # os.O_WRONLY: Open the file for WRiting ONLY (no reading).
    # |: The glue that mixes these rules together.
    # os.O_CREAT: If the file does not exist yet, CREATe it.
    # os.O_TRUNC: If the file already has text inside, TRUNCate (erase) it completely.
    # 0o644: Security permissions: "I can read/write, others can only read."

    command_name = parts[0]

    # Run Builtins or External Commands
    if command_name == "echo":
        sys.stdout.write(" ".join(parts[1:]) + "\n")
    elif command_name == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
    elif command_name == "type":
        found = False
        target = parts[1] if len(parts) > 1 else ""
        if target in builtins_list:
            sys.stdout.write(f"{target} is a shell builtin\n")
        else:
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                full_path = os.path.join(directory, target)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    sys.stdout.write(f"{target} is {full_path}\n")
                    found = True
                    break
            if not found:
                sys.stdout.write(f"{target}: not found\n")
    elif command_name == "history":
        limit = len(history_log)
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except ValueError:
                pass

        start_index = max(0, len(history_log) - limit)
        for i in range(start_index, len(history_log)):
            # The exact spacing (two spaces) often matters for CodeCrafters
            sys.stdout.write(f"  {i + 1}  {history_log[i]}\n")

        # Slice the list to only get the last 'limit' items
        # start_index helps us keep the numbering correct (e.g., 3, 4 instead of 1, 2)
        start_index = max(0, len(history_log) - limit)
        display_list = history_log[start_index:]

        for i, cmd in enumerate(display_list):
            real_num = start_index + i + 1
            sys.stdout.write(f"  {real_num}  {cmd}\n")
    else:
        # It's an external command (cat, wc, ls, etc.)
        try:
            os.execvp(command_name, parts)
        except FileNotFoundError:
            sys.stderr.write(f"{command_name}: not found\n")
            os._exit(1)


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


def main():
    history_log = load_history()
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        builtins_list = ["echo", "exit", "type", "pwd", "cd", "history"]
        command = get_input(builtins_list, history_log)
        if command:
            history_log.append(command)  # Add it to the list
            append_to_history(command)
        # expansion logic for !number
        if command.startswith("!"):
            try:
                # Extract the number (e.g., !1 -> index 0)
                idx = int(command[1:]) - 1
                if 0 <= idx < len(history_log):
                    command = history_log[idx]
                    # Print the expanded command so the user sees it
                    sys.stdout.write(command + "\n")
                else:
                    sys.stdout.write(f"{command}: event not found\n")
                    continue
            except ValueError:
                pass  # Not a number, treat as a normal command
        if not command:
            continue
        if command.strip() == "exit":
            break

        # Handle 'cd' separately because it MUST happen in the parent process
        if command.startswith("cd"):
            parts = parse_arguments(command)
            destination = parts[1].strip() if len(parts) > 1 else os.environ.get("HOME")
            if destination.startswith("~"):
                destination = destination.replace("~", os.environ.get("HOME"), 1)
            try:
                os.chdir(destination)
            except (FileNotFoundError, NotADirectoryError) as e:
                print(f"cd: {destination}: {e.strerror}")
            continue

        # Handle Pipes
        commands = command.split("|")
        prev_pipe_read = None
        pids = []

        for i, cmd_str in enumerate(commands):
            cmd_str = cmd_str.strip()
            curr_pipe_read, curr_pipe_write = None, None

            # Create a pipe if this is not the last command in the chain
            if i < len(commands) - 1:
                curr_pipe_read, curr_pipe_write = os.pipe()

            pid = os.fork()
            if pid == 0:
                # CHILD PROCESS: Setup pipes
                if prev_pipe_read is not None:
                    os.dup2(prev_pipe_read, 0)
                    os.close(prev_pipe_read)
                if curr_pipe_write is not None:
                    os.dup2(curr_pipe_write, 1)
                    os.close(curr_pipe_write)
                    os.close(curr_pipe_read)

                # Execute the actual command logic
                execute_command(cmd_str, builtins_list, history_log)
                os._exit(0)
            else:
                # PARENT PROCESS
                pids.append(pid)
                if prev_pipe_read is not None:
                    os.close(prev_pipe_read)
                if curr_pipe_write is not None:
                    os.close(curr_pipe_write)
                prev_pipe_read = curr_pipe_read

        # Wait for all processes in the pipe chain to finish
        for p in pids:
            os.waitpid(p, 0)


if __name__ == "__main__":
    main()
# force update
# force updatee
