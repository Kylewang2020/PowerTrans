#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   myWhisper.py
@Time    :   2024/07/19 12:54:01
@Author  :   Kyle Wang 
@Version :   1.0
@Contact :   wangkui2000@hotmail.com
@License :   (C)Copyright 2017-2030, KyleWang
@Desc    :   whisper模型的加载和运行管理
ModelType = ["tiny", "base", "small", "medium",  "large"]
'''

import whisper
import queue
import logging
import time
import threading
''' Add project path to sys.path V1.0'''
import os, sys
__dir_name = os.path.dirname(os.path.realpath(__file__))
for _ in range(5):
    if "lib" not in os.listdir(__dir_name):
        __dir_name =  os.path.dirname(__dir_name)
    else:
        if __dir_name not in sys.path:
            sys.path.insert(0, __dir_name)
        break
from lib.funcsLib import timer, log_init


isTimerOn = True

class my_whisper(object):
    '''
    realtime Speech To Text. Wrap of OpenAI whisper model.
    '''
    def __init__(self, logger=None, maxQueueSize=10, isRealtime=False) -> None:
        '''
        isRealtime: 是否是在进行实时识别，如果是，则丢弃掉老语音数据，只对最新的语音进行识别
        '''
        self.isInit = False
        self.isRun  = False
        self.isRealtime = isRealtime
        self.audioQueue = queue.Queue(maxsize=10)
        self.callBack   = None
        if logger is None:
            self.log = log_init("my_whisper.log", 3, logging.DEBUG)
        else:
            self.log = logger
        self.log.info('*** my_whisper object init ***')


    def __del__(self):
        self.stop()


    @timer(4, isTimerOn)
    def init(self, model="base",folder="D:\\github\\whisper"):
        self.model  = whisper.load_model(model, download_root=folder)
        self.isInit = True


    @timer(4, isTimerOn)
    def trans(self, waveFile):
        '''transcribe single file. using the decode method for speed'''
        if not self.isInit:
            self.log.error("my_whisper object not Inited")
            return None
        result = None
        try:
            # TODO 是否可以不用音频文件，而是直接使用音频数据?
            if waveFile is not None:
                self.log.debug('trans_start. {}'.format(waveFile))
                audio = whisper.load_audio(waveFile)    # 耗时 0.05秒左右.
                audio = whisper.pad_or_trim(audio)      # 耗时 0.00 秒左右
                # make log-Mel spectrogram and move to the same device as the model
                mel = whisper.log_mel_spectrogram(audio).to(self.model.device) #耗时 0.01 秒左右
                # options = whisper.DecodingOptions(language="en")
                options = whisper.DecodingOptions()
                result = whisper.decode(self.model, mel, options)
                print(' '*4, result.text)
                return result.text
        except Exception as e:
            self.log.error("trans_failed: {}".format(e))
        return None


    @timer(4, isTimerOn)
    def trans2(self, waveFile):
        '''transcribe single file. using the decode method for speed'''
        if not self.isInit:
            self.log.error("my_whisper object not Inited")
            return None
        result = None
        try:
            # TODO 是否可以不用音频文件，而是直接使用音频数据?
            if waveFile is not None:
                self.log.debug('trans_start. {}'.format(waveFile))
                result = self.model.transcribe(waveFile)
                for segment in result['segments']:
                    print(' '*4, segment['text'])
                return result
        except Exception as e:
            self.log.error("trans_failed: {}".format(e))
        return None


    def run(self, callback=None):
        '''
        自动启动线程运行。
        callback: 获取结果后的回调函数
        '''
        self.isRun = True
        self.callBack = callback
        self.transT = threading.Thread(target=self.__trans_t, daemon=True)
        self.transT.start()
        self.log.debug("auto run start.")
    

    def add_audio(self, audioFile):
        if self.audioQueue.full():
            discard_file = self.audioQueue.get()
            self.audioQueue.task_done()
            self.log.warning('audio full. discard file:{}. qsize:{}'.format(discard_file, self.audioQueue.qsize()))
        self.audioQueue.put(audioFile)


    def stop(self):
        self.isRun = False
        self.log.debug("auto run stop.")


    def __trans_t(self):
        while True:
            if not self.isRun:
                break
            cur_audio = self.__get_audio()
            if cur_audio is None:
                time.sleep(0.1)
                continue
            res = self.trans(cur_audio)
            if res is None:
                continue
            if self.callBack is not None:
                self.callBack(res)
            

    def __get_audio(self):
        result = None
        if not self.audioQueue.empty():
            result = self.audioQueue.get()
            self.audioQueue.task_done()
            while self.isRealtime and not self.audioQueue.empty():
                result = self.audioQueue.get()
                self.audioQueue.task_done()
                self.log.warning('remove old result set.')
        return result


if __name__ == '__main__':
    isTimerOn = True
    myWhisper = my_whisper()
    myWhisper.init()
    # waveFile = ".//test_data//chinese01.wav"
    # waveFile = ".//test_data//english01.wav"
    waveFile = ".//test_data//japan01.wav"
    # res = myWhisper.trans(waveFile)
    # print(res)

    try:
        # myWhisper.run()
        for i in range(3):
            # myWhisper.add_audio(waveFile)
            res = myWhisper.trans2(waveFile)
            time.sleep(5)
        myWhisper.stop()
    except KeyboardInterrupt:
        myWhisper.stop()
        print("  Stop by KeyboardInterrupt!")
    del myWhisper