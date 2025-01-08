#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#########################################################
#@Project      : libpowertrans
#@File         : pyaudio_basic.py
#@Created Date : 2024-12-29, 01:13:19
#@Author       : KyleWang[kylewang1977@gmail.com]
#@Version      : 1.0.1
#@Last Modified: Kyle@2025-01-03
#@Description  : 通用pyaudio 函数定义、基本功能测试，带命令解析
#@               设备列表、hostapi信息、录音测试
#@Copyright (c) 2025 KyleWang 
#########################################################
import pyaudio
import wave

_paFormat2Name = {
    pyaudio.paFloat32: 'paFloat32',
    pyaudio.paInt32: 'paInt32',
    pyaudio.paInt24: 'paInt24',
    pyaudio.paInt16: 'paInt16',
    pyaudio.paInt8:  'paInt8',
    pyaudio.paUInt8: 'paUInt8',
}

def hostapi_show(apiList=None, show_detail=True):
    default_hostapi_index = None
    try:
        audio = pyaudio.PyAudio()      # 初始化 PyAudio
        if show_detail:
            if apiList is None:
                apiList = []
                for i in range(audio.get_device_count()):
                    device_info = audio.get_device_info_by_index(i)
                    device_host_api = device_info["hostApi"]
                    if device_host_api not in apiList:
                        apiList.append(device_host_api)                
            print("\n当前设备的host_api[总数={}]列表:".format(len(apiList)))
            for api_id in apiList:
                api_Info = audio.get_host_api_info_by_index(api_id)
                print(api_Info)
        print("\n系统默认的 host_api:")
        api_Info = audio.get_default_host_api_info()
        default_hostapi_index = api_Info["index"]
        audio.terminate()
        print(api_Info)
    except Exception as e:
        print("hostapi-show Error: ", e)
    return apiList, default_hostapi_index

def find_stereo_mix_device(audio, host_api_index=0):
    """查找名称中包含“立体声混音”或“Stereo Mix”的设备编号"""
    mix_device_index = None
    info = audio.get_host_api_info_by_index(host_api_index)
    num_devices = info.get('deviceCount')
    
    for i in range(num_devices):
        device_info = audio.get_device_info_by_host_api_device_index(host_api_index, i)
        if 'Stereo Mix' in device_info.get('name', '') or '立体声混音' in device_info.get('name', ''):
            mix_device_index = i
            break
    return mix_device_index

def device_info_show(show_detail=True):
    """ 格式化列出所有音频设备"""
    hostApis = []
    try:
        audio = pyaudio.PyAudio()      # 初始化 PyAudio
        default_input_device  = audio.get_default_input_device_info()["index"]
        default_output_device = audio.get_default_output_device_info()["index"]
        mix_device = find_stereo_mix_device(audio)

        print("\n当前设备的音频设备[总数={}]列表:".format(audio.get_device_count()))
        print("  index, hostApi, Channels,       name")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            # 获取设备名称并尝试进行解码
            device_name = device_info['name']
            error_str = "鑰虫満"
            if error_str in device_name:
                device_name = device_name.encode('gbk').decode('utf-8', errors='replace')
                device_name = device_name.replace('\n', '').replace('\r', '')

            device_host_api = device_info["hostApi"]
            if device_host_api not in hostApis:
                hostApis.append(device_host_api)
            if show_detail or i in [default_input_device, default_output_device, mix_device]:
                print("  {:2d} |      {} |   [in:{}, out:{}] | {}".format(
                    i, device_info['hostApi'], device_info['maxInputChannels'], 
                    device_info['maxOutputChannels'], device_name))

        print("  缺省设置:[输入设备:{}, 输出设备:{}, Stereo Mix:{}]".format(
                default_input_device, default_output_device, mix_device))
        audio.terminate()
    except Exception as e:
        print("device-info-show Error: ", e)
    
    return hostApis, default_input_device, mix_device

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

def audio_capture(
    input_device_index = 1,
    seconds=3, 
    OUTPUT_FILENAME = "output.wav",
    format=pyaudio.paInt16, 
    channels=1, 
    rate=16000, 
    chunk=1024,
    ):
    """录制声音文件的测试函数"""
    try:
        audio = pyaudio.PyAudio()      # 初始化 PyAudio
        if input_device_index is None:
            input_device_index = audio.get_default_input_device_info()["index"]
            print(f"未指定录音设备，选择默认设备编号:{input_device_index} 进行录音")
        # 打开录音流
        stream = audio.open(format=format,
                        channels=channels,
                        rate=rate,
                        input=True,
                        input_device_index=input_device_index,  # 指定录音设备
                        frames_per_buffer=chunk)
        
        print("\n录音开始[device_id={}, ch={}, sr={}, format={}, 时长:{}s]...".format(
            input_device_index, channels, rate, _paFormat2Name.get(format), seconds))
        frames = []
        # 录制 5 秒的音频
        count = int(rate / chunk * seconds)
        for i in range(0, count):
            data = stream.read(chunk)  # 读取音频数据
            frames.append(data)        # 将读取的数据添加到 frames 列表中
            print_progress_bar(i, count)
        # 停止录音流
        print("\n录音结束.")
        stream.stop_stream()
        stream.close()    

        # 保存录音数据为 WAV 文件
        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(channels)    # 设置音频通道
            wf.setsampwidth(audio.get_sample_size(format))  # 设置采样宽度
            wf.setframerate(rate)        # 设置采样率
            wf.writeframes(b''.join(frames))  # 写入音频数据
        print(f"  录音已保存为{OUTPUT_FILENAME}")
    except Exception as e:
        print("audio-capture Error: ", e)

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
        print("get-hostapi Error: ", e)
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

if __name__ == '__main__':
    import argparse, sys, os
    fineN = os.path.basename(__file__)
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="使用pyAudio查看设备音频信息的脚本", 
                                     formatter_class=argparse.RawTextHelpFormatter)
    # 添加命令行参数
    parser.add_argument('-a', '--api', action='store_true', help=f"显示可用的 host api信息.\npython3 {fineN} -a")
    parser.add_argument('-d', '--device_list', action='store_true', help=f'显示设备可用的音频设备列表.\npython3 {fineN} -d')
    parser.add_argument('-r', '--record', action='store_true', help=f'是否进行录音(默认启用).\npython3 {fineN} -r -i 1 -l 5 -o test.wav')
    parser.add_argument('-i', '--device_id', type=int, default=None, help="指定录音设备的 ID")
    parser.add_argument('-l', '--length', type=int, default=3, help="录音时长（秒），默认为 5 秒")
    parser.add_argument('-o', '--output', type=str, default="output.wav", help="录音文件的输出路径（默认为 output.wav）")
    # 解析命令行参数
    args = parser.parse_args()

    ApiList = None
    if args.device_list:
        # 列出所有的音频设备信息
        ApiList, input_device, mix_device = device_info_show(True)
    
    if args.api:
        # 列出所有的HostApi信息
        hostapi_show(ApiList, True)

    if args.record:    # 声音录制
        audio_capture(input_device_index=args.device_id,
                      seconds=args.length,
                      OUTPUT_FILENAME=args.output)
    
    # 检查是否没有输入任何参数
    if len(sys.argv) == 1:
        hostapiInfo, default_hostapi_index = get_hostapi()
        print(f"\n设备的HostAPI 有:\n  {hostapiInfo}")
        print(f"  设备默认的 HostAPI: {default_hostapi_index}")

        InputDevice, default_input_device = get_input_device()
        print(f"  设备默认的 HostAPI下输入设备有:\n    {InputDevice}")
        print(f"\n默认摄入设备Index: {default_input_device}")
        if default_input_device in InputDevice.keys():
            print(f"  默认设备名称: {InputDevice.get(default_input_device)}")
