import os
import sys


def main():
    path_template = "tezos-reward.service_template"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path_service = os.path.join(dir_path, "tezos-reward.service")
    python_executable=sys.executable

    # if len(sys.argv)==1:
    #    print("ERROR: Arguments not given. See list of arguments below:")
    #    os.system(dir_path+"/src/main.py --help")

    with open(path_template, 'r') as template_file:
        content = template_file.read()
        content = content.replace("<USER>", os.getlogin())
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


if __name__ == '__main__':
    main()
