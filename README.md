**_TkPdfWidget_** is a python librairy extending **_tkinter_** with a PDF file reader widget.

Here is an exemple of how it looks like in a minimalist tkinter window :

<img width="316" height="398" alt="TkPDF_Exemple" src="https://github.com/user-attachments/assets/dc44a4e1-4031-4b6e-92d0-a24a90c11e63" />


## **Intallation** ##

Download the latest package on github or, using pip :
> pip install TkPdfWidget

## **Features :** ##

* Several viewing modes (full width, full page, real size and free move)
* zoom in / out, horizontal and vertical scroll
* 90° pages rotation
* easy access to any page of a document
* keyboard shortcuts (wip)


## **Known alternatives :** ##

Do not hesitate to have a look to these other projects that may better suit your needs
* [CTkPDFViewer](https://github.com/Akascape/CTkPDFViewer)
* [tkPDFViewer](https://pypi.org/project/tkPDFViewer/)


## **How does it work ?** ##

You can use this Pdf reader like you would for any standard tkinter's widget.
It got the same options and methods than a Frame widget, with a few additions :
* **Two options at instantiation :** defaultMode (default viewing mode) and filepath (automatic call to the load method below)
* **One public method** : load (load a new pdf document in the reader)

**_Here is a quick exemple :_**

```python
from tkinter import Tk
from TkPdfWidget import PdfReader

tk = Tk()
tk.title("simple example")
reader = PdfReader(tk, width=500, height=600, fp="CodeCivil.pdf")
reader.pack()
tk.mainloop()
```


## **Dependancies :** ##

* **_tkinter_** (obviously)
* [Pillow](https://pillow.readthedocs.io)
* [pymupdf](https://pymupdf.readthedocs.io)








