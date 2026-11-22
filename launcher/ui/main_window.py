"""Главное окно: боковая панель, страницы и контроллер действий.
Здесь нет собственной логики запуска/скачивания — только связывание UI с launcher.*"""
import time

from PyQt6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QTimer, QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import covers, launch, net
from .. import java as javamod
from ..instance import Instance
from . import icons
from .pages.accounts import AccountsPage
from .pages.home import HomePage
from .pages.instance import InstancePage
from .pages.install import InstallPage
from .pages.launch import LaunchPage
from .pages.library import LibraryPage
from .pages.settings import SettingsPage
from .pages.skins import SkinsPage
from .backdrop import Backdrop
from .theme import PALETTES, repolish, tm
from .accountswitch import AccountSwitch
from .titlebar import EdgeGrip, TitleBar
from .widgets import Btn, NavButton, card_frame, label
from .workers import Worker

NAV = [("home", "Главная", "home"), ("library", "Библиотека", "library"),
       ("accounts", "Аккаунты", "user"), ("settings", "Настройки", "settings")]


class FadeStack(QStackedWidget):
    """Стек страниц с плавным появлением. Быстрые переключения не накладывают эффекты друг на друга:
    прежний эффект гасится до запуска нового, а снимается он не изнутри собственного сигнала."""

    def __init__(self):
        super().__init__()
        self._fade = None  # (виджет, анимация)

    def _drop_fade(self):
        if not self._fade:
            return
        w, anim = self._fade
        self._fade = None
        try:
            anim.stop()
            w.setGraphicsEffect(None)
        except RuntimeError:  # виджет уже удалён
            pass

    def set_page(self, widget):
        if self.currentWidget() is widget:
            return
        self._drop_fade()
        self.setCurrentWidget(widget)
        try:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", widget)
            anim.setDuration(170)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade = (widget, anim)
            anim.finished.connect(lambda: QTimer.singleShot(0, self._drop_fade))
            anim.start()
        except RuntimeError:
            self._fade = None


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setProperty("role", "chip")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_text(self, text, kind="info"):
        self.setText(text)
        self.setStyleSheet(
            f"QLabel {{ background: {tm.p.surface2}; border: 1px solid "
            f"{tm.p.danger if kind == 'error' else tm.p.primary}; border-radius: 12px; padding: 10px 18px; "
            f"color: {tm.p.text}; font-weight: 600; }}")
        self.adjustSize()
        p = self.parentWidget()
        self.move((p.width() - self.width()) // 2, p.height() - self.height() - 28)
        self.raise_()
        self.show()
        self.timer.start(3500 if kind == "error" else 2500)


class Overlay(QWidget):
    """Подтверждение поверх главного окна (не отдельное окно ОС)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self._yes = self._no = None
        self.card, cl = card_frame(spacing=12, margins=(24, 22, 24, 20))
        self.card.setFixedWidth(440)
        self.title = label("", "h2", wrap=True)
        self.text = label("", wrap=True)
        self.b_yes = Btn("Да", variant="primary")
        self.b_no = Btn("Отмена")
        self.b_yes.clicked.connect(lambda: self._done(self._yes))
        self.b_no.clicked.connect(lambda: self._done(self._no))
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.b_no)
        row.addWidget(self.b_yes)
        cl.addWidget(self.title)
        cl.addWidget(self.text)
        cl.addSpacing(6)
        cl.addLayout(row)
        lay = QVBoxLayout(self)
        lay.addWidget(self.card, 0, Qt.AlignmentFlag.AlignCenter)

    def ask(self, title, text, on_yes, yes_text="Да", on_no=None, danger=False, no_text="Отмена"):
        self.title.setText(title)
        self.text.setText(text)
        self.b_yes.setText(yes_text)
        self.b_no.setText(no_text)
        self.b_yes.set_variant("danger" if danger else "primary")
        self._yes, self._no = on_yes, on_no
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.setFocus()

    def _done(self, cb):
        self.hide()
        if cb:
            cb()

    def paintEvent(self, _):
        QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 170))

    def mousePressEvent(self, e):
        e.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._done(self._no)


class MainWindow(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        tm.init(cfg)
        tm.apply()
        self.sessions = []
        self.selected_id = None
        self._workers = []
        self.setWindowTitle("MollowLauncher")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setObjectName("Root")
        self.resize(1240, 780)
        self.setMinimumSize(1000, 640)

        # --- боковая панель
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 22, 14, 16)
        sl.setSpacing(4)
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name = label("MollowLauncher", "h2")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag = label("Minecraft Launcher", "muted")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self.logo)
        sl.addWidget(name)
        sl.addWidget(tag)
        sl.addSpacing(22)
        self.nav = {}
        for key, text, ic in NAV:
            b = NavButton(text, ic)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            self.nav[key] = b
            sl.addWidget(b)
        sl.addStretch()
        self.run_btn = Btn("", "play", "primary", 16)
        self.run_btn.hide()
        self.run_btn.clicked.connect(self.show_running)
        sl.addWidget(self.run_btn)
        sl.addSpacing(6)
        sl.addWidget(label("Аккаунт", "muted"))
        self.acc_btn = AccountSwitch(self)
        sl.addWidget(self.acc_btn)

        # --- страницы
        self.stack = FadeStack()
        self.pages = {
            "home": HomePage(self), "library": LibraryPage(self),
            "accounts": AccountsPage(self), "settings": SettingsPage(self),
            "install": InstallPage(self), "launch": LaunchPage(self), "instance": InstancePage(self),
            "skins": SkinsPage(self),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)
        self.launch_page = self.pages["launch"]
        self.skins_page = self.pages["skins"]

        self.titlebar = TitleBar(self)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.backdrop = Backdrop(self)  # фон лаунчера: рисуется за прозрачными страницами
        bd = QVBoxLayout(self.backdrop)
        bd.setContentsMargins(0, 0, 0, 0)
        bd.addWidget(self.stack)
        body.addWidget(side)
        body.addWidget(self.backdrop, 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.titlebar)
        outer.addLayout(body, 1)
        E, C = Qt.Edge, Qt.CursorShape
        self.grips = {
            "l": EdgeGrip(self, E.LeftEdge, C.SizeHorCursor), "r": EdgeGrip(self, E.RightEdge, C.SizeHorCursor),
            "t": EdgeGrip(self, E.TopEdge, C.SizeVerCursor), "b": EdgeGrip(self, E.BottomEdge, C.SizeVerCursor),
            "tl": EdgeGrip(self, E.TopEdge | E.LeftEdge, C.SizeFDiagCursor),
            "br": EdgeGrip(self, E.BottomEdge | E.RightEdge, C.SizeFDiagCursor),
            "tr": EdgeGrip(self, E.TopEdge | E.RightEdge, C.SizeBDiagCursor),
            "bl": EdgeGrip(self, E.BottomEdge | E.LeftEdge, C.SizeBDiagCursor),
        }
        self.toast_w = Toast(self)
        self.overlay = Overlay(self)
        self._closing = False
        self._lt_mark = time.monotonic()
        self.clock = QTimer(self)
        self.clock.setInterval(60_000)
        self.clock.timeout.connect(self.tick)
        self.clock.start()
        tm.changed.connect(self.on_theme)
        self.on_theme()
        self.refresh_all()
        self.go("home" if Instance.all() else "library")

    # ---------- общие сервисы для страниц
    def instances(self):
        return Instance.all()

    def get(self, inst_id):
        from .. import paths
        try:
            return Instance(paths.INSTANCES / inst_id)
        except Exception:
            return None

    # ---------- учёт времени и запущенные игры
    def running_ids(self):
        return {x.inst.id for x in self.sessions if x.running}

    def session_for(self, inst_id):
        return next((x for x in self.sessions if x.running and x.inst.id == inst_id), None)

    def launcher_seconds(self):
        return self.cfg["launcher_time"] + (time.monotonic() - self._lt_mark)

    def _flush_session(self, s):
        sec = s.take_elapsed()
        inst = self.get(s.inst.id) if sec > 0 else None
        if inst:
            inst.data["play_time"] = round(inst.data.get("play_time", 0) + sec, 1)
            inst.save()

    def flush_time(self):
        now = time.monotonic()
        self.cfg["launcher_time"] = round(self.cfg["launcher_time"] + (now - self._lt_mark), 1)
        self._lt_mark = now
        for s in list(self.sessions):
            self._flush_session(s)
        self.cfg.save()

    def tick(self):
        self.flush_time()
        self.pages["home"].update_stats()

    def on_session_finished(self, s):
        self._flush_session(s)
        s.stop_clock()
        self.on_session_changed()

    def on_session_changed(self):
        n = len(self.running_ids())
        self.run_btn.setVisible(n > 0)
        if n:
            self.run_btn.setText("  Игра запущена" if n == 1 else f"  Запущено игр: {n}")
        self.refresh_cards()

    def show_running(self):
        s = next((x for x in reversed(self.sessions) if x.running), None)
        if s:
            self.show_session(s)

    def show_session(self, s):
        self.launch_page.attach(s)
        self.go("launch")

    def toast(self, text, kind="info"):
        self.toast_w.show_text(text, kind)

    def confirm(self, title, text, on_yes, yes_text="Да", on_no=None, danger=False):
        self.overlay.ask(title, text, on_yes, yes_text, on_no, danger)

    def run(self, fn, ok=None, fail=None, progress=None):
        w = Worker(fn, self)
        if progress:
            w.progress.connect(progress)
        w.ok.connect(lambda r: ok(r) if ok else None)
        w.fail.connect(lambda e: fail(e) if fail else self.toast(f"{type(e).__name__}: {e}", "error"))
        w.finished.connect(lambda w=w: self._workers.remove(w) if w in self._workers else None)
        self._workers.append(w)
        w.start()
        return w

    def on_theme(self):
        self.logo.setPixmap(icons.logo(56, tm.p.primary))
        for key, b in self.nav.items():
            b.refresh_icon()
        for p in self.pages.values():
            p.update()
        self.refresh_cards()

    def go(self, key):
        page = self.pages[key]
        for k, b in self.nav.items():  # подсвечена ровно одна вкладка (или ни одной)
            b.setChecked(k == key)
        if hasattr(page, "refresh"):
            page.refresh()
        self.stack.set_page(page)

    def refresh_cards(self):
        self.acc_btn.refresh()
        for k in ("home", "library"):
            self.pages[k].refresh()

    def refresh_all(self):
        self.refresh_cards()
        for k in ("accounts", "settings"):
            self.pages[k].refresh()

    # ---------- действия над сборками
    def handle_action(self, inst_id, act):
        inst = self.get(inst_id)
        if not inst:
            self.toast("Сборка не найдена", "error")
            self.refresh_all()
            return
        if act == "select":
            self.selected_id = inst_id
            return
        self.selected_id = inst_id
        if act == "play":
            running = self.session_for(inst_id)
            if running:
                self.show_session(running)
            else:
                self.play(inst)
        elif act == "stop":
            s = self.session_for(inst_id)
            if s:
                s.kill()
                self.toast(f"Игра «{inst.name}» останавливается…")
        elif act == "logs":
            s = self.session_for(inst_id)
            if s:
                self.show_session(s)
        elif act == "settings":
            self.pages["instance"].load(inst)
            self.go("instance")
        elif act == "favorite":
            inst.data["favorite"] = not inst.data.get("favorite", False)
            inst.save()
            self.refresh_cards()
        elif act == "folder":
            inst.game_dir.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(inst.game_dir)))
        elif act == "mods":
            self.pages["instance"].load(inst, "mods")
            self.go("instance")
        elif act == "cover":
            self.change_cover(inst)
        elif act == "cover_reset":
            self.reset_cover(inst)
        elif act == "clone":
            inst.clone()
            self.refresh_all()
            self.toast("Сборка скопирована")
        elif act == "delete":
            def do():
                inst.delete()
                self.selected_id = None
                self.refresh_all()
                self.toast("Сборка удалена")

            self.confirm("Удалить сборку?",
                         f"«{inst.name}» будет удалена вместе с мирами, модами и настройками.\n"
                         "Это действие необратимо.", do, "Удалить", danger=True)

    def change_cover(self, inst):
        f, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "",
                                           "Изображения (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not f:
            return
        try:
            covers.set_cover(inst, f)
        except (ValueError, OSError) as e:
            self.toast(str(e), "error")
            return
        self.refresh_cards()
        self.toast("Обложка обновлена")

    def reset_cover(self, inst):
        covers.reset_cover(inst)
        self.refresh_cards()
        self.toast("Возвращена стандартная обложка")

    # ---------- запуск
    def play(self, inst):
        if any(w.isRunning() for w in self._workers if getattr(w, "tag", "") == "launch"):
            self.toast("Подготовка другой сборки ещё идёт", "error")
            return
        if not self.cfg.selected_account():
            self.toast("Сначала добавьте офлайн-ник", "error")
            self.go("accounts")
            return
        stages = ([inst.loader_label] if inst.data["loader"] != "vanilla" else []) + \
                 ["Клиент Minecraft", "Библиотеки", "Ресурсы", "Запуск игры"]
        net.reset_stats()
        self.launch_page.begin(inst, stages)
        self.go("launch")

        def ok(spec):
            fresh = self.get(inst.id) or inst
            fresh.data["last_played"] = time.time()
            fresh.save()
            self.launch_page.start_game(fresh, spec)

        def fail(e):
            self._launch_failed(inst, e)

        w = self.run(lambda cb: launch.prepare(inst, self.cfg, cb), ok, fail, self.launch_page.on_progress)
        w.tag = "launch"

    def _launch_failed(self, inst, e):
        page = self.launch_page
        if isinstance(e, net.Cancelled):
            page.cancelled()
        elif isinstance(e, launch.JavaMissing):
            page.failed(e)
            self.confirm("Java не найдена",
                         f"Для этой версии нужна Java {e.major}. Скачать автоматически (Eclipse Temurin)?",
                         lambda: self._download_java_then_play(inst, e.major), "Скачать")
        else:
            page.failed(e)

    def _download_java_then_play(self, inst, major):
        net.reset_stats()
        self.launch_page.begin(inst, [f"Скачивание Java {major}", f"Распаковка Java {major}"],
                               title=f"Установка Java {major}")
        w = self.run(lambda cb: javamod.download_java(major, cb),
                     lambda _p: self.play(inst),
                     lambda e: self.launch_page.cancelled() if isinstance(e, net.Cancelled)
                     else self.launch_page.failed(e),
                     self.launch_page.on_progress)
        w.tag = "launch"

    def place_grips(self):
        w, h, t, c = self.width(), self.height(), 6, 12
        geo = {"l": (0, c, t, h - 2 * c), "r": (w - t, c, t, h - 2 * c), "t": (c, 0, w - 2 * c, t),
               "b": (c, h - t, w - 2 * c, t), "tl": (0, 0, c, c), "tr": (w - c, 0, c, c),
               "bl": (0, h - c, c, c), "br": (w - c, h - c, c, c)}
        for k, (x, y, ww, hh) in geo.items():
            g = self.grips[k]
            g.setGeometry(x, y, ww, hh)
            g.setVisible(not self.isMaximized())
            g.raise_()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.WindowStateChange:
            self.titlebar.sync()
            self.place_grips()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.place_grips()
        self.overlay.setGeometry(self.rect())
        if self.toast_w.isVisible():
            self.toast_w.move((self.width() - self.toast_w.width()) // 2,
                              self.height() - self.toast_w.height() - 28)

    def closeEvent(self, e):
        if not self._closing and any(s.running for s in self.sessions):
            e.ignore()

            def quit_all():
                self._closing = True
                self.flush_time()
                for s in self.sessions:
                    s.kill()
                self.close()

            self.confirm("Игра запущена", "Закрытие лаунчера завершит запущенную игру. Закрыть?",
                         quit_all, "Закрыть всё")
            return
        self.flush_time()
        e.accept()
