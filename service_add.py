import os
import sys
import argparse
from src.Constants import BASE_DIR, CONFIG_DIR
from util.exit_program import exit_program, ExitCode


def command_line_arguments():
    parser = argparse.ArgumentParser(
        description="Stop the running trd process.", prog="trd_stopper"
    )
    default_config_dir = os.path.join(os.path.normpath(BASE_DIR), CONFIG_DIR, "")
    parser.add_argument(
        "-f",
        "--config_dir",
        help=(
            "Directory to find configuration files and the lock file. " "Default: {}"
        ).format(default_config_dir),
        default=default_config_dir,
    )
    return parser.parse_args()


def main():
    path_template = "tezos-reward.service_template"
    args = command_line_arguments()
    config_dir = os.path.join(os.path.expanduser(os.path.normpath(args.config_dir)), "")
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_service = os.path.join(dir_path, "tezos-reward.service")
    # in windows ['C:', 'Users', 'user_name', 'tezos-reward-distributor']
    # in linux ['', 'home', 'user_name', 'tezos-reward-distributor']
    path_split = dir_path.split(os.sep)
    username_from_path = (
        path_split[2]
        if len(path_split) > 3 and path_split[1] in ["Users", "home"]
        else None
    )
    username_from_system = get_username()

    username = username_from_path if username_from_path else username_from_system

    if username_from_path is not None and username_from_path != username_from_system:
        print(
            "User name from path '{}' and user name from system does not match [{}!={}].".format(
                dir_path, username_from_path, username_from_system
            )
        )
        print(
            "User name inside service definition file '{}' is '{}'. Make sure it is correct!".format(
                path_service, username
            )
        )
    elif username == "root":
        print(
            "User name inside service definition file '{}' is 'root'. Make sure it is correct!".format(
                path_service
            )
        )

    python_executable = sys.executable

    # if len(sys.argv)==1:
    #    print("ERROR: Arguments not given. See list of arguments below:")
    #    os.system(dir_path+"/src/main.py --help")

    with open(path_template, "r") as template_file:
        content = template_file.read()
        content = content.replace("<USER>", username)
        content = content.replace("<PYTHON_PATH>", python_executable)
        content = content.replace("<ABS_PATH_TO_BASE>", dir_path)
        content = content.replace("<OPTIONS>", " ".join(sys.argv[1:]))
        content = content.replace("<CONFIGDIR>", config_dir)
        content = content.replace("<STOPARGS>", " --config_dir " + str(config_dir))

        print("-------------")
        print(content)
        print("-------------")

        try:
            with open(path_service, "w") as service_file:
                service_file.write(content)
        except Exception as e:
            import errno

            print("Exception during write operation invoked: {}".format(e))
            if e.errno == errno.ENOSPC:
                error_msg = "Exception during write operation invoked: {}. Not enough space on device.".format(
                    e
                )
                exit_program(ExitCode.NO_SPACE, error_msg)
            else:
                error_msg = "Exception during write operation invoked: {}".format(e)
                exit_program(ExitCode.GENERAL_ERROR, error_msg)

    cmd = "systemctl enable " + path_service
    print("Running command:'{}'".format("systemctl enable " + path_service))
    os.system(cmd)


def get_username():
    try:
        import pwd
    except ImportError:
        import getpass

        pwd = None

    if pwd:
        return pwd.getpwuid(os.geteuid()).pw_name
    else:
        return getpass.getuser()


if __name__ == "__main__":
    main()
