#!/usr/bin/env python
# =========================================
# -*- coding: utf-8 -*-
# Project     : power_trans
# Module      : funcsLib.py
# Author      : KyleWang[kylewang1977@gmail.com]
# Time        : 2024-12-26 20:26
# Version     : 1.0.0
# Last Updated: 
# Description : 通用函数定义
# =========================================
import time
import logging
from datetime import datetime
""" Add project path to sys.path V1.0"""
import os, sys
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

_outputToName = {
    1: 'File',
    2: 'Stream',
    3: 'Stream&File',
}

def log_init(
    LogFileName:str = "log.log", 
    FilePath:os.PathLike = "./log", 
    logOutput:int = 3, 
    logLevel:int = logging.DEBUG, 
    logger_name:str = None
    ):
    """
    日志初始化. V2.0.

    Parameters
    ----------
    LogFileName:  str
        file name of the log file.
    FilePath: os.PathLike
        log file's path
    logOutput: int
        [1:log file only; 2:console only; 3:both]. 
    logLevel:  int
        same as the defination in logging module. logging.DEBUG, logging.INFO...
    logger_name: str
        if logger_name is None, then use the default and update it to the settings.
    """
    logger = None
    try:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level=logLevel)
        if logLevel > logging.DEBUG:
            formatter= logging.Formatter(
                fmt = '[%(levelname)-5s|%(asctime)s.%(msecs)03d|%(thread)s|%(lineno)03d@%(funcName)-9s]: %(message)s',
                datefmt='%m-%d %H:%M:%S')
        else:
            formatter = logging.Formatter(
                fmt = '[%(levelname)-5s|%(asctime)s.%(msecs)03d|%(thread)s|%(filename)s:%(lineno)d@%(funcName)s]: %(message)s',
                datefmt = '%m-%d %H:%M:%S')
        if logOutput==2 or logOutput==3:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            logger.addHandler(console)
        if logOutput==1 or logOutput==3:
            if not os.path.exists(FilePath): os.mkdir(FilePath)
            LogFileName = os.path.join(FilePath, LogFileName)
            handler = logging.FileHandler(LogFileName, encoding='utf-8')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.info("log_level:{}, output:{}, file: \"{}\"".format(
                logging.getLevelName(logLevel), _outputToName.get(logOutput), LogFileName))
    except Exception as e:
        print("logger init failed:", e)
    
    if logger is None:
        raise Exception("logger init failed.")
    return logger


def timer(indent=2, isTimer=True):
    """
    Decorator to count the time consuming. 
    Could stop by set the var isTimer=False.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if isTimer: start_time = time.time()
            result = func(*args, **kwargs)
            if isTimer: 
                print(' '*indent, "{:<15}耗时:{:.2f}s".format(func.__name__+"()", time.time()-start_time))
            return result
        return wrapper
    return decorator

# dict key 字段最大长度
def dict_key_max_len(curArg):
    max_len = 10
    if not isinstance(curArg, dict):
        return max_len
    for key in curArg.keys():
        if len(key)>max_len: max_len = len(key)
    return max_len


def str_code_correct(value):
    error_str = "鑰虫満"
    if type(value) is str and error_str in value:
        value = value.encode('gbk').decode('utf-8', errors='replace')
        value = value.replace('\n', '').replace('\r', '')
    return value


# dict 遍历 print
def print_dict(curArg, isPrintShort=True, indent=4):
    if isinstance(curArg, dict):
        key_len = dict_key_max_len(curArg)
        for key, value in curArg.items():
            if (isinstance(value, list) and isinstance(value[0], dict)) or  isinstance(value, dict):
                print(' '*indent, "{} : [类型:{}, 元素个数:{}]".format(key, type(value), len(value)))
                print_dict(value, indent+4)
            else:
                if type(key) is str and 'default' in key and isPrintShort: return
                value = str_code_correct(value)
                print(' '*indent, "{:<{}}: {}".format(key, key_len+1, value))
    elif isinstance(curArg, list) and isinstance(curArg[0], dict):
        for i in range(len(curArg)):
            print_dict(curArg[i], indent)
    else:
        print(' '*indent, curArg)


def get_date_time_string():
    # 获取当前日期时间
    now = datetime.now()
    date_time_string = now.strftime("%m_%d_%H_%M_%S")
    return date_time_string


# 枚举所有 指定 host_api的音频设备
def list_audio_devices(audio, host_api_index=0):
    info = audio.get_host_api_info_by_index(host_api_index)
    print(info)
    num_devices = info.get('deviceCount')
    print(num_devices)
    
    for i in range(num_devices):
        device_info = audio.get_device_info_by_host_api_device_index(0, i)
        print(f"Device {i}: {device_info['name']}")
        print_dict(device_info)


# 查找名称中包含“立体声混音”或“Stereo Mix”的设备编号
def find_stereo_mix_device(audio, host_api_index=0):
    info = audio.get_host_api_info_by_index(host_api_index)
    num_devices = info.get('deviceCount')
    
    for i in range(num_devices):
        device_info = audio.get_device_info_by_host_api_device_index(host_api_index, i)
        if 'Stereo Mix' in device_info.get('name', '') or '立体声混音' in device_info.get('name', ''):
            return i
    return None


def GetFileName(id=None, folder=None, isMic=None, Channels=2, Rate=44100, Fmt="paInt16", suffix=".wav"):
    """
    获取录音文件名称。缺省为当前运行目录下的data子目录中
    如: D08_01-54-32_Speaker_channels1_rate16000_paFloat32_No-1.wav
    """
    # 创建目录
    if folder is None:
        path = os.getcwd()
        path = os.path.join(path, "data")
    if not os.path.exists(path): os.mkdir(path)

    fileName = datetime.now().strftime("D%d_%H-%M-%S") + "_" 
    if isMic is not None:
        if isMic: fileName += "Mic_"
        else:     fileName += "Speaker_"
    fileName += "channels"+ str(Channels)+ "_rate" + str(Rate) + "_" + Fmt
    if id is not None:
        fileName += "_No-" + str(id)
    fileName += suffix
    fileName = os.path.join(path, fileName)
    return fileName


# 查找名称中包含“立体声混音”或“Stereo Mix”的设备编号
def get_mix_device(audio, host_api_index=0):
    info = audio.get_host_api_info_by_index(host_api_index)
    num_devices = info.get('deviceCount')
    for i in range(num_devices):
        device_info = audio.get_device_info_by_host_api_device_index(host_api_index, i)
        if 'Stereo Mix' in device_info.get('name', '') or '立体声混音' in device_info.get('name', ''):
            return i
    return None


def is_text_char(char):
    # 判断是否是英文字母或汉字
    return char.isalpha() or ('\u4e00' <= char <= '\u9fff')


def print_progress_bar(iteration, total, length=50):
    """
    打印进度条
    :param iteration: 当前进度
    :param total: 总进度
    :param length: 进度条的长度（字符数）
    """
    percent = ("{0:5.1f}").format(100 * (iteration / float(total)))  # 计算进度百分比
    filled_length = int(length * iteration // total)  # 已完成的部分
    bar = '\u2588' * filled_length + '-' * (length - filled_length)  # 进度条
    print(f'\r{percent}% [{bar}]', end='')  # 使用 end='' 防止换行并更新进度条
    # if iteration==total: print()


if __name__ == '__main__':
    # log_init()
    # print(logging.getLogger().getEffectiveLevel())
    
    def audio_test():
        # For Audio Funcs test
        import wave, pyaudio

        PyAudio = pyaudio.PyAudio()
        list_audio_devices(PyAudio)

        mix_id = find_stereo_mix_device(PyAudio)
        print(mix_id)
    
    def bar_test():
        # import time
        # for i in range(60):
        #     print_progress_bar(i, 50)
        #     time.sleep(0.05)
        # 红色文本
        print("\033[31mThis is red text\033[0m")
        # 绿色文本
        print("\033[32m This is green text\033[0m")
        # 蓝色文本
        print("\033[34mThis is blue text\033[0m")
        log_init()
        logging.debug("\033[34mThis is blue text\033[0m") 
        for i in range(3):
            logging.debug(f"\033[32m This is blue text {i}\033[0m {i}") 
    bar_test()