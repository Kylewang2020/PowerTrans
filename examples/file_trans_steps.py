import whisper
import time

def time_consume_print(start, funcName):
    print("  {:<20} 耗时: {:.2f}s".format(funcName, time.time()-start))

start = time.time()
model = whisper.load_model("base")
time_consume_print(start, "load_model")

# load audio and pad/trim it to fit 30 seconds
waveFile = ".//test_data//chinese01.wav"
start = time.time()
audio = whisper.load_audio(waveFile)
time_consume_print(start, "load_audio")

start = time.time()
audio = whisper.pad_or_trim(audio)
time_consume_print(start, "pad_or_trim")

# make log-Mel spectrogram and move to the same device as the model
start = time.time()
mel = whisper.log_mel_spectrogram(audio).to(model.device)
time_consume_print(start, "log_mel_spectrogram")

# detect the spoken language
start = time.time()
_, probs = model.detect_language(mel)
time_consume_print(start, "detect_language")
print(f"Detected language: {max(probs, key=probs.get)}")

# decode the audio
start = time.time()
options = whisper.DecodingOptions()
result = whisper.decode(model, mel, options)
time_consume_print(start, "decode")

# print the recognized text
print(result.text)
