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
from libpowertrans.funcsLib import (
        logging, 
        log_init, 
        find_stereo_mix_device,
        print_progress_bar)

_paFormat2Name = {
    pyaudio.paFloat32: 'paFloat32',
    pyaudio.paInt32: 'paInt32',
    pyaudio.paInt24: 'paInt24',
    pyaudio.paInt16: 'paInt16',
    pyaudio.paInt8:  'paInt8',
    pyaudio.paUInt8: 'paUInt8',
}

_IsDEBUG = True

class Recorder(object):
    """ 
    audio record class. For recording to the possible devices which could be mic or speaker 
    """
    PyAudio = None; PyStream = None; isInit = False; isStop = False
    framerate = 16000; channels = 1
    chunkSize = 1024; format = pyaudio.paInt16
    audio_queue = None; audioId=0

    def __init__(self, maxQueueSize=10) -> None:
        self.audio_queue = queue.Queue(maxsize=maxQueueSize)
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
        :param deviceId:    the id of the wanted audio capture device in your computer. 
                            If it's None, then choose the default device.
        :param isMic:       whether to choose the default mic as capture device when the deviceId is None.
                            == True : audio from mic
                            == False: audio from speaker[Stereo Mix]
        :param samplerate:  Sampling rate(Hz).
        :param channels:    Number of sample channels
        :param format:      Sampling size and format. See |PaSampleFormat|. A |PaSampleFormat| constant. 
        :param frames_per_buffer:   Specifies the number of frames per buffer.
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
            self.sample_size = pyaudio.get_sample_size(format)

            self.PyStream = self.PyAudio.open(rate=samplerate, 
                                              channels=channels, 
                                              format=format, 
                                              input=True, 
                                              input_device_index=device_id, 
                                              frames_per_buffer=self.chunkSize )
            logging.info("录音器: audio_id:{}; sr:{:.2g}k; format={}; channels={}".format(
                device_id, self.framerate/1000, _paFormat2Name.get(format), channels, device_info["name"]))
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
            logging.debug('时长:{:.2g}s. File[{}]:"{}"'.format(
                duration/self.framerate, self.audioId, file_name))
        return file_name
    
    def listen(self, 
        seconds=5, 
        save_wave:bool=False, 
        file_name:str=None, 
        mute_check:bool=False,
        return_array:bool=True,
        ):
        """
        Capture the audio data from the select input stream to a file or a ndarray.

        Parameters
        ----------
        :param seconds:     recording time length. in seconds.
        :param save_wave:   whether save the listen data to a wave file.
        :param file_name:   Used when the Param "save_wave" is true. The wave file's name.
                            if it's None, the use the auto generated file name.
        :param mute_check:  whether to check the audio signal is mute or not.
        :param return_array: Whether convert the raw audio data the a standard np.ndarray and return the array.

        Return: Dict
        ----------
        =["is_save":bool, "file":str, "is_array":bool, "array":np.ndarry, "is_mute":bool]
        dict["array"]: np.ndarray or None when the is_array is False.
              :shape=(frames, channels); when channels>1
              :shape=(frames, ); when channels==1
              :dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        self.audioId += 1
        
        res = {"is_save": save_wave, "file": file_name, "is_array":return_array, 
               "is_mute":False,"array":None}
        audio_data = []
        total_frames = int(self.framerate*seconds)
        remaining_frames = total_frames

        while remaining_frames>0:
            num_frames_to_read = min(self.chunkSize, remaining_frames)
            data = self.PyStream.read(num_frames_to_read)
            audio_data.append(data)
            remaining_frames -= num_frames_to_read
            if self.isStop: break
            if _IsDEBUG:
                print_progress_bar(total_frames-remaining_frames, total_frames)
        if _IsDEBUG: print()
        logging.debug((f'Audio[{self.audioId}] {seconds}s ok.[ch{self.channels}, sr:{(self.framerate/1000):.3g}k]'
                       f' save:{save_wave} r_arr:{return_array} mute_check={mute_check}'))
        
        if save_wave:
            file_name = self.__saveF(file_name, self.channels, self.sample_size, self.framerate, audio_data)
            res["file"] = file_name
        if return_array:
            array = self.b2array(audio_data, self.format)
            res["array"] = array
            if mute_check:
                res["is_mute"] = self.muteCheck(array)
            logging.debug(f'data[max={np.max(res["array"]):.4f}, min={np.min(res["array"]):.4f}, shape:{res["array"].shape}], mute:{res["is_mute"]}')

        return res
    
    @staticmethod
    def muteCheck(
        audio_signal:np.ndarray, 
        sr:int=16000, 
        frame_time_len:float = 0.1,
        threshold:float=0.001):
        """
        基于音频能量的静默检测.
        将输入的声音数据进行分段[依据], 平方平均, 判断是否超过阈值。
        并汇总整个分段后的结果。

        Parameters
        ----------
        
        :audio_signal: np.ndarray
            standardlized input audio signal data. 
            Require: shape:(xxx, channels); dtype=float32; data range:[-1, 1]
        :sr: int
            sample rate for input audion signal data.
        :frame_time_len: float
            对输入数据进行分段的段窗口的时间长度, 单位"秒"。
            如: 值0.1、sr=16000, 则意味着要将数据分成 1600个一段,进行能量计算和判断。
        :param threshold: 
            能量阈值，低于此值认为是静默段

        Return: 
        ----------
        一个布尔数组, 指示每一帧是否为静默(0:表示静默, 1:表示不静默)
        """
        audio_len = audio_signal.shape[0]
        frame_size = int(sr*frame_time_len)
        num_frames = audio_len//frame_size
        silence = [0]*num_frames
        
        logging.debug((f"muteCheck start: len={audio_len/sr}s, ch={audio_signal.shape[1]}, "
                       f"frame_time_len={frame_time_len}s, threshold={threshold}"))
        for ch in range(audio_signal.shape[1]):
            ch_audio = audio_signal[:, ch]
            ch_silence = []
            e_list = []
            for i in range(num_frames):
                start_idx = i * frame_size
                end_idx = (i + 1) * frame_size
                frame = audio_signal[start_idx:end_idx]
                # 计算当前帧的能量
                energy = np.sum(np.square(frame)) / len(frame)  # 平均能量
                # 判断是否为静默
                if energy < threshold:
                    ch_silence.append(0)
                else:
                    ch_silence.append(1)
                if _IsDEBUG: e_list.append(energy)
            
            silence = [x | y for x, y in zip(silence, ch_silence)]
            if _IsDEBUG:
                logging.debug(f"能量检测: ch{ch} frmes[{i}] energy:")
                e_list_s = [f"{x:.4f}" for x in e_list]
                for i in range(0, len(e_list_s), 10):
                    print(" ".join(e_list_s[i:i+10]))
        sound_frames = sum(silence)
        logging.debug(f"sound_frames:{(sound_frames*frame_time_len):.1f}s of {audio_len/sr}s")
        if sound_frames==0:
            return True
        else:
            return False
        
    def b2array(self, audio_data, sample_format):
        """
        bytes to array. convert the bytes list from pystream to a np.ndarry.
        将读到的音频字节流转化为ndarry, 并均一化.

        Parameters
        ----------
        audio_data: bytes list from audio stream.

        Return:
        ----------
        np.ndarray: 
            :shape=(frames, channels); when channels>1
            :shape=(frames, ); when channels==1
            :dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        # 1: bytes stream==>> np.ndarray
        audio_data = b"".join(audio_data)
        if sample_format==pyaudio.paFloat32:
            dtype=np.float32
        elif sample_format==pyaudio.paInt32:
            dtype=np.int32
        elif sample_format==pyaudio.paInt16:
            dtype=np.int16
        elif sample_format==pyaudio.paInt8:
            dtype=np.int8
        else:
            raise RuntimeError("paaudion 采集数据格式不在范围内!")
        audio_np = np.frombuffer(audio_data, dtype=dtype)
        
        # 2: reshaped from (xxx, ) to (xxx/channels, channels)
        if self.channels>1:
            audio_np = audio_np.reshape(-1, self.channels)
        
        # 3: dtype==>>np.float32; data range==>>[-1, 1]
        if dtype==np.int32:
            audio_np = audio_np.astype(np.float32)/2147483648.0
            # logging.debug(f"数据格式转化&均一化: paInt32=>np.int32=>np.float32")
        elif dtype==np.int16:
            audio_np = audio_np.astype(np.float32)/32768.0
            # logging.debug(f"数据格式转化&均一化: paInt16=>np.int16=>np.float32")
        elif dtype==np.int8:
            audio_np = audio_np.astype(np.float32)/128.0
            # logging.debug(f"数据格式转化&均一化: paInt8=>np.int8=>np.float32")
        return audio_np

    def listen_t(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=False,
        return_array:bool=True,
        ):
        """
        loop for continuously generate the audio file.
        put the result into the queue: data queue and manage it.
        """
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
        fileName = datetime.now().strftime("%d_%H-%M-%S")+"_ch"+str(self.channels)+"_id"+str(id)+".wav"
        if folder is None:
            path = os.getcwd()
            path = os.path.join(path, "temp")
        if not os.path.exists(path): os.mkdir(path)
        fileName = os.path.join(path, fileName)
        return fileName
    
    def run(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=False,
        return_array:bool=True,
        ):
        """ 
        Auto run. start the listen_t thread. put audio result to data queue. manage the queue.
        """
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
    recoder.init()

    for i in range(2, 0, -1):
        print(f'\r   录音开始倒计时: {i} 秒', end='', flush=True)
        time.sleep(1)
    print('\r   开始录音  ........      ')
    audio_data = recoder.listen(seconds=3, save_wave=True, mute_check=True, return_array=True)
