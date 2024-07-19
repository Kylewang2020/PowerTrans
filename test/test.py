def is_text_char(char):
    # 判断是否是英文字母或汉字
    return char.isalpha() or ('\u4e00' <= char <= '\u9fff')

def is_punctuation(char):
    # 判断是否是停顿符号
    return char in '.,;:!?，。；：！？"\'()[]{}-—/\\' or char.isspace()

# 测试
text = "这是一个测试，包含英文和中文。いずれも平年より1日早い発表です。次を開けした地域を中心に厳しい厚さも予想されています。"
for char in text:
    if is_text_char(char):
        print(f"'{char}' 是文字")
    elif is_punctuation(char):
        print(f"'{char}' 是停顿符号")

text = "这是一个测试，包含英文和中文"
if is_text_char(text[-1]):
    print(f"'{text[-1]}' 是文字")
elif is_punctuation(text[-1]):
    print(f"'{text[-1]}' 是停顿符号")
