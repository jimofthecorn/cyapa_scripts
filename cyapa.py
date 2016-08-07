#!/usr/bin/python
from __future__ import print_function
import sys
import subprocess
import re
from functools import partial
import argparse
from time import sleep


def get_device_num( filter_func ):
    p = subprocess.Popen('xinput',stdout=subprocess.PIPE)
    output,junk = p.communicate()
    line = filter_func(output)
    r = re.compile("id=(\d+)\t")
    m = r.search(line)
    idString = line[(m.start()+3):(m.end()-1)]
    return int(idString)

def touchpad_filter_func(output):
    lineList = [l for l in output.split('\n') if 'cyapa' in l]
    if len(lineList) < 1:
        raise ValueError, "No Cypress touchpad found"
    elif len(lineList) > 1:
        raise ValueError, "Multiple Cypress touchpads found"
    line = lineList[0]
    return line

get_touchpad_device_num = partial( get_device_num, touchpad_filter_func )


def get_device_prop_string( deviceNum, propName ):
    p = subprocess.Popen(('xinput','list-props',str(deviceNum)),stdout=subprocess.PIPE)
    output,junk = p.communicate()
    lineList = [l for l in output.split('\n') if propName in l]
    if len(lineList) < 1:
        raise ValueError, "No {} property found".format(propName)
    elif len(lineList) > 1:
        raise ValueError, "Multiple {} properties found".format(propName)
    line = lineList[0]
    result = line.split(':')[1].strip()
    return result

def tablet_stylus_filter_func(output):
    linelist = [l for l in output.split('\n') if 'Wacom' in l and 'stylus' in l]
    if len(linelist) < 1:
        raise ValueError, "no Wacom stylus found"
    elif len(linelist) > 1:
        raise ValueError, "multiple Wacom styli found"
    line = linelist[0]
    return line

get_tablet_device_num = partial( get_device_num, tablet_stylus_filter_func )

def set_touchpad_int_property( deviceNum, propName, val ):
    currVal = int(get_device_prop_string( deviceNum, propName ))
#     print( "value of {}: {}".format(propName,currVal))
    if currVal != val:
        print("setting {} on device {} to {}".format(propName,deviceNum,val))
        cmdTuple = ('xinput','set-prop',str(deviceNum),'--type=int',propName,str(int(val)))
        subprocess.call(cmdTuple)

set_touchpad_click_zone = partial( set_touchpad_int_property, propName='Button Right Click Zone Enable' )

set_touchpad_tap_click = partial( set_touchpad_int_property, propName='Tap Enable' )

def touchpad_fixes(deviceNum):
    check_set_device_active(deviceNum,True)
    set_touchpad_tap_click(deviceNum=deviceNum,val=0)
    set_touchpad_click_zone(deviceNum=deviceNum,val=1)

def set_device_active( deviceNum, onoff ):
    if onoff:
        onoffString = 'enable'
        print("enabling device:",deviceNum)
    else:
        onoffString = 'disable'
        print("disabling device:",deviceNum)
    cmdString = 'xinput {} {}'.format(onoffString,deviceNum)
    subprocess.call(cmdString.split(' '))

def get_device_active( deviceNum ):
    cmdString = 'xinput list-props {}'.format(deviceNum)
    cmdList = cmdString.split(' ')
    p = subprocess.Popen(cmdList,stdout=subprocess.PIPE)
    output,junk = p.communicate()
    linelist = [l for l in output.split('\n') if 'Device Enabled' in l]
    if len(linelist) != 1:
        print(linelist)
        raise ValueError, "Bad output from xinput"
    line = linelist[0]
    idString = line.split('\t')[-1]
    return int(idString)

def check_set_device_active( deviceNum, onoff ):
    currState = get_device_active( deviceNum )
    if currState != onoff:
        set_device_active( deviceNum, onoff )

def touchpad_onoff(args):
    devNum = get_touchpad_device_num()
    if args.activate:
        set_device_active(devNum,True)
    elif args.deactivate:
        set_device_active(devNum,False)
    

def deactivate_touchpad_on_mouse(touchDevice):
    try:
        tabletDevice = get_tablet_device_num()
    except ValueError:
        if not get_device_active(touchDevice):
            print( "Error checking tablet status, activating touchpad" )
            set_device_active(touchDevice,True)
        return
    mouseOn = get_device_active(tabletDevice)
    touchOn = get_device_active(touchDevice)
    if mouseOn and touchOn:
        print( "Tablet active, deactivating touchpad" )
        set_device_active(touchDevice,False)
    elif not (mouseOn or touchOn):
        print( "Tablet inactive, activating touchpad" )
        set_device_active(touchDevice,True)


def check_touchpad_at_interval( interval, action ):
    touchDevice = get_touchpad_device_num()
    if get_device_active(touchDevice):
        print( "Touchpad is active" )
    else:
        print( "Touchpad is not active" )
    try:
        while True:
            action(touchDevice)
            sleep(interval)
    except KeyboardInterrupt:
        print( "Activating touchpad" )
        set_device_active(touchDevice,True)
    else:
        print( "Activating touchpad" )
        set_device_active(touchDevice,True)


def main():
    parser = argparse.ArgumentParser("Cypress APA Touchpad hacks")
    parser.add_argument('-a','--activate',action='store_true')
    parser.add_argument('-d','--deactivate',action='store_true')
    parser.add_argument('-m','--deactivate-mouse',action='store_true')
    parser.add_argument('-f','--fixes',action='store_true')
    args = parser.parse_args(sys.argv[1:])
    if sum((args.activate,args.deactivate,args.deactivate_mouse,args.fixes))!=1:
        raise ValueError, "cyapa.py run with mutually inconsistent arguments"
    if args.fixes:
        check_touchpad_at_interval( 3., touchpad_fixes )
        return
    if args.activate or args.deactivate:
        if args.activate:
            action = partial(check_set_device_active,onoff=True)
        else:
            action = partial(check_set_device_active,onoff=False)
        check_touchpad_at_interval( 3., action )
        return
    check_touchpad_at_interval( 3., deactivate_touchpad_on_mouse )


if __name__ == '__main__':
    main()

