# Test4enforcers
Test4Enforcers is the first test case generation approach designed to address the challenge of testing the correctness of software enforcers.
It exploits Droidbot, a state-of-the-art test input generation tool for Android apps, to send to the connected Android device event sequences through which it explores the app under test and to validate enforcers for Android apps.

## Folder structure
Test4Enforcers project is composed of different stand-alone parts that work in conjunction to test enforcer on device.
It is structured as follows:
- `bin/`: contains utils and CLI runnable scripts. At the current stage, it only contains an utility to convert an enforcer to a json I/O automaton for HSI method to work.
- `mutation-generator/`: contains the GUI for major and mutants generation. The README.md in this folder further explains how to interact with the tool to generate mutated enforcers.
- `resources/`: stores compiled apks (both faulty and correct versions) of applications under test, json I/O automatons and enforcer apks.

## Prerequisites
To run Test4Enforcers you will need:
- Android SDK
- Python 3
- Java 8
- Droidbot
- An emulator/device with Xposed installed

## Environment
Set up the following environment variables pointing at the correct folders:
1. Android SDK:

    - ANDROID_HOME
      - Default location is `/usr/lib/android-sdk` (*nix) or `C:/Users/<your_pc_name>/AppData/Local/Android/Sdk` (Windows)
    - TOOLS
      - Default location is `%ANDROID_HOME%/tools` (*nix) or `%ANDROID_HOME%/tools` (Windows)
    - PLATFORM_TOOLS
      - Default location is `%ANDROID_HOME%/platform-tools` (*nix) or `%ANDROID_HOME%/platform-tools` (Windows)
    - EMULATOR
      - Default location is `%ANDROID_HOME%/emulator` (*nix) or `%ANDROID_HOME%/emulator` (Windows)

2. Java 8:

    On Windows OS, set the following enviroment variable:
    - JAVA_HOME
      - It should be C:/Program Files/Java/jdk1.8.0_191/bin

3. Droidbot:

        git clone https://github.com/honeynet/droidbot.git
        cd droidbot/
        pip install -e .

4. Xposed installed on the emulator/device:
    - https://repo.xposed.info/module/de.robv.android.xposed.installer

5. Application to test, its policy enforcer and ProactiveLibraries.apk installed on the device.

## How to use the tool
1. Open the Android emulator or connect a physical device to the computer.
2. Make sure either the emulator or the device is recognized by ADB (use `adb devices` command).
3. If necessary, install the target application and the enforcer of the policy to test.
4. If necessary, install ProactiveLibraries.apk and open it. In the application list, select the target application and enable the enforcers you want to test.
5. If you dont have a `.env` file in the root of this project, make a copy of `.env.example`.
6. Update the `.env` settings with the following values:
   - `TARGET_POLICY`: the policy under test.
   - `TARGET_POLICY_FAULTY`: whether the target policy is being tested on correct or faulty application.
   - `DROIDBOT_REBOOT_DELAY`: how many seconds to wait between device reboots. Suggested values are: 20 seconds for emulator and 70 seconds for physical device.
   - `DEVICE_IS_EMULATOR`: whether the application is running on an emulator or physical device.
   - `OUTPUT_PATH`: where to store droidbot and Test4Enforcers outputs.
   - `XPOSED_FOLDER`: contains the location of the xposed folder where the `conf` and `log` folders are located. This should be already set to the correct path for the emulator (the default for xposed on android 7 is already set in `.env.example` file)
   - (mutation testing only) `MUTATIONS_PATH`: the location of the compiled enforcer mutations
   - (mutation testing only) `MUTATIONS_SKIP_UNTIL`: skip the mutations below or equal to the provided id (useful if Genymotion crashes during the execution).
   - (mutation testing only) `MUTATIONS_SKIP_SEQUENCE_INDEX`: skip the sequences below or equal to the provided id (useful if Genymotion crashes during the execution).
   - `SKIP_DROIDBOT_EXPLORATION`: whether to skip the initial droidbot exploration or not (useful if Genymotion crashes during the execution).

7. In the `main.py` update the following variable:
   - `event_list`: list of method used to map the graph.

8. After these changes use `python3 ./main.py` to execute the script. Test4Enforcers expects the enforcer to be disabled beforehand. Its activation and deactivation will be managed automatically by the script. In case the script exits unexpectedly, make sure to manually disable the enforcer or run `cleanup.py` before running a new test.

### Cleanup
During mutation testing, if the android emulator crashes, it would be left in an unconsistent state for a new execution.
To overcome this problem, run the `cleanup.py` script once, which will perform the following actions:

1. Uninstall the enforcer from device
2. Install the original enforcer apk (its apk must be provided)
3. Deactivate the enforcer from Xposed configuration
4. Reboot the device

# Automaton to JSON
Test4enforcer packages an handy tool to convert an editautomaton (generated through Proactive Libraries' modeling editor) to a JSON representation of an I/O automaton. This format will be used by the HSI module to generate test sequences.

## Usage
Open a terminal session in the `bin` folder of this project and run the script with:
```py
$ python -m automaton2json.py "path\\to\\automaton.editautomaton"
```

The default behaviour will create an output json file in the same folder as the input `.editautomaton` file. To cusomize the output filename or location, pass the `-o` (`--output`) argument to the command.

For more in-depth usage info use the `--help` flag.
