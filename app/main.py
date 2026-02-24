import sys
import os
import termios
import tty

# ... (keep your get_lcp, parse_arguments, and execute_command functions) ...


def get_matches(prefix):
    path_dirs = os.environ.get("PATH", "").split(":")
    matches = set()
    for directory in path_dirs:
        if os.path.isdir(directory):
            for file in os.listdir(directory):
                if file.startswith(prefix):
                    matches.add(file)
    return sorted(list(matches))


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        command = ""
        while True:
            # Setting terminal to raw mode to catch single keypresses
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            if char == "\r" or char == "\n":  # Enter key
                sys.stdout.write("\n")
                break
            elif char == "\t":  # Tab key
                matches = get_matches(command)
                if len(matches) == 1:
                    # Only one match: complete it and add a space
                    completed = matches[0][len(command) :] + " "
                    command += completed
                    sys.stdout.write(completed)
                elif len(matches) > 1:
                    # Multiple matches: complete to the LCP, no space
                    lcp = get_lcp(matches)
                    if len(lcp) > len(command):
                        completed = lcp[len(command) :]
                        command += completed
                        sys.stdout.write(completed)
                    else:
                        # Optional: Ring bell if no more shared prefix
                        sys.stdout.write("\a")
                sys.stdout.flush()
            elif ord(char) == 127:  # Backspace
                if len(command) > 0:
                    command = command[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            else:
                command += char
                sys.stdout.write(char)
                sys.stdout.flush()

        if command.strip():
            args = parse_arguments(command)
            execute_command(args)


if __name__ == "__main__":
    main()
