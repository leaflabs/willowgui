from PyQt4 import QtCore, QtGui
import os, sys, h5py

import numpy as np

from progressbar import ProgressBar
from ProgressBarWindow import ProgressBarWindow

from parameters import DAEMON_DIR, DATA_DIR
sys.path.append(os.path.join(DAEMON_DIR, 'util'))
from daemon_control import *

import numpy as np
import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure

from collections import OrderedDict
from WaterfallPlotWindow import WaterfallPlotWindow

def createLabelLine(labelText, lineWidget):
    widget = QtGui.QWidget()
    layout = QtGui.QHBoxLayout()
    layout.addWidget(QtGui.QLabel(labelText))
    layout.addWidget(lineWidget)
    widget.setLayout(layout)
    return widget

class PlotWindow(QtGui.QWidget):

    def __init__(self, parent, filename, sampleRange):
        super(PlotWindow, self).__init__(None)

        self.parent = parent
        self.filename = filename
        self.sampleRange = sampleRange
        self.importData()


        ###################
        # Control Panel
        ###################


        ### Control Panel

        self.controlPanel = self.ControlPanel(self)

        ###################
        # Matplotlib Setup
        ###################

        self.initializeMPL()
        self.updateChannels()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.mplLayout = QtGui.QVBoxLayout()
        self.mplLayout.addWidget(self.canvas)
        self.mplLayout.addWidget(self.mpl_toolbar)
        self.mplWindow = QtGui.QWidget()
        self.mplWindow.setLayout(self.mplLayout)


        ###################
        # Top-level stuff
        ##################

        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.controlPanel)
        self.layout.addWidget(self.mplWindow)
        self.setLayout(self.layout)

        self.setWindowTitle('Plotting: %s' % self.filename)
        self.setWindowIcon(QtGui.QIcon('round_logo_60x60.png'))
        self.resize(1600,800)

    class ControlPanel(QtGui.QWidget):

        def __init__(self, parent):
            super(parent.ControlPanel, self).__init__()
            self.parent = parent
            self.channelsGroup = self.ChannelsGroup(self)
            self.zoomGroup = self.ZoomGroup(self)
            self.waterfallButton = QtGui.QPushButton('Waterfall')
            self.waterfallButton.clicked.connect(self.parent.launchWaterfall)
            self.layout = QtGui.QHBoxLayout()
            self.layout.addWidget(self.channelsGroup)
            self.layout.addWidget(self.zoomGroup)
            self.layout.addWidget(self.waterfallButton)
            self.setLayout(self.layout)
            self.setMaximumHeight(175)

        class ChannelsGroup(QtGui.QGroupBox):

            def __init__(self, parent):
                super(parent.ChannelsGroup, self).__init__()
                self.parent = parent
                self.setTitle('Channel Control')

                self.nchannelsDropdown = QtGui.QComboBox()
                self.nchannelsLayoutDict = OrderedDict([(1,(1,1)),
                                                        (2,(2,1)),
                                                        (3,(3,1)),
                                                        (4,(4,1)),
                                                        (5,(5,1)),
                                                        (6,(3,2)),
                                                        (8,(4,2)),
                                                        (10,(5,2)),
                                                        (12,(6,2)),
                                                        (16,(4,4))
                                            ])
                for item in self.nchannelsLayoutDict.items():
                    self.nchannelsDropdown.addItem(str(item[0]))
                self.nchannelsDropdown.setCurrentIndex(6)
                self.nchannelsDropdown.currentIndexChanged.connect(self.handleNChannelChange)

                self.bankSpinBox = QtGui.QSpinBox()
                nchannels = int(self.nchannelsDropdown.currentText())
                self.bankSpinBox.setMaximum(1023//nchannels)
                self.bankSpinBox.valueChanged.connect(self.handleBankChange)

                self.layout = QtGui.QVBoxLayout()
                self.layout.addWidget(QtGui.QLabel('Number of Channels:'))
                self.layout.addWidget(self.nchannelsDropdown)
                self.layout.addWidget(QtGui.QLabel('Bank:'))
                self.layout.addWidget(self.bankSpinBox)
                self.setLayout(self.layout)
                self.setMaximumWidth(220)

            def handleNChannelChange(self, index):
                nchannels = int(self.nchannelsDropdown.currentText())
                self.bankSpinBox.setMaximum(1023//nchannels)
                self.parent.parent.updateChannels()

            def handleBankChange(self):
                self.parent.parent.updateChannels()

        class ZoomGroup(QtGui.QGroupBox):

            def __init__(self, parent):
                super(parent.ZoomGroup, self).__init__()
                self.parent = parent
                self.setTitle('Zoom Control')
                xmin = self.parent.parent.sampleRange[0]
                xmax = self.parent.parent.sampleRange[1]
                ymin = 0
                ymax = 2**16-1
                self.xminLine = QtGui.QLineEdit(str(xmin))
                self.xmaxLine = QtGui.QLineEdit(str(xmax))
                self.yminLine = QtGui.QLineEdit(str(ymin))
                self.ymaxLine = QtGui.QLineEdit(str(ymax))
                grid = QtGui.QWidget()
                gridLayout = QtGui.QGridLayout()
                gridLayout.addWidget(QtGui.QLabel('X-Range:'), 0,0)
                gridLayout.addWidget(self.xminLine, 0,1)
                gridLayout.addWidget(self.xmaxLine, 0,2)
                gridLayout.addWidget(QtGui.QLabel('Y-Range:'), 1,0)
                gridLayout.addWidget(self.yminLine, 1,1)
                gridLayout.addWidget(self.ymaxLine, 1,2)
                grid.setLayout(gridLayout)

                self.refreshButton = QtGui.QPushButton('Refresh')
                self.refreshButton.clicked.connect(self.parent.parent.updateZoom)
                self.defaultButton = QtGui.QPushButton('Default')
                self.defaultButton.clicked.connect(self.parent.parent.defaultZoom)
                buttons = QtGui.QWidget()
                buttonLayout = QtGui.QHBoxLayout()
                buttonLayout.addWidget(self.refreshButton)
                buttonLayout.addWidget(self.defaultButton)
                buttons.setLayout(buttonLayout)

                self.layout = QtGui.QVBoxLayout()
                self.layout.addWidget(grid)
                self.layout.addWidget(buttons)

                self.setLayout(self.layout)
                self.setMaximumWidth(220)

                """
                for widg in [self.xminLine, self.xmaxLine, self.yminLine, self.ymaxLine]:
                    widg.editingFinished.connect(self.flagZoom)
                """

        class ButtonStack(QtGui.QWidget):
            """
            No longer used?
            """

            def __init__(self, parent):
                super(parent.ButtonStack, self).__init__()
                self.parent = parent
                self.refreshButton = QtGui.QPushButton('Refresh')
                self.refreshButton.clicked.connect(self.parent.refresh)
                self.defaultButton = QtGui.QPushButton('Default')
                self.defaultButton.clicked.connect(self.parent.default)
                self.waterfallButton = QtGui.QPushButton('Waterfall')
                self.waterfallButton.clicked.connect(self.parent.launchWaterfall)
                self.layout = QtGui.QVBoxLayout()
                self.layout.addWidget(self.refreshButton)
                self.layout.addWidget(self.defaultButton)
                self.layout.addWidget(self.waterfallButton)
                self.setLayout(self.layout)

        def launchWaterfall(self):
            self.parent.launchWaterfall()

    def importData(self):
        f = h5py.File(self.filename)
        dset = f['wired-dataset']
        if self.sampleRange == -1:
            self.sampleRange = [0, len(dset)-1]
        self.nsamples = self.sampleRange[1] - self.sampleRange[0] + 1
        self.sampleNumbers = np.arange(self.sampleRange[0], self.sampleRange[1]+1)
        self.data = np.zeros((1024,self.nsamples), dtype='uint16')
        progressBarWindow = ProgressBarWindow(self.nsamples, 'Importing data...')
        progressBarWindow.show()
        for i in range(self.nsamples):
            self.data[:,i] = dset[i][3][:1024]
            progressBarWindow.update(i)

    def initializeMPL(self):
        #self.fig = Figure((5.0, 4.0), dpi=100)
        self.fig = Figure()
        #self.fig.subplots_adjust(left=0.,bottom=0.,right=1.,top=1., wspace=0.04, hspace=0.1)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)

    def updateChannels(self):
        channelsGroup = self.controlPanel.channelsGroup
        zoomGroup = self.controlPanel.zoomGroup
        nchannels = int(channelsGroup.nchannelsDropdown.currentText())
        nrows, ncols = channelsGroup.nchannelsLayoutDict[nchannels]
        bank = int(channelsGroup.bankSpinBox.value())
        channelList = range(bank*nchannels,(bank+1)*nchannels)
        xmin = int(zoomGroup.xminLine.text())
        xmax = int(zoomGroup.xmaxLine.text())
        ymin = int(zoomGroup.yminLine.text())
        ymax = int(zoomGroup.ymaxLine.text())
        self.fig.clear()
        self.axesList = []
        self.waveformList = []
        for i in range(nchannels):
            channel = channelList[i]
            axes = self.fig.add_subplot(nrows, ncols, i+1)
            axes.set_title('Channel %d' % channel, fontsize=10, fontweight='bold')
            #axes.yaxis.set_ticklabels([])
            #xtickLabels = axes.xaxis.get_ticklabels()
            #axes.xaxis.set_ticklabels([0,self.maxXvalue/2, self.maxXvalue], fontsize=10)
            axes.tick_params(labelsize=10)
            axes.set_axis_bgcolor('k')
            axes.axis([xmin, xmax, ymin, ymax], fontsize=10)
            waveform = axes.plot(self.sampleNumbers, self.data[channel,:], color='#8fdb90')
            self.axesList.append(axes)
            self.waveformList.append(waveform)
        self.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.98, top=0.92, wspace=0.08, hspace=0.4)
        self.canvas.draw()

    def updateZoom(self):
        zoomGroup = self.controlPanel.zoomGroup
        xmin = int(zoomGroup.xminLine.text())
        xmax = int(zoomGroup.xmaxLine.text())
        ymin = int(zoomGroup.yminLine.text())
        ymax = int(zoomGroup.ymaxLine.text())
        for axes in self.axesList:
            axes.axis([xmin, xmax, ymin, ymax], fontsize=10)
        self.canvas.draw()

    def defaultZoom(self):
        """
        self.nchannelsDropdown.setCurrentIndex(6)
        self.channelListLine.setText('96, 97, 98, 99, 100, 101, 102, 103')
        self.xRangeMin.setText(str(self.sampleRange[0]))
        self.xRangeMax.setText(str(self.sampleRange[1]))
        self.yRangeMin.setText('0')
        self.yRangeMax.setText(str(2**16-1))
        self.updateChannels()
        """
        zoomGroup = self.controlPanel.zoomGroup
        zoomGroup.xminLine.setText(str(self.sampleRange[0]))
        zoomGroup.xmaxLine.setText(str(self.sampleRange[1]))
        zoomGroup.yminLine.setText(str(0))
        zoomGroup.ymaxLine.setText(str(2**16-1))
        self.updateZoom()

    def launchWaterfall(self):
        self.waterfallPlotWindow = WaterfallPlotWindow(self)
        self.waterfallPlotWindow.show()

    """
    def refresh(self):
        self.updateChannels()
        self.updateZoom()
    """

    def closeEvent(self, event):
        print 'closing'

if __name__=='__main__':
    app = QtGui.QApplication(sys.argv)
    main = PlotWindow(None, '/home/chrono/sng/data/justin/neuralRecording_10sec.h5', [0,5000])
    main.show()
    app.exec_()
    #main.exit()