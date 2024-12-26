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
    PyAudio = None; PyStream = None; isInit = False; isStop = False
    framerate = 16000; channels = 1
    chunkSize = 1024; format = pyaudio.paInt16
    audio_queue = None; audioId=0

    def __init__(self) -> None:
        self.audio_queue = queue.Queue(maxsize=10)
        logging.debug('*** Recorder object init ***')

    def init(self, 
             deviceId:int= None, 
             isMic:bool= True, 
             samplerate:int= 16000, 
             channels:int = 2, 
             format=pyaudio.paInt16, 
             frames_per_buffer:int= 1024):
        """
        Initialize the record equipment[mic or speaker] by pyAudio. Set the recording parameters. 
        Open the choosed device. Initialize an audio stream.
        
        By default(no input params), the mic will be choosed as audion sample device.
        
        Parameters
        ----------
        deviceId : int
            the device id of your computer. If it's None, then choose the default device.
        isMic : bool
            If the deviceId is None, choose the default mic or speaker.
            == True : audio from mic
            == False: audio from speaker[Stereo Mix]
        samplerate: int
            Sampling rate
        channels: int
            Number of channels
        format: 
            Sampling size and format. See |PaSampleFormat|.
            A |PaSampleFormat| constant. 
        frames_per_buffer: int
            Specifies the number of frames per buffer.
        """
        if self.isInit: raise RuntimeError(f"重复初始化!")

        self.PyAudio = pyaudio.PyAudio()
        try:
            device_id = deviceId
            if device_id is None:
                if isMic: # 麦克风
                    device_id   = self.PyAudio.get_default_input_device_info()["index"]
                else:     # 查找“立体声混音”设备
                    device_id   = find_stereo_mix_device(self.PyAudio, 0)
            device_info = self.PyAudio.get_device_info_by_index(device_id)

            self.framerate = samplerate
            self.channels  = channels
            self.chunkSize = frames_per_buffer
            self.format = format
            self.sample_size = pyaudio.get_sample_size(self.format)

            self.PyStream = self.PyAudio.open(rate=self.framerate, 
                                              channels=self.channels, 
                                              format=self.format, 
                                              input=True, 
                                              input_device_index=device_id, 
                                              frames_per_buffer=self.chunkSize )

            logging.info("录音设备:\"{}\"; audio_index:{}; rate:{}; format={}; channels={}".format(
                            device_info["name"], device_id, self.framerate, self.format, self.channels))
            self.isInit = True
        except Exception as e:
            logging.error("init failed:{}".format(e))
        if not self.isInit:
            raise Exception("No input devices found.")

    def __saveF(self, file_name, Channels, sample_size, Rate, frames):
        """
        save audio bytes to wave file. 保存音频流数据到以wav格式到文件.
        """
        if file_name is None:
            file_name = self.fileNameGet(self.audioId)
        with wave.open(file_name, 'wb') as wf:
            wf.setnchannels(Channels)
            wf.setsampwidth(sample_size)
            wf.setframerate(Rate)
            wf.writeframes(b''.join(frames))
            duration = wf.getnframes()
            logging.debug('File[{}] saved. duration:{:.2f}s. file:"{}"'.format(
                self.audioId, duration/self.framerate, file_name))

    def listen(self, seconds=5, save_wave:bool=False, file_name:str=None, return_array:bool=True):
        """
        record from select input stream to audio file.
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        logging.debug(f'Audio[{self.audioId}] {seconds}s [ch={self.channels}; sr={self.framerate}] starting...')
        
        self.audioId += 1
        
        audio_data = []
        total_frames = int(self.framerate*seconds)
        remaining_frames = total_frames
        while remaining_frames>0:
            num_frames_to_read = min(self.chunkSize, remaining_frames)
            data = self.PyStream.read(num_frames_to_read)
            audio_data.append(data)
            remaining_frames -= num_frames_to_read
            if self.isStop: break
        logging.debug(f'Audio[{self.audioId}] {seconds}s ok. save file:{save_wave}. return ndarray:{return_array}')
        
        # if there is a file_nam, then save the result to the file_name. 
        # Else convert the audio_data to a ndarray.
        if save_wave:
            self.__saveF(file_name, self.channels, self.sample_size, self.framerate, audio_data)
        if return_array:
            return self.b2array(audio_data)
        

    def b2array(self, audio_data):
        """
        将读到的音频字节流转化为ndarry, 并均一化.
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        audio_data = b"".join(audio_data)

        if self.format==pyaudio.paFloat32:
            dtype=np.float32
        elif self.format==pyaudio.paInt32:
            dtype=np.int32
        elif self.format==pyaudio.paInt16:
            dtype=np.int16
        elif self.format==pyaudio.paInt8:
            dtype=np.int8
        else:
            raise RuntimeError("paaudion 采集数据格式不在范围内!")
        audio_np = np.frombuffer(audio_data, dtype=dtype)
        if self.channels==2:
            audio_np = audio_np.reshape(-1, 2)
        if dtype==np.int32:
            audio_np = audio_np.astype(np.float32)/2147483648.0
            logging.debug(f"数据格式转化&均一化: paInt32=>np.int32=>np.float32")
        elif dtype==np.int16:
            audio_np = audio_np.astype(np.float32)/32768.0
            logging.debug(f"数据格式转化&均一化: paInt16=>np.int16=>np.float32")
        elif dtype==np.int8:
            audio_np = audio_np.astype(np.float32)/128.0
            logging.debug(f"数据格式转化&均一化: paInt8=>np.int8=>np.float32")
        logging.debug(f"audio ndarry shape={audio_np.shape}, dtype={audio_np.dtype} pa-format={self.format}")

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

            listen_res = self.listen(seconds=seconds, return_array=True)
            if self.isStop: break
            self.audio_queue.put(listen_res)
        logging.debug('listen_loop end')

    def fileNameGet(self, id, folder=None):
        fileName = datetime.now().strftime("%d_%H-%M-%S") + "_id" + str(id)  + "_ch" + str(self.channels)+ ".wav"
        if folder is None:
            path = os.getcwd()
            path = os.path.join(path, "temp")
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

    def __del__(self):
        if self.isInit:
            self.PyStream.close()
            self.PyAudio.terminate()
            logging.info("PyStream and PyAudio closed")


if __name__ == "__main__":
    log_init(LogFileName="recorder.log", logLevel=logging.DEBUG)
    recoder = Recorder()
    recoder.init(channels=1, format=pyaudio.paInt16)

    for i in range(3, 0, -1):
        print(f'\r 录音开始倒计时: {i} 秒', end='', flush=True)
        time.sleep(1)
    print('\r 开始录音...')
    audio_data = recoder.listen(seconds=5, save_wave=True, return_array=True)
    # print(audio_data.shape)