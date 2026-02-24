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
                        # If they share a common start (like 'my_command_v1' and 'my_command_v2')
                        # only fill in the 'my_command_' part and don't add a space yet.
                        remainder = common[len(command) :]
                        sys.stdout.write(remainder)
                        command += remainder
                    else:
                        # If no more common letters, print the list and ring the bell
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


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        builtins = ["echo", "exit", "type", "pwd", "cd"]
        command = get_input(builtins)
        if not command:
            continue

        if command == "exit":
            break
        elif command.startswith("echo "):
            # Parse the command using your new function
            args = parse_arguments(command)
            if "2>>" in args:
                idx = args.index("2>>")
                with open(args[idx + 1], "a"):
                    pass
                args = args[:idx]
            elif "2>" in args:
                idx = args.index("2>")
                with open(args[idx + 1], "w"):
                    pass
                args = args[:idx]

            if ">>" in args or "1>>" in args:
                op = ">>" if ">>" in args else "1>>"
                idx = args.index(op)
                with open(args[idx + 1], "a") as f:
                    f.write(" ".join(args[1:idx]) + "\n")
            elif ">" in args or "1>" in args:
                op = ">" if ">" in args else "1>"
                idx = args.index(op)
                with open(args[idx + 1], "w") as f:
                    f.write(" ".join(args[1:idx]) + "\n")
            else:
                print(" ".join(args[1:]))
        elif command == "echo":
            print("")
        elif command.startswith("type"):
            args = command.split("type ", 1)
            command_name = args[1]
            if command_name in ("echo", "exit", "type", "pwd", "cd"):
                print(f"{command_name} is a shell builtin")
                continue

            found = False
            path = os.environ.get("PATH", "")
            path_separator = os.pathsep
            for directory in path.split(path_separator):
                full_path = os.path.join(directory, command_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    print(f"{command_name} is {full_path}")
                    found = True
                    break

            if not found:
                print(f"{command_name}: not found")

        elif command.split()[0] not in builtins:
            found = False
            path = os.environ.get("PATH", "")
            path_separator = os.pathsep
            parts = parse_arguments(command)

            redirect_out = None
            redirect_err = None
            append_out = False
            append_err = False

            if "2>>" in parts:
                idx = parts.index("2>>")
                redirect_err = parts[idx + 1]
                append_err = True
                parts = parts[:idx]
            elif "2>" in parts:
                idx = parts.index("2>")
                redirect_err = parts[idx + 1]
                parts = parts[:idx]

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

            command_name = parts[0]
            for directory in path.split(path_separator):
                full_path = os.path.join(directory, command_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found = True
                    break
            if found:
                pid = os.fork()
                if pid == 0:
                    if redirect_out:
                        flags = (
                            os.O_WRONLY
                            | os.O_CREAT
                            | (os.O_APPEND if append_out else os.O_TRUNC)
                        )
                        fd = os.open(redirect_out, flags, 0o644)
                        os.dup2(fd, sys.stdout.fileno())
                        os.close(fd)
                    if redirect_err:
                        flags = (
                            os.O_WRONLY
                            | os.O_CREAT
                            | (os.O_APPEND if append_err else os.O_TRUNC)
                        )
                        fd = os.open(redirect_err, flags, 0o644)
                        os.dup2(fd, sys.stderr.fileno())
                        os.close(fd)
                    os.execvp(command_name, parts)
                else:
                    os.waitpid(pid, 0)
            else:
                print(f"{command_name}: not found")

        elif command == ("pwd"):
            current_location = os.getcwd()
            if current_location:
                print(current_location)
            else:
                print("Error: Could not retrieve directory.")

        elif command == "cd" or command.startswith("cd"):
            parts = command.split(" ", 1)
            if len(parts) == 1 or parts[1].strip() == "":
                destination = os.environ.get("HOME")
            else:
                destination = parts[1].strip()

            if destination and destination.startswith("~"):
                home = os.environ.get("HOME")
                destination = destination.replace("~", home, 1)

            try:
                if destination:
                    os.chdir(destination)
            except FileNotFoundError:
                print(f"cd: {destination}: No such file or directory")
            except NotADirectoryError:
                print(f"cd: {destination}: Not a directory")


if __name__ == "__main__":
    main()
