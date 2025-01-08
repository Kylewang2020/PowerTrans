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

import time
import queue
import threading
import wave
import pyaudio
import numpy as np
from datetime import datetime
from typing import Union, Tuple

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
    def __init__(self, maxQueueSize=10) -> None:
        self.PyAudio = None; 
        self.PyStream = None; 
        self.isInit = False; 
        self.isStop = False
        self.framerate = 16000; 
        self.channels = 1
        self.chunkSize = 1024; 
        self.format = pyaudio.paInt16
        self.sample_size = 0
        self.audioId=0
        self.audio_queue = queue.Queue(maxsize=maxQueueSize)
        self.listenT = None
        self.isRunning = False
        self.PyAudio = pyaudio.PyAudio()
        logging.debug('*** Recorder object init ***')

    def init(self, 
             deviceId:int= None, 
             isMic:bool= True, 
             samplerate:int= 16000, 
             channels:int = 1, 
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
        self.isStop = False
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
            logging.info("录音器Stream: audio_id:{}; sr:{:.2g}k; format={}; channels={}".format(
                device_id, self.framerate/1000, _paFormat2Name.get(format), channels, device_info["name"]))
            self.isInit = True
        except Exception as e:
            logging.error("init failed:{}".format(e))
        if not self.isInit:
            raise Exception("No input devices found.")

    def listen_t(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=False,
        speech_completeness:bool=False,
        )->None:
        """
        loop for continuously generate the audio file.
        put the result into the queue: data queue and manage it.
        """
        if not self.isInit: raise RuntimeError(f"未初始化!")
        logging.info('listen_loop start')
        self.isRunning = True
        while True:
            if self.audio_queue.full():
                discard_file = self.audio_queue.get()
                self.audio_queue.task_done()
                logging.warning('audio full. discard file:{}. qsize:{}'.format(discard_file, self.audio_queue.qsize()))

            listen_res = self.listen(seconds=seconds, 
                                     save_wave=save_wave,
                                     mute_check=mute_check,
                                     speech_completeness=speech_completeness,
                                     )
            if self.isStop: break
            self.audio_queue.put(listen_res)
            logging.debug('audio-queue qsize:{}'.format(self.audio_queue.qsize()))
        self.isRunning = False
        logging.info('listen_loop end')

    def listen(self, 
        seconds:int=5, 
        save_wave:bool=False, 
        file_name:str=None, 
        mute_check:bool=True,
        speech_completeness:bool=False,
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
        :param speech_completeness: whether to secure a speech is completed. 
                            when it's true, the duration will be a dynamic one and a max 10 seconds more data could be added.
                            if the mute_check is on, then, the start silent segments will be discard untill there is a voice.

        Return: Dict["is_save":bool, "file":str, "is_array":bool, "array":np.ndarry, "is_mute":bool]
        ----------
        dict["array"]: == None when the is_array is False. Or np.ndarray:
                       shape=(frames, channels); dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        self.audioId += 1
        
        res = {"is_save": save_wave, "file": file_name, "is_mute":False, "array":None}
        logging.debug((f"数据获取-audioId[{self.audioId}]:{seconds}s ch={self.channels}; sr:{(self.framerate/1000):.3g}k "
                        f"save:{save_wave}; mute_check:{mute_check}; speech_completeness:{speech_completeness}"))
        if not speech_completeness or seconds<5:
            second_bytes_list = []
            total_frames = int(self.framerate*seconds)
            remaining_frames = total_frames
            while remaining_frames>0:
                if self.isStop: break
                num_frames_to_read = min(self.chunkSize, remaining_frames)
                data = self.PyStream.read(num_frames_to_read)
                second_bytes_list.append(data)
                remaining_frames -= num_frames_to_read
                if _IsDEBUG and seconds>3:
                    print_progress_bar(total_frames-remaining_frames, total_frames)
            if _IsDEBUG and seconds>3: print()
            if save_wave and not self.isStop:
                file_name = self.__saveF(file_name, self.channels, self.sample_size, self.framerate, second_bytes_list)
                res["file"] = file_name
            array = self.__b2array(second_bytes_list, self.format)
            res["array"] = array
            if mute_check and not speech_completeness:
                res["is_mute"] = self.__muteEnergyCheck(array)
        else:
            array = self.listen_speech(seconds=seconds, mute_check=mute_check)
            if save_wave and not self.isStop:
                file_name = self.__saveF(file_name, self.channels, 2, self.framerate, array)
                res["file"] = file_name
            if not self.isStop:
                res["array"] = array
        if not self.isStop:
            logging.debug('array[shape:{}, max={:.4f}, min={:.4f}, 实际时长:{:.1f}s]'.format(
                res["array"].shape, np.max(res["array"]), np.min(res["array"]), (res["array"].shape[0]/self.framerate)))
        return res
    
    def listen_speech(self, 
        seconds:int=5, 
        mute_check:bool=True,
        )->np.ndarray:
        """
        完整语音捕捉。
        Capture the audio data from the select input stream. And secure a speech is completed.
        the duration will be a dynamic one and a max 10 seconds more data could be added.

        Parameters
        ----------
        :param seconds:     recording time length. in seconds. 期望时长.
        :param mute_check:  whether to check the audio signal is mute or not.
            只会影响到声音数据的开始。对于一次声音捕获而言，如果mute_check==True，
            则必须等待有声音的帧才开始记录捕获数据、开始录音；否则从声音捕获开始录音。

        Return: 
        ----------
        np.ndarray:
                shape=(frames, channels); 
                dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"未初始化!")
        array = None
        batch_bytes_list = []
        chunk_read_times  = 0                                       # 当前读取批次 所读取的 次数
        sum_read_times    = 0                                       # 当前数据 实际 所积累读取 的次数
        second_read_times = round(self.framerate/self.chunkSize)    # 每秒应该读取的次数
        min_read_times    = second_read_times*(seconds-2)           # 最小读取次数 = 期望时长减去2s 所需要读取的次数
        max_read_times    = second_read_times*(seconds+10)          # 最大读取次数 = 期望时长+10s 所需要读取的次数

        logging.info(f"完整语音数据获取开始: ch={self.channels}; mute_check:{mute_check}; chunkSize:{self.chunkSize}")
        logging.debug(f"期望时长:{seconds}s; 每秒读取次数:{second_read_times}, 最小读取次数={min_read_times}; 最大读取次数:{max_read_times};")
        # 1. 先按照 1s 的数据进行读取
        # 2. 对1s的数据开始判断，如果能量值低于阈值，则放弃对应的数据
        # 3. 检测到有能量的数据后，保存当前1s的数据到 array，array不为空，有了第一秒的数据作为起始
        batch_times = second_read_times
        isDone = False
        while not self.isStop and not isDone:
            data = self.PyStream.read(self.chunkSize)
            batch_bytes_list.append(data)
            chunk_read_times += 1
            # 对每一秒的数据进行一次处理
            if chunk_read_times < batch_times:
                continue
            batch_array = self.__b2array(batch_bytes_list, self.format)
            if array is None:           # 获取起始帧
                if not mute_check or not self.__muteEnergyCheck(batch_array):
                    array = batch_array
                    sum_read_times += chunk_read_times
            else:
                array = np.vstack((array, batch_array))
                sum_read_times += chunk_read_times
                if sum_read_times >= min_read_times:
                    batch_times = int(second_read_times*0.5)
                    if self.__muteEnergyCheck(batch_array):
                        isDone = True
                elif sum_read_times>max_read_times:
                    isDone = True
            logging.info(f"批次读取次数:{chunk_read_times}; 当前数据总次数:{sum_read_times}")
            chunk_read_times = 0
            batch_bytes_list = []
        
        if self.isStop:
            return None
        return array

    def run(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=True,
        speech_completeness:bool=True,
        ):
        """ 
        Auto run. start the listen_t thread. 
        put audio result to data queue[audio_queue]. manage the queue.
        
        Parameters
        ----------
        :param seconds:     recording time length. in seconds.
        :param save_wave:   whether save the listen data to a wave file.
        :param mute_check:  whether to check the audio signal is mute or not.
        """
        if not self.isInit: raise RuntimeError(f"未初始化!")
        self.listenT = threading.Thread(target=self.listen_t, 
                                        args=(seconds, save_wave, mute_check, speech_completeness), 
                                        daemon=True)
        self.listenT.start()

    def stop(self):
        """stop the liston loop."""
        self.isStop = True
        if self.isRunning:
            stop_waiting_times = 0
            while self.isRunning:
                time.sleep(0.1)
                stop_waiting_times += 1
                if stop_waiting_times>10:
                    break
        if self.isRunning:
            logging.warning('Recorder stop abnormal. The listed thread still on!')
        if self.isInit:
            self.isInit = False
            self.PyStream.close()
            self.PyStream = None
            logging.info('PyStream closed')
        logging.info('Recorder stopping')

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

    @staticmethod
    def __muteEnergyCheck(
        audio_signal:np.ndarray,
        framesize:int = 1024,
        threshold:float=0.001):
        """
        基于音频能量的静默检测.
        将输入的声音数据进行分段[framesize], 平方平均, 判断是否超过阈值。
        并汇总整个分段后的结果。
        @2025-1-6 日修改:
          不以时间为分段,而是以读取数据的chunksize来进行分段。

        Parameters
        ----------
        
        :audio_signal: np.ndarray
            standardlized input audio signal data. 
            Require: shape:(xxx, channels); dtype=float32; data range:[-1, 1]
        :framesize: int
            数据进行分段的尺寸
        :param threshold: 
            能量阈值，低于此值认为是静默段

        Return: 
        ----------
        布尔值, 指示是否每一帧为静默(0:表示静默, 1:表示不静默)
        """
        audio_len = audio_signal.shape[0]
        num_frames = audio_len//framesize
        if num_frames<=0:
            logging.warning(f"能量检测异常! data_len={audio_len}, framesize={framesize}")
            raise RuntimeError(f"能量检测异常! data_len={audio_len}, framesize={framesize}")
        silence = [0]*num_frames
        
        logging.debug("能量检测开始: data_len:{}, ch:{}, threshold:{}, framesize:{}, num_frames:{}".format(
                    audio_len, audio_signal.shape[1], threshold, framesize, num_frames))
        for ch in range(audio_signal.shape[1]):
            ch_audio = audio_signal[:, ch]
            ch_silence = []
            e_list = []
            for i in range(num_frames):
                start_idx = i * framesize
                end_idx = (i + 1) * framesize
                frame = ch_audio[start_idx:end_idx]
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
                logging.debug("ch[{} of {}]\n切片能量:{}".format(
                            ch+1, audio_signal.shape[1], np.round(e_list, 4)))
        sound_frames = sum(silence)
        if sound_frames==0:
            logging.debug(f"\033[31mIs Mute! 无声音!\033[0m")
            return True
        else:
            logging.debug(f"\033[32m有声音: 能量切片数:{sound_frames}, 总切片数:{num_frames}\033[0m")
            return False
        
    def __b2array(self, bytes_list, sample_format):
        """
        bytes to array. convert the bytes list from pystream to a np.ndarry.
        将读到的音频字节流转化为ndarry, 并均一化.

        Parameters
        ----------
        bytes_list: bytes list from audio stream.

        Return:
        ----------
        np.ndarray: 
            :shape=(frames, channels); when channels>=1
            :dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        # 1: bytes stream==>> np.ndarray
        bytes_list = b"".join(bytes_list)
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
        audio_np = np.frombuffer(bytes_list, dtype=dtype)
        
        # 2: reshaped from (xxx, ) to (xxx/channels, channels)
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

    def __saveF(self, 
        file_name:str = None, 
        Channels:int = 1,
        sample_size:int = 2, 
        Rate:int = 16000, 
        frames:Union[list, np.ndarray] = None):
        """
        save audio bytes to wave file. 保存音频流数据到以wav格式到文件.
        """
        if file_name is None:
            file_name = self.fileNameGet(self.audioId)
        if isinstance(frames, np.ndarray):
            if frames.dtype == np.float32:
                frames = np.clip(frames*32767, -32768, 32767).astype(np.int16)  # 映射到 int16 范围
                sample_size = 2
            elif frames.dtype != np.int16:
                logging.warning(f"当前需要保存的ndarry数据格式:{frames.dtype} 不在支持的范围内")
                raise RuntimeError(f"保存ndarry数据类型异常![{frames.dtype}]")
        with wave.open(file_name, 'wb') as wf:
            wf.setnchannels(Channels)
            wf.setsampwidth(sample_size)
            wf.setframerate(Rate)
            wf.writeframes(b''.join(frames))
            duration = wf.getnframes()
            logging.info('录音时长:{:.2g}s. 保存文件[{}]:"{}"'.format(
                duration/self.framerate, self.audioId, file_name))
        return file_name
    
    def fileNameGet(self, id, folder=None):
        fileName = datetime.now().strftime("%d_%H-%M-%S")+"_ch"+str(self.channels)+"_id"+str(id)+".wav"
        if folder is None:
            path = os.getcwd()
            path = os.path.join(path, "temp")
        if not os.path.exists(path): os.mkdir(path)
        fileName = os.path.join(path, fileName)
        return fileName
    
    def __del__(self):
        if self.isInit:
            self.PyStream.close()
            logging.info("PyStream closed")
        self.PyAudio.terminate()
        logging.info("PyAudio terminate")


if __name__ == "__main__":
    
    def listen_test():
        log_init(LogFileName="recorder.log", logLevel=logging.DEBUG)
        recoder = Recorder()
        recoder.init(isMic=True,
                     channels=1,
                    )
        for i in range(2, 0, -1):
            print(f'\r   录音开始倒计时: {i} 秒', end='', flush=True)
            time.sleep(1)
        print('\r   开始录音  ........      ')
        listen_res = recoder.listen(seconds=5, 
                                    save_wave=True, 
                                    mute_check=True, 
                                    speech_completeness=True
                                   )
        print(listen_res["array"].shape)
        recoder.stop()
    listen_test()

    def auto_run_test():
        log_init(LogFileName="recorder.log", logLevel=logging.DEBUG)
        recoder = Recorder()
        recoder.init()
        logging.info("\033[34m recoder.init() ok.\033[0m")
        try:
            recoder.run(seconds=5, 
                        save_wave=True, 
                        mute_check=True, 
                        speech_completeness=True
                        )
            logging.info("\033[34m recoder.run() ok.\033[0m")
            # 模拟外部信号控制程序停止
            while True:
                time.sleep(1)
                curData = recoder.get(False)
                if curData is not None:
                    logging.info("\033[34m 取得数据. array.shape={}\033[0m".format(curData["array"].shape))
        except KeyboardInterrupt:
            recoder.stop()  # 在 Ctrl+C 时停止
        time.sleep(2)
        logging.info("\033[34mMain: Threads have been stopped.\033[0m")
    
    # auto_run_test()