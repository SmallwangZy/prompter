import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
                             QTextEdit, QLabel, QMessageBox, QInputDialog, QDialog)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QTextCharFormat, QColor, QSyntaxHighlighter

class ContentHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setForeground(QColor("red"))

    def highlightBlock(self, text):
        pattern = "{content}"
        index = text.find(pattern)
        while index >= 0:
            self.setFormat(index, len(pattern), self.highlight_format)
            index = text.find(pattern, index + len(pattern))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.skills = {}
        self.initUI()
        self.loadSkills()

    def initUI(self):
        self.setWindowTitle('提示词生成器')
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧技能列表和按钮
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.skill_list = QListWidget()
        self.skill_list.itemClicked.connect(self.onSkillSelected)
        left_layout.addWidget(QLabel("技能列表"))
        left_layout.addWidget(self.skill_list)

        # 按钮组
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")
        
        self.add_btn.clicked.connect(self.addSkill)
        self.edit_btn.clicked.connect(self.editSkill)
        self.delete_btn.clicked.connect(self.deleteSkill)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        
        left_layout.addLayout(button_layout)
        main_layout.addWidget(left_widget)

        # 右侧内容区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.content_widgets = QWidget()
        self.content_layout = QVBoxLayout(self.content_widgets)
        right_layout.addWidget(self.content_widgets)

        # 预览区域
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right_layout.addWidget(QLabel("预览"))
        right_layout.addWidget(self.preview)

        # 复制按钮
        self.copy_btn = QPushButton("复制到剪贴板")
        self.copy_btn.clicked.connect(self.copyToClipboard)
        right_layout.addWidget(self.copy_btn)

        main_layout.addWidget(right_widget)

    def loadSkills(self):
        try:
            with open('skills.json', 'r', encoding='utf-8') as f:
                self.skills = json.load(f)
                for skill_name in self.skills:
                    self.skill_list.addItem(skill_name)
        except FileNotFoundError:
            self.skills = {}

    def saveSkills(self):
        with open('skills.json', 'w', encoding='utf-8') as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)

    def closeEvent(self, event):
        self.saveSkills()
        event.accept()

    def addSkill(self):
        name, ok = QInputDialog.getText(self, '添加技能', '请输入技能名称：')
        if ok and name:
            if name in self.skills:
                QMessageBox.warning(self, '警告', '技能名称已存在！')
                return
            template, ok = QInputDialog.getMultiLineText(self, '添加技能', '请输入技能模板：\n(使用{content}表示可替换内容)')
            if ok and template:
                self.skills[name] = template
                self.skill_list.addItem(name)
                self.saveSkills()

    def editSkill(self):
        current_item = self.skill_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择一个技能！')
            return
        
        name = current_item.text()
        dialog = QDialog(self)
        dialog.setWindowTitle('编辑技能')
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        
        # 创建说明标签
        label = QLabel('请编辑技能模板：\n(使用{content}表示可替换内容)')
        layout.addWidget(label)
        
        # 创建文本编辑框并应用高亮
        text_edit = QTextEdit()
        text_edit.setText(self.skills[name])
        highlighter = ContentHighlighter(text_edit.document())
        layout.addWidget(text_edit)
        
        # 创建按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定')
        cancel_button = QPushButton('取消')
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 连接按钮信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            template = text_edit.toPlainText()
            self.skills[name] = template
            self.saveSkills()
            self.onSkillSelected(current_item)

    def deleteSkill(self):
        current_item = self.skill_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择一个技能！')
            return
        
        reply = QMessageBox.question(self, '确认删除',
                                   f'确定要删除技能 "{current_item.text()}" 吗？',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            name = current_item.text()
            del self.skills[name]
            self.skill_list.takeItem(self.skill_list.row(current_item))
            self.saveSkills()
            self.clearContentWidgets()

    def onSkillSelected(self, item):
        self.clearContentWidgets()
        if not item:
            return

        template = self.skills[item.text()]
        content_count = template.count('{content}')
        
        self.content_inputs = []
        for i in range(content_count):
            label = QLabel(f'内容 {i+1}：')
            text_edit = QTextEdit()
            text_edit.textChanged.connect(self.updatePreview)
            self.content_layout.addWidget(label)
            self.content_layout.addWidget(text_edit)
            self.content_inputs.append(text_edit)

        # 更新预览
        self.updatePreview()

    def clearContentWidgets(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.preview.clear()

    def updatePreview(self):
        current_item = self.skill_list.currentItem()
        if not current_item:
            return

        template = self.skills[current_item.text()]
        result = template
        
        for input_widget in self.content_inputs:
            result = result.replace('{content}', input_widget.toPlainText(), 1)
            
        self.preview.setText(result)

    def copyToClipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.preview.toPlainText())
        QMessageBox.information(self, '成功', '内容已复制到剪贴板！')

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()