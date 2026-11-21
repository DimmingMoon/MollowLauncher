import faulthandler
import os
import sys
import threading
import traceback
from datetime import datetime

# В exe без консоли (--noconsole) sys.stdout/sys.stderr равны None — любая библиотека, пишущая в них, падает.
for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from launcher import net, paths
from launcher.config import Config
from launcher.ui.main_window import MainWindow

_win = None


def _log(text):
    try:
        with open(paths.DATA / "launcher.log", "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n{text}\n")
    except OSError:
        pass


def _install_crash_handling():
    """PyQt6 завершает процесс при любом необработанном исключении в слоте/событии.
    Свой excepthook гасит это: ошибка пишется в launcher.log, лаунчер показывает уведомление и работает дальше."""
    try:  # аппаратные сбои (access violation и т.п.) — в отдельный файл
        faulthandler.enable(open(paths.DATA / "fault.log", "a", encoding="utf-8"))
    except Exception:
        pass

    def hook(et, ev, tb):
        _log("".join(traceback.format_exception(et, ev, tb)))
        if _win is not None:
            QTimer.singleShot(0, lambda: _win.toast(
                f"Внутренняя ошибка: {et.__name__}: {str(ev)[:120]}. Подробности в launcher.log", "error"))

    sys.excepthook = hook
    threading.excepthook = lambda a: hook(a.exc_type, a.exc_value, a.exc_traceback)


def main():
    global _win
    migrated = paths.ensure()
    _install_crash_handling()
    app = QApplication(sys.argv)
    app.setApplicationName(paths.APP_NAME)
    icon = QIcon(str(paths.resource("assets/icon.png")))
    app.setWindowIcon(icon)
    _win = MainWindow(Config())
    _win.setWindowIcon(icon)
    _win.show()
    if migrated:
        _win.toast(f"Данные перенесены в {paths.DATA}")
    code = app.exec()
    # Фоновые загрузки (QThread) не ждём: обычный выход с ними мог ронять процесс
    # сообщением «QThread: Destroyed while thread is still running».
    net.CANCEL.set()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(code)


if __name__ == "__main__":
    main()
