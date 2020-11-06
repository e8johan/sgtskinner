#! /bin/env python

import os
import sys
import pathlib
import zipfile

from PySide2.QtWidgets import QApplication \
                            , QPushButton \
                            , QMainWindow \
                            , QTreeView \
                            , QHBoxLayout \
                            , QVBoxLayout \
                            , QWidget \
                            , QSizePolicy \
                            , QSlider \
                            , QCheckBox \
                            , QFrame \
                            , QRadioButton \
                            , QGroupBox \
                            , QColorDialog \
                            , QLineEdit \
                            , QFileDialog \
                            , QMessageBox \
                            , QSplitter
from PySide2.QtGui import QIcon, QPixmap, QImage \
                        , QMouseEvent, QPaintEvent \
                        , QPainter, QBrush \
                        , qRgba, qRed, qGreen, qBlue, qAlpha
from PySide2.QtCore import Qt, Signal, QObject \
                         , QRect, QPoint, QMargins, QSize \
                         , QSortFilterProxyModel, QAbstractTableModel

def findFilesInDir(path):
    res = []
    for dirName, dirList, fileList in os.walk(path):
        dn = dirName.replace('\\', '/')
        for f in fileList:
            relfn = dn + '/' + f
            if relfn.startswith(path):
                relfn = relfn[len(path):]
            res.append(relfn)
    return res

class ColourBox(QWidget):
    colourPicked = Signal(int, int, int, int)

    def __init__(self, cols = 16, rows = 4):
        QWidget.__init__(self)

        self._colours = [qRgba(255, 0, 0, 255), qRgba(0, 255, 0, 255), qRgba(0, 0, 255, 255)]
        self._cols = cols
        self._rows = rows
        self.setMinimumSize(cols*16, rows*16)
    
    def addColour(self, r, g, b, a):
        c = qRgba(r, g, b, a)
        if c in self._colours:
            # TODO we should touch the colour here
            pass
        else:
            if len(self._colours) >= self._cols * self._rows:
                self._colours = self._colours[1:]
            self._colours.append(c)

        self.update()

    def _colourRects(self):
        sfromw = self.width() / self._cols
        sfromh = self.height() / self._rows
        s = min(sfromw, sfromh)

        xo = (self.width() - self._cols*s) / 2
        yo = (self.height() - self._rows*s) / 2

        return (xo, yo, s)

    def paintEvent(self, event):
        xo, yo, s = self._colourRects()
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.white)
        p.setPen(Qt.black)
        for r in range(self._rows):
            for c in range(self._cols):
                if r*self._cols+c < len(self._colours):
                    # TODO, show alpha here
                    p.setBrush(QBrush(self._colours[r*self._cols + c]))
                    p.drawRect(xo + c*s+1, yo + r*s+1, s-2, s-2)

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        xo, yo, s = self._colourRects()
        for r in range(self._rows):
            for c in range(self._cols):
                if r*self._cols+c < len(self._colours):
                    rect = QRect(xo + c*s, yo + r*s, s, s)
                    if rect.contains(event.pos()):
                        colour = self._colours[r*self._cols + c]
                        self.colourPicked.emit(qRed(colour), qGreen(colour), qBlue(colour), qAlpha(colour))

class ColourButton(QPushButton):
    colourChanged = Signal(int, int, int, int)

    def __init__(self):
        QPushButton.__init__(self)
        self.setIconSize(QSize(32, 32))
        self._colour = qRgba(0, 0, 0, 255)
        self.pressed.connect(self.on_button_pressed)
        self._updateColour()

    def setColour(self, r, g, b, a):
        c = qRgba(r, g, b, a)
        if self._colour == c:
            return
        self._colour = c
        self._updateColour()

    def _updateColour(self):
        # TODO, handle alpha here as well
        img = QImage(32, 32, QImage.Format.Format_ARGB32)
        img.fill(self._colour)
        self.setIcon(QIcon(QPixmap.fromImage(img)))

    def on_button_pressed(self):
        res = QColorDialog.getColor(self._colour, options = QColorDialog.ShowAlphaChannel)
        if res.isValid():
            self._colour = qRgba(res.red(), res.green(), res.blue(), res.alpha())
            self.colourChanged.emit(res.red(), res.green(), res.blue(), res.alpha())
            self._updateColour()

class Document(QObject):
    imageChanged = Signal(str)
    allChanged = Signal()

    def isSkin(path):
        # TODO
        # fileexists("pack.mcmeta")
        # fileexists("pack.png")
        # direxists("assets")
        return True

    def isSkinOrEmpty(path):
        # TODO
        return True

    def __init__(self):
        QObject.__init__(self)

        self.jarFilename = ''
        self._path = ''
        self.zf = None
        self._images = {}
        self._isDirty = False

    def clear(self):
        self._images = {}
        self._isDirty = False
        self.allChanged.emit()

    def isDirty(self):
        return self._isDirty

    def hasPath(self):
        if self._path == '':
            return False
        else:
            return True

    def load(self, path):
        self._path = path
        self._images = {}
        filesInAssets = findFilesInDir(path + "/assets/")
        for fn in filesInAssets:
            if fn.endswith(".png"):
                self._images["pack.png"] = QImage(path + "/pack.png")
                self._images["assets/" + fn] = QImage(path + "/assets/" + fn)
        self._isDirty = False
        self.allChanged.emit()

    def save(self):
        for fn in self._images:
            destination = self._path + '/' + fn
            path = pathlib.Path(destination)
            path.parents[0].mkdir(parents=True, exist_ok=True)
            self._images[fn].save(destination)
        self._isDirty = False
        self.allChanged.emit()

    def removeDuplicates(self):
        # TODO is this to be a part of saving, or something optional?
        if self.zf:
            dupes = []
            for fn in self._images:
                ni = self._images[fn]
                if self.hasOriginalImage(fn):
                    oi = self.getOriginalImage(fn)
                    if oi.width() == ni.width() and oi.height() == ni.height():
                        dupe = True
                        for y in range(oi.height()):
                            for x in range(oi.width()):
                                if oi.pixel(x, y) != ni.pixel(x, y):
                                    dupe = False
                        if dupe:
                            dupes.append(fn)
                    else:
                        print("FAILURE: " + fn + " mismatch in size.")
                else:
                    print("FAILURE: " + fn + " not in zip.")

            for fn in dupes:
                del self._images[fn]
        else:
            print("FAILURE: no zip loaded.")

    def saveAs(self, path):
        self._path = path
        self.save()

    def clearImage(self, filename):
        if filename in self._images:
            self._images.remove(filename)
            self._isDirty = True

    def setMinecraftJar(self, fn):
        self.jarFilename = fn
        self.zf = zipfile.ZipFile('C:/Users/Thelin/AppData/Roaming/.technic/modpacks/vanilla/bin/minecraft.jar', 'r')
        self.allChanged.emit()

    def hasOriginalImage(self, filename):
        if self.zf:
            return filename in self.zf.namelist()
        else:
            return False

    def getOriginalImage(self, filename):
        if self.zf:
            return QImage.fromData(self.zf.read(filename))
        else:
            # TODO what about None, and hasOriginalImage?
            return QImage(16, 16, QImage.Format_ARGB32)

    def getImage(self, filename):
        return self._images[filename]

    def hasImage(self, filename):
        if filename in self._images:
            return True
        else:
            return False

    def setImage(self, filename, image):
        self._images[filename] = image
        self._isDirty = True
        self.imageChanged.emit(filename)

class ImageEditor(QFrame):
    colourPicked = Signal(int, int, int, int)
    colourChanged = Signal(int, int, int, int)

    # Tools (operating modes)
    MODE_DRAW = 0
    MODE_COLOURPICKER = 1

    def __init__(self):
        QFrame.__init__(self)

        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setLineWidth(1)

        self.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        self.setMinimumSize(100, 100)

        self._originalOnTop = False
        self._originalAlpha = 255
        self._originalImage = QImage(16, 16, QImage.Format_ARGB32)
        self._image = QImage(16, 16, QImage.Format_ARGB32)

        self._imageIsDirty = False
        self._drawing = False
        self._colour = qRgba(0, 0, 0, 255)
        self._mode = ImageEditor.MODE_DRAW

        self._updateImagePosition()
        self._updateOriginalAlphaImage()

    def setMode(self, m):
        self._drawing = False

        self._mode = m

    def setColour(self, r, g, b, a):
        c = qRgba(r, g, b, a)
        if self._colour == c:
            return

        self._colour = c
        self.colourChanged.emit(r, g, b, a)

    def _updateImagePosition(self):
        hfromw = int((float(self.width()-2) / float(self._originalImage.width())) * self._originalImage.height())
        wfromh = int((float(self.height()-2) /float(self._originalImage.height())) * self._originalImage.width())

        if wfromh > self.width()-2:
            width = self.width()-2
            height = hfromw
        else:
            width = wfromh
            height = self.height()-2

        xoffset = (self.width() - 2 - width)/2+1
        yoffset = (self.height() - 2 - height)/2+1

        self._imageRect = QRect(xoffset, yoffset, width, height)

    def _updateOriginalAlphaImage(self):
        tempImage = self._originalImage.copy()
        for y in range(tempImage.height()):
            for x in range(tempImage.width()):
                pixel = tempImage.pixel(x,y)
                tempImage.setPixel(x, y, qRgba(qRed(pixel), qGreen(pixel), qBlue(pixel), qAlpha(pixel)*self._originalAlpha/255.0))
        self._originalAlphaImage = tempImage

    def setImage(self, img):
        self._image = img.convertToFormat(QImage.Format_ARGB32).copy()
        self._imageIsDirty = False
        self.update()

    def image(self):
        return self._image

    def setOriginalImage(self, img):
        if img.format() == QImage.Format_ARGB32:
            self._originalImage = img
        else:
            self._originalImage = img.convertToFormat(QImage.Format_ARGB32)
        self._image = QImage(self._originalImage.width(), self._originalImage.height(), QImage.Format_RGBA8888)
        self._image.fill(Qt.transparent)
        self._imageIsDirty = False
        self._updateImagePosition()
        self._updateOriginalAlphaImage()
        self.update()

    def imageIsDirty(self):
        return self._imageIsDirty

    def setOriginalOnTop(self, value):
        self._originalOnTop = value
        self.update()

    def setOriginalAlpha(self, value):
        self._originalAlpha = value
        self._updateOriginalAlphaImage()
        self.update()

    def _widgetToImagePos(self, widgetpos):
        pixelPos = widgetpos - self._imageRect.topLeft()
        pixelX = int(float(pixelPos.x())/float(self._imageRect.width())*float(self._originalImage.width()))
        pixelY = int(float(pixelPos.y())/float(self._imageRect.width())*float(self._originalImage.width()))
        return QPoint(pixelX, pixelY)

    def _getPixel(self, pos):
        imagePos = self._widgetToImagePos(pos)
        if self._image.rect().contains(imagePos):
            return self._image.pixel(imagePos)
        return qRgba(0, 0, 0, 0)

    def _getOriginalPixel(self, pos):
        imagePos = self._widgetToImagePos(pos)
        if self._image.rect().contains(imagePos):
            return self._originalImage.pixel(imagePos)
        return qRgba(0, 0, 0, 0)

    def _putPixel(self, pos):
        imagePos = self._widgetToImagePos(pos)
        if self._image.rect().contains(imagePos):
            self._image.setPixel(imagePos, self._colour)
            self._imageIsDirty = True
            self.update()

    def _clearPixel(self, pos):
        imagePos = self._widgetToImagePos(pos)
        if self._image.rect().contains(imagePos):
            self._image.setPixel(imagePos, qRgba(0, 0, 0, 0))
            self._imageIsDirty = True
            self.update()

    def paintEvent(self, event):
        QFrame.paintEvent(self, event)

        p = QPainter(self)

        p.fillRect(QRect(1, 1, self.width()-2, self.height()-2), Qt.darkGray)
        p.fillRect(self._imageRect, Qt.white)
        for y in range(int(self._imageRect.height() / 16.0)+1):
            for x in range(int(self._imageRect.width() / 16.0)+1):
                if (x+y) % 2 == 0:
                    r = QRect(self._imageRect.left() + x*16, self._imageRect.top() + y*16, 16, 16)
                    r = self._imageRect.intersected(r)
                    p.fillRect(r, Qt.lightGray)

        if not self._originalOnTop:
            p.drawImage(self._imageRect, self._originalAlphaImage)
        p.drawImage(self._imageRect, self._image)
        if self._originalOnTop:
            p.drawImage(self._imageRect, self._originalAlphaImage)

    def resizeEvent(self, event):
        self._updateImagePosition()

    def mousePressEvent(self, event):
        if self._mode == ImageEditor.MODE_DRAW:
            if event.button() == Qt.LeftButton:
                self._drawing = True
                self._putPixel(event.pos())
            else:
                self._drawing = False
                self._clearPixel(event.pos())

    def mouseMoveEvent(self, event):
        if self._mode == ImageEditor.MODE_DRAW:
            if self._drawing:
                self._putPixel(event.pos())
            else:
                self._clearPixel(event.pos())

    def mouseReleaseEvent(self, event):
        if self._mode == ImageEditor.MODE_COLOURPICKER:
            if event.button() == Qt.LeftButton:
                # TODO, mix the two colours from original and image...
                res = self._getPixel(event.pos())
            else:
                res = self._getOriginalPixel(event.pos())
            self.colourPicked.emit(qRed(res), qGreen(res), qBlue(res), qAlpha(res))

class DocumentModel(QAbstractTableModel):
    FilePathRole = Qt.UserRole+1

    def __init__(self, document):
        QAbstractTableModel.__init__(self)

        self._fns = []

        self._document = document
        self._document.allChanged.connect(self.on_all_changed)
        self._document.imageChanged.connect(self.on_image_changed)

    def columnCount(self, parent):
        if not parent.isValid():
            return 3
        else:
            return 0

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self._fns)
        else:
            return 0

    def data(self, index, role):
        fn = self._fns[index.row()]
        if index.column() == 0:
            if role == Qt.DecorationRole:
                if self._document.hasOriginalImage(fn):
                    return self._document.getOriginalImage(fn).scaled(32, 32, Qt.KeepAspectRatio)
            elif role == Qt.SizeHintRole:
                return QSize(32, 32)
        elif index.column() == 1:
            if role == Qt.DecorationRole:
                if self._document.hasImage(fn):
                    return self._document.getImage(fn).scaled(32, 32, Qt.KeepAspectRatio)
            elif role == Qt.SizeHintRole:
                return QSize(32, 32)
        else: # index.column() == 2:
            if role == Qt.DisplayRole:
                return fn
        if role == DocumentModel.FilePathRole:
            return fn

        return None
        
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            return ["Orig", "Skin", "File"][section]
        else:
            return None

    def on_all_changed(self):
        self.beginResetModel()
        if self._document.zf:
            self._fns = list(filter(lambda x: x.endswith(".png"), self._document.zf.namelist()))
        else:
            self._fns = []
        self.endResetModel()

    def on_image_changed(self, fn):
        pass #TODO
        print("IMG " + fn)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.currentFilename = ''
        self.document = Document()

        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction("New Skin", self.on_file_new_skin)
        fileMenu.addSeparator()
        fileMenu.addAction("Open Skin", self.on_file_open_skin)
        fileMenu.addAction("Save Skin", self.on_file_save_skin)
        fileMenu.addAction("Save Skin As", self.on_file_save_skin_as)
        fileMenu.addSeparator()
        fileMenu.addAction("Open minecraft.jar", self.on_file_open_minecraft)
        fileMenu.addSeparator()
        fileMenu.addAction("Quit", self.on_file_quit)

        toolsMenu = self.menuBar().addMenu("&Tools")
        toolsMenu.addAction("Remove duplicates", self.on_tools_remove_duplicates)

        root = QSplitter()

        leftRoot = QWidget()
        leftRoot.setLayout(QVBoxLayout())
        
        treeView = QTreeView()
        self.model = DocumentModel(self.document)
        self.filterModel = QSortFilterProxyModel()
        self.filterModel.setSortRole(DocumentModel.FilePathRole)
        self.filterModel.sort(0)
        self.filterModel.setFilterRole(DocumentModel.FilePathRole)
        self.filterModel.setSourceModel(self.model)
        treeView.setModel(self.filterModel)
        treeView.setAllColumnsShowFocus(True)
        treeView.setColumnWidth(0, 64)
        treeView.setColumnWidth(1, 32)
        treeView.setHeaderHidden(False)
        treeView.clicked.connect(self.on_item_clicked)

        self.textFilter = QLineEdit()
        self.textFilter.setPlaceholderText("Enter Filter Text")
        self.textFilter.textChanged.connect(self.on_filter_text_changed)

        leftRoot.layout().addWidget(treeView)
        leftRoot.layout().addWidget(self.textFilter)

        self.editor = ImageEditor()
        self.editor.colourPicked.connect(self.on_colour_picked)

        rightRoot = QWidget()
        rightRoot.setLayout(QVBoxLayout())
        rightRoot.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        colourBox = ColourBox()
        colourBox.colourPicked.connect(self.editor.setColour)
        self.editor.colourChanged.connect(colourBox.addColour)

        colourButton = ColourButton()
        colourButton.colourChanged.connect(self.editor.setColour)
        self.editor.colourChanged.connect(colourButton.setColour)

        toolsRoot = QGroupBox("Tools")
        toolsRoot.setLayout(QHBoxLayout())

        self.toolDraw = QRadioButton("Draw")
        self.toolPick = QRadioButton("Pick")
        self.toolDraw.setChecked(True)

        self.toolDraw.toggled.connect(self.on_tool_changed)
        self.toolPick.toggled.connect(self.on_tool_changed)

        toolsRoot.layout().addWidget(self.toolDraw)
        toolsRoot.layout().addWidget(self.toolPick)

        sliderOriginalAlpha = QSlider(Qt.Horizontal)
        sliderOriginalAlpha.setRange(0, 255)
        sliderOriginalAlpha.setValue(255)
        sliderOriginalAlpha.valueChanged[int].connect(self.editor.setOriginalAlpha)

        checkBoxOriginalOnTop = QCheckBox("Original on top")
        checkBoxOriginalOnTop.toggled.connect(self.editor.setOriginalOnTop)

        buttonCopyOriginal = QPushButton("Copy Original")
        buttonCopyOriginal.clicked.connect(self.on_copy_original)

        rightRoot.layout().addWidget(colourBox)
        rightRoot.layout().addWidget(colourButton)
        rightRoot.layout().addWidget(toolsRoot)
        rightRoot.layout().addWidget(sliderOriginalAlpha)
        rightRoot.layout().addWidget(checkBoxOriginalOnTop)
        rightRoot.layout().addWidget(buttonCopyOriginal)

        root.addWidget(leftRoot)
        root.addWidget(self.editor)
        root.addWidget(rightRoot)

        self.setCentralWidget(root)

    def _syncImageToDocument(self):
        if self.editor.imageIsDirty() and self.currentFilename != '':
            self.document.setImage(self.currentFilename, self.editor.image())

    def on_item_clicked(self, index):
        self._syncImageToDocument()
        self.currentFilename = index.data(DocumentModel.FilePathRole)
        self.editor.setOriginalImage(self.document.getOriginalImage(self.currentFilename))
        if self.document.hasImage(self.currentFilename):
            self.editor.setImage(self.document.getImage(self.currentFilename))

    def on_copy_original(self):
        if self.currentFilename != '':
            self.document.setImage(self.currentFilename, self.document.getOriginalImage(self.currentFilename))
            self.editor.setImage(self.document.getOriginalImage(self.currentFilename))

    def on_tool_changed(self):
        if self.toolPick.isChecked():
            self.editor.setMode(ImageEditor.MODE_COLOURPICKER)
        else:
            self.editor.setMode(ImageEditor.MODE_DRAW)

    def on_colour_picked(self, r, g, b, a):
        self.editor.setColour(r, g, b, a)

    def on_filter_text_changed(self):
        text = self.textFilter.text().strip()
        if len(text) == 0:
            self.filterModel.setFilterWildcard("*")
        else:
            self.filterModel.setFilterWildcard("*" + text + "*")

    def _maybeSave(self):
        self._syncImageToDocument()
        if self.document.isDirty():
            if QMessageBox.question(self, "Skin modified", "The skin has unsaved modification.\nDo you want to save it?") == QMessageBox.Yes:
                return self.on_file_save_skin()
            else:
                return True
        else:
            return True

    def on_file_new_skin(self):
        if self._maybeSave():
            self.document.clear()

    def on_file_open_skin(self):
        path = QFileDialog.getExistingDirectory(self, "Open skin", 'C:\\Users\\Thelin\\Documents\\Johans\\coding\\sgskinner\\testing\\Eriks_Resource_Pack')
        if path != '' and Document.isSkin(path):
            if self._maybeSave():
                self.document.load(path)

    def on_file_save_skin(self):
        if self.document.hasPath():
            self._syncImageToDocument()
            self.document.save()
            return True
        else:
            return self.on_file_save_skin_as()

    def on_file_save_skin_as(self):
        path = QFileDialog.getExistingDirectory(self, "Save skin", 'C:/Users/Thelin/Documents/Johans/coding/sgskinner/testing/skin')
        if path != '' and Document.isSkinOrEmpty(path):
            self._syncImageToDocument()
            self.document.saveAs(path)
            return True
        else:
            return False

    def on_file_open_minecraft(self):
        fn, flt = QFileDialog.getOpenFileName(self, "Open minecraft.jar", 'C:/Users/Thelin/AppData/Roaming/.technic/modpacks/vanilla/bin/', "Minecraft (minecraft.jar)")
        if fn != '':
            self.document.setMinecraftJar(fn)

    def on_file_quit(self):
        if self._maybeSave():
            self.close()

    def on_tools_remove_duplicates(self):
        self.document.removeDuplicates()

    def closeEvent(self, event):
        if not self._maybeSave():
                event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())