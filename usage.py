import time
from libsensevoiceOne.model import SenseVoiceOne
from libpowertrans.funcsLib import logging, log_init
from libpowertrans.myRecorder import Recorder
from libpowertrans.myWin import myWin

def v2t_steps():
    senseVoice_model_dir = "./resources/SenseVoice"
    senseVoice_model_file = "sense-voice-encoder-int8.onnx"
    device = -1
    num_threads = 4
    language = "auto"

    # 初始化ASR模型
    ssOnnx = SenseVoiceOne()
    ssOnnx.load_model(senseVoice_model_file=senseVoice_model_file)

    # 初始化录音机
    recoder = Recorder()
    recoder.init(channels=2)

    # 监听&翻译
    for _ in range(3):
        for i in range(3, 0, -1):
            print(f'\r 录音开始倒计时: {i} 秒', end='', flush=True)
            time.sleep(1)
        print('\r 开始录音...')
        audio_data = recoder.listen(seconds=5, save_wave=True)
        print(audio_data.shape)
        res = ssOnnx.transcribe(audio_data, language=language, use_itn=True, 
                                use_vad=True, ForceMono=True)
        print(res)

if __name__ == "__main__":
    log_init(LogFileName="v2t.log", logLevel=logging.DEBUG)
    v2t_steps()
