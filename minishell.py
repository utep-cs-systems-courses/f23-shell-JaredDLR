#! /usr/bin/env python3

import os
import sys

DEFAULT_PROMPT = "$$$$ "
QUIT_COMMAND = "quit"


def change_directory(path: str) -> None:
    """Change the current directory"""
    try:
        os.chdir(path)
    except OSError as e:
        print(e.strerror, file=sys.stderr)


def execute_command(arguments: list[str]) -> None:
    """Iterate through each directory in PATH until the command executes"""
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        try:
            os.execve(os.path.join(directory, arguments[0]), arguments, os.environ)
        except:
            continue
    print(f"Couldn't find command '{arguments[0]}'", file=sys.stderr)


def wait_for_child_process() -> None:
    """Wait for the child process to finish and display any exit codes"""
    exit_info = os.wait()
    if exit_info[1]:
        print(f"Program terminated: exit code {exit_info[1]}")


def run_process(arguments: list[str]) -> None:
    """Execute a command in a child process"""
    process_id = os.fork()
    if not process_id:
        execute_command(arguments)


def redirect_process_out(arguments: list[str], pathname: str) -> None:
    """Redirect a command's output to a file"""
    process_id = os.fork()
    if not process_id:
        file_descriptor = os.open(pathname, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC)
        os.dup2(file_descriptor, sys.stdout.fileno())
        execute_command(arguments)


def redirect_process_in(arguments: list[str], pathname: str) -> None:
    """Redirect a command's input to a file"""
    process_id = os.fork()
    if not process_id:
        file_descriptor = os.open(pathname, os.O_RDONLY | os.O_CLOEXEC)
        os.dup2(file_descriptor, sys.stdin.fileno())
        execute_command(arguments)


def pipe_process(write_arguments: list[str], read_arguments: list[str]) -> None:
    """Send output of a command as input of another command"""
    read_file_descriptor, write_file_descriptor = os.pipe2(os.O_CLOEXEC)
    read_process_id = os.fork()

    if read_process_id:
        write_process_id = os.fork()

        if write_process_id:
            os.close(read_file_descriptor)
            os.close(write_file_descriptor)
            wait_for_child_process()
        else:
            os.dup2(write_file_descriptor, sys.stdout.fileno())
            execute_command(write_arguments)
    else:
        os.dup2(read_file_descriptor, sys.stdin.fileno())
        execute_command(read_arguments)


def main() -> None:
    prompt = os.environ.get("PS1", DEFAULT_PROMPT)

    while True:
        command_line = input(prompt).strip()
        run_foreground = True

        if command_line == QUIT_COMMAND:
            quit()
        elif command_line[-1] == "&":
            command_line = command_line[:-1]
            run_foreground = False

        if "|" in command_line:
            commands = command_line.split("|")
            pipe_process(commands[0].split(), commands[-1].split())
        elif "<" in command_line:
            arguments = command_line.split("<")
            redirect_process_in(arguments[0].split(), arguments[-1].strip())
        elif ">" in command_line:
            arguments = command_line.split(">")
            redirect_process_out(arguments[0].split(), arguments[-1].strip())
        else:
            arguments = command_line.split()
            if arguments[0] == "cd":
                change_directory(arguments[-1])
                continue
            else:
                run_process(arguments)

        if run_foreground:
            wait_for_child_process()


if __name__ == "__main__":
    main()
