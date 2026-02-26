import sys
import os
import termios
import tty


def get_completions(prefix, builtins):
    matches = set()
    for b in builtins:
        if b.startswith(prefix):
            matches.add(b)
    paths = os.environ.get("PATH", "").split(":")
    for path in paths:
        if os.path.isdir(path):
            try:
                for file in os.listdir(path):
                    if file.startswith(prefix):
                        full_path = os.path.join(path, file)
                        if os.access(full_path, os.X_OK):
                            matches.add(file)
            except PermissionError:
                pass
    return list(matches)


def common_prefix(strings):
    if not strings:
        return ""
    m1 = min(strings)
    m2 = max(strings)
    for i, c in enumerate(m1):
        if c != m2[i]:
            return m1[:i]
    return m1


def parse_arguments(command):
    args = []
    current_arg = ""
    in_single = False
    in_double = False
    escape = False
    for char in command:
        if escape:
            if in_double and char not in ['"', "\\", "$", "`", "\n"]:
                current_arg += "\\"
            current_arg += char
            escape = False
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == " " and not in_single and not in_double:
            if current_arg:
                args.append(current_arg)
                current_arg = ""
        elif char == "\\" and not in_single:
            escape = True
        else:
            current_arg += char
    if current_arg:
        args.append(current_arg)
    return args


def split_pipeline(command):
    cmds = []
    curr = ""
    in_s = False
    in_d = False
    esc = False
    for char in command:
        if esc:
            curr += char
            esc = False
        elif char == "'":
            if not in_d:
                in_s = not in_s
            curr += char
        elif char == '"':
            if not in_s:
                in_d = not in_d
            curr += char
        elif char == "\\" and not in_s:
            esc = True
            curr += char
        elif char == "|" and not in_s and not in_d:
            cmds.append(curr)
            curr = ""
        else:
            curr += char
    if curr.strip():
        cmds.append(curr)
    return [c.strip() for c in cmds if c.strip()]


def get_input(builtins, history_log):
    command = ""
    hist_idx = len(history_log)
    tab_count = 0
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin)
    try:
        while True:
            char = sys.stdin.read(1)
            if char == "\x1b":
                tab_count = 0
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
            if char == "\t":
                completions = get_completions(command, builtins)
                if not completions:
                    sys.stdout.write("\a")
                    tab_count = 0
                elif len(completions) == 1:
                    addition = completions[0][len(command) :] + " "
                    command += addition
                    sys.stdout.write(addition)
                    tab_count = 0
                else:
                    prefix = common_prefix(completions)
                    if len(prefix) > len(command):
                        addition = prefix[len(command) :]
                        command += addition
                        sys.stdout.write(addition)
                        tab_count = 0
                    else:
                        if tab_count == 0:
                            sys.stdout.write("\a")
                            tab_count += 1
                        else:
                            sys.stdout.write("\r\n")
                            comps = sorted(completions)
                            sys.stdout.write("  ".join(comps) + "\r\n")
                            sys.stdout.write("$ " + command)
                            tab_count = 0
                sys.stdout.flush()
                continue
            if char in ("\n", "\r"):
                sys.stdout.write("\r\n")
                return command
            elif char == "\x7f":
                tab_count = 0
                if len(command) > 0:
                    command = command[:-1]
                    sys.stdout.write("\b \b")
            elif char == "\x03":
                sys.exit(0)
            else:
                tab_count = 0
                sys.stdout.write(char)
                command += char
            sys.stdout.flush()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def append_to_history(command):
    history_file = os.path.expanduser("~/.shell_history")
    with open(history_file, "a") as f:
        f.write(command + "\n")


def execute_single(command_str, builtins_list, history_log):
    parts = parse_arguments(command_str)
    if not parts:
        return

    new_parts = []
    i = 0
    redir_out = None
    redir_err = None
    append_out = False
    append_err = False

    while i < len(parts):
        if parts[i] in (">", "1>"):
            redir_out = parts[i + 1]
            append_out = False
            i += 2
        elif parts[i] in (">>", "1>>"):
            redir_out = parts[i + 1]
            append_out = True
            i += 2
        elif parts[i] == "2>":
            redir_err = parts[i + 1]
            append_err = False
            i += 2
        elif parts[i] == "2>>":
            redir_err = parts[i + 1]
            append_err = True
            i += 2
        else:
            new_parts.append(parts[i])
            i += 1

    if not new_parts:
        return

    old_stdout = os.dup(1)
    old_stderr = os.dup(2)

    if redir_out:
        mode = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append_out else os.O_TRUNC)
        fd = os.open(redir_out, mode, 0o644)
        os.dup2(fd, 1)
        os.close(fd)
    if redir_err:
        mode = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append_err else os.O_TRUNC)
        fd = os.open(redir_err, mode, 0o644)
        os.dup2(fd, 2)
        os.close(fd)

    cmd_name = new_parts[0]

    if cmd_name == "echo":
        sys.stdout.write(" ".join(new_parts[1:]) + "\n")
    elif cmd_name == "pwd":
        sys.stdout.write(os.getcwd() + "\n")
    elif cmd_name == "type":
        if len(new_parts) > 1:
            target = new_parts[1]
            if target in builtins_list:
                sys.stdout.write(f"{target} is a shell builtin\n")
            else:
                found = False
                for path in os.environ.get("PATH", "").split(":"):
                    full_path = os.path.join(path, target)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        sys.stdout.write(f"{target} is {full_path}\n")
                        found = True
                        break
                if not found:
                    sys.stdout.write(f"{target}: not found\n")
    elif cmd_name == "history":
        limit = len(history_log)
        if len(new_parts) > 1:
            try:
                limit = int(new_parts[1])
            except ValueError:
                pass
        start_index = max(0, len(history_log) - limit)
        for j in range(start_index, len(history_log)):
            sys.stdout.write(f"{j + 1:>5}  {history_log[j]}\n")
    else:
        try:
            os.execvp(cmd_name, new_parts)
        except FileNotFoundError:
            sys.stderr.write(f"{cmd_name}: not found\n")
            os._exit(1)

    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(old_stdout, 1)
    os.dup2(old_stderr, 2)
    os.close(old_stdout)
    os.close(old_stderr)


def execute_command(command_str, builtins_list, history_log):
    cmds = split_pipeline(command_str)
    if len(cmds) == 1:
        pid = os.fork()
        if pid == 0:
            execute_single(cmds[0], builtins_list, history_log)
            os._exit(0)
        else:
            os.waitpid(pid, 0)
        return

    fd_in = 0
    pids = []
    for i, cmd in enumerate(cmds):
        is_last = i == len(cmds) - 1
        if not is_last:
            pipe_r, pipe_w = os.pipe()

        pid = os.fork()
        if pid == 0:
            if fd_in != 0:
                os.dup2(fd_in, 0)
                os.close(fd_in)
            if not is_last:
                os.dup2(pipe_w, 1)
                os.close(pipe_r)
                os.close(pipe_w)
            execute_single(cmd, builtins_list, history_log)
            os._exit(0)
        else:
            pids.append(pid)
            if fd_in != 0:
                os.close(fd_in)
            if not is_last:
                os.close(pipe_w)
                fd_in = pipe_r

    for pid in pids:
        os.waitpid(pid, 0)


def main():
    history_log = []
    builtins_list = ["echo", "exit", "type", "pwd", "cd", "history"]

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

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
            except Exception:
                sys.stdout.write(f"cd: {dest}: No such file or directory\n")
            history_log.append(command)
            append_to_history(command)
            continue
        elif parts[0] == "history" and len(parts) > 1 and parts[1] == "-r":
            history_log.append(command)
            append_to_history(command)
            file_path = parts[2] if len(parts) > 2 else ""
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    for line in f:
                        history_log.append(line.strip())
            continue

        history_log.append(command)
        append_to_history(command)
        execute_command(command, builtins_list, history_log)


if __name__ == "__main__":
    main()
