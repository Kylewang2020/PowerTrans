#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   recorder.py
@Time    :   2024/06/06 11:37:56
@Author  :   Kyle Wang 
@Version :   1.0
@Contact :   wangkui2000@hotmail.com
@License :   (C)Copyright 2017-2030, KyleWang
@Desc    :   实时抓取音频, 类定义
"""

from datetime import datetime
import numpy as np
import threading
import wave, pyaudio
import queue
import time

""" Add project path to sys.path V1.0"""
import os, sys
if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
from libpowertrans.funcsLib import logging, log_init, find_stereo_mix_device


class Recorder(object):
    """ 
    audio record class. For recording to the possible devices which could be mic or speaker 
    """
    audio = None; stream = None; isInit = False; isStop = False
    audioId=0; duration=0; framerate = 16000; channels = 1
    chunkSize = 1024; Format = pyaudio.paInt16; audio_queue = None

    def __init__(self, 
                 logFile="log.log", logOutput=3, 
                 logLevel=logging.DEBUG, logger=None) -> None:
        """
        Objects init, preparing logging. 日志初始化相关: 

        Parameters
        ----------
        logFile:  file name of log file.
        logOutput: [1:log file only; 2:console only; 3:both]. 
        logLevel:  same as the defination in logging module.
        """
        # self.framerate = 16000 # 16000 44100
        self.audio_queue = queue.Queue(maxsize=10)
        log_init(logFile, logOutput, logLevel) if logger is None else logger
        logging.debug('*** Recorder object init ***')

    def __del__(self):
        if self.isInit:
            self.stream.close()
            self.audio.terminate()
            logging.info("stream and audio closed")

    def init(self, 
        deviceId:int=None, isMic:bool=True, 
        CHANNELS=2, RATE=16000, FORMAT=pyaudio.paInt16, chunk=1024, 
        Threshold=0.025, MinSeconds=2, Silence_Duration=2):
        """
        Initialize the record equipment[mic or speaker] by pyAudio. Set the recording parameters. 
        
        By default(no input params), the mic will be choosed as audion sample device.
        
        Parameters
        ----------
        deviceId : int
            the device id of your computer. If it's None, then choose the default device.
        isMic : bool
            If the deviceId is None, choose the default mic or speaker.
            == True : audio from mic
            == False: audio from speaker[Stereo Mix]
        
        Threshold : 静音检测的阈值. 
                    如果数据格式是pyaudio.paInt16, 则实际阈值为0.016*32768.
                    如果数据格式是pyaudio.paFloat32, 则实际阈值为0.016*1.
        MinSeconds: 音频结果最短的时长
        Silence_Duration: 多少秒的静音判定为停顿
        """
        self.audio = pyaudio.PyAudio()
        try:
            device_id = deviceId
            if device_id is None:
                if isMic: # 麦克风
                    device_id   = self.audio.get_default_input_device_info()["index"]
                else:     # 查找“立体声混音”设备
                    device_id   = find_stereo_mix_device(self.audio, 0)
            device_info = self.audio.get_device_info_by_index(device_id)

            self.framerate = RATE
            self.channels  = CHANNELS
            self.chunkSize = chunk
            self.Format = FORMAT
            self.sample_size = pyaudio.get_sample_size(self.Format)

            self.stream = self.audio.open(rate=self.framerate, channels=self.channels, 
                                          format=self.Format, input=True, 
                                          input_device_index=device_id, 
                                          frames_per_buffer=self.chunkSize)

            logging.info("使用录音设备:\"{}\"; audio_index:{}; rate:{}; FORMAT={}; channels={}".format(
                           device_id, device_info["name"], self.framerate, self.channels, 
                           self.Format, self.channels))
            self.isInit = True
        except Exception as e:
            logging.error("init failed:{}".format(e))
        if not self.isInit:
            raise Exception("No input devices found.")

    def save_wave(self, file_name, Channels, sample_size, Rate, frames):
        with wave.open(file_name, 'wb') as wf:
            wf.setnchannels(Channels)
            wf.setsampwidth(sample_size)
            wf.setframerate(Rate)
            wf.writeframes(b''.join(frames))
            self.duration = wf.getnframes()
            logging.debug('SaveWave[{}] done. file:{}. duration:{:.2f}s'.format(
                self.audioId, file_name, self.duration/self.framerate))

    def listen(self, file_name:str=None, seconds=5):
        """record from select input stream to audio file."""
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        logging.debug(f'Record[{self.audioId}]...')
        
        audio_data = []
        total_frames = int(self.framerate*seconds)
        remaining_frames = total_frames
        while remaining_frames>0:
            num_frames_to_read = min(self.chunkSize, remaining_frames)
            data = self.stream.read(num_frames_to_read)
            audio_data.append(data)
            remaining_frames -= num_frames_to_read
            if self.isStop: break
        logging.debug(f'设备[{self.audioId}] {seconds}s 音频数据ok. len="{len(audio_data)}"')
        
        # if there is a file_nam, then save the result to the file_name. 
        # Else convert the audio_data to a ndarray.
        if file_name is not None:
            self.save_wave(file_name, self.channels, self.sample_size, self.framerate, audio_data)
            return file_name
        else:
            return self.bytes2ndarry(audio_data)

    def bytes2ndarry(self, audio_data):
        """
        将读到的音频字节流转化为ndarry,并均一化.
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        audio_data = b"".join(audio_data)
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        if self.channels==2:
            audio_np = audio_np.reshape(-1, 2)
        audio_np = audio_np.astype(np.float32)/2**15
        return audio_np

    def listen_t(self, seconds=1):
        """loop for continuously generate the audio file.
           put the result into the queue: data queue and manage it."""
        logging.debug('listen_loop start')
        while True:
            if self.audio_queue.full():
                discard_file = self.audio_queue.get()
                self.audio_queue.task_done()
                logging.warning('audio full. discard file:{}. qsize:{}'.format(discard_file, self.audio_queue.qsize()))

            self.audioId += 1
            # file_name = self.fileNameGet(self.audioId)
            listen_res = self.listen(seconds=seconds)
            if self.isStop: break
            self.audio_queue.put(listen_res)
        logging.debug('listen_loop end')


    def fileNameGet(self, id, folder=None):
        fileName = datetime.now().strftime("%d_%H-%M-%S") + "_" + str(id) + ".wav"
        if folder is None:
            path = os.getcwd()
            path = os.path.join(path, "data")
        if not os.path.exists(path): os.mkdir(path)
        fileName = os.path.join(path, fileName)
        return fileName
    

    def run(self, seconds=1):
        """ Auto run. start the listen_t thread. put audio result to data queue. manage the queue. """
        self.listenT = threading.Thread(target=self.listen_t, args=(seconds,), daemon=True)
        self.listenT.start()


    def get(self, isRealtime=True):
        """isRealtime=True: only keep and return the last result"""
        result = None
        if not self.audio_queue.empty():
            result = self.audio_queue.get()
            self.audio_queue.task_done()
            while isRealtime and not self.audio_queue.empty():
                result = self.audio_queue.get()
                self.audio_queue.task_done()
                logging.warning('audio data clean once. qsize:{}'.format(self.audio_queue.qsize()))
        return result


    def stop(self):
        """stop the liston loop."""
        self.isStop = True
        logging.debug('Recorder stopping')

if __name__ == "__main__":
    recoder = Recorder()
    recoder.init(CHANNELS=2)
    recoder.listen(seconds=2)