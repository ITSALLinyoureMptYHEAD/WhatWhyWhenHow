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
    if not strings: return ""
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
            if not in_d: in_s = not in_s
            curr += char
        elif char == '"':
            if not in_s: in_d = not in_d
            curr += char
        elif char == '\\' and not in_s:
            esc = True
            curr += char
        elif char == '|' and not in_s and not in_d:
            cmds.append(curr)
            curr = ""
        else:
            curr += char
    cmds.append(curr)
    return [c.strip() for c in cmds if c.strip()]

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
                elif next1 == "[" and next