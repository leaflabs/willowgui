from PyQt4 import QtCore, QtGui
import sys, os, h5py
import numpy as np
import hwif

import config

from WillowDataset import WillowDataset, WillowImportError

class ImportThread(QtCore.QThread):

    progressUpdated = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(object)
    msgPosted = QtCore.pyqtSignal(str)
    canceled = QtCore.pyqtSignal()

    def __init__(self, dataset=None):
        QtCore.QThread.__init__(self)
        if dataset:
            self.dataset = dataset
            self.dataset.progressUpdated.connect(self.progressUpdated)
        self.isTerminated = False

    def handleCancel(self):
        """
        This is required to prevent the race condition between QProgressDialog
        and this thread. self.isTerminated is checked before emission of valueChanged.
        """
        self.isTerminated = True
        self.terminate()

    def run(self):
        try:
            self.dataset.importData()
            self.finished.emit(self.dataset)
        except WillowImportError:
            self.msgPosted.emit('Memory limit exceeded: %3.2f' % config.importLimit_GB)

