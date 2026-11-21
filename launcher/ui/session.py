import time

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class GameSession(QObject):
    """Один запущенный процесс игры: лог, статус, учёт времени игры."""
    output = pyqtSignal(str)
    started = pyqtSignal()
    finished = pyqtSignal(int)

    def __init__(self, inst, spec, parent=None):
        super().__init__(parent)
        self.inst, self.spec = inst, spec
        self.log, self.stages = [], []
        self._mark = None  # момент, с которого время ещё не записано
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.setWorkingDirectory(spec.cwd)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.started.connect(self._on_started)
        self.proc.finished.connect(lambda code, _s: self.finished.emit(code))
        self.proc.errorOccurred.connect(self._on_error)

    @property
    def running(self):
        return self.proc.state() != QProcess.ProcessState.NotRunning

    def start(self):
        self._emit("> " + self.spec.java + " " + " ".join(self.spec.args) + "\n")
        self.proc.start(self.spec.java, self.spec.args)

    def kill(self):
        self.proc.kill()

    def take_elapsed(self):
        """Секунды игры с прошлого вызова (для накопления времени в сборке)."""
        if self._mark is None:
            return 0.0
        now = time.monotonic()
        d, self._mark = now - self._mark, now
        return d

    def stop_clock(self):
        self._mark = None

    def _emit(self, text):
        self.log.append(text)
        self.output.emit(text)

    def _on_started(self):
        self._mark = time.monotonic()
        self.started.emit()

    def _on_error(self, err):
        self._emit(f"[ошибка запуска процесса: {err}]")
        if err == QProcess.ProcessError.FailedToStart:
            self.finished.emit(-1)

    def _read(self):
        self._emit(bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace"))
