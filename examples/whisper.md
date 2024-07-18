# Whisper

Whisper 是一种通用语音识别模型。它是在大量不同音频数据集上进行训练的，也是一个多任务模型，可以执行多语言语音识别、语音翻译和语言识别。
[Whisper](https://github.com/openai/whisper)
[faster-whisper](https://github.com/SYSTRAN/faster-whisper)
[语音识别whisper的介绍、安装、错误记录](https://blog.csdn.net/zdm_0301/article/details/133854913)
[FileNotFoundError: [WinError 2] 系统找不到指定的文件](https://blog.csdn.net/qq_24118527/article/details/90579328)

## 安装步骤

[Windows系统 Whisper(OpenAI) 安装指南（全局python环境）](https://www.bilibili.com/read/cv25735051/)

``` sh
# 1-配置环境
#   PyTorch + Python

# 2-whisper (798 kb)
pip install -U openai-whisper

# 3-ffmpeg 安装，
# 并将可执行目录添加到环境变量中，在cmd窗口中可以运行ffmpeg命令即可

```

## whisper 常用命令

--model 指定使用的模型

--model_dir 模型存放文件夹

--device PyTorch推理所用设备（默认CUDA，可切换为CPU）

--output_dir 输出文件夹

--output_format 输出格式，默认全格式都输出一份

--language 指定所要扫描的音频使用的语言

--word_timestamps 词级时间戳（更精确的时间戳），推荐打开

## whisper 问题

- c++ 调用？
  - https://github.com/ggerganov/whisper.cpp
- whisper 转换的文本为繁体字，可否设定为简体

>Whisper 是一个 OpenAI 的语音识别模型，可以将语音转换为文本。如果你使用的是 Whisper 来进行语音转文本转换，并且希望将输出的文本设定为简体中文，可以通过后处理的方式实现这一点。Whisper 本身可能不会直接提供简体和繁体转换的选项，但你可以使用 Python 的 opencc 库来进行繁体字和简体字之间的转换。

- whisper 直接加载numpy的数据

>可以使用 Whisper 模型直接加载 NumPy 数据。Whisper 模型支持从 NumPy 数组中加载音频数据，这样你可以在内存中直接处理音频而无需保存和加载临时文件。

- Whisper 模型 要求 的 音频数据格式
  - NumPy 音频数据
  - 模型期望输入是标准化的单声道音频数据
  - 采样率为 16000Hz