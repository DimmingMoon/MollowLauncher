from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...library import filter_sort
from ..cards import CardGrid
from ..widgets import Btn, SearchEdit, card_frame, fmt_duration, label, scrolled


class HomePage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.hello = label("", "h1")
        self.sub = label("Готов к новому приключению?", "muted")
        self.search = SearchEdit("Поиск сборок…")
        self.search.setMinimumWidth(320)
        self.search.textChanged.connect(self.refresh)
        new = Btn("Создать сборку", "plus", "primary")
        new.clicked.connect(lambda: ctl.go("install"))

        top = QHBoxLayout()
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(self.hello)
        head.addWidget(self.sub)
        top.addLayout(head, 1)
        top.addWidget(self.search)
        top.addWidget(new)

        self.stats = {}
        stats = QHBoxLayout()
        stats.setSpacing(14)
        for key, cap in (("builds", "Установлено сборок"), ("fav", "В избранном"), ("mods", "Модов всего"),
                         ("game", "Время в играх"), ("launcher", "Время в лаунчере")):
            f, l = card_frame(margins=(18, 14, 18, 14), spacing=2)
            n = label("0", "h2")
            l.addWidget(n)
            l.addWidget(label(cap, "muted"))
            self.stats[key] = n
            stats.addWidget(f)

        self.t_fav = label("Избранное", "h2")
        self.g_fav = CardGrid()
        self.t_recent = label("Недавно запускались", "h2")
        self.g_recent = CardGrid("Вы ещё не запускали ни одной сборки — нажмите «Играть» на любой карточке.")
        self.t_found = label("Результаты поиска", "h2")
        self.g_found = CardGrid("Ничего не найдено")
        for g in (self.g_fav, self.g_recent, self.g_found):
            g.action.connect(ctl.handle_action)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(14)
        lay.addLayout(stats)
        for w in (self.t_fav, self.g_fav, self.t_recent, self.g_recent, self.t_found, self.g_found):
            lay.addWidget(w)
        lay.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 20, 20)
        root.setSpacing(16)
        root.addLayout(top)
        root.addWidget(scrolled(body), 1)

    def refresh(self):
        insts = self.ctl.instances()
        acc = self.ctl.cfg.selected_account()
        self.hello.setText(f"Привет, {acc['name']}!" if acc else "Привет!")
        self.update_stats(insts)
        sel = self.ctl.selected_id
        run = self.ctl.running_ids()
        q = self.search.text().strip()
        searching = bool(q)
        favs = filter_sort(insts, flt="favorites")
        recent = [i for i in filter_sort(insts, sort="recent") if i.data.get("last_played")][:4]
        for w, show in ((self.t_fav, not searching and bool(favs)), (self.g_fav, not searching and bool(favs)),
                        (self.t_recent, not searching), (self.g_recent, not searching),
                        (self.t_found, searching), (self.g_found, searching)):
            w.setVisible(show)
        self.g_fav.set_instances(favs, sel, run)
        self.g_recent.set_instances(recent, sel, run)
        self.g_found.set_instances(filter_sort(insts, query=q), sel, run)

    def update_stats(self, insts=None):
        insts = self.ctl.instances() if insts is None else insts
        self.stats["builds"].setText(str(len(insts)))
        self.stats["fav"].setText(str(sum(1 for i in insts if i.data.get("favorite"))))
        self.stats["mods"].setText(str(sum(i.mod_count for i in insts)))
        self.stats["game"].setText(fmt_duration(sum(i.data.get("play_time", 0) for i in insts)))
        self.stats["launcher"].setText(fmt_duration(self.ctl.launcher_seconds()))
