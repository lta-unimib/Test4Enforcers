import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)

def disable_enforcer(enabled_modules_path, enforcer, wait_for_device=True):
    """Disable the specified Xposed module in the emulator/connected device.

    Args:
        enabled_modules_path (String): Location of the enabled_modules.xml in the device fs
        enforcer (String): The module to disable
    """
    subprocess.call(f'adb shell "su -c \'echo -n > {enabled_modules_path}\'"', shell=True)
    subprocess.call('adb reboot', shell=True)

    if wait_for_device:
        subprocess.call('adb wait-for-device', shell=True)

    # with tempfile.TemporaryFile() as buf:
    #     subprocess.call(f'adb pull "{enabled_modules_path}" "{buf.name}"', shell=True)
    #     modules = ET.parse(buf.name)
    #     root = modules.getroot()

    #     node = root.find(f'./int[@name=\'{enforcer}\']')
    #     if node is None:
    #         return

    #     root.remove(node)
    #     modules.write(buf.name, encoding='utf-8', xml_declaration=True)
    #     subprocess.call(f'adb push "{buf.name}" "{enabled_modules_path}"', shell=True)
    #     subprocess.call('adb reboot', shell=True)


def enable_enforcer(enabled_modules_list_file, enforcer_apk_path, wait_for_device=False):
    """Enable the specified Xposed module in the emulator/connected device.

    Args:
        enabled_modules_list_file (String): Location of the enabled_modules.xml in the device fs
        enforcer_apk_path (String): The module to disable
        wait_for_device (bool): Wait for device to be discoverable by adb before returning.
            Note that when adb wait-for-device ends, the device might still be in the boot
            process and could be unresponsive to commands.
    """
    subprocess.call(f'adb shell "su -c \'[ -f {enforcer_apk_path} ] && echo {enforcer_apk_path} > {enabled_modules_list_file}\'"', shell=True)
    subprocess.call('adb reboot', shell=True)
    if wait_for_device:
        subprocess.call('adb wait-for-device', shell=True)

    # with tempfile.TemporaryFile() as buf:
    #     subprocess.call(f'adb pull "{enabled_modules_path}" "{buf.name}"', shell=True)
    #     modules = ET.parse(buf.name)
    #     root = modules.getroot()

    #     node = root.find(f'./int[@name=\'{enforcer}\']')
    #     if node is None:
    #         node = ET.Element('int')
    #         node.set('name', enforcer)
    #         root.append(node)

    #     node.set('value', '1')
    #     modules.write(buf.name, encoding='utf-8', xml_declaration=True)
    #     subprocess.call(f'adb push "{buf.name}" "{enabled_modules_path}"', shell=True)
    #     subprocess.call('adb reboot', shell=True)
