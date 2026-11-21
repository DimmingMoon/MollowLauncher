import traceback

from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ... import covers, net
from ..session import GameSession
from ..theme import tm
from ..widgets import Btn, LogView, ProgressBlock, label


class CoverPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.inst = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(320)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return w * 9 // 16

    def sizeHint(self):
        return QSize(640, 360)

    def paintEvent(self, _):
        if not self.inst:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 18, 18)
        p.setClipPath(path)
        p.drawPixmap(0, 0, covers.pixmap(self.inst, self.width(), self.height()))
        g = QLinearGradient(0, 0, self.width(), 0)
        c0, c1 = QColor(tm.p.bg), QColor(tm.p.bg)
        c0.setAlpha(0)
        c1.setAlpha(150)
        g.setColorAt(0, c0)
        g.setColorAt(1, c1)
        p.fillRect(self.rect(), g)


class LaunchPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.inst = None
        self.session = None
        self.cover = CoverPanel()
        self.title = label("", "h1", wrap=True)
        self.sub = label("", "muted", wrap=True)
        self.state = label("", "h3", wrap=True)
        self.error = label("", "error", wrap=True)
        self.progress = ProgressBlock()
        self.log = LogView()
        self.log.hide()

        self.b_cancel = Btn("Отмена", "stop")
        self.b_kill = Btn("Завершить игру", "stop", "danger")
        self.b_logs = Btn("Логи", "terminal")
        self.b_back = Btn("К библиотеке", "back", "ghost")
        self.b_cancel.clicked.connect(net.CANCEL.set)
        self.b_kill.clicked.connect(self.kill)
        self.b_logs.clicked.connect(lambda: self.log.setVisible(not self.log.isVisible()))
        self.b_back.clicked.connect(lambda: ctl.go("library"))
        row = QHBoxLayout()
        row.setSpacing(8)
        for b in (self.b_cancel, self.b_kill, self.b_logs, self.b_back):
            row.addWidget(b)
        row.addStretch()

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(self.title)
        right.addWidget(self.sub)
        right.addSpacing(8)
        right.addWidget(self.state)
        right.addWidget(self.progress)
        right.addWidget(self.error)
        right.addLayout(row)
        right.addWidget(self.log, 1)
        right.addStretch()

        left = QVBoxLayout()
        left.addWidget(self.cover)
        left.addStretch()
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(28)
        root.addLayout(left, 5)
        root.addLayout(right, 4)

    # --- управление этапами
    def begin(self, inst, stages, title=None):
        self.inst = inst
        self.cover.inst = inst
        self.cover.update()
        self.title.setText(title or f"Запуск {inst.name}")
        self.sub.setText(f"Minecraft {inst.data['mc_version']} · {inst.loader_label}")
        self.state.setText("Подготовка…")
        self.error.setText("")
        self.log.clear()
        self.progress.start(stages)
        self.b_cancel.show()
        self.b_cancel.setEnabled(True)
        self.b_kill.hide()
        self.b_back.hide()

    def on_progress(self, msg, done, total):
        self.state.setText(msg)
        self.progress.on_progress(msg, done, total)
        if done == 0:
            self.log.append(f"[{msg}] {total}")

    def start_game(self, inst, spec):
        """Все файлы готовы — запускаем процесс игры."""
        self.progress.set_stage("Запуск игры")
        self.state.setText("Запуск игры…")
        self.b_cancel.setEnabled(False)
        s = GameSession(inst, spec, self.ctl)
        s.stages = list(self.progress.stages.stages)
        self.session = s
        self.ctl.sessions.append(s)
        s.output.connect(lambda t, s=s: self._out(s, t))
        s.started.connect(lambda s=s: self._started(s))
        s.finished.connect(lambda code, s=s: self._finished(s, code))
        s.start()
        self.ctl.on_session_changed()

    def _out(self, s, text):
        if s is self.session:
            self.log.append(text)

    def _started(self, s):
        self.ctl.on_session_changed()
        if s is not self.session:
            return
        self.progress.finish(True)
        self.state.setText("Игра запущена")
        self.b_cancel.hide()
        self.b_kill.show()
        self.b_back.show()

    def _finished(self, s, code):
        if s in self.ctl.sessions:
            self.ctl.sessions.remove(s)
        self.ctl.on_session_finished(s)
        if s is not self.session:
            return
        self.log.append(f"\n[процесс завершён, код {code}]")
        self.b_kill.hide()
        self.b_back.show()
        if code == 0:
            self.state.setText("Игра закрыта")
        else:
            self.state.setText("Игра завершилась с ошибкой")
            self.error.setText(f"Код выхода {code}. Откройте «Логи», чтобы увидеть причину.")
            self.progress.fail()
            self.log.show()

    def attach(self, s):
        """Вернуться к окну уже запущенной игры (лог, остановка)."""
        inst = s.inst
        self.session, self.inst, self.cover.inst = s, inst, inst
        self.cover.update()
        self.title.setText(inst.name)
        self.sub.setText(f"Minecraft {inst.data['mc_version']} · {inst.loader_label}")
        self.error.setText("")
        self.progress.start(s.stages or ["Запуск игры"])
        self.progress.finish(True)
        self.state.setText("Игра запущена" if s.running else "Игра закрыта")
        self.log.clear()
        for line in s.log:
            self.log.append(line)
        self.b_cancel.hide()
        self.b_kill.setVisible(s.running)
        self.b_back.show()

    def kill(self):
        if self.session and self.session.running:
            self.session.kill()

    def failed(self, e):
        self.progress.fail()
        self.state.setText("Не удалось запустить")
        self.error.setText(f"{type(e).__name__}: {e}")
        self.log.append("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        self.b_cancel.hide()
        self.b_back.show()

    def cancelled(self):
        self.progress.fail()
        self.state.setText("Операция отменена")
        self.error.setText("Скачанные файлы сохранены — при следующем запуске загрузка продолжится.")
        self.b_cancel.hide()
        self.b_back.show()
