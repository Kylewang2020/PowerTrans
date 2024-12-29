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

    def listen_t(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=False,
        speech_completeness:bool=False,
        return_array:bool=True,
        )->None:
        """
        loop for continuously generate the audio file.
        put the result into the queue: data queue and manage it.
        """
        logging.info('listen_loop start')
        while True:
            if self.audio_queue.full():
                discard_file = self.audio_queue.get()
                self.audio_queue.task_done()
                logging.warning('audio full. discard file:{}. qsize:{}'.format(discard_file, self.audio_queue.qsize()))

            listen_res = self.listen(seconds=seconds, 
                                     save_wave=save_wave,
                                     mute_check=mute_check,
                                     speech_completeness=speech_completeness,
                                     return_array=return_array,
                                     )
            if self.isStop: break
            self.audio_queue.put(listen_res)
            logging.debug('audio-queue qsize:{}'.format(self.audio_queue.qsize()))
        logging.info('listen_loop end')

    def listen(self, 
        seconds:int=5, 
        save_wave:bool=False, 
        file_name:str=None, 
        mute_check:bool=True,
        speech_completeness:bool=False,
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
        :param speech_completeness: whether to secure a speech is completed. 
                            when it's true, the duration will be a dynamic one and a max 10 seconds more data could be added.
                            if the mute_check is on, then, the start silent segments will be discard untill there is a voice.
        :param return_array: Whether convert the raw audio data the a standard np.ndarray and return the array.

        Return: Dict["is_save":bool, "file":str, "is_array":bool, "array":np.ndarry, "is_mute":bool]
        ----------
        dict["array"]: == None when the is_array is False. Or np.ndarray:
                       shape=(frames, channels); dtype=np.float32; data range=[-1, 1]
        """
        if not self.isInit: raise RuntimeError(f"could not listern without init()")
        self.audioId += 1
        
        res = {"is_save": save_wave, "file": file_name, "is_array":return_array, 
               "is_mute":False,"array":None}
        if not speech_completeness or seconds<5:
            logging.debug((f"正常数据获取开始: channels={self.channels}; mute_check:{mute_check}; "
                           f"speech_completeness:{speech_completeness}"))
            second_bytes_list = []
            total_frames = int(self.framerate*seconds)
            remaining_frames = total_frames
            while remaining_frames>0:
                if self.isStop: break
                num_frames_to_read = min(self.chunkSize, remaining_frames)
                data = self.PyStream.read(num_frames_to_read)
                second_bytes_list.append(data)
                remaining_frames -= num_frames_to_read
                if _IsDEBUG:
                    print_progress_bar(total_frames-remaining_frames, total_frames)
            
            if _IsDEBUG: print()
            logging.debug((f'Audio[{self.audioId}]:{seconds}s, [ch{self.channels}, sr:{(self.framerate/1000):.3g}k].'
                        f' save:{save_wave}; r_arr:{return_array}; mute_check:{mute_check}; speech_completeness:{speech_completeness}'))
            
            if save_wave:
                file_name = self.__saveF(file_name, self.channels, self.sample_size, self.framerate, second_bytes_list)
                res["file"] = file_name
            if return_array:
                array = self.__b2array(second_bytes_list, self.format)
                res["array"] = array
                if mute_check and not speech_completeness:
                    res["is_mute"] = self.muteCheck(array)
                logging.debug(f'data[max={np.max(res["array"]):.4f}, min={np.min(res["array"]):.4f}, shape:{res["array"].shape}], mute:{res["is_mute"]}')
        else:
            array = self.listen_speech(seconds=seconds, mute_check=mute_check)
            if save_wave:
                file_name = self.__saveF(file_name, self.channels, 2, self.framerate, array)
                res["file"] = file_name
            if return_array:
                res["array"] = array
            logging.debug(f'data[max={np.max(res["array"]):.4f}, min={np.min(res["array"]):.4f}, shape:{res["array"].shape}]')
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
        :param seconds:     recording time length. in seconds.
        :param mute_check:  whether to check the audio signal is mute or not.
            只会影响到声音数据的开始。对于一次声音捕获而言，如果mute_check==True，
            则必须等待有声音的帧才开始记录捕获数据、开始录音；否则从声音捕获开始录音。

        Return: 
        ----------
        np.ndarray:
                shape=(frames, channels); 
                dtype=np.float32; data range=[-1, 1]
        """
        array = None
        array_seconds = 0
        second_bytes_list = []
        read_times = 0
        second_read_times = round(self.framerate/self.chunkSize)

        logging.debug((f"完整语音数据获取开始: channels={self.channels}; mute_check:{mute_check}; "
                        f"seconds:{seconds}"))
        while not self.isStop:
            data = self.PyStream.read(self.chunkSize)
            second_bytes_list.append(data)
            read_times += 1
            # 对没一秒的数据进行一次处理
            if read_times < second_read_times:
                continue
            logging.debug(f"read_times:{read_times}; second_read_times:{second_read_times}; array_seconds:{array_seconds}")
            seconds_arr = self.__b2array(second_bytes_list, self.format)
            if array is None:           # 获取起始帧
                if not mute_check:
                    array = seconds_arr
                    array_seconds += 1
                else:
                    if not self.muteCheck(seconds_arr):
                        array = seconds_arr
                        array_seconds += 1
            else:
                array = np.vstack((array, seconds_arr))
                array_seconds += 1
                if array_seconds>=(seconds-2):
                    if self.muteCheck(seconds_arr):
                        break
                if array_seconds>(seconds+10):
                    break

            read_times = 0
            second_bytes_list = []
        
        return array

    def run(self, 
        seconds=1,
        save_wave:bool=False, 
        mute_check:bool=True,
        speech_completeness:bool=True,
        return_array:bool=True,
        ):
        """ 
        Auto run. start the listen_t thread. 
        put audio result to data queue[audio_queue]. manage the queue.
        
        Parameters
        ----------
        :param seconds:     recording time length. in seconds.
        :param save_wave:   whether save the listen data to a wave file.
        :param mute_check:  whether to check the audio signal is mute or not.
        :param return_array: Whether convert the raw audio data the a standard np.ndarray and return the array.
        """
        self.listenT = threading.Thread(target=self.listen_t, 
                                        args=(seconds, save_wave, mute_check, speech_completeness, return_array), 
                                        daemon=True)
        self.listenT.start()

    def stop(self):
        """stop the liston loop."""
        self.isStop = True
        logging.debug('Recorder stopping')

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
        布尔值, 指示是否每一帧为静默(0:表示静默, 1:表示不静默)
        """
        audio_len = audio_signal.shape[0]
        frame_size = int(sr*frame_time_len)
        num_frames = audio_len//frame_size
        silence = [0]*num_frames
        
        logging.debug((f"能量检测开始: len={audio_len/sr}s, ch={audio_signal.shape[1]}, "
                       f"frame_time_len={frame_time_len}s, threshold={threshold}"))
        for ch in range(audio_signal.shape[1]):
            ch_audio = audio_signal[:, ch]
            ch_silence = []
            e_list = []
            for i in range(num_frames):
                start_idx = i * frame_size
                end_idx = (i + 1) * frame_size
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
                logging.debug(f"ch[{ch+1} of {audio_signal.shape[1]}] 切片数[{num_frames}]@切片时长{frame_time_len}s 之 能量列表:")
                e_list_s = [f"{x:.4f}" for x in e_list]
                for i in range(0, len(e_list_s), 10):
                    print(" ".join(e_list_s[i:i+10]))
        sound_frames = sum(silence)
        if sound_frames==0:
            logging.debug(f"\033[31mIs Mute! 无声音!\033[0m")
            return True
        else:
            logging.debug(f"\033[32m有声音: sound_frames={(sound_frames*frame_time_len):.1f}s of {audio_len/sr}s\033[0m")
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
            logging.debug('时长:{:.2g}s. File[{}]:"{}"'.format(
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
            self.PyAudio.terminate()
            logging.info("PyStream and PyAudio closed")


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
        listen_res = recoder.listen(seconds=10, 
                                    save_wave=True, 
                                    mute_check=True, 
                                    speech_completeness=True
                                   )
    # listen_test()

    def auto_run_test():
        log_init(LogFileName="recorder.log", logLevel=logging.DEBUG)
        recoder = Recorder()
        recoder.init()
        logging.info("\033[34m recoder.init() ok.\033[0m")
        try:
            recoder.run(seconds=10, 
                        save_wave=True, 
                        mute_check=True, 
                        speech_completeness=True
                        )
            logging.info("\033[34m recoder.run() ok.\033[0m")
            # 模拟外部信号控制程序停止
            while True:
                time.sleep(1)
                user_input = input("Press 'q' to quit: ")
                if user_input.lower() == 'q':
                    recoder.stop()  # 停止采集线程
                    break
        except KeyboardInterrupt:
            recoder.stop()  # 在 Ctrl+C 时停止
        time.sleep(2)
        logging.info("\033[34mMain: Threads have been stopped.\033[0m")
    
    auto_run_test()