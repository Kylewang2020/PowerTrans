# PowerTrans

Using OpenAi's whisper model and run realtime speech recognition locally.  
Whisper 使用学习笔记

## 主要功能

- [ ] 实时进行音频录制
  - [ ] 进行VAD检测，去除无人声部分
  - [x] 将音频文件保存为5~10s的wav文件
  - [x] 将音频文件传送到whisper模型进行语音识别
- [x] whisper 模型加载&使用
- [ ] 将语音识别的结果翻译为指定的语言
- [ ] 将最终的文字结果进行处理
  - [x] 实时屏幕显示
  - [ ] 保存为字幕文件

## 语音活动检测（VAD）

[WebRTC VAD](https://github.com/wiseman/py-webrtcvad)

## Ref

[Whisper](https://github.com/openai/whisper)
