from tkinter import Tk, Canvas, Label, StringVar
from tkinter.constants import BOTH, LEFT
''' Add project path to sys.path V1.0'''
import os, sys
__dir_name = os.path.dirname(os.path.realpath(__file__))
for _ in range(5):
    if "audio_lib" not in os.listdir(__dir_name):
        __dir_name =  os.path.dirname(__dir_name)
    else:
        if __dir_name not in sys.path:
            sys.path.insert(0, __dir_name)
        break
from audio_lib.funcsLib import logging, log_init

# bg_color = ["lightgrey", "silver", "darkgrey", "grey", "dimgrey"]
bg_color = "darkgrey"


class myWin(object):
    def __init__(self, width=500, height=80, txtSize=16, maxWidth=1000, minWidth=300,
                 logF="myWin.log", logOut=3, logL=logging.INFO, logger=None) -> None:
        self.win = Tk()
        self.width  = width
        self.height = height
        self.maxWidth = maxWidth
        self.minWidth = minWidth
        self.txtSize  = txtSize
        self.mouseX = 0
        self.mouseY = 0
        self.isMouseBt1Down = False
        self.isMouseMove    = False
        self.showTimes = 0
        if logger is None:
            self.log = self.log_init(logF, logOut, logL)
        else:
            self.log = logger
        self.init_form()
        self.log.info('*** myWin object init ***')


    def init_form(self):
        '''main window init'''
        self.win.config(bg='grey')
        self.win.config(cursor='sb_h_double_arrow')
        self.win.attributes("-transparentcolor", "grey") # So that it doesn't look like a square
        self.win.overrideredirect(True)
        self.win.resizable(False, False)
        self.win.attributes('-topmost', True)
        self.win.attributes("-alpha", 0.85)
        screen_w = self.win.winfo_screenwidth() #得到屏幕宽度
        screen_h = self.win.winfo_screenheight() #得到屏幕高度
        win_w = self.width
        win_h = self.height
        x = (screen_w-win_w)//2
        y = screen_h-win_h-100
        self.win.geometry("{:d}x{:d}+{:d}+{:d}".format(win_w, win_h, x, y))
        self.canvas = Canvas(self.win, bg='grey', highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True)
        self.round_rectangle(self.canvas, 0, 0, self.width, self.height, 25)
        self.init_ctl()
        self.win.bind("<Escape>", self.close)
        self.win.bind("x", self.close)
        self.win.bind("<Button-1>",self.MouseDown)
        self.win.bind("<B1-Motion>",self.MouseMove)
        self.win.bind("<ButtonRelease-1>",self.MouseRelease)
        self.win.bind("<<NewTxtComing>>",self.NewTxtComing)

    
    def init_ctl(self):
        '''the controls init and layout'''
        self.lblStr= StringVar()
        self.label = Label(self.canvas, justify=LEFT, font=('Arial', self.txtSize),
                        textvariable=self.lblStr, cursor="fleur", anchor="nw")
        self.label.config(bg=bg_color)
        self.label.pack(fill=BOTH, padx=5, pady=5, expand=True)


    def round_rectangle(self, canvas, x1, y1, x2, y2, radius=25): 
        """Creating a rounded rectangle"""
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1,
                x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2,
                x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2,
                x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return canvas.create_polygon(points, smooth=True, fill=bg_color, tags="Round")


    def close(self, event):
        '''main window exit'''
        self.log.debug('*** myWin object destroy ***')
        self.win.destroy()


    def MouseDown(self, event):
        self.mouseX = event.x
        self.mouseY = event.y
        self.isMouseBt1Down = True
        self.isMouseMove    = False


    def MouseMove(self, event):
        abs_x = self.win.winfo_pointerx() - self.win.winfo_rootx()
        if (self.isMouseBt1Down and abs_x>self.minWidth and (self.win.winfo_width()-event.x)<10) or self.isMouseMove:
            self.isMouseMove = True
            self.win.geometry("{}x{}".format(abs_x, self.win.winfo_height()))
            self.canvas.delete("Round")
            self.round_rectangle(self.canvas, 0, 0, self.win.winfo_width(), self.win.winfo_height(), 25)
            self.label.pack_forget()
            self.label.pack(fill=BOTH, padx=5, pady=5, expand=True)
        else:
            self.win.geometry("+{:d}+{:d}".format(
                event.x_root - self.mouseX- self.label.winfo_x(),
                event.y_root - self.mouseY- self.label.winfo_y()))


    def MouseRelease(self, event):
        self.isMouseMove    = False
        self.isMouseBt1Down = False


    def NewTxtComing(self, event):
        self.label.config(text="[From NewTxtComing() event] Times:{}".format(self.showTimes))
        self.showTimes += 1


    def autoTxt(self):
        '''Test Function. Auto update the label text every 1 second'''
        text = self.lblStr.get()
        text = '[From autoTxt()] Time:{}'.format(self.showTimes) + "\n" + text
        self.lblStr.set(text)
        self.showTimes += 1
        self.win.after(1000, self.autoTxt)


if __name__ == '__main__':
    logger = log_init(logF="myWin.log")
    myApp  = myWin(logger=logger, txtSize=10)
    myApp.autoTxt()
    myApp.win.mainloop()
