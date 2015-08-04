import os, subprocess, socket 

import config, hwif
from StatusBar import StatusBar
from ButtonPanel import ButtonPanel
from MessageLog import MessageLog

from PyQt4 import QtCore, QtGui

import datetime, time, zipfile
if not os.path.isdir('../log'):
    os.mkdir('../log')
oFile = open('../log/oFile', 'w')
eFile = open('../log/eFile', 'w')

class MainWindow(QtGui.QWidget):

    def __init__(self, debugFlag, parent=None):
        QtGui.QWidget.__init__(self)

        self.debugFlag = debugFlag

        self.msgLog = MessageLog(debugFlag)
        self.statusBar = StatusBar(self.msgLog)
        self.buttonPanel = ButtonPanel(self.msgLog)
        self.buttonPanel.logPackageRequested.connect(self.packageLogs)

        self.statusBar.diskFillupDetected.connect(self.buttonPanel.handleDiskFillup)
        self.statusBar.daemonRestartRequested.connect(self.restartDaemon)


        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.statusBar)
        mainLayout.addWidget(self.buttonPanel)
        mainLayout.addWidget(self.msgLog)
        self.setLayout(mainLayout)

        self.setWindowTitle('Willow Control Panel')
        self.setWindowIcon(QtGui.QIcon('../img/round_logo_60x60.png'))
        #self.resize(400,200)
        self.center()

        ###
        self.restartDaemon()

    def startDaemon(self):
        subprocess.call(['killall', 'leafysd'])
        self.daemonProcess = subprocess.Popen([os.path.join(config.daemonDir, 'build/leafysd'),
                                                '-N', '-A', '192.168.1.2', '-I', config.networkInterface],
                                                stdout=oFile, stderr=eFile)
        self.msgLog.post('Daemon started.')
        print 'daemon started'

    def restartDaemon(self):
        self.startDaemon()
        try:
            hwif.init()
            self.statusBar.initializeWatchdog()
            self.msgLog.post('Daemon connection established, watchdog started')
        except socket.error:
            self.msgLog.post('Could not establish a connection with the daemon.')

    def exit(self):
        print 'Cleaning up, then exiting..'
        if self.debugFlag:
            self.packageLogs()
        self.statusBar.watchdogThread.terminate()
        subprocess.call(['killall', 'leafysd'])
        subprocess.call(['killall', 'proto2bytes'])

    def center(self):
        windowCenter = self.frameGeometry().center()
        screenCenter = QtGui.QDesktopWidget().availableGeometry().center()
        self.move(screenCenter-windowCenter)

    def packageLogs(self):
        log_dir = '../log'
        messagesFilename = log_dir+'/messages'
        self.msgLog.messageWrite(messagesFilename)
        actionsFilename = log_dir+'/actions'
        self.msgLog.actionWrite(actionsFilename)
        vitalsLogFilename = log_dir+'/vitals'
        self.statusBar.writeVitalsLog(vitalsLogFilename)
        dt = datetime.datetime.fromtimestamp(time.time())
        zipFilename = str(QtGui.QFileDialog.getSaveFileName(self, 'Save Zipped logs', '../log/logs_from_%02d-%02d-%04d_%02d:%02d:%02d.zip' % (dt.month, dt.day, dt.year, dt.hour, dt.minute, dt.second)))
        if zipFilename:
            with zipfile.ZipFile(zipFilename, 'w') as f:
                f.write(messagesFilename)
                f.write(actionsFilename)
                f.write(vitalsLogFilename)
                f.write('../log/oFile')
                f.write('../log/eFile')
        self.msgLog.post('Saved debugging logs to {0}'.format(zipFilename))
