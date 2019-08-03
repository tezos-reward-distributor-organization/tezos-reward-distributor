import os
import sys


def main():
    path_template = "tezos-reward.service_template"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_service = os.path.join(dir_path, "tezos-reward.service")
    # in windows ['C:', 'Users', 'user_name', 'tezos-reward-distributor']
    # in linux ['', 'home', 'user_name', 'tezos-reward-distributor']
    path_split = dir_path.split(os.sep)
    username_from_path = path_split[2] if len(path_split) > 3 and path_split[1] in ['Users','home'] else None
    username_from_system = get_username()

    username = username_from_path if username_from_path else username_from_system

    if username_from_path is not None and username_from_path != username_from_system:
        print("User name from path '{}' and user name from system does not match [{}!={}].".format(dir_path, username_from_path, username_from_system))
        print("User name inside service definition file '{}' is {}. Make sure it is correct!".format(path_service, username))
    elif username=='root':
        print("User name inside service definition file '{}' is 'root'. Make sure it is correct!".format(path_service))


    python_executable=sys.executable

    # if len(sys.argv)==1:
    #    print("ERROR: Arguments not given. See list of arguments below:")
    #    os.system(dir_path+"/src/main.py --help")

    with open(path_template, 'r') as template_file:
        content = template_file.read()
        content = content.replace("<USER>", username)
        content = content.replace("<PYTHON_PATH>", python_executable)
        content = content.replace("<ABS_PATH_TO_BASE>", dir_path)
        content = content.replace("<OPTIONS>", ' '.join(sys.argv[1:]))

        print("Content is :")
        print("-------------")
        print(content)
        print("-------------")
        with open(path_service, 'w') as service_file:
            service_file.write(content)

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

if __name__ == '__main__':
    main()
