#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#########################################################
#@Project      : PowerTrans
#@File         : main.py
#@Created Date : 2025-01-04, 03:00:08
#@Author       : KyleWang[kylewang1977@gmail.com]
#@Version      : 1.0.0
#@Last Modified: 
#@Description  : PowerTrans主程序
#@               
#@Copyright (c) 2025 KyleWang 
#########################################################
import sys
import random
import platform
import ctypes
import pyaudio
import time

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMessageBox, QGraphicsDropShadowEffect)
from ui.settingWin import Ui_Dialog
from ui.subtitle import SubtitleWindow
from libsensevoiceOne.model import SenseVoiceOne
from libpowertrans.funcsLib import logging, log_init
from libpowertrans.AudioCapture import Recorder
import numpy as np

def get_hostapi():
    try:
        hostapiInfo = {}
        audio = pyaudio.PyAudio()      # 初始化 PyAudio
        apiList = []
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            device_host_api = device_info["hostApi"]
            if device_host_api not in apiList:
                apiList.append(device_host_api)
        for j in range(len(apiList)):
            api_Info = audio.get_host_api_info_by_index(j)
            hostapiInfo[j] = api_Info['name']
        api_Info = audio.get_default_host_api_info()
        default_hostapi_index = api_Info["index"]
    except Exception as e:
        print("hostapi_show Error: ", e)
    finally:
        audio.terminate()
        return hostapiInfo, default_hostapi_index

def get_input_device(hostapi_id=None):
    try:
        InputDevice = {}
        default_input_device = None
        audio = pyaudio.PyAudio()      # 初始化 PyAudio
        default_input_device  = audio.get_default_input_device_info()["index"]
        if hostapi_id is None:
            api_Info = audio.get_default_host_api_info()
            hostapi_id = api_Info["index"]
        info = audio.get_host_api_info_by_index(hostapi_id)
        num_devices = info.get('deviceCount')
        for i in range(num_devices):
            device_info = audio.get_device_info_by_host_api_device_index(hostapi_id, i)
            # 获取设备名称并尝试进行解码
            error_str = "鑰虫満"
            if error_str in device_info['name']:
                device_info['name'] = device_info['name'].encode('gbk').decode('utf-8', errors='replace')
                device_info['name'] = device_info['name'].replace('\n', '').replace('\r', '')
            if device_info["maxInputChannels"]>0:
                InputDevice[device_info["index"]] = device_info["name"]
    except Exception as e:
        print("get_input_device() Error: ", e)
    finally:
        audio.terminate()      # 关闭 PyAudio
        return InputDevice, default_input_device

# 定义主窗口类
class MainWindow(QDialog, Ui_Dialog):
    def __init__(self):
        super().__init__()
        if(platform.system()=='Windows'):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid") # pyqt任务栏图标问题
        self.setupUi(self)  # 初始化 UI
        self.setWindowIcon(QIcon("./ui/icon.ico"))
        self.DrawWaveLen = 0.1
        self.sr = 16000
        self.drawWavePoints = 500  # 降采样：将原音频点数量降采样为 500 个点
        self.sub_window = SubtitleWindow(self)
        self.sub_window.return_to_main_signal.connect(self.return_from_sub_window)
        self.init_ui()      # 初始化窗口

        self.recoder = Recorder()
        # 初始化ASR模型
        self.model_file = "sense-voice-encoder-int8.onnx"
        self.language = "zh"
        self.ssOnnx = SenseVoiceOne()
        self.isModelLoaded = False

    def init_ui(self):
        self.setWindowTitle("PowerTrans")
        self.buttonRun.clicked.connect(self.button_run_func)
        self.buttonExit.clicked.connect(self.close)
        self.buttonDrawVoice.clicked.connect(self.button_draw_func)
        self.cb_hostapi.currentIndexChanged.connect(self.hostapi_change)
        # 设置样式表
        self.setStyleSheet("""
            /* 设置 QDialog 的背景颜色和字体 */
            QDialog {
                background-color: #e0e0e0;
                color: #333333;
                font-size: 14px;
                font-family: Arial, sans-serif;
            }
            /* 设置 QGroupBox 的样式 */
            QGroupBox {
                background-color: #f5f5f5;
                color: #333333;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            /* 设置 QLabel 的样式 */
            QLabel {
                font-family: "Arial";
                font-size: 13px;
                text-decoration: underline;                           
                font-weight: bold;
                padding-left: 5px; /* 设置QLabel内部内容的左边距为10px */
            }                                               
            /* 设置 QComboBox 的样式 */
            QComboBox {
                background-color: white;
                color: #333333;
                font-size: 13px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid #cccccc;
            }
            /* 设置 QCheckBox 的样式 */
            QCheckBox {
                color: #333333;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #606060;
                border: 1px solid #333333;
            }
            QCheckBox::indicator:unchecked {
                background-color: white;
                border: 1px solid #cccccc;
            }
            /* 设置 QPushButton 的样式 */
            QPushButton {
                    background-color: #ffffff;  /* 背景颜色：白色 */
                    color: #000000;             /* 文本颜色：黑色 */
                    font-family: "Helvetica Neue", sans-serif; /* 字体类型：Helvetica Neue */
                    font-size: 14px;            /* 字体大小 */
                    font-weight: bold;          /* 字体加粗 */
                    border: 1px solid #d1d1d1;  /* 边框颜色：浅灰色 */
                    border-radius: 8px;         /* 圆角半径 */
                    padding: 4px;               /* 内边距 */
            }
            QPushButton:hover {
                background-color: #f5f5f5;  /* 悬停时的背景颜色：浅灰色 */
                border: 1px solid #c1c1c1;  /* 悬停时的边框颜色：稍深的灰色 */
            }
            QPushButton:pressed {
                background-color: #e0e0e0;  /* 按下时的背景颜色：更深的灰色 */
                border: 1px solid #b1b1b1;  /* 按下时的边框颜色：更深的灰色 */
            }
        """)

        shadow1 = QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(10)  # 阴影模糊半径
        shadow1.setColor(Qt.gray)  # 阴影颜色
        shadow1.setOffset(2, 2)    # 阴影偏移量
        self.buttonRun.setGraphicsEffect(shadow1)
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(10)  # 阴影模糊半径
        shadow2.setColor(Qt.gray)  # 阴影颜色
        shadow2.setOffset(2, 2)    # 阴影偏移量
        self.buttonExit.setGraphicsEffect(shadow2)
        shadow3 = QGraphicsDropShadowEffect()
        shadow3.setBlurRadius(10)  # 阴影模糊半径
        shadow3.setColor(Qt.gray)  # 阴影颜色
        shadow3.setOffset(2, 2)    # 阴影偏移量
        self.buttonDrawVoice.setGraphicsEffect(shadow3)

        # 设置 HostApi
        hostapiInfo, default_hostapi_index = get_hostapi()
        for key, value in hostapiInfo.items():
            display_text = f"{key}-{value}"  # 格式化为 key-value
            self.cb_hostapi.addItem(display_text, key)  # 将 key 存储为用户数据
        self.cb_hostapi.setCurrentIndex(default_hostapi_index)

        # 绘制声音波形图
        self.widgetWave.paintEvent = self.draw_paint_event
        self.data = np.zeros(self.drawWavePoints)  # 初始化数据
        self.timerDraw = QTimer()
        self.timerDraw.timeout.connect(self.timer_draw_func)

        # 字幕窗口定时更新字幕
        self.timerSubtitle = QTimer()
        self.timerSubtitle.timeout.connect(self.timer_sub_func)
        self.runtimes = 0
        self.subtitle1 = ""
        self.subtitle2 = ""
        self.subtitle3 = ""

    def button_draw_func(self):
        # 启动或停止定时器
        if self.timerDraw.isActive():
            self.timerDraw.stop()
            self.stop_get_voice_data()
            self.buttonDrawVoice.setText("启动采集")
        else:
            self.timerDraw.start(int(self.DrawWaveLen*1000))  # 每 50 毫秒更新一次
            self.buttonDrawVoice.setText("停止采集")

    def timer_draw_func(self):
        if not self.recoder.isInit:
            self.recoder.init(deviceId=self.cb_audio.currentData(), channels=1)
        listen_res = self.recoder.listen(seconds=0.1, mute_check=False)
        new_data = listen_res["array"]
        if new_data.shape[0]<500:
            logging.warning(f'采集音频数据错误! res shape={new_data.shape}')
            return
        self.data = new_data[:,0]
        self.widgetWave.update()  # 使用 update() 加入重绘请求

    def stop_get_voice_data(self):
        if self.timerDraw.isActive():
            self.timerDraw.stop()
        if self.recoder.isInit:
            self.recoder.stop()
        self.data = np.zeros(self.drawWavePoints)  # 初始化数据
        self.widgetWave.update()

    def draw_paint_event(self, event):
        # 在 paintEvent 中使用 QPainter 绘制动态数据
        painter = QPainter(self.widgetWave)
        painter.setPen(QPen(Qt.blue, 2))  # 设置画笔颜色和宽度

        # 降采样：将 16000 个点降采样为 800 个点
        downsample_num = self.drawWavePoints
        downsample_factor = len(self.data) // downsample_num
        downsampled_data = self.data[::downsample_factor]
        width = self.widgetWave.width()
        hight = self.widgetWave.height()
        x = np.int_(np.linspace(0, 1, len(downsampled_data))*width)
        y = np.int_((1-downsampled_data)*hight/2)
        # 绘制波形
        for i in range(len(downsampled_data) - 1):
            painter.drawLine(x[i], y[i], x[i+1], y[i+1])

    def hostapi_change(self):
        self.cb_audio.clear()
        # 设置 音频设备选项
        InputDevice, default_input_device = get_input_device(self.cb_hostapi.currentData())
        for key, value in InputDevice.items():
            display_text = f"{key}-{value}"  # 格式化为 key-value
            self.cb_audio.addItem(display_text, key)  # 将 key 存储为用户数据
        if default_input_device in InputDevice.keys():
            self.cb_audio.setCurrentIndex(default_input_device)

    def button_run_func(self):
        # 创建并显示子窗口
        self.stop_get_voice_data()
        self.hide()
        self.toggle_subtitle_timer(True)
        self.sub_window.show()
        self.sub_window.update_subtitle("", "", "")

    def toggle_subtitle_timer(self, status=True):
        # 启动或停止定时器
        if not status:
            self.timerSubtitle.stop()
            self.recoder.stop()
        else:
            self.timerSubtitle.start(1000)
            if not self.recoder.isInit:
                self.recoder.init(deviceId=self.cb_audio.currentData(), channels=1)
            self.recoder.run(seconds=5, 
                             save_wave=True, 
                             mute_check=True, 
                             speech_completeness=True
                            )

    def timer_sub_func(self):
        if not self.isModelLoaded:
            self.ssOnnx.load_model(senseVoice_model_file=self.model_file)
            self.isModelLoaded = True
        audio_res = self.recoder.get(False)
        res = ""
        if audio_res is not None:
            logging.info("\033[34m 取得数据. array.shape={}. 队列长度:{}\033[0m".format(
                audio_res["array"].shape, self.recoder.audio_queue.qsize()))
            res = self.ssOnnx.transcribe(audio_res["array"], 
                                         language=self.language,
                                         use_itn=True,
                                         use_vad=True,
                                         ForceMono=True,
                                         str_result=True)
        # TODO 长语句的换行显示、时间
        # 没有用到GPU
        text1 = self.subtitle1
        self.subtitle1 = res
        if len(text1) != 0: 
            text2 = self.subtitle2
            self.subtitle2 = text1
            if len(text2) != 0: 
                self.subtitle3 = text2
        elif len(self.subtitle2) != 0 and len(self.subtitle3) == 0:
            self.subtitle3 = self.subtitle2
            self.subtitle2 = ""
        self.runtimes += 1
        self.sub_window.update_subtitle("1:"+self.subtitle1, "2:"+self.subtitle2, "3:"+self.subtitle3)

    def return_from_sub_window(self, child_id):
        logging.debug(f"从子窗口 {child_id} 返回！")
        self.toggle_subtitle_timer(False)
        self.show()

    def closeEvent(self, event):
        """
        重写 closeEvent 方法，自定义关闭行为
        """
        # 弹出确认对话框
        reply = QMessageBox.question(
            self,
            "确认关闭",
            "你确定要关闭窗口吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.stop_get_voice_data()
            event.accept()  # 接受关闭事件，窗口会关闭
        else:
            event.ignore()  # 忽略关闭事件，窗口不会关闭


if __name__ == "__main__":
    log_init(LogFileName="powerTrans.log", logLevel=logging.INFO)
    app = QApplication(sys.argv)
    # 创建主窗口
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())