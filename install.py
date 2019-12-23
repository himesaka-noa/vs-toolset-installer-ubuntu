import argparse
import datetime
import json
import logging
import os
import sys
from contextlib import ExitStack
from functools import partial
from importlib import util
from subprocess import run, PIPE

if sys.version_info[0] == 2:
    print('Please run the script with python3')
    exit(1)

if not util.find_spec('pip'):
    print('Please run: sudo apt install python3-pip')
    exit(1)
else:
    try:
        from pip._internal.operations import freeze
    except ImportError:
        from pip.operations import freeze

logging.basicConfig(level=logging.DEBUG, filemode='a', filename='install.log')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

today = datetime.datetime.today()
date_string = str(today.year) + str(today.month).zfill(2) + str(today.day).zfill(2)
python_script_install_location = '/usr/lib/python3/dist-packages'
base_dependencies = ['git', 'checkinstall', 'autoconf', 'pkg-config', 'meson', 'ninja-build', 'libtool', 'cmake']


def check_success(func):
    def wrapper(*args, **kwargs):
        resp = func(*args, **kwargs)
        logging.debug(resp.stdout.decode())
        if resp.returncode != 0:
            logging.warning(resp.stderr.decode())
            return False
        return True

    return wrapper


def run_cmd(*args, **kwargs):
    # compatible with python3.6-
    logging.debug('{}'.format(args))
    return run(*args, **kwargs, stdout=PIPE, stderr=PIPE)


def dpkg_check_installed(pkg_name):
    resp = run_cmd(['dpkg', '-s', pkg_name])
    if resp.returncode == 0:
        logging.info('{} has been already installed.'.format(pkg_name))
        return True
    return False


def pip_check_installed(pkg_name):
    pip_list_gen = freeze.freeze()
    pip_list = [i.split('==')[0] for i in pip_list_gen]
    if pkg_name in pip_list:
        logging.info('{} has been already installed.'.format(pkg_name))
        return True
    return False


def vs_plugin_check_installed(plugin_name):
    resp = run_cmd(
        ['python3 -c "from vapoursynth import core; exit(0) if \'{}\' in dir(core) else exit(1)"'.format(plugin_name)],
        shell=True)
    if resp.returncode == 0:
        return True
    return False


@check_success
def run_shell_cmd(cmd):
    return run_cmd([cmd], shell=True)


@check_success
def untar(tar_file):
    return run_cmd(['tar', 'xzvf', tar_file])


@check_success
def delete_file(file):
    return run_cmd(['rm', file])


@check_success
def delete_folder(file):
    return run_cmd(['sudo', 'rm', '-rf', file])


def untar_and_delete(tar_file):
    if not untar(tar_file):
        logging.error('Error untaring file {}.'.format(tar_file))
        return False
    delete_file(tar_file)
    return True


@check_success
def git_clone(repo_url, tag=None):
    res = run_cmd(['git', 'clone', repo_url])
    if tag:
        current_dir = os.getcwd()
        os.chdir(repo_url.split('/')[-1].split('.')[0])
        run_cmd(['git', 'checkout', tag])
        os.chdir(current_dir)
    return res


@check_success
def download_file(url):
    return run_cmd(['wget', url])


@check_success
def apt_update():
    return run_cmd(['sudo', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', '-y', 'update'])


@check_success
def apt_install(pkg_name):
    return run_cmd(['sudo', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', '-y', 'install', pkg_name])


@check_success
def pip_install(pkg_name):
    return run_cmd(['pip3', 'install', pkg_name])


@check_success
def sudo_pip_install(pkg_name):
    return run_cmd(['sudo', 'pip3', 'install', pkg_name])


@check_success
def python_script_install(file):
    return run_cmd(['sudo', 'cp', file, python_script_install_location])


@check_success
def autogen():
    return run_cmd(['./autogen.sh'], shell=True)


@check_success
def configure(configure_options):
    return run_cmd([' '.join(['./configure'] + configure_options)], shell=True)


@check_success
def cmake():
    return run_cmd(['cmake ..'], shell=True)


@check_success
def make():
    return run_cmd(['make', '-j4'])


@check_success
def meson():
    return run_cmd(['meson', 'build'])


@check_success
def ninja_compile():
    return run_cmd(['ninja', '-C', 'build'])


@check_success
def check_install(pkg_name, pkg_version, ninja=False, custom=None):
    if ninja:
        make_commands = ['ninja', '-C', 'build', 'install']
    elif custom:
        make_commands = custom
    else:
        make_commands = []
    return run_cmd(['sudo', 'checkinstall', '-y', '--pkgname', pkg_name, '--pkgversion', pkg_version, '--provides',
                    pkg_name] + make_commands)


def custom_compile(folder_name, install_ops):
    current_dir = os.getcwd()
    with ExitStack() as stack:
        stack.callback(partial(os.chdir, current_dir))
        os.chdir(folder_name)
        for op in install_ops:
            if not run_shell_cmd(op):
                logging.error('Installation command: {} has failed.'.format(op))
                return False
        return True


def meson_compile(folder_name, pkg_name=None, pre_install_script=None,
                  post_install_script=None):
    current_dir = os.getcwd()
    with ExitStack() as stack:
        stack.callback(partial(os.chdir, current_dir))
        os.chdir(folder_name)
        pkg_name = pkg_name if pkg_name else folder_name
        pkg_version = date_string
        if pre_install_script:
            for cmd in pre_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Pre installation command: {} has failed.'.format(cmd))
                    return False
        if not meson():
            logging.error('meson for {} has failed.'.format(pkg_name))
            return False
        if not ninja_compile():
            logging.error('ninja compile for {} has failed.'.format(pkg_name))
            return False
        if not check_install(pkg_name, pkg_version, ninja=True):
            logging.error('checkinstall for {} has failed.'.format(pkg_name))
            return False
        if post_install_script:
            for cmd in post_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Post installation command: {} has failed.'.format(cmd))
                    return False
        return True


def cmake_compile(folder_name, pkg_name=None, pre_install_script=None,
                  post_install_script=None):
    current_dir = os.getcwd()
    with ExitStack() as stack:
        stack.callback(partial(os.chdir, current_dir))
        os.chdir(folder_name)
        pkg_name = pkg_name if pkg_name else folder_name
        pkg_version = date_string
        if pre_install_script:
            for cmd in pre_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Pre installation command: {} has failed.'.format(cmd))
                    return False
        delete_folder('build')
        os.mkdir('build')
        os.chdir('build')
        if not cmake():
            logging.error('cmake for {} has failed.'.format(pkg_name))
            return False
        if not make():
            logging.error('make for {} has failed.'.format(pkg_name))
            return False
        if not check_install(pkg_name, pkg_version):
            logging.error('checkinstall for {} has failed.'.format(pkg_name))
            return False
        if post_install_script:
            for cmd in post_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Post installation command: {} has failed.'.format(cmd))
                    return False
        return True


def default_compile(folder_name, use_autogen=False, configure_options=None, pkg_name=None, pkg_version=None,
                    submodule=None, pre_install_script=None, post_install_script=None, use_configure=True):
    current_dir = os.getcwd()
    with ExitStack() as stack:
        stack.callback(partial(os.chdir, current_dir))
        os.chdir(folder_name)
        if submodule:
            os.chdir(submodule)

        if not pkg_name:
            pkg_name = folder_name
        if not pkg_version:
            pkg_version = date_string
        if not configure_options:
            configure_options = []

        if pre_install_script:
            for cmd in pre_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Pre installation command: {} has failed.'.format(cmd))
                    return False
        if use_autogen and not autogen():
            logging.error('autogen for {} has failed.'.format(pkg_name))
            return False

        if use_configure and not configure(configure_options):
            logging.error('configure for {} has failed.'.format(pkg_name))
            return False
        if not make():
            logging.error('make for {} has failed.'.format(pkg_name))
            return False
        if not check_install(pkg_name, pkg_version):
            logging.error('checkinstall for {} has failed.'.format(pkg_name))
            return False
        if post_install_script:
            for cmd in post_install_script:
                if not run_shell_cmd(cmd):
                    logging.error('Post installation command: {} has failed.'.format(cmd))
                    return False
        return True


def check_and_install(pkg_name, all_pkg_info):
    logging.info('Installing {}.'.format(pkg_name))
    # use APT, and do not consider dependencies
    if pkg_name not in all_pkg_info:
        if dpkg_check_installed(pkg_name):
            return True
        if not apt_install(pkg_name):
            return False
        logging.info('{} is successfully installed from APT.'.format(pkg_name))
        return True
    pkg_info = all_pkg_info[pkg_name]
    pkg_id = pkg_info.get('identifier', pkg_name)
    # do not consider dependencies for pip
    if pkg_info['install'] == 'pip3':
        if pip_check_installed(pkg_id):
            return True
        if not pip_install(pkg_id):
            return False
        logging.info('Python package {} is successfully installed.'.format(pkg_name))
        return True
    elif pkg_info['install'] == 'pip3-sudo':
        if pip_check_installed(pkg_id):
            return True
        if not sudo_pip_install(pkg_id):
            return False
        logging.info('Python package {} is successfully installed.'.format(pkg_name))
        return True
    elif pkg_info['install'] == 'python-script':
        script_filename = pkg_info['url'].split('/')[-1]
        # check if the script is installed
        if os.path.exists(os.path.join(python_script_install_location, script_filename)):
            logging.info('Python script {} is already installed.'.format(pkg_name))
            return True

        # handle dependencies
        for pkg in pkg_info.get('dependencies', []):
            check_and_install(pkg, all_pkg_info)

        if not download_file(pkg_info['url']):
            logging.error('File {} downloading error.'.format(script_filename))
            return False
        if not python_script_install(script_filename):
            logging.error('Script {} installation error.'.format(script_filename))
            return False
        logging.info('Script {} is successfully installed.'.format(pkg_name))
        return True
    elif pkg_info['install'] == 'source':
        # check if installed
        # check with dpkg is valid, since all packages are installed with checkinstall
        # this will not find manually make installed packages
        if dpkg_check_installed(pkg_name):
            return True

        # extra check for vs plugins

        # handle dependencies
        for pkg in pkg_info.get('dependencies', []):
            check_and_install(pkg, all_pkg_info)
        # obtain the source code
        if pkg_info['url_type'] == 'git':
            folder_name = pkg_info['url'].split('/')[-1].split('.')[0]
            # remove existing repos to prevent clone error
            if os.path.exists(folder_name):
                delete_folder(folder_name)
            tag = pkg_info.get('git_tag', None)
            if not git_clone(pkg_info['url'], tag):
                return False

        elif pkg_info['url_type'] == 'targz':
            tar_filename = pkg_info['url'].split('/')[-1]
            if not download_file(pkg_info['url']):
                logging.error('File {} downloading error.'.format(tar_filename))
                return False
            if not untar_and_delete(tar_filename):
                return False
            folder_name = tar_filename[:-7]
        else:
            logging.error('Unknown url type {} for package {}.'.format(pkg_info['url_type'], pkg_name))
            return False

        # compile and install
        if pkg_info['compile_mode'] == 'default':
            pre_install_ops = pkg_info.get('pre_install_script', [])
            post_install_ops = pkg_info.get('post_install_script', [])
            use_autogen = pkg_info.get('autogen', False)
            submodule = pkg_info.get('submodule', None)
            use_configure = pkg_info.get('configure', True)
            configure_options = pkg_info.get('configure_options', None)
            if not default_compile(folder_name, use_autogen=use_autogen, configure_options=configure_options,
                                   submodule=submodule, pkg_name=pkg_name, pre_install_script=pre_install_ops,
                                   post_install_script=post_install_ops, use_configure=use_configure):
                return False
        elif pkg_info['compile_mode'] == 'custom':
            if not custom_compile(folder_name, pkg_info['install_script']):
                return False
        elif pkg_info['compile_mode'] == 'cmake':
            pre_install_ops = pkg_info.get('pre_install_script', [])
            post_install_ops = pkg_info.get('post_install_script', [])
            if not cmake_compile(folder_name, pkg_name=pkg_name, pre_install_script=pre_install_ops,
                                 post_install_script=post_install_ops):
                return False
        elif pkg_info['compile_mode'] == 'meson':
            pre_install_ops = pkg_info.get('pre_install_script', [])
            post_install_ops = pkg_info.get('post_install_script', [])
            if not meson_compile(folder_name, pkg_name=pkg_name, pre_install_script=pre_install_ops,
                                 post_install_script=post_install_ops):
                return False
        else:
            logging.error('Unknown compile method {} for package {}.'.format(pkg_info['compile_mode'], pkg_name))

    else:
        logging.error('Unknown install method {} for package {}.'.format(pkg_info['install'], pkg_name))
        return False
    logging.info('Package {} is successfully installed from source.'.format(pkg_name))
    if pkg_name.startswith('vs-') and pkg_info['install'] != 'python-script':
        plugin_name = pkg_name[3:]
        if vs_plugin_check_installed(plugin_name):
            logging.info('VS plugin {} is verified to be installed.'.format(plugin_name))
            return True
        else:
            logging.warning('VS plugin {} is not found in namespace.'.format(plugin_name))
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description='Install VapourSynth and related tools on Ubuntu')
    parser.add_argument('package', nargs='*', help='packages to install')
    parser.add_argument('-d', dest='dest', default='video_encoding_tools', help='place to store source code')
    parser.add_argument('--plugins-only', dest='plugins_only', action='store_true', default=False,
                        help='install all filters only')
    args = parser.parse_args()

    # possible locations for package_info.json
    package_info_dirs = [os.getcwd(), os.path.dirname(os.path.realpath(__file__))]
    for package_info_dir in package_info_dirs:
        location_candidate = os.path.join(package_info_dir, 'package_info.json')
        if os.path.exists(location_candidate):
            package_info_location = location_candidate
            break
    else:
        # fetch from internet
        download_file(
            'https://raw.githubusercontent.com/himesaka-noa/vs-toolset-installer-ubuntu/master/package_info.json')
        package_info_location = os.path.join(os.getcwd(), 'package_info.json')
    with open(package_info_location, 'r') as f:
        pkg_info_list = json.load(f)
    all_pkg_info = {i['name']: i for i in pkg_info_list}
    apt_update()
    if not args.package or len(args.package) == 0:
        install_list = base_dependencies + [i['name'] for i in pkg_info_list]
    elif args.plugins_only:
        install_list = base_dependencies + [i['name'] for i in pkg_info_list if i['name'].startswith('vs-')]
    else:
        install_list = base_dependencies + args.package
    logging.info('Check and install: {}'.format(install_list))

    os.makedirs(args.dest, exist_ok=True)
    os.chdir(args.dest)
    logging.info('Downloads will save to: {}'.format(args.dest))
    failed_packages = []
    for pkg in install_list:
        if not check_and_install(pkg, all_pkg_info):
            failed_packages.append(pkg)
    logging.info('The following packages have failed to install: {}.'.format(failed_packages))


if __name__ == '__main__':
    main()
