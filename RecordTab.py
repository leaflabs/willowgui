from PyQt4 import QtCore, QtGui
import subprocess, h5py
import numpy as np
from progressbar import ProgressBar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from parameters import DAEMON_DIR, DATA_DIR

class RecordTab(QtGui.QWidget):

    def __init__(self, parent):
        super(RecordTab, self).__init__(None)
        self.parent = parent

        self.DATA_DIR = DATA_DIR

        self.nsampLine = QtGui.QLineEdit('30000')
        self.dirLine = QtGui.QLineEdit(self.DATA_DIR)
        self.dirLine.editingFinished.connect(self.updateDataDir)
        self.filenameLine = QtGui.QLineEdit()
        self.recordButton = QtGui.QPushButton('Record Data')
        self.recordButton.clicked.connect(self.recordData)
        self.plotRecentButton = QtGui.QPushButton('Plot Most Recent')
        self.plotRecentButton.clicked.connect(self.plotRecent)
        self.mostRecentFilename = None

        self.plotSpecificButton = QtGui.QPushButton('Plot Specific File:')
        self.plotSpecificButton.clicked.connect(self.plotSpecific)
        self.specificLine = QtGui.QLineEdit()

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(QtGui.QLabel('Number of Samples:'))
        self.layout.addWidget(self.nsampLine)
        self.layout.addWidget(QtGui.QLabel('Directory:'))
        self.layout.addWidget(self.dirLine)
        self.layout.addWidget(QtGui.QLabel('Filename:'))
        self.layout.addWidget(self.filenameLine)
        self.layout.addWidget(self.recordButton)
        self.layout.addSpacing(100)
        self.layout.addWidget(self.plotRecentButton)
        tmpLayout = QtGui.QHBoxLayout()
        tmpLayout.addWidget(self.plotSpecificButton)
        tmpLayout.addWidget(self.specificLine)
        tmpWidget = QtGui.QWidget()
        tmpWidget.setLayout(tmpLayout)
        self.layout.addWidget(tmpWidget)

        self.setLayout(self.layout)

    def updateDataDir(self):
        self.DATA_DIR = str(self.dirLine.text())
        if self.DATA_DIR[-1] != '/':
            self.DATA_DIR = self.DATA_DIR + '/'

    def recordData(self):
        if self.parent.isDaemonRunning:
            self.DATA_DIR = str(self.dirLine.text())
            if self.DATA_DIR[-1] != '/':
                self.DATA_DIR = self.DATA_DIR + '/'
            filename = str(self.filenameLine.text())
            nsamp = self.nsampLine.text()
            self.parent.statusBox.append('Recording...')
            status1 = subprocess.call([DAEMON_DIR+'util/acquire.py', 'start'])
            status2 = subprocess.call([DAEMON_DIR+'util/acquire.py', 'save_stream', self.DATA_DIR+filename, nsamp])
            status3 = subprocess.call([DAEMON_DIR+'util/acquire.py', 'stop'])
            if (status1==1 or status2==1 or status3==1):
                self.parent.statusBox.append('Error')
            else:
                self.parent.statusBox.append('Saved '+nsamp+' samples to: '+self.DATA_DIR+filename)
                self.mostRecentFilename = self.DATA_DIR+filename
        else:
            self.parent.statusBox.append('Please start daemon first!')

    def plotFromFile(self, filename):
        f = h5py.File(filename)
        dset = f['wired-dataset'] # each element is this convoluted tuple
        ns = len(dset)  # number of samples
        data = np.zeros((1024,ns), dtype='uint16')      # 1024 channels at 30 kHz
        pbar = ProgressBar(maxval=ns-1).start()
        self.parent.statusBox.append('Reading in data from '+filename)
        print 'Reading in data from '+filename
        for i in range(ns):
            pbar.update(i)
            data[:,i] = dset[i][3][:1024]
        pbar.finish()
        self.parent.statusBox.append('Done.')
        bank = 3
        self.parent.statusBox.append('Plotting multi-channel data...')
        newFig = Figure((5.,4.), dpi=100)
        self.parent.fig.clear()
        for i in range(32):
            ax = self.parent.fig.add_subplot(8,4,i+1)
            ax.set_axis_bgcolor('k')
            ax.plot(data[bank*32+i,:], color='y')
            ax.set_ylim([0,2**16-1])
            ax.xaxis.set_ticklabels([]) # this makes the axes text invisible (but not the ticks themselves)
            ax.yaxis.set_ticklabels([]) # this makes the axes text invisible (but not the ticks themselves)
        self.parent.fig.subplots_adjust(left=0.,bottom=0.,right=1.,top=1., wspace=0.04, hspace=0.1)
        self.parent.canvas.draw()
        self.parent.statusBox.append('Done.')

    def plotRecent(self):
        if self.mostRecentFilename:
            self.plotFromFile(self.mostRecentFilename)
        else:
            self.parent.statusBox.append('Nothing recorded yet.')

    def plotSpecific(self):
        specificFilename = str(self.specificLine.text())
        if specificFilename:
            self.plotFromFile(self.DATA_DIR + specificFilename)
        else:
            self.parent.statusBox.append('Please enter filename to plot.')
