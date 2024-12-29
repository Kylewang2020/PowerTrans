# PyAudio

PyAudio为跨平台音频 I/O 库PortAudio v19 提供Python 绑定。借助 PyAudio, 您可以轻松地使用 Python 在各种平台(例如 GNU/Linux、Microsoft Windows 和 Apple macOS)上播放和录制音频。

PyAudio 根据 MIT 许可证分发
[PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)
[PortAudio](https://www.portaudio.com/)

## Install

``` sh
pip install pyaudio
```

## 主要函数

``` py
import pyaudio

# Create an interface to PortAudio
p = pyaudio.PyAudio()  

# 获取计算机上的音频设备数量
device_count = p.get_device_count()

# 获取指定设备的详细信息
device_info = p.get_device_info_by_index(i)

# 使用 get_host_api_info_by_index 方法获取主机 API 的详细信息, 包括主机 API 的名称. 
# 其中的 hostapi 字段表示该设备所使用的音频主机 API(Audio Host API)。
host_api_info = p.get_host_api_info_by_index(hostApis[j])
```

## hostapi

>音频主机 API 是用于与音频设备进行通信的软件接口。指的是音频库或音频接口, 用于与计算机的音频硬件交互。不同的 Host API 提供了不同的功能和性能特性, 并且支持不同的平台和音频设备。理解和使用合适的 Host API 对于确保音频应用程序的兼容性和性能至关重要。不同的操作系统和系统配置可能会支持不同的音频主机 API。

#### 常见的 Host API

- **MME (Multimedia Extensions)**:Windows 的默认音频接口, 兼容性好, 但延迟较高。
- ** WASAPI(Windows Audio Session API)**:
  Windows 平台的音频主机 API, 用于访问音频设备和音频功能。
- **DirectSound**:
  Windows 平台上的音频主机 API, 用于低延迟的音频输入输出。
- **ALSA(Advanced Linux Sound Architecture)**:
  Linux 平台上的音频主机 API, 提供对音频硬件的访问。
- **Core Audio**:
  MacOS 平台上的音频主机 API, 用于音频输入输出和处理。
- **ASIO (Audio Stream Input/Output)**:
  专业音频接口, 提供非常低的延迟, 但需要专用驱动程序。

> `hostapi` 字段的值是一个整数, 表示该设备所使用的音频主机 API 的索引。通常情况下, 大多数用户不需要关心 `hostapi` 字段, 除非他们需要特定的音频主机 API 功能或者与特定平台相关的音频处理。
在 PyAudio 中, `hostapi` 字段的值可以通过 get_device_info_by_index 方法返回的设备信息字典中获取。如果需要使用特定的音频主机 API, 可以在打开音频流时通过参数指定。
例如, 在使用 PyAudio 打开音频流时, 可以使用 `output_host_api_specific_stream_info` 或 `input_host_api_specific_stream_info` 参数来指定与特定音频主机 API 相关的参数。

## PyAudio 直接录制扬声器

- Windows 上的 `立体声混音` (**Stereo Mix**) 是一个录音功能, 允许用户录制计算机播放的所有声音。也就是说, 使用“立体声混音”可以捕捉到所有通过声卡输出的音频, 包括系统提示音、媒体播放器播放的音乐和视频、网络电话的声音等。这对于制作教程、录制在线流媒体、捕捉游戏音效等非常有用。
- PyAudio 主要用于录制和播放麦克风或其他输入设备的声音, 而不是直接录制扬声器的声音。如果您想要录制扬声器输出的声音, 您可以尝试以下方法:
- 使用系统默认输入设备录制:将系统的默认输入设备设置为“立体声混音”或“立体声混音 (**Stereo Mix**)”(在 Windows 上), 然后使用 PyAudio 录制这个默认输入设备。

## .wav 文件格式

- .wav （Waveform Audio File Format）文件的编码方式
  通常采用无损的线性脉冲编码调制（Linear Pulse Code Modulation, LPCM）编码方式，
- 一个 .wav 文件主要由以下几个部分组成:
  > 52 49 46 46  E4 1C 1A 00  57 41 56 45
  - RIFF Header（文件头）
    - "RIFF"标识 = 52 49 46 46（ASCII编码）
    - 文件大小   = E4 1C 1A 00（十六进制，表示 1,764,040 字节）
    - "WAVE"    = 57 41 56 45（ASCII编码）
  
  > 66 6D 74 20  10 00 00 00  01 00 02 00  44 AC 00 00
10 B1 02 00  04 00 10 00
  - Format Chunk（格式块）
    - "fmt " = 66 6D 74 20（ASCII编码）
    - 格式块大小 = 10 00 00 00（16字节）
    - 音频格式 = 01 00（LPCM）
    - 声道数 = 02 00（2声道）
    - 采样率 = 44 AC 00 00（44,100 Hz）
    - 字节率 = 10 B1 02 00（176,400 字节/秒）
    - 块对齐 = 04 00（4字节）
    - 位深 = 10 00（16位）
  - Data Chunk（数据块）
    - "data" = 64 61 74 61（ASCII编码）
    - 数据大小 = E0 1C 1A 00（表示1,764,000字节音频数据）
    - 后面跟着的是实际的音频数据（如采样点的二进制表示，通常是连续的16位整数）。
