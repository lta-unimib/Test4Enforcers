import os
import re
import shutil
import subprocess
import sys
import tempfile

from PyQt5 import uic
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QProgressBar, QTreeWidgetItem
from natsort import natsorted


class BackgroundTask(QThread):
    complete = pyqtSignal(str)

    def __init__(self, command, parent=None):
        super(QThread, self).__init__()
        self.command = command

    def run(self):
        try:
            output = subprocess.check_output(self.command, stderr=subprocess.STDOUT, shell=True, text=True)
            self.complete.emit(output)
        except subprocess.CalledProcessError as e:
            self.complete.emit(e.output)

class App(QMainWindow):
    def __init__(self):
        super(App, self).__init__()
        uic.loadUi('ui/application.ui', self)

        self.generator_thread = None
        self.connect_signals()
        self.initialize_mutations()
        self.show()

    def connect_signals(self):
        # self.majorPath.setText(r'C:\Users\mdexp\Uni\UniLM\Tesi\major')
        self.majorPath.setCursorPosition(0)
        self.pickMajorPath.clicked.connect(self.ask_path('Select major path...', self.majorPath))

        # self.sourceFile.setText(r'C:/Users/mdexp/Uni/UniLM/Tesi/proactivelibraries/org.eclipse.acceleo.policyenforcergenerator/modenforcer/LocationManagerServiceEnforcer/app/src/main/java/com/proactive/locationmanagerserviceenforcer/LocationManagerServiceEnforcer.java')
        self.sourceFile.setCursorPosition(0)
        self.pickSourceFile.clicked.connect(self.ask_path('Select enforcer source file...', self.sourceFile, files_only=True, filters='Java Files (*.java)'))

        self.mutationsOutputPath.setText(os.path.join(os.getcwd(), 'mutations'))
        self.mutationsOutputPath.setCursorPosition(0)
        self.pickMutationsOutputPath.clicked.connect(self.ask_path('Select destination path...', self.mutationsOutputPath))

        self.pickMmlFile.clicked.connect(self.ask_path('Select MML settings file...', self.mmlFile, files_only=True, filters='Major MML settings (*.mml)')),
        self.mmlFile.textChanged.connect(lambda: self.checkMutationGroupFilter.setChecked(False))

        self.checkMutationGroupFilter.stateChanged.connect(lambda state: (
            state and self.mmlFile.clear(),
            self.mutationsLabel.setEnabled(state),
            self.mutationsTree.setEnabled(state),
        ))
        self.generateButton.clicked.connect(self.generate)

        # Compile Tab
        self.pickMutationsInputPath.clicked.connect(self.ask_path('Select input path...', self.mutationsInputPath))
        self.copyMutationsPath.clicked.connect(lambda: self.mutationsInputPath.setText(self.mutationsOutputPath.text()))

        # self.enforcerPath.setText(r'C:\Users\mdexp\Uni\UniLM\Tesi\proactivelibraries\org.eclipse.acceleo.policyenforcergenerator\modenforcer\LocationManagerServiceEnforcer')
        self.enforcerPath.setCursorPosition(0)
        self.pickEnforcerPath.clicked.connect(self.ask_path('Select enforcer base project...', self.enforcerPath))

        self.apkOutputPath.setText(os.path.join(os.getcwd(), 'apk'))
        self.pickApkOutputPath.clicked.connect(self.ask_path('Select apk output path...', self.apkOutputPath))

        self.mutantsLogPath.setText(os.path.join(os.getcwd(), 'mutants.log'))
        self.pickMutantsLogPath.clicked.connect(self.ask_path('Select mutants.log file path...', self.mutantsLogPath, files_only=True, filters='Log files (*.log)'))

        self.flagDisableLogs.clicked.connect(self.estimate_generated_apks)
        self.flagDisableHookMethod.clicked.connect(self.estimate_generated_apks)
        self.flagDisableStacktrace.clicked.connect(self.estimate_generated_apks)
        self.dropFromLine.textEdited.connect(self.estimate_generated_apks)
        self.compileButton.clicked.connect(self.compile_projects)

        self.logClearButton.clicked.connect(lambda: self.logWindow.setPlainText(''))

    def ask_path(self, title, target_widget, files_only=False, filters=None):
        def _ask_path():
            if files_only:
                selected, _ = QFileDialog.getOpenFileName(self, title, '.', filters)
            else:
                selected = QFileDialog.getExistingDirectory(self, title, '.')

            if selected:
                target_widget.setText(selected)

        return _ask_path

    def initialize_mutations(self):
        mutations = ['AOR', 'LOR', 'COR', 'ROR', 'SOR', 'ORU', 'EVR', 'LVR', 'STD']

        for mutation in mutations:
            mutation_item = QTreeWidgetItem()
            mutation_item.setCheckState(0, Qt.CheckState.Unchecked)
            mutation_item.setText(0, mutation)

            self.mutationsTree.addTopLevelItem(mutation_item)

    def generate(self):
        major_bin_path = os.path.join(self.majorPath.text(), 'bin')
        major_executable = os.path.join(major_bin_path, 'javac')
        if not os.path.exists(major_executable):
            QMessageBox.critical(self, 'Error', 'Major executable not found!\n\nMake sure you selected the correct path.')
            return

        source_file = self.sourceFile.text()
        if not os.path.exists(source_file):
            QMessageBox.critical(self, 'Error', 'Source file not found!\n\nSpecify the correct file to mutate.')
            return

        settings_file = self.mmlFile.text()
        if settings_file:
            if not os.path.exists(settings_file):
                QMessageBox.critical(self, 'Error', 'Settings file not found!\n\nSpecify the correct file settings file to use.')
                return

            if not self.compile_mml_settings():
                return
            settings_file = f'={settings_file}.bin'

        progress_bar = QProgressBar()
        progress_bar.setMaximumHeight(30)
        progress_bar.setMaximum(0)
        self.statusBar.addPermanentWidget(progress_bar)

        mutants_output_path = self.mutationsOutputPath.text()
        if os.path.exists(mutants_output_path):
            shutil.rmtree(mutants_output_path)
        os.makedirs(mutants_output_path)

        flag = settings_file
        if self.checkMutationGroupFilter.isChecked() or not settings_file:
            flag = self.compute_major_generation_flags()

        command = ' '.join([
            'bash.exe',
            major_executable,
            # f'-XMutator:{mutator_flag}',
            f'-XMutator{flag}',
            '-Xlint:none',
            '-J-Dmajor.export.mutants=true',
            f'-J-Dmajor.export.directory={mutants_output_path}',
            f'-cp "android.jar;xposed-api-82.jar;xposed-api-82-sources.jar"',
            source_file,
        ])

        self.generator_thread = BackgroundTask(command)
        self.generator_thread.complete.connect(lambda x: (
            self.logWindow.insertPlainText(x),
            self.statusBar.removeWidget(progress_bar),
            QMessageBox.information(self, 'Process complete', 'Generation has been completed successfully.\nMutations has been saved in the specified folder.')
        ))
        self.generator_thread.start()

    def compile_mml_settings(self):
        major_bin_path = os.path.join(self.majorPath.text(), 'bin')
        mml_compiler_executable = os.path.join(major_bin_path, 'mmlc')
        settings_file = self.mmlFile.text()

        print('Compiling MML script')
        try:
            output = subprocess.check_output(' '.join([
                'bash.exe',
                mml_compiler_executable,
                settings_file,
            ]), shell=True, text=True)
            print(output)
        except subprocess.CalledProcessError as e:
            print(e.output)
            QMessageBox.critical(self, 'Compilation error', 'Settings compilation error!\n\nMake sure the syntax is correct!')
            return False

        return True

    def compute_major_generation_flags(self):
        active_mutations = []
        root = self.mutationsTree.invisibleRootItem()
        for i in range(root.childCount()):
            if root.child(i).checkState(0) == Qt.CheckState.Checked:
                active_mutations.append(root.child(i).text(0))

        mutator_flag = ':ALL'
        if active_mutations:
            mutator_flag = ':' + ','.join(active_mutations)

        return mutator_flag

    def estimate_generated_apks(self):
        estimated_count = len(self.keep_valid_mutations())
        self.estimatedCountLabel.setText(f'A total of {estimated_count} mutants apk(s) will be generated.')

    def compile_projects(self):
        mutations_input_path = self.mutationsInputPath.text()
        if not os.path.exists(mutations_input_path):
            QMessageBox.critical(self, 'Error', 'Mutations folder not found!\n\nSpecify the correct mutations to compile.')
            return

        enforcer_path = self.enforcerPath.text()
        if not os.path.exists(enforcer_path):
            QMessageBox.critical(self, 'Error', 'Enforcer project not found!\n\nSpecify the correct project to use as scaffold.')
            return

        mutants_log_path = self.mutantsLogPath()
        if not os.path.exists(mutants_log_path) or not os.path.isfile(mutants_log_path):
            QMessageBox.critical(self, 'Error', 'Mutants.log file not found!\n\nSpecify the correct mutants.log file.')
            return

        apk_path = self.apkOutputPath.text()
        if os.path.exists(apk_path):
            shutil.rmtree(apk_path)
        os.makedirs(apk_path)

        # Prepare base project folder
        temp = tempfile.mkdtemp()
        shutil.copytree(enforcer_path, temp, dirs_exist_ok=True)

        # Retain enforcers which are useful to test
        valid_mutations = self.keep_valid_mutations()

        cwd = os.getcwd()
        for directory in natsorted(os.listdir(mutations_input_path)):
            if directory in valid_mutations:
                print(f'> Generating apk for mutant {directory} in path: {temp}')
                src_directory = os.path.join(temp, 'app', 'src', 'main', 'java')
                mutant_directory = os.path.join(mutations_input_path, directory)

                shutil.rmtree(src_directory)
                shutil.copytree(mutant_directory, src_directory, dirs_exist_ok=True)

                os.chdir(temp)
                subprocess.call('gradle build', shell=True)
                os.chdir(cwd)

                generated_apk = os.path.join(temp, 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk')
                if os.path.exists(generated_apk):
                    shutil.move(generated_apk, os.path.join(apk_path, f'{directory}.apk'))
                else:
                    print(f'> Generation failure. Mutation {directory} cannot be compiled!')

    def keep_valid_mutations(self):
        valid = set()

        flags = []
        if self.flagDisableLogs.isChecked():
            flags.append('XposedBridge\.log')
        if self.flagDisableHookMethod.isChecked():
            flags.append('findAndHookMethod')
        if self.flagDisableStacktrace.isChecked():
            flags.append('e.printStackTrace')

        drop_from = None
        try:
            if self.dropFromLine.text():
                drop_from = int(self.dropFromLine.text())
        except:
            drop_from = None

        mutants_log_path = self.mutantsLogPath.text()
        if not os.path.exists(mutants_log_path) or not os.path.isfile(mutants_log_path):
            return valid

        exclusions = ''.join(map(lambda x: f'(?!{x})', flags))
        pattern = re.compile(r'(\d+):(.+):(.+):(.+):(.+):(\d+):(?:'+ exclusions + r'(.+)|'+ exclusions + r'(.+\s.+)) \|==> (.+)')

        with open(mutants_log_path) as f:
            lines = f.read()

        matches = pattern.finditer(lines, re.MULTILINE)
        for match in matches:
            mutation_id, op, original_op, replacement_op, class_fqdn, line, content, multiline_content, replacement = match.groups()
            line = int(line)

            if content is None:
                content = multiline_content.replace('\n', '')

            if drop_from is None or (drop_from and line < drop_from):
                valid.add(mutation_id)

        return valid

app = QApplication(sys.argv)
window = App()
sys.exit(app.exec_())
