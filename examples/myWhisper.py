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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from libpowertrans.funcsLib import timer, log_init, is_text_char

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
        self.language   = None
        self.callBack   = None
        if logger is None:
            self.log = log_init("my_whisper.log", 3, logging.DEBUG)
        else:
            self.log = logger
        self.log.info('*** my_whisper object init ***')


    def __del__(self):
        if self.isRun:
            self.stop()


    @timer(4, isTimerOn)
    def init(self, model="base",folder="D:\\github\\whisper"):
        self.model  = whisper.load_model(model, download_root=folder)
        self.isInit = True

    
    @timer(4, isTimerOn)
    def detect_language(self, waveFile):
        '''确定音频文件的语音类型'''
        if not self.isInit:
            self.log.error("my_whisper object not Inited")
            return
        if waveFile is not None:
            audio = whisper.load_audio(waveFile)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            _, probs = self.model.detect_language(mel)
            self.log.debug(f"当前语音类型是:{max(probs, key=probs.get)}")
            return max(probs, key=probs.get)


    def get_res_txt(self, res):
        resTxt = ""
        try:
            if isinstance(res, whisper.decoding.DecodingResult):
                resTxt = res.text
            elif isinstance(res, dict):
                for segment in res['segments']:
                    resTxt += segment['text']
                    if is_text_char(segment['text'][-1]):
                        resTxt += ", "
            else:
                self.log.error(f"Wrong result type: {type(res)}!")
        except Exception as e:
            self.log.warning(f"get result txt wrong: {e}")
        finally:
            return resTxt


    @timer(4, isTimerOn)
    def trans(self, waveFile):
        '''transcribe single file. using the decode method for speed'''
        if not self.isInit:
            self.log.error("my_whisper object not Inited")
            return None
        res = None
        try:
            # TODO 是否可以不用音频文件，而是直接使用音频数据?
            if waveFile is not None:
                self.log.debug('trans_start. {}'.format(waveFile))
                audio = whisper.load_audio(waveFile)    # 耗时 0.05秒左右.
                audio = whisper.pad_or_trim(audio)      # 耗时 0.00 秒左右
                # make log-Mel spectrogram and move to the same device as the model
                mel = whisper.log_mel_spectrogram(audio).to(self.model.device) #耗时 0.01 秒左右
                if self.language is None:
                    self.language = self.detect_language(waveFile)
                options = whisper.DecodingOptions(language=self.language)
                res = whisper.decode(self.model, mel, options)
                return self.get_res_txt(res)
        except Exception as e:
            self.log.error("trans_failed: {}".format(e))
        return None


    @timer(4, isTimerOn)
    def trans2(self, waveFile):
        '''transcribe single file. using the decode method for speed'''
        if not self.isInit:
            self.log.error("my_whisper object not Inited")
            return None
        res = None
        try:
            # TODO 是否可以不用音频文件，而是直接使用音频数据?
            if waveFile is not None:
                self.log.debug('trans_start. {}'.format(waveFile))
                if self.language is None:
                    self.language = self.detect_language(waveFile)
                res = self.model.transcribe(waveFile, language=self.language)
                return self.get_res_txt(res)
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
    myWhisper.init(model="medium")
    waveFile = ".//test_data//chinese01.wav"
    # waveFile = ".//test_data//english01.wav"
    waveFile = ".//test_data//japan01.wav"

    def test1(myWhisper): # 手动运行
        print("手动调用运行:")
        try:
            for i in range(3):
                res = myWhisper.trans(waveFile)
                print(f"    Result= \"{res}\"")
            myWhisper.language = None
            for i in range(3):
                res = myWhisper.trans2(waveFile)
                print(f"    Result= \"{res}\"")
            myWhisper.stop()
        except KeyboardInterrupt:
            myWhisper.stop()
            print("  Stop by KeyboardInterrupt!")
        del myWhisper

    def test2(myWhisper): # 自动运行
        print("自动调用运行:")
        try:
            myWhisper.run()
            for i in range(1):
                myWhisper.add_audio(waveFile)
                time.sleep(5)
            myWhisper.stop()
        except KeyboardInterrupt:
            myWhisper.stop()
            print("  Stop by KeyboardInterrupt!")
        del myWhisper
    
    test1(myWhisper)
