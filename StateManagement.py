"""
StateManagement.py
created by Chris Chronopoulos on 20140903
This set of functions enables 'safe' state changes.
Call changeState(instruction) with an instruction like:
    'start streaming'
    'stop recording'
    'take snapshot'
    etc.
It will first read the registers on the datanode to determine the state
of the hardware.
Then, if the state change is allowed, it will issue the appropriate set
of ControlCommands to implement the change safely (without losing data,
or creating an error condition).
"""

import sys, os, socket
from time import time

from parameters import *
sys.path.append(os.path.join(DAEMON_DIR, 'util'))
from daemon_control import *


class DaemonControlError(Exception):
    pass


class StateChangeError(Exception):
    pass


def checkState():
    """
    Queries datanode and returns bitfield where:
        bit 0: streaming
        bit 1: snapshot
        bit 3: recording
    """
    cmds = []
    cmds.append(reg_read(3,9))
    cmds.append(reg_read(3,11))
    resps = do_control_cmds(cmds)
    vals = [resp.reg_io.val for resp in resps]
    if vals == [0,0]:
        # idle
        return 0b000
    elif vals == [1,0]:
        # streaming
        return 0b001
    elif vals == [0,3]:
        # recording
        return 0b100
    elif vals == [1,3]:
        # recording and streaming
        return 0b101


def checkState_long():
    cmds = []
    cmds.append(reg_read(2,1))
    cmds.append(reg_read(3,1))
    cmds.append(reg_read(3,9))
    cmds.append(reg_read(3,11))
    cmds.append(reg_read(4,1))
    resps = do_control_cmds(cmds)
    vals = [resp.reg_io.val for resp in resps]
    print 'checkState_long vals = ', vals


def toggleStreaming(enable, state):
    streaming = bool(state & 0b001)
    snapshotting = bool(state & 0b010)
    recording = bool(state & 0b100)
    ###
    cmds = []
    cmd = ControlCommand(type=ControlCommand.FORWARD)
    if enable:
        if streaming:
            print 'Alreading streaming!'
            return
        elif snapshotting:
            # warning: nothing exists to set snapshotting=True yet
            print 'Cannot start stream while snapshot in progress'
            return
        else:
            cmd.forward.sample_type = BOARD_SUBSAMPLE
            cmd.forward.force_daq_reset = not recording # if recording, then DAQ is already running
            try:
                aton = socket.inet_aton(DEFAULT_FORWARD_ADDR)
            except socket.error:
                print 'Invalid address: %s' % DEFAULT_FORWARD_ADDR
                raise
            cmd.forward.dest_udp_addr4 = struct.unpack('!l', aton)[0]
            cmd.forward.dest_udp_port = DEFAULT_FORWARD_PORT
            cmd.forward.enable = True
            cmds.append(cmd)
    else:
        if not streaming:
            print 'Already not streaming!'
            return
        elif snapshotting:
            # warning: nothing exists to set snapshotting=True yet
            print "Cannot do this while shapshot is in progress"
            return
        else:
            cmd.forward.enable = False
            cmds.append(cmd)
            if not recording:
                cmd = ControlCommand(type=ControlCommand.ACQUIRE)
                cmd.acquire.enable = False
                cmds.append(cmd)
    resps = do_control_cmds(cmds)
    #TODO check resps in a robust way, raise DaemonControlError if bad


def takeSnapshot(nsamples, filename, state):
    streaming = bool(state & 0b001)
    snapshotting = bool(state & 0b010)
    recording = bool(state & 0b100)
    ###
    cmds = []
    if streaming:
        # can't handle this yet (GUI crashes, look into BSMP vs BSUB issue)
        raise StateChangeError
        """
        cmd = ControlCommand(type=ControlCommand.STORE)
        cmd.store.path = filename
        cmd.store.nsamples = nsamples
        cmds.append(cmd)
        ###
        # need this to set sample_type back to BOARD_SAMPLE, otherwise daemon barfs forever
        cmd = ControlCommand(type=ControlCommand.FORWARD)
        cmd.forward.sample_type = BOARD_SAMPLE
        cmd.forward.force_daq_reset = False # ???
        try:
            aton = socket.inet_aton(DEFAULT_FORWARD_ADDR)
        except socket.error:
            self.parent.statusBox.append('Invalid address: ' + DEFAULT_FORWARD_ADDR)
            return
        cmd.forward.dest_udp_addr4 = struct.unpack('!l', aton)[0]
        cmd.forward.dest_udp_port = DEFAULT_FORWARD_PORT
        cmd.forward.enable = True
        cmds.append(cmd)
        """
    elif recording:
        # if not streaming, but recording...
        cmd = ControlCommand(type=ControlCommand.STORE)
        cmd.store.path = filename
        cmd.store.nsamples = nsamples
        cmds.append(cmd)
        ###
        # need this to turn off daq->udp, otherwise state gets broken
        cmd = ControlCommand(type=ControlCommand.FORWARD)
        cmd.forward.enable = False
        cmds.append(cmd)
    else:
        # if idle...
        cmd = ControlCommand(type=ControlCommand.FORWARD)
        cmd.forward.sample_type = BOARD_SAMPLE
        cmd.forward.force_daq_reset = True
        try:
            aton = socket.inet_aton(DEFAULT_FORWARD_ADDR)
        except socket.error:
            self.parent.statusBox.append('Invalid address: ' + DEFAULT_FORWARD_ADDR)
            return
        cmd.forward.dest_udp_addr4 = struct.unpack('!l', aton)[0]
        cmd.forward.dest_udp_port = DEFAULT_FORWARD_PORT
        cmd.forward.enable = True
        cmds.append(cmd)

        cmd = ControlCommand(type=ControlCommand.STORE)
        cmd.store.path = filename
        cmd.store.nsamples = nsamples
        cmds.append(cmd)

        cmd = ControlCommand(type=ControlCommand.ACQUIRE)
        cmd.acquire.enable = False
        cmds.append(cmd)
    resps = do_control_cmds(cmds)
    #TODO check resps in a robust way, raise DaemonControlError if bad


def toggleRecording(enable, state):
    streaming = bool(state & 0b001)
    snapshotting = bool(state & 0b010)
    recording = bool(state & 0b100)
    ###
    cmds = []
    if enable:
        if recording:
            print 'Already recording!'
            return
        elif snapshotting:
            print "Cannot do this while shapshot is in progress"
            return
        else:
            if streaming:
                # temporarily turn off streaming (expect a blip in the stream)
                cmd = ControlCommand(type=ControlCommand.FORWARD)
                cmd.forward.enable = False
                cmds.append(cmd)
            cmd = ControlCommand(type=ControlCommand.ACQUIRE)
            cmd.acquire.exp_cookie = long(time())
            cmd.acquire.start_sample = 0
            cmd.acquire.enable = True
            cmds.append(cmd)
            if streaming:
                # turn streaming back on again
                cmd = ControlCommand(type=ControlCommand.FORWARD)
                cmd.forward.sample_type = BOARD_SUBSAMPLE
                cmd.forward.force_daq_reset = False
                try:
                    aton = socket.inet_aton(DEFAULT_FORWARD_ADDR)
                except socket.error:
                    print 'Invalid address: %s' % DEFAULT_FORWARD_ADDR
                    raise
                cmd.forward.dest_udp_addr4 = struct.unpack('!l', aton)[0]
                cmd.forward.dest_udp_port = DEFAULT_FORWARD_PORT
                cmd.forward.enable = True
                cmds.append(cmd)
    else:
        if not recording:
            print 'Already not recording!'
            return
        elif snapshotting:
            print "Cannot do this while shapshot is in progress"
            return
        else:
            cmd = ControlCommand(type=ControlCommand.ACQUIRE)
            cmd.acquire.enable = False
            cmds.append(cmd)

            if streaming:
                print 'turning streaming back on again..'
                # turn streaming back on again
                cmd = ControlCommand(type=ControlCommand.FORWARD)
                cmd.forward.sample_type = BOARD_SUBSAMPLE
                cmd.forward.force_daq_reset = True
                try:
                    aton = socket.inet_aton(DEFAULT_FORWARD_ADDR)
                except socket.error:
                    print 'Invalid address: %s' % DEFAULT_FORWARD_ADDR
                    raise
                cmd.forward.dest_udp_addr4 = struct.unpack('!l', aton)[0]
                cmd.forward.dest_udp_port = DEFAULT_FORWARD_PORT
                cmd.forward.enable = True
                cmds.append(cmd)
    resps = do_control_cmds(cmds)
    #TODO check resps in a robust way, raise DaemonControlError if bad


def changeState(instruction, nsamples=None, filename=None, debug=False):
    verb, mode = instruction.split()
    if verb == 'start':
        enable = True
    elif verb == 'stop':
        enable = False
    elif verb == 'take':
        enable = None
    else:
        print 'invalid verb: %s' % verb
        return
    if mode == 'streaming':
        try:
            state = checkState()
            if debug: print 'Current state: %s' % bin(state)
            toggleStreaming(enable, state)
        except socket.error:
            print "Can't open connection to daemon"
            raise
        except DaemonControlError:
            print "Daemon reported errors"
            raise
    elif mode == 'snapshot':
        if verb == 'take':
            if nsamples and filename:
                state = checkState()
                if debug: print 'Current state: %s' % bin(state)
                takeSnapshot(nsamples, filename, state)
            else:
                print 'please specify nsamples and filename'
                return
        else:
            print 'invalid instruction: %s' % instruction
            return
    elif mode == 'recording':
        try:
            state = checkState()
            if debug: print 'Current state: %s' % bin(state)
            toggleRecording(enable, state)
        except socket.error:
            print "Can't open connection to daemon"
            raise
        except DaemonControlError:
            print "Daemon reported errors"
            raise
    else:
        print 'invalid mode: %s' % mode

