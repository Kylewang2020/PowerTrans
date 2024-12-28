import time
from libsensevoiceOne.model import SenseVoiceOne
from libpowertrans.funcsLib import logging, log_init
from libpowertrans.AudioCapture import Recorder
from libpowertrans.myWin import myWin
import numpy as np

def v2t_steps():
    # model_file = "./resources/SenseVoice"
    model_file = "sense-voice-encoder-int8.onnx"
    language = "zh"

    # 初始化ASR模型
    ssOnnx = SenseVoiceOne()
    ssOnnx.load_model(senseVoice_model_file=model_file)

    # 初始化录音机
    recoder = Recorder()
    recoder.init(channels=2)

    # 监听&转译
    times = 5
    wave_len = 1

    for i in range(3, 0, -1):
        print(f'\r 录音开始倒计时: {i} 秒', end='', flush=True)
        time.sleep(1)
    print()

    for j in range(times):
        print(f'\r times[{j+1} of {times}] 开始 {wave_len}s 录音...       ')
        audio_res = recoder.listen(seconds=wave_len,
                                   save_wave=True,
                                   mute_check=True,
                                   return_array=True)
        if not audio_res["is_mute"]:
            res = ssOnnx.transcribe(audio_res["array"], language=language, use_itn=True, 
                                    use_vad=True, ForceMono=True, str_result=True)
            print(f"result: {res}")
        else:
            print("    没有检测到声音, pass\n")

if __name__ == "__main__":
    log_init(LogFileName="v2t.log", logLevel=logging.DEBUG)
    v2t_steps()
