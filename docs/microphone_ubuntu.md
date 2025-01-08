# ubuntu 下的 usb micro-phone 使用

## 1. 查找设备

``` sh
arecord -l
```

该命令会列出所有 ALSA 支持的录音设备。输出示例：

``` cmd
**** List of CAPTURE Hardware Devices ****
card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

## 2. 测试录音

``` sh
arecord -D plughw:2,0 -f cd test.wav

# 设置 16kHz 采样率录音的命令
# -r 16000：设置采样频率为 16kHz（16000 Hz）
arecord -D plughw:2,0 -r 16000 -f cd test_16k.wav
```

解释：

- `-D plughw:1,0`：指定录音设备（1,0 是 card 1 和 device 0，你可以根据需要更改）。
- `-f cd`：设置音频格式为 CD 质量（16 位、44.1kHz、立体声）。
- `test.wav`：保存录音的文件名。
- 录音结束后，按 `Ctrl + C` 停止录音。

``` cmd
**** List of CAPTURE Hardware Devices ****
card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```


## 3. 设置 Micro Phone

``` sh
alsamixer
```

- 调整麦克风音量：
  - 一旦选择了正确的设备，你会看到不同的音频控制选项。
  - 使用 左/右箭头 查找 Capture 或 Mic（麦克风）通道。
  - 通过 上/下箭头 来调整音量。通常，这会影响麦克风输入的增益。
  - 如果音量控制显示为 MM（静音），按 M 键取消静音。
- 调整自动增益控制（AGC）：
  - 如果你的设备有 Auto Gain Control (AGC) 选项，确保它根据需要开启或关闭。
  - 使用 左右箭头 移动到 Auto Gain Control，然后按 M 键打开或关闭它（根据需求）。自动增益控制有时会带来不必要的噪声，关闭它可能会改善录音质量。