import whisper
import time

def time_consume_print(start, funcName):
    print("  {:<20} 耗时: {:.2f}s".format(funcName, time.time()-start))

start = time.time()
model = whisper.load_model("base", download_root="D:\\github\\whisper")
time_consume_print(start, "load_model")

# waveFile = ".//test_data//chinese01.wav"
# waveFile = ".//test_data//english01.wav"
waveFile = ".//test_data//japan01.wav"

for i in range(3):
    print("Times {}:".format(i))
    start = time.time()
    result = model.transcribe(waveFile, language='ja')
    time_consume_print(start, "transcribe")

