# 依赖库安装

## PyQt5

``` sh
pip install PyQt5 -i https://pypi.tuna.tsinghua.edu.cn/simple

# Qt Designer 是 Qt 开发环境的一部分
pip install pyqt5-tools -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> 使用 pyuic5 命令行工具将 .ui 文件转换为 Python 文件

``` sh
pyuic5 -o design_ui.py design.ui
```