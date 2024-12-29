# PowerTrans

Using SenseVoice-small onnx model to achieve realtime speech recognition locally on Pi 5B.

## 主要功能
- [ ] Recorder
  - [x] 选择录音设备[麦克风 or 扬声器] 并 初始化
  - [x] 实时进行音频录制
    - [x] 麦克风音频的获取
    - [x] or 直接抓取 计算机扬声器输出的音频
  - [x] 进行音频能量检测，去除明显的静音部分
  - [x] 进行VAD检测，去除无人声部分
  - [x] 将音频数据 保存为不定时长的的 ndarray
  - [x] 保存录音结果数据 ndarray 到 audio_queue
- [x] SenseVoiceOne
  - [x] 由 asr 模型 进行语音识别 Recorder对象所获取的数据
  - [ ] SenseVoice-small Onnx 模型加载&使用
  - [ ] 将语音识别的结果翻译为指定的语言
- [x] 窗口对象
  - [ ] 将最终的文字结果进行处理
    - [x] 实时屏幕显示
    - [ ] 保存为字幕文件
    - [x] 字幕弹窗
    - [ ] 自动断句
- [x] 运行日志
- [x] 功能测试
  - 不同平台
  - 长时间
  - 低负载

## 实现方式

- 三个对象
  - 窗口对象myWin窗口
    - 主窗口-参数的设置调整
    - 字母弹窗-实现字幕的实时显示
  - 录音对象AudioCapture(实现实时音频的抓取)
  - Asr 模型对象封装
  
## 语音活动检测（VAD）+ 音频能量检测

音频能量检测做初步的过滤，确保不是静音状态；然后将数据进行VAD检测后，再做ASR。
降低系统的负载，少做无用功。

[WebRTC VAD](https://github.com/wiseman/py-webrtcvad)

## Docs

[pyAudio 相关的笔记](./docs/pyaudio.md)
[Whisper 笔记](./docs/whisper.md)

## Ref

[Whisper](https://github.com/openai/whisper)
