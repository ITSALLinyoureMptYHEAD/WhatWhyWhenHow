import sys
import os


#
# import shlex
# args = shlex.split(command)
# This automatically handles single quotes, double quotes, and escaped characters
#
def parse_arguments(command):
    args = []
    current_arg = ""
    # """switches""" eg. b_l_a_h = False
    in_single_quotes = False
    in_double_quotes = False
    escape_next = False
    for char in command:
        if escape_next:
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
        elif char == "\\" and not in_single_quotes and not in_double_quotes:
            escape_next = True
        else:
            # Add any other character (or spaces inside quotes) to the argument
            # now we do current_arg = current_arg + char, but faster
            current_arg += char
    #
    # Imagine you have a piece of paper.
    #   Without +=:
    # You take a new blank paper. You look at your old paper (which says "ec"), copy "ec" onto the new paper,
    #  and then write "h" at the end. Then you throw away the old paper.
    # current_arg = current_arg + char
    #   With +=:
    # You just take your pen and write "h" at the end of the paper you already have.
    # current_arg += char
    # It is just a shortcut that means "stick this onto the end of what is already there."
    #
    # Add the final argument after the loop finishes
    if current_arg:
        args.append(current_arg)
    return args


def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        builtins = {"echo", "exit", "type", "pwd", "cd"}
        if command == "exit":
            break
        elif command.startswith("echo "):
            # Parse the command using your new function
            args = parse_arguments(command)
            # Join everything after the word "echo" (which is args[0]) with a space
            output = " ".join(args[1:])
            print(output)
        elif command == "echo":
            print("")
        elif command.startswith("type"):
            found = False
            args = command.split("type ", 1)
            command_name = args[1]
            if args[1] in ("echo", "exit", "type", "pwd", "cd"):
                print(f"{args[1]} is a shell builtin")
                continue
            elif command_name not in builtins:
                path = os.environ.get("PATH", "")
                path_separator = os.pathsep
                for directory in path.split(path_separator):
                    full_path = os.path.join(directory, command_name)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        print(f"{command_name} is {full_path}")
                        found = True
                        break

                if not found:
                    try:
                        print(f"{command_name}: not found")
                    except OSError:
                        break

        elif command.split()[0] not in builtins:
            found = False
            path = os.environ.get("PATH", "")
            path_separator = os.pathsep
            # old code: 'parts = command.split()' , new code:
            parts = parse_arguments(command)
            #
            command_name = parts[0]
            for directory in path.split(path_separator):
                full_path = os.path.join(directory, command_name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    found = True
                    break
            if found:
                pid = os.fork()
                if pid == 0:
                    os.execvp(command_name, parts)
                else:
                    os.waitpid(pid, 0)
            if not found:
                try:
                    print(f"{command_name}: not found")
                except OSError:
                    break

        elif command == ("pwd"):
            current_location = os.getcwd()
            if current_location:
                print(current_location)
            else:
                print("Error: Could not retrieve directory.")

        elif command == "cd" or command.startswith("cd"):
            parts = command.split(" ", 1)
            # Split the command to see if there's a second part
            if len(parts) == 1 or parts[1].strip() == "":
                #
                # How .strip() works:
                # .strip() only removes invisible "whitespace" (like if you accidentally hit the spacebar...
                # ...  five times after typing "cow").
                # Input: "cow   "
                # Result: "cow"
                # It doesn't touch the letters in the middle.
                #
                # No folder specified? Go to the HOME directory!
                destination = os.environ.get("HOME")
            else:
                # Folder specified? Use that one.
                destination = parts[1].strip()
            # If the user types "cd /Desktop", this grabs "/Desktop"
            if destination and destination.startswith("~"):
                home = os.environ.get("HOME")
                # This swaps the ~ for the actual home path (like /home/user)
                destination = destination.replace("~", home, 1)
            #
            # How .replace() works:
            # # Use commas to separate arguments: 1st is what to find ("~"),
            # 2nd is what to replace it with (home),
            # 3rd is "1" to only replace the first occurrence.
            #
            try:
                if destination:
                    os.chdir(destination)
            # chdir stands for CHange DIRectory
            # what about ../ you ask? yeah it(os.chdir) handles the parents dir
            # (one before the one we are in rn)
            except FileNotFoundError:
                print(f"cd: {destination}: No such file or directory")
            except NotADirectoryError:
                print(f"cd: {destination}: Not a directory")


if __name__ == "__main__":
    main()
