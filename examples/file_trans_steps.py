import whisper
import time

def time_consume_print(start, funcName):
    print("  {:<20} 耗时: {:.2f}s".format(funcName, time.time()-start))

def decode_file(model, waveFile, detect_language=True):
    # load audio and pad/trim it to fit 30 seconds. 
    audio = whisper.load_audio(waveFile)    # 耗时 0.05秒左右，忽略不计.

    # start = time.time()
    audio = whisper.pad_or_trim(audio)      #耗时 0.00 秒左右，忽略不计.
    # time_consume_print(start, "pad_or_trim")

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device) #耗时 0.01 秒左右，忽略不计.

    # detect the spoken language
    if detect_language:
        start = time.time()
        _, probs = model.detect_language(mel)
        language = max(probs, key=probs.get)
        time_consume_print(start, "detect_language")
        print(f"    Detected language: {language}")

    # decode the audio
    start = time.time()
    # options = whisper.DecodingOptions(language="en")
    options = whisper.DecodingOptions()
    result = whisper.decode(model, mel, options)
    time_consume_print(start, "decode1")
    # decode the audio 2
    start = time.time()
    options = whisper.DecodingOptions(language=language)
    result = whisper.decode(model, mel, options)
    time_consume_print(start, "decode2")

    return result

start = time.time()
model = whisper.load_model("base", download_root="D:\\github\\whisper")
time_consume_print(start, "load_model")

waveFile = ".//test_data//chinese01.wav"
# waveFile = ".//test_data//english01.wav"
# waveFile = ".//test_data//japan01.wav"
for i in range(3):
    print("Times {}:".format(i))
    result = decode_file(model, waveFile, detect_language=True)

print(result.text)
