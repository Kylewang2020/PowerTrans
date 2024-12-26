from libpowertrans.myRecorder import Recorder
from libpowertrans.myWin import myWin

def v2t_steps():
    recoder = Recorder()
    recoder.init(CHANNELS=2)
    audio_data = recoder.listen(seconds=1)
    print(audio_data.shape)


if __name__ == "__main__":
    v2t_steps()
