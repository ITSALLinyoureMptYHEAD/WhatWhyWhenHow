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


def get_input(builtins):
    command = ""
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin)

    try:
        while True:
            char = sys.stdin.read(1)

            # Enter key
            if char in ("\n", "\r"):
                sys.stdout.write("\r\n")
                return command

            elif char == "\t":
                # Gather all possible matches
                matches = set([b for b in builtins if b.startswith(command)])
                path_env = os.environ.get("PATH", "")
                if path_env:
                    for directory in path_env.split(os.pathsep):
                        if os.path.isdir(directory):
                            try:
                                for filename in os.listdir(directory):
                                    if filename.startswith(command):
                                        full_path = os.path.join(directory, filename)
                                        if os.path.isfile(full_path) and os.access(
                                            full_path, os.X_OK
                                        ):
                                            matches.add(filename)
                            except OSError:
                                continue

                matches = sorted(list(matches))

                # SCENARIO A: Exactly one match -> Complete it + one space
                if len(matches) == 1:
                    remainder = matches[0][len(command) :]
                    sys.stdout.write(remainder + " ")
                    command += remainder + " "

                # SCENARIO B: Multiple matches
                elif len(matches) > 1:
                    # Find the longest common part they all share
                    common = os.path.commonprefix(matches)

                    if len(common) > len(command):
                        # If they share a common start
                        remainder = common[len(command) :]
                        sys.stdout.write(remainder)
                        command += remainder
                    else:
                        sys.stdout.write("\a")
                        sys.stdout.write("\r\n" + "  ".join(matches) + "\r\n")
                        sys.stdout.write("$ " + command)

                # SCENARIO C: No matches
                else:
                    sys.stdout.write("\a")

            # Backspace key
            elif char == "\x7f":
                if len(command) > 0:
                    command = command[:-1]
                    sys.stdout.write("\b \b")

            # Ctrl+C to exit safely
            elif char == "\x03":
                sys.exit(0)

            # Normal typing
            else:
                sys.stdout.write(char)
                command += char

            sys.stdout.flush()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def execute_command(command_str, builtins_list):
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
    else:
        # It's an external command (cat, wc, ls, etc.)
        try:
            os.execvp(command_name, parts)
        except FileNotFoundError:
            sys.stderr.write(f"{command_name}: not found\n")
            os._exit(1)


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        builtins_list = ["echo", "exit", "type", "pwd", "cd"]
        command = get_input(builtins_list)

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
                execute_command(cmd_str, builtins_list)
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
