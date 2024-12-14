'''
@Project:       examples
@File:          file_trans_one.py
@File Created:  Kyle Wang(wangkui2000@hotmail.com) @[2024-07-18 09:39:39]
@Last Modified: 2024-12-13 03:05:08
@Copyright:     MIT License 2024-2034 Kyle
@Function:      whisper 模型加载处理语音文件。transcribe方法。
'''

import whisper
import time

def time_consume_print(start, funcName):
    print("  {:<20} 耗时: {:.2f}s".format(funcName, time.time()-start))


def is_text_char(char):
    # 判断是否是英文字母或汉字
    return char.isalpha() or ('\u4e00' <= char <= '\u9fff')

def printRes(result):
    resTxt = ""
    if isinstance(result, whisper.decoding.DecodingResult):
        resTxt = result.text
    elif isinstance(result, dict):
        if "segments" in result.keys():
            for segment in result['segments']:
                resTxt += segment['text']
                if is_text_char(segment['text'][-1]):
                    resTxt += ", "
        else:
            resTxt = result
    else:
        resTxt = result
    print("  ASR结果: {}".format(resTxt))
        

def main():
    start = time.time()
    model = whisper.load_model("base", download_root="D:\\github\\whisper")
    time_consume_print(start, "load_model")
    # 将模型设置为评估模式
    model.eval()

    # waveFile = ".//test_data//chinese01.wav"
    waveFile = ".//test_data//english01.wav"
    # waveFile = ".//test_data//japan01.wav"

    for i in range(3):
        print("Times {}:".format(i))
        start = time.time()
        result = model.transcribe(waveFile)
        time_consume_print(start, "transcribe1")
        printRes(result)
        start = time.time()
        result = model.transcribe(waveFile, language='zh')
        time_consume_print(start, "transcribe2")
        printRes(result)


if __name__ == '__main__':
    main()
    