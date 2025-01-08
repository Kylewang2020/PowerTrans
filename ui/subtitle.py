import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QPainter, QColor, QCursor

class SubtitleWindow(QWidget):
    return_to_main_signal = pyqtSignal(int)  # 定义一个信号，用于传递子窗口 ID
    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置窗口标志：无边框，始终在最前
        self.setWindowFlags(Qt.Window| Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 设置窗口背景为灰色
        self.setStyleSheet("background-color: gray; border-radius: 10px;")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.9)  # 设置窗口半透明

        # 设置窗口初始大小
        self.resize(600, 200)

        # 使用 QVBoxLayout 布局
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(3, 3, 3, 3)  # 设置边距
        self.layout.setSpacing(0)
        # 添加三个 QLabel 用于显示字幕
        # style = "color: #4ec9b0; font-size: 14px; font-weight: bold; font-family: Arial, sans-serif;"
        style = """
                QLabel {
                        color: white;                       /* 字体颜色：白色 */
                        font-size: 14px;                    /* 字体大小：20px */
                        font-weight: normal;                  /* 字体加粗 */
                        font-family: Arial, sans-serif;     /* 字体类型：Arial，备选 sans-serif */
                        background-color: rgba(102, 102, 102, 0.95); /* 背景颜色：黑色，70% 不透明度 */
                        padding: 5px;                      /* 内边距 */
                        border-radius: 5px;                 /* 圆角 */
                    }
                """
        self.label1 = QLabel("这是第一行", self)
        self.label1.setStyleSheet(style)
        self.label1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.label1.setWordWrap(True)  # 启用自动换行
        self.layout.addWidget(self.label1)
        self.label2 = QLabel("这是第二行", self)
        self.label2.setStyleSheet(style)
        self.label2.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.label2.setWordWrap(True)  # 启用自动换行
        self.layout.addWidget(self.label2)
        self.label3 = QLabel("这是第三行", self)
        self.label3.setStyleSheet(style)
        self.label3.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 左对齐
        self.label3.setWordWrap(True)  # 启用自动换行
        self.layout.addWidget(self.label3)
        self.setLayout(self.layout) # 将布局应用到窗口

        # 初始化鼠标拖动变量
        self.dragging = False
        self.offset = QPoint()

        # 初始化调整大小变量
        self.resize_dragging = False
        self.resize_direction = None

        # 设置窗口边缘的调整大小区域宽度
        self.resize_margin = 10
        # 允许窗口调整大小
        self.setMinimumSize(300, 110)  # 设置最小尺寸
        # 启用鼠标追踪
        self.setMouseTracking(True)        

        self.child_id = 1

    def paintEvent(self, event):
        # 重绘窗口以实现圆角
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(128, 128, 128))  # 灰色背景
        painter.drawRoundedRect(self.rect(), 5, 5)  # 设置圆角半径

    def mousePressEvent(self, event: QMouseEvent):
        # 检查是否在调整大小区域
        if self.is_resize_area(event.pos()):
            self.resize_dragging = True
            self.resize_direction = self.get_resize_direction(event.pos())
        else:
            # 否则拖动窗口
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        
    def mouseMoveEvent(self, event: QMouseEvent):
        # 检查鼠标是否在调整大小区域，并更新鼠标指针
        if self.is_resize_area(event.pos()):
            direction = self.get_resize_direction(event.pos())
            if direction in ["left", "right"]:
                self.setCursor(Qt.SizeHorCursor)
            elif direction in ["top", "bottom"]:
                self.setCursor(Qt.SizeVerCursor)
            elif direction in ["top-left", "bottom-right"]:
                self.setCursor(Qt.SizeFDiagCursor)
            elif direction in ["top-right", "bottom-left"]:
                self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        if self.resize_dragging and self.resize_direction:
            self.handle_resize(event.globalPos())       # 调整窗口大小
        elif self.dragging:
            self.move(event.globalPos() - self.offset)  # 拖动窗口

    def mouseReleaseEvent(self, event: QMouseEvent):
        # 停止拖动或调整大小
        self.dragging = False
        self.resize_dragging = False
        self.resize_direction = None
        # self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:    # 按下 ESC 键退出
            self.close()
            self.return_to_main_signal.emit(self.child_id)
            # self.parent().show()

    def resizeEvent(self, event):
        # 当窗口大小改变时，调整 QLabel 的大小
        pass

    def is_resize_area(self, pos):
        # 检查鼠标是否在调整大小区域
        rect = self.rect()
        if (
            pos.x() <= self.resize_margin
            or pos.x() >= rect.width() - self.resize_margin
            or pos.y() <= self.resize_margin
            or pos.y() >= rect.height() - self.resize_margin
        ):
            return True
        return False

    def get_resize_direction(self, pos):
        # 获取调整大小的方向
        rect = self.rect()
        if pos.x() <= self.resize_margin:
            if pos.y() <= self.resize_margin:
                return "top-left"
            elif pos.y() >= rect.height() - self.resize_margin:
                return "bottom-left"
            else:
                return "left"
        elif pos.x() >= rect.width() - self.resize_margin:
            if pos.y() <= self.resize_margin:
                return "top-right"
            elif pos.y() >= rect.height() - self.resize_margin:
                return "bottom-right"
            else:
                return "right"
        elif pos.y() <= self.resize_margin:
            return "top"
        elif pos.y() >= rect.height() - self.resize_margin:
            return "bottom"
        return None

    def handle_resize(self, global_pos):
        # 根据调整方向调整窗口大小
        rect = self.geometry()
        if self.resize_direction == "left":
            rect.setLeft(global_pos.x())
        elif self.resize_direction == "right":
            rect.setRight(global_pos.x())
        elif self.resize_direction == "top":
            rect.setTop(global_pos.y())
        elif self.resize_direction == "bottom":
            rect.setBottom(global_pos.y())
        elif self.resize_direction == "top-left":
            rect.setTopLeft(global_pos)
        elif self.resize_direction == "top-right":
            rect.setTopRight(global_pos)
        elif self.resize_direction == "bottom-left":
            rect.setBottomLeft(global_pos)
        elif self.resize_direction == "bottom-right":
            rect.setBottomRight(global_pos)

        # 限制最小尺寸
        if rect.width() < self.minimumWidth():
            rect.setWidth(self.minimumWidth())
        if rect.height() < self.minimumHeight():
            rect.setHeight(self.minimumHeight())

        self.setGeometry(rect)

    def update_subtitle(self, text1, text2, text3):
        # 更新三个 QLabel 的文本
        self.label1.setText(text1)
        self.label2.setText(text2)
        self.label3.setText(text3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SubtitleWindow()
    window.show()
    label = "这是一个很长的文本，用于测试 QLabel 的自动换行功能。当文本长度超过 QLabel 的宽度时，文本会自动换行"
    window.update_subtitle(label, label, label)
    sys.exit(app.exec_())