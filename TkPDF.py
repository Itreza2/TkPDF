from tkinter import Tk, Widget, Canvas, Scrollbar
from PIL import Image, ImageTk
from pdf2image import convert_from_path, convert_from_bytes


class PdfReader(Widget):

    FULL_WIDTH = 0
    FULL_PAGE = 1
    REAL_SIZE = 2
    FREE_MOVE = 3

    def __init__(self, master=None, **kw):
        '''Construct a PdfReader widget with the parent MASTER.'''
        self.mode = PdfReader.FULL_WIDTH
        defaultFile = None
        if 'defaultMode' in kw:
            if kw['defaultMode'] > 0 and kw['defaultMode'] <= 2:
                self.mode = kw.pop('defaultMode')
        if 'fp' in kw:
            defaultFile = kw.pop('fp')

        Widget.__init__(self, master, 'frame', {}, kw)

        self.__sourceImg : list[Image.Image] = []
        self.__photoImg : dict[int : ImageTk.PhotoImage] = {}
        self.pageCount : int = 0
        self.currentPage : int = 0
        self.__zoom = 1
        self.__offsetX, self.__offsetY = 0, 0
        self.__width, self.__height = 1, 1
        self.__ctrl : bool = False

        self.canvas : Canvas = Canvas(self, kw)
        self.canvas.pack(anchor='nw')
        self.canvas.bind('<MouseWheel>', self.__mousewheel)
        self.canvas.bind('<Key-Control_L>', self.__ctrlKey); self.canvas.bind('<Key-Control_R>', self.__ctrlKey)
        self.canvas.bind('<KeyRelease-Control_L>', self.__ctrlKeyRelease); self.canvas.bind('<KeyRelease-Control_R>', self.__ctrlKeyRelease)
        self.canvas.focus_set()

        self.verticalScrollBar : Scrollbar = Scrollbar(self, width=20, orient='vertical', command=self.__verticalScrollBar)
        self.verticalScrollBar.place()
        self.horizontalScrollBar : Scrollbar = Scrollbar(self, width=20, orient='horizontal', command=self.__horizontalScrollBar)
        self.horizontalScrollBar.place()

        if defaultFile != None:
            self.loadFromPath(defaultFile)
        self.__loop()

    #--------------------#
    #[> Public Methods <]#
    #--------------------#

    def loadFromPath(self, fp : str) -> None:
        self.__load(convert_from_path(fp))

    def loadFromBytes(self, bytes) -> None:
        self.__load(convert_from_bytes(bytes))

    def load(self, fp : str) -> None: 
        self.loadFromPath(fp)

    #---------------------#
    #[> Private Methods <]#
    #---------------------#

    def __loop(self):
        if self.__resized(): self.__resize()

        self.canvas.after(16, self.__loop)

    def __load(self, pdf : list[Image.Image]):
        self.__pageWidth : int = pdf[0].width
        self.__pageHeight : int = pdf[0].height
        self.currentPage = 1
        self.pageCount = len(pdf)

        self.__sourceImg = pdf

        self.__resize()

    def __resized(self) -> bool:
        '''Check if the PdfReader was resized inside the main frame'''
        if (self.__width, self.__height) != (self.winfo_width(), self.winfo_height()):
            self.__width, self.__height = self.winfo_width(), self.winfo_height()
            return True
        return False

    def __resize(self):
        if self.mode == PdfReader.FULL_WIDTH:
            self.__zoom = self.__width / self.__pageWidth
            self.__offsetX = 0
        elif self.mode == PdfReader.FULL_PAGE:
            if self.__pageHeight > self.__pageWidth:
                self.__zoom = self.__height / self.__pageHeight
            else:
                self.__zoom = self.__width / self.__pageWidth
                self.__offsetX = 0
            self.__offsetY = self.__pageHeight * self.currentPage
        elif self.mode == PdfReader.REAL_SIZE:
            self.__zoom = self.winfo_fpixels('1i') / 200
        if self.__pageWidth * self.__zoom < self.__width:
            self.__offsetX = (self.__width - self.__pageWidth * self.__zoom) / self.__zoom / 2
            self.horizontalScrollBar.place_forget()
        else:
            self.__offsetX = max(min(0, self.__offsetX), self.__width / self.__zoom - self.__pageWidth)
            self.horizontalScrollBar.place(x=0, y=self.__height, anchor='sw', width=self.__width - 20, height=20)

        self.verticalScrollBar.place(x=self.__width, y=0, anchor='ne', width=20, height=self.__height)

        self.__photoImg : dict[int : ImageTk.PhotoImage] = {}
        for page in range(self.currentPage, self.currentPage + (self.__height // int(self.__pageHeight * self.__zoom)) + 2):
            self.__renderPage(page)
        self.__print()

    def __renderPage(self, page : int):
        '''Convert a Pillow Image object to a Tk PhotoImage of the right size'''
        if page > 0 and page <= self.pageCount:
            self.__photoImg[page] = ImageTk.PhotoImage(
                self.__sourceImg[page - 1].resize(
                    (max(1, int(self.__sourceImg[page - 1].width * self.__zoom)), 
                        max(1, int(self.__sourceImg[page - 1].height * self.__zoom)))
                )
            ) 

    def __print(self):
        '''Create new canvas elements after deleting the previous ones'''
        self.canvas.delete('all')

        self.imgId : dict[int : int] = {}
        for page in self.__photoImg:
            self.imgId[page] = (
                self.canvas.create_image(
                    int(self.__offsetX * self.__zoom),
                    int((self.__offsetY + self.__pageHeight * (page - 1)) * self.__zoom),
                    image=self.__photoImg[page], anchor='nw'
                )
            )

    def __relocate(self):
        '''relocate the image after an offset change'''
        for page in self.imgId:
            self.canvas.moveto(
                self.imgId[page], int(self.__offsetX * self.__zoom),
                int((self.__offsetY + self.__pageHeight * (page - 1)) * self.__zoom)
            )

    def __verticalScrollBar(self, *args):
        '''Vertical ScrollBar widget handling'''
        if args[0] == 'moveto':
            self.verticalScrollBar.set(max(0, float(args[1]) - 0.02), float(args[1]) + 0.02)
            self.__offsetY = - float(args[1]) * (self.pageCount - 1) * self.__pageHeight
            self.currentPage = int((- self.__offsetY) // self.__pageHeight) + 1
            self.__resize()

    def __horizontalScrollBar(self, *args):
        '''Horizontal ScrollBar widget handling'''
        if args[0] == 'moveto':
            self.horizontalScrollBar.set(max(0, float(args[1]) - 0.02), float(args[1]) + 0.02)
            self.__offsetX = float(args[1]) * (self.__width - self.__pageWidth * self.__zoom) / self.__zoom
            self.__relocate()

    def __ctrlKey(self, event):
        '''Tk's control key event handler'''
        self.__ctrl = True

    def __ctrlKeyRelease(self, event):
        '''Tk's control key release event handler'''
        self.__ctrl = False

    def __mousewheel(self, event):
        '''Tk's mousewheel event handler'''
        self.mode = PdfReader.FREE_MOVE
        if self.__ctrl: # Zoom in/out
            delta = event.delta / 5000

            #TODO : adjust offset according to cursor position

            self.__zoom += delta
            self.__resize()
        else: # Scroll up/down
            self.__offsetY += event.delta
            if self.pageCount > 1:
                self.verticalScrollBar.set(
                    - self.__offsetY / ((self.pageCount - 1) * self.__pageHeight) - 0.02,
                    - self.__offsetY / ((self.pageCount - 1) * self.__pageHeight) + 0.02
                )
            if self.currentPage != ((- self.__offsetY) // self.__pageHeight) + 1:
                oldPage = max(self.__photoImg.keys()) if event.delta > 0 else min(self.__photoImg.keys())
                newPage = min(self.__photoImg.keys()) - 1 if event.delta > 0 else max(self.__photoImg.keys()) + 1

                if oldPage != 1 and oldPage != self.pageCount:
                    self.canvas.delete(self.imgId.pop(oldPage))
                    self.__photoImg.pop(oldPage)
                if newPage > 0 and newPage <= self.pageCount:
                    self.__renderPage(newPage)
                    self.imgId[newPage] = (
                        self.canvas.create_image(0, 0, image=self.__photoImg[newPage], anchor='nw')
                    )
                self.currentPage = ((- self.__offsetY) // self.__pageHeight) + 1
            self.__relocate()

tk = Tk()
test = PdfReader(tk, fp='test.pdf', width=500, height=700)
test.pack()
tk.mainloop()