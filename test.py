import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('测试窗口')
        self.setGeometry(100, 100, 300, 200)
        
        button = QPushButton('测试按钮', self)
        button.move(100, 80)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_()) 