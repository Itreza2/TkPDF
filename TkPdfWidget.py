from tkinter import Widget, Canvas, Entry, Scrollbar, IntVar
from PIL import Image, ImageTk
import pymupdf as pdf
from threading import Thread


class PdfReader(Widget):
    '''A PDF file reader inside a Tk frame, behaving like a widget'''

    '''Viewing modes'''
    FULL_WIDTH = 0
    FULL_PAGE = 1
    REAL_SIZE = 2
    FREE_MOVE = 3

    def __init__(self, master=None, *, 
                 defaultMode : int = FULL_WIDTH,
                 fp : str = ..., filepath : str = ...,
                 **kw):
        '''
        Construct a PdfReader "widget" with the parent MASTER.
        Have the same options than a classic "Frame" widget, in addition of the following :
        @param defaultMode (optional) the default viewing mode of the reader, can be one of {FULL_WIDTH = 0, FULL_PAGE = 1, REAL_SIZE = 2}
        @param fp (optional) the address of a pdf file to load with the widget, default to no file
        @param filepath (optional) the address of a pdf file to load with the widget, default to no file
        '''
        self.mode = defaultMode
        defaultFile = (filepath if filepath != ... else fp)

        Widget.__init__(self, master, 'frame', {}, kw)

        self.__sourceImg : list[Image.Image] = []
        self.__photoImg : dict[int : ImageTk.PhotoImage] = {}
        self.pageCount : int = 0
        self.currentPage : int = 0
        self.__zoom = 1
        self.__rotation = 0
        self.__offsetX, self.__offsetY = 0, 0
        self.__width, self.__height = 1, 1
        self.__ctrl : bool = False
        self.__cX, self.__cY, self.__clic = 0, 0, False
        self.__lrArrowPressed = False
        self.__pageVar : IntVar = IntVar(value=0)

        self.canvas : Canvas = Canvas(self, kw)
        self.canvas.pack(anchor='nw')
        self.canvas.bind('<Button-1>', self.__leftClic)
        self.canvas.bind('<ButtonRelease-1>', self.__leftClicRelease)
        self.canvas.bind('<Motion>', self.__motion)
        self.canvas.bind('<MouseWheel>', self.__mousewheel)
        self.canvas.bind('<Key-Control_L>', self.__ctrlKey); self.canvas.bind('<Key-Control_R>', self.__ctrlKey)
        self.canvas.bind('<KeyRelease-Control_L>', self.__ctrlKeyRelease); self.canvas.bind('<KeyRelease-Control_R>', self.__ctrlKeyRelease)
        self.canvas.bind('<Key>', self.__anyKey)
        self.canvas.bind('<KeyRelease>', self.__anyKeyRelease)
        self.canvas.focus_set()

        self.verticalScrollBar : Scrollbar = Scrollbar(self, width=20, orient='vertical', command=self.__verticalScrollBar)
        self.verticalScrollBar.place()
        self.horizontalScrollBar : Scrollbar = Scrollbar(self, width=20, orient='horizontal', command=self.__horizontalScrollBar)
        self.horizontalScrollBar.place()
        self.__pageEntry : Entry = Entry(self, textvariable=self.__pageVar, justify='center')

        self.__buttons : dict[str : PdfReader.__IconButton] = {
            'glassP' : PdfReader.__IconButton(self.canvas, 0.008, 0.008, 0.075, 4),
            'glassM' : PdfReader.__IconButton(self.canvas, 0.008, 0.08, 0.075, 5),
            'modeFW' : PdfReader.__IconButton(self.canvas, 0.12, 0.008, 0.075, 6),
            'modeFP' : PdfReader.__IconButton(self.canvas, 0.2, 0.008, 0.075, 7),
            'left' : PdfReader.__IconButton(self.canvas, 0.38, 0.025, 0.05, 0),
            'right' : PdfReader.__IconButton(self.canvas, 0.55, 0.025, 0.05, 1),
            'rotCC' : PdfReader.__IconButton(self.canvas, 0.715, 0.008, 0.075, 2),
            'rotC' : PdfReader.__IconButton(self.canvas, 0.795, 0.008, 0.075, 3)
        }
        if defaultFile != ...:
            self.load(defaultFile)
        self.__loop()

    #--------------------#
    #[> Public Methods <]#
    #--------------------#

    def load(self, fp : str, first : int | None = None, last : int | None = None) -> None: 
        '''
        load a new pdf file into the reader
        @param fp the address of the file to load
        @param first (optional) the first page of the document to load (previous pages will be omitted)
        @param last (optional) the last page of the document to load (following pages will be omitted)
        '''
        if first is not int or first < 1:
            first = 1
        if last is not int or last < first:
            last = None
        Thread(target=self.__load, kwargs={'fp' : fp, 'first' : first, 'last' : last}).start()
        while len(self.__sourceImg) == 0: pass #Busy waiting until one page at least is loaded (not optimal)

    #---------------------#
    #[> Private Methods <]#
    #---------------------#

    def __loop(self):
        '''Control loop of the PdfReader'''
        if self.__resized(): self.__resize()

        if self.focus_get() == self.__pageEntry:
            try: # get raise an exception when the entry is empty
                if self.currentPage != self.__pageVar.get():
                    self.currentPage = max(min(self.__pageVar.get(), self.pageCount), 1)
                    self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
                    self.__resize()
            except Exception as e: pass # :(
        else:
            self.__pageVar.set(int(self.currentPage))

        #UI controls
        if self.__clic:
            self.__clic = False
            if self.__buttons['glassP'].hovered(self.__cX, self.__cY):
                self.mode = PdfReader.FREE_MOVE
                self.__zoom += 0.1
                self.__resize()
            elif self.__buttons['glassM'].hovered(self.__cX, self.__cY):
                self.mode = PdfReader.FREE_MOVE
                self.__zoom -= 0.1
                self.__resize()
            elif self.__buttons['modeFW'].hovered(self.__cX, self.__cY):
                self.mode = PdfReader.FULL_WIDTH
                self.__resize()
            elif self.__buttons['modeFP'].hovered(self.__cX, self.__cY):
                self.mode = PdfReader.FULL_PAGE
                self.__resize()
            elif self.__buttons['left'].hovered(self.__cX, self.__cY):
                self.currentPage = max(min(self.currentPage - 1, self.pageCount), 1)
                self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
                self.__resize()
            elif self.__buttons['right'].hovered(self.__cX, self.__cY):
                self.currentPage = max(min(self.currentPage + 1, self.pageCount), 1)
                self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
                self.__resize()
            elif self.__buttons['rotC'].hovered(self.__cX, self.__cY):
                self.__rotation -= 90
                self.__pageWidth, self.__pageHeight = self.__pageHeight, self.__pageWidth
                self.__offsetY = self.__offsetY * (self.__pageHeight / self.__pageWidth)
                self.__resize()
            elif self.__buttons['rotCC'].hovered(self.__cX, self.__cY):
                self.__rotation += 90
                self.__pageWidth, self.__pageHeight = self.__pageHeight, self.__pageWidth
                self.__offsetY = self.__offsetY * (self.__pageHeight / self.__pageWidth)
                self.__resize()
        else:
            for button in self.__buttons.keys():
                self.__buttons[button].hovered(self.__cX, self.__cY)

        self.after(16, self.__loop)

    def __load(self, fp : str, first : int, last : int | None):
        '''Load the pages of a pdf document as Pillow Image objects'''
        self.__pageWidth : int = 1
        self.__pageHeight : int = 1
        self.currentPage = 1
        self.pageCount = 0

        self.__sourceImg = []
        doc = pdf.open(fp)
        if last == None:
            last = len(doc)
        for page in range(len(doc)):
            if page >= first - 1 and page <= last - 1:
                pix = doc[page].get_pixmap()
                self.__sourceImg.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
                
                self.__pageWidth = self.__sourceImg[-1].width
                self.__pageHeight = self.__sourceImg[-1].height
                self.pageCount += 1

        for button in self.__buttons.keys():
            self.__buttons[button].resize()
        self.__resize()

    def __resized(self) -> bool:
        '''Check if the widget was resized'''
        if (self.__width, self.__height) != (self.winfo_width(), self.winfo_height()):
            self.__width, self.__height = self.winfo_width(), self.winfo_height()
            for button in self.__buttons.keys():
                self.__buttons[button].resize()
            return True
        return False

    def __resize(self):
        '''Resize all the elements of the PdfReader'''
        if len(self.__sourceImg) > 0:
            if self.mode == PdfReader.FULL_WIDTH:
                self.__zoom = self.__width / self.__pageWidth
                self.__offsetX = 0
            elif self.mode == PdfReader.FULL_PAGE:
                if self.__pageHeight > self.__pageWidth:
                    self.__zoom = self.__height / self.__pageHeight
                else:
                    self.__zoom = self.__width / self.__pageWidth
                    self.__offsetX = 0
                self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
            elif self.mode == PdfReader.REAL_SIZE:
                self.__zoom = self.winfo_fpixels('1i') / 200
            if self.__pageWidth * self.__zoom < self.__width:
                self.__offsetX = (self.__width - self.__pageWidth * self.__zoom) / self.__zoom / 2
                self.horizontalScrollBar.place_forget()
            else:
                self.__offsetX = max(min(0, self.__offsetX), self.__width / self.__zoom - self.__pageWidth)
                self.horizontalScrollBar.place(x=0, y=self.__height, anchor='sw', width=self.__width - 20, height=20)

            self.verticalScrollBar.place(x=self.__width, y=0, anchor='ne', width=20, height=self.__height)
            self.__pageEntry.place(x=self.__width * 0.5, y=self.__width * 0.045, anchor='e', width=self.__width * 0.06, height=self.__width * 0.04)

            self.__photoImg : dict[int : ImageTk.PhotoImage] = {}
            for page in range(int(self.currentPage), int(self.currentPage) + (self.__height // int(self.__pageHeight * self.__zoom)) + 2):
                self.__renderPage(page)
        self.__print()

    def __renderPage(self, page : int):
        '''Convert a Pillow Image object to a Tk PhotoImage of the right size'''
        if page > 0 and page <= self.pageCount:
            self.__photoImg[page] = ImageTk.PhotoImage(
                self.__sourceImg[page - 1].resize(
                    (max(1, int(self.__sourceImg[page - 1].width * self.__zoom)), 
                        max(1, int(self.__sourceImg[page - 1].height * self.__zoom)))
                ).rotate(self.__rotation, expand=True)
            )

    def __print(self):
        '''Create new canvas elements after deleting the existing ones'''
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
        for button in self.__buttons.keys():
            self.__buttons[button].print()
        self.canvas.create_text(
            self.__width * 0.5, self.__width * 0.045, anchor='w',
            text=f'/ {self.pageCount}', font=('Arial', int(self.__width * 0.02))
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
            self.__offsetY = - float(args[1]) * (self.pageCount - 1) * self.__pageHeight * 1.042
            self.currentPage = int((- self.__offsetY) // self.__pageHeight) + 1
            self.__resize()

    def __horizontalScrollBar(self, *args):
        '''Horizontal ScrollBar widget handling'''
        if args[0] == 'moveto':
            self.horizontalScrollBar.set(max(0, float(args[1]) - 0.02), float(args[1]) + 0.02)
            self.__offsetX = float(args[1]) * (self.__width - self.__pageWidth * self.__zoom) / self.__zoom
            self.__relocate()

    def __leftClic(self, event):
        '''Tk's mouse left clic event handler'''
        self.__clic = True
        self.canvas.focus_set()

    def __leftClicRelease(self, event):
        '''Tk's mouse left clic release event handler'''
        self.__clic = False

    def __motion(self, event):
        '''Tk's mouse motion event handler'''
        self.__cX, self.__cY = event.x, event.y

    def __ctrlKey(self, event):
        '''Tk's control key event handler'''
        self.__ctrl = True

    def __ctrlKeyRelease(self, event):
        '''Tk's control key release event handler'''
        self.__ctrl = False

    def __anyKey(self, event):
        '''Tk's other keys events handler'''
        if not self.__lrArrowPressed:
            if event.keysym == 'Left':
                self.__lrArrowPressed = True
                self.currentPage = max(min(self.currentPage - 1, self.pageCount), 1)
                self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
                self.__resize()
            elif event.keysym == 'Right':
                self.__lrArrowPressed = True
                self.currentPage = max(min(self.currentPage + 1, self.pageCount), 1)
                self.__offsetY = - (self.currentPage - 1) * self.__pageHeight
                self.__resize()

    def __anyKeyRelease(self, event):
        '''Tk's other keys release events handler'''
        if self.__lrArrowPressed and event.keysym in ('Right', 'Left'):
            self.__lrArrowPressed = False

    def __mousewheel(self, event):
        '''Tk's mousewheel event handler'''
        self.mode = PdfReader.FREE_MOVE
        self.canvas.focus_set()
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
                self.__print()
            else:
                self.__relocate()


    class __IconButton:
        '''Iteractible canvas element, a lot less ugly than a button widget'''

        ICON_SIZE = 64
        source : Image.Image = Image.open(__file__[:len(__file__) - len(__file__.split('\\')[-1])] + 'icons.png')

        def __init__(self, canvas : Canvas, x : float, y : float, w : float, icon : int):
            self.canvas : Canvas = canvas
            self.x, self.y, self.w = x, y, w
            self.pxX, self.pxY, self.pxW = 0, 0, 0
            self.icon = icon
            self.id = 0

            self.resize()

        def resize(self):
            canWidth = self.canvas.winfo_width()
            self.pxX, self.pxY, self.pxW = self.x * canWidth, self.y * canWidth, int(self.w * canWidth)
            self.image : ImageTk.PhotoImage = ImageTk.PhotoImage(
                self.source.crop((
                    self.ICON_SIZE * self.icon, 0, self.ICON_SIZE * (self.icon + 1), self.ICON_SIZE
                )).resize((max(1, self.pxW), max(1, self.pxW)))
            )
            self.imageHovered : ImageTk.PhotoImage = ImageTk.PhotoImage(
                self.source.crop((
                    self.ICON_SIZE * self.icon, self.ICON_SIZE, self.ICON_SIZE * (self.icon + 1), 2* self.ICON_SIZE
                )).resize((max(1, self.pxW), max(1, self.pxW)))
            )

        def print(self):
            self.id = self.canvas.create_image(
                self.pxX, self.pxY, image=self.image, anchor='nw', tags='hud'
            )

        def hovered(self, x, y) -> bool :
            if x > self.pxX and x < self.pxX + self.pxW and y > self.pxY and y < self.pxY + self.pxW:
                if self.id != 0:
                    self.canvas.itemconfigure(self.id, image=self.imageHovered)
                return True
            elif self.id != 0:
                self.canvas.itemconfigure(self.id, image=self.image)
            return False