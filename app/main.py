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


def split_pipeline(command):
    commands = []
    current = ""
    in_single = False
    in_double = False
    escape = False
    for char in command:
        if escape:
            current += char
            escape = False
        elif char == "'":
            if not in_double:
                in_single = not in_single
            current += char
        elif char == '"':
            if not in_single:
                in_double = not in_double
            current += char
        elif char == "\\" and not in_single:
            escape = True
            current += char
        elif char == "|" and not in_single and not in_double:
            commands.append(current)
            current = ""
        else:
            current += char
