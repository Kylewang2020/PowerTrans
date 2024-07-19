#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   recorder.py
@Time    :   2024/06/06 11:37:56
@Author  :   Kyle Wang 
@Version :   1.0
@Contact :   wangkui2000@hotmail.com
@License :   (C)Copyright 2017-2030, KyleWang
@Desc    :   实时抓取音频, 类定义
'''

from datetime import datetime
import numpy as np
import threading
import wave, pyaudio
import queue
import time
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
from lib.funcsLib import logging, log_init, find_stereo_mix_device


class myRecorder(object):
    ''' audio record from mic or speaker '''
    def __init__(self, logF="myRecorder.log", logOut=3, 
                 logL=logging.DEBUG, logger=None) -> None:
        '''
        日志初始化相关: 
        logOut[1:log file only; 2:console only; 3:both]. 
        logL=same as logging def
        '''
        self.audio   = None
        self.stream  = None
        self.isInit  = False
        self.isStop  = False
        self.audioId   = 0
        self.duration  = 0
        self.framerate = 16000 # 16000 44100
        self.channels  = 2
        self.chunkSize = 1024
        self.Format    = pyaudio.paInt16 # pyaudio.paInt16 pyaudio.paFloat32
        self.audio_queue = queue.Queue(maxsize=10)
        if logger is None:
            self.log = log_init(logF, logOut, logL)
        else:
            self.log = logger
        self.log.info('*** myRecorder object init ***')

    def __del__(self):
        if self.isInit:
            self.stream.close()
            self.audio.terminate()
            self.log.info("stream and audio closed")

    def init(self, deviceId=None, isMic=True, CHANNELS=2, RATE=16000, FORMAT=pyaudio.paInt16, chunk=1024, 
             Threshold=0.025, MinSeconds=2, Silence_Duration=2):
        '''
        pyAudio open default input[isMic=True] or speaker[Stereo Mix] or specified deviceId as input source.
        isMic[True: audio from mic; False: audio from speaker]
        Threshold : 静音检测的阈值. 
                    如果数据格式是pyaudio.paInt16, 则实际阈值为0.016*32768.
                    如果数据格式是pyaudio.paFloat32, 则实际阈值为0.016*1.
        MinSeconds: 音频结果最短的时长
        Silence_Duration: 多少秒的静音判定为停顿
        '''
        self.audio = pyaudio.PyAudio()
        try:
            if deviceId is not None:
                device_id = deviceId
            elif isMic: # 麦克风
                device_id   = self.audio.get_default_input_device_info()["index"]
            else:     # 查找“立体声混音”设备
                device_id   = find_stereo_mix_device(self.audio, 0)
            device_info = self.audio.get_device_info_by_index(device_id)

            self.framerate = RATE
            self.channels  = CHANNELS
            self.chunkSize = chunk
            self.Format = FORMAT
            if self.Format == pyaudio.paInt16:      self.fmt = "paInt16"
            elif self.Format==pyaudio.paFloat32:    self.fmt = "paFloat32"
            else:                                   self.fmt = "unKnown"
            self.sample_size = self.audio.get_sample_size(self.Format)

            self.stream = self.audio.open(rate=self.framerate, channels=self.channels, 
                                          format=self.Format, input=True, 
                                          input_device_index=device_id, 
                                          frames_per_buffer=self.chunkSize)

            self.log.info("audio_index:{}; name:\"{}\"; rate:{}; FORMAT={}; channels={}".format(
                           device_id, device_info["name"], self.framerate, self.channels, self.fmt, self.channels))
            self.isInit = True
        except Exception as e:
            self.log.error("init failed:{}".format(e))
        if not self.isInit:
            raise Exception("No input devices found.")

    def save_wave(self, file_name, Channels, sample_size, Rate, frames):
        with wave.open(file_name, 'wb') as wf:
            wf.setnchannels(Channels)
            wf.setsampwidth(sample_size)
            wf.setframerate(Rate)
            wf.writeframes(b''.join(frames))
            self.duration = wf.getnframes()
            self.log.debug('SaveWave[{}] done. file:{}. duration:{:.2f}s'.format(
                self.audioId, file_name, self.duration/self.framerate))

    def listen(self, file_name, seconds=5):
        '''record from select input stream to audio file.'''
        self.log.debug(f'Record[{self.audioId}]...')
        count  = self.framerate//self.chunkSize*seconds
        frames = []
        silence_count = 0
        for i in range(0, count):
            data = self.stream.read(self.chunkSize)
            frames.append(data)
            audio_data = np.frombuffer(data, dtype=np.int16)    # 将二进制数据转换为numpy数组
            volume = np.mean(np.abs(audio_data))                # 计算音频振幅的均值作为音量
            silence_count = silence_count+1 if volume<(count/2) else 0
            if silence_count>50 and i>(self.framerate/self.chunkSize*seconds)/2: 
                break
            if self.isStop: return
        self.log.debug(f'Record[{self.audioId}] data ready')

        self.save_wave(file_name, self.channels, self.sample_size, self.framerate, frames)


    def listen_t(self, seconds=5):
        '''loop for continuously generate the audio file.
           put the result into the queue: data queue and manage it.'''
        self.log.debug('listen_loop start')
        while True:
            if self.audio_queue.full():
                discard_file = self.audio_queue.get()
                self.audio_queue.task_done()
                self.log.warning('audio full. discard file:{}. qsize:{}'.format(discard_file, self.audio_queue.qsize()))

            self.audioId += 1
            file_name = self.fileNameGet(self.audioId)
            self.listen(file_name, seconds)
            if self.isStop: break
            self.audio_queue.put(file_name)
        self.log.debug('listen_loop end')


    def fileNameGet(self, id, folder=None):
        fileName = datetime.now().strftime("%d_%H-%M-%S") + "_" + str(id) + ".wav"
        if folder is None:
            path = os.getcwd()
            path = os.path.join(path, "data")
        if not os.path.exists(path): os.mkdir(path)
        fileName = os.path.join(path, fileName)
        return fileName
    

    def run(self, seconds=5):
        ''' Auto run. start the listen_t thread. put audio result to data queue. manage the queue. '''
        self.listenT = threading.Thread(target=self.listen_t, args=(seconds,), daemon=True)
        self.listenT.start()


    def get(self, isRealtime=True):
        '''isRealtime=True: only keep and return the last result'''
        result = None
        if not self.audio_queue.empty():
            result = self.audio_queue.get()
            self.audio_queue.task_done()
            while isRealtime and not self.audio_queue.empty():
                result = self.audio_queue.get()
                self.audio_queue.task_done()
                self.log.warning('audio data clean once. qsize:{}'.format(self.audio_queue.qsize()))
        return result


    def stop(self):
        '''stop the liston loop.'''
        self.isStop = True
        self.log.debug('myRecorder stopping')
