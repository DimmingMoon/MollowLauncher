from PyQt6.QtCore import QThread, pyqtSignal


class Worker(QThread):
    progress = pyqtSignal(str, int, int)
    ok = pyqtSignal(object)
    fail = pyqtSignal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.ok.emit(self.fn(self.progress.emit))
        except Exception as e:  # noqa
            self.fail.emit(e)
