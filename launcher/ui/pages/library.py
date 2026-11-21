from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ... import loaders
from ...library import SORTS, filter_sort
from ..cards import CardGrid
from ..widgets import Btn, MenuButton, SearchEdit, label, scrolled


class LibraryPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.title = label("Мои сборки", "h1")
        self.count = label("0", "chip")
        self.search = SearchEdit("Поиск сборок…")
        self.search.textChanged.connect(self.refresh)
        flt = [("all", "Все"), ("favorites", "Избранные")] + [(l.id, l.label) for l in loaders.all_loaders()]
        self.flt = MenuButton("Фильтр", flt, "all", "library")
        self.sort = MenuButton("Сортировка", SORTS, "name")
        self.flt.changed.connect(lambda _: self.refresh())
        self.sort.changed.connect(lambda _: self.refresh())
        new = Btn("Создать сборку", "plus", "primary")
        new.clicked.connect(lambda: ctl.go("install"))

        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(self.title)
        head.addWidget(self.count)
        head.addStretch()
        head.addWidget(self.flt)
        head.addWidget(self.sort)
        head.addWidget(new)

        self.grid = CardGrid("Сборок не найдено. Создайте первую кнопкой «Создать сборку».")
        self.grid.action.connect(ctl.handle_action)
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 8, 0)
        bl.addWidget(self.grid)
        bl.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 20, 20)
        root.setSpacing(14)
        root.addWidget(self.search)
        root.addLayout(head)
        root.addWidget(scrolled(body), 1)

    def refresh(self):
        insts = self.ctl.instances()
        shown = filter_sort(insts, self.search.text(), self.flt.current, self.sort.current)
        self.count.setText(str(len(insts)))
        self.grid.set_instances(shown, self.ctl.selected_id, self.ctl.running_ids())
