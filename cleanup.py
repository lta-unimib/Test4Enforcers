import os
import subprocess

from dotenv import dotenv_values
from config import get_config_for_policy


def main():
    env = dotenv_values('.env')

    is_faulty = env['TARGET_POLICY_FAULTY']
    config = get_config_for_policy(env['TARGET_POLICY'], is_faulty)

    enforcer_package = config['enforcer_package']
    print(f'- Removing {enforcer_package}')
    subprocess.call(f'adb uninstall {enforcer_package}', shell=True)

    base_enforcer = config['default_enforcer_apk']
    enforcer_apk = os.path.join(os.getcwd(), 'resources', base_enforcer)
    print(f'- Installing default {enforcer_apk}')
    subprocess.call(f'adb install {enforcer_apk}', shell=True)

    print(f'- Disabling module from xposed')
    xposed_file = env['XPOSED_FOLDER'] + '/conf/modules.list'
    subprocess.call(f'adb shell "su -c \'echo -n > {xposed_file}\'', shell=True)
    # subprocess.call(f'adb shell "su -c \'touch {xposed_file}\'', shell=True)

    print(f'- Rebooting device...')
    subprocess.call(f'adb reboot', shell=True)

if __name__ == '__main__':
    main()
