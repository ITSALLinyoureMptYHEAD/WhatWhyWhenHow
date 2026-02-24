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


def get_input(builtins):
    command = ""
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin)

    try:
        while True:
            char = sys.stdin.read(1)

            if char in ("\n", "\r"):
                sys.stdout.write("\r\n")
                return command

            elif char == "\t":
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

                if len(matches) == 1:
                    remainder = matches[0][len(command) :]
                    sys.stdout.write(remainder + " ")
                    command += remainder + " "
                elif len(matches) > 1:
                    common = os.path.commonprefix(matches)
                    if len(common) > len(command):
                        remainder = common[len(command) :]
                        sys.stdout.write(remainder)
                        command += remainder
                    else:
                        sys.stdout.write("\a")
                        sys.stdout.write("\r\n" + "  ".join(matches) + "\r\n")
                        sys.stdout.write("$ " + command)
                else:
                    sys.stdout.write("\a")

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

        # Handle built-in echo with redirection
        elif command.startswith("echo"):
            args = parse_arguments(command)
            # Redirection logic
            redirect_out = None
            append_out = False

            if ">>" in args or "1>>" in args:
                op = ">>" if ">>" in args else "1>>"
                idx = args.index(op)
                redirect_out, append_out = args[idx + 1], True
                args = args[:idx]
            elif ">" in args or "1>" in args:
                op = ">" if ">" in args else "1>"
                idx = args.index(op)
                redirect_out = args[idx + 1]
                args = args[:idx]

            output = " ".join(args[1:])
            if redirect_out:
                mode = "a" if append_out else "w"
                with open(redirect_out, mode) as f:
                    f.write(output + "\n")
            else:
                print(output)

        # Handle type
        elif command.startswith("type"):
            parts = parse_arguments(command)
            if len(parts) < 2:
                continue
            cmd_name = parts[1]
            found = False
            if cmd_name in builtins:
                print(f"{cmd_name} is a shell builtin")
                found = True
            else:
                path = os.environ.get("PATH", "")
                for directory in path.split(os.pathsep):
                    full_path = os.path.join(directory, cmd_name)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{cmd_name} is {full_path}")
                        found = True
                        break
            if not found:
                print(f"{cmd_name}: not found")

        # Handle pwd
        elif command == "pwd":
            print(os.getcwd())

        # Handle cd
        elif command.startswith("cd"):
            parts = parse_arguments(command)
            destination = os.environ.get("HOME") if len(parts) == 1 else parts[1]
            if destination.startswith("~"):
                destination = destination.replace("~", os.environ.get("HOME"), 1)
            try:
                os.chdir(destination)
            except FileNotFoundError:
                print(f"cd: {destination}: No such file or directory")

        # Handle External Commands
        else:
            parts = parse_arguments(command)
            if not parts:
                continue

            # Find in PATH
            cmd_name = parts[0]
            found_path = None
            path = os.environ.get("PATH", "")
            for directory in path.split(os.pathsep):
                full_path = os.path.join(directory, cmd_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found_path = full_path
                    break

            if found_path:
                # Setup redirection flags
                redirect_out = None
                redirect_err = None
                append_out = False
                append_err = False

                if "2>>" in parts:
                    idx = parts.index("2>>")
                    redirect_err, append_err, parts = parts[idx + 1], True, parts[:idx]
                elif "2>" in parts:
                    idx = parts.index("2>")
                    redirect_err, parts = parts[idx + 1], parts[:idx]

                if ">>" in parts or "1>>" in parts:
                    op = ">>" if ">>" in parts else "1>>"
                    idx = parts.index(op)
                    redirect_out, append_out, parts = parts[idx + 1], True, parts[:idx]
                elif ">" in parts or "1>" in parts:
                    op = ">" if ">" in parts else "1>"
                    idx = parts.index(op)
                    redirect_out, parts = parts[idx + 1], parts[:idx]

                pid = os.fork()
                if pid == 0:
                    if redirect_out:
                        flags = (
                            os.O_WRONLY
                            | os.O_CREAT
                            | (os.O_APPEND if append_out else os.O_TRUNC)
                        )
                        fd = os.open(redirect_out, flags, 0o644)
                        os.dup2(fd, 1)
                        os.close(fd)
                    if redirect_err:
                        flags = (
                            os.O_WRONLY
                            | os.O_CREAT
                            | (os.O_APPEND if append_err else os.O_TRUNC)
                        )
                        fd = os.open(redirect_err, flags, 0o644)
                        os.dup2(fd, 2)
                        os.close(fd)
                    os.execv(found_path, parts)
                else:
                    os.waitpid(pid, 0)
            else:
                print(f"{cmd_name}: command not found")


if __name__ == "__main__":
    main()
