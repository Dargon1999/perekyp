from PyQt6.QtWidgets import QComboBox, QLineEdit, QCompleter, QStyledItemDelegate
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QStringListModel
from PyQt6.QtGui import QTextDocument, QAbstractTextDocumentLayout

class HTMLDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        options = option
        self.initStyleOption(options, index)

        painter.save()
        doc = QTextDocument()
        # Highlight match
        text = options.text
        search_text = options.widget.lineEdit().text()
        if search_text:
            import re
            pattern = re.compile(re.escape(search_text), re.IGNORECASE)
            text = pattern.sub(lambda m: f"<span style='background-color: #f1c40f; color: black;'>{m.group(0)}</span>", text)
        
        doc.setHtml(text)
        options.text = ""
        options.widget.style().drawControl(options.widget.style().ControlElement.CE_ItemViewItem, options, painter)

        painter.translate(options.rect.left(), options.rect.top())
        clip = options.rect.translated(-options.rect.left(), -options.rect.top())
        painter.setClipRect(clip)
        layout = doc.documentLayout()
        ctx = QAbstractTextDocumentLayout.PaintContext()
        layout.draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        return super().sizeHint(option, index)

class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setSourceModel(self.model())
        
        self.completer = QCompleter(self.proxy_model, self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self.completer)
        
        self.lineEdit().textChanged.connect(self.proxy_model.setFilterFixedString)
        
        # Match highlighting delegate
        self.setItemDelegate(HTMLDelegate(self)) 

    def setItems(self, items):
        self.clear()
        self.addItems(items)
        self.proxy_model.setSourceModel(self.model())
