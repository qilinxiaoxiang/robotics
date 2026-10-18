# SPDX-License-Identifier: MIT
"""Mac keyboard client; one SSH child, 10Hz command stream, no listening server."""
import argparse
import json
import os
import select
import shlex
import subprocess
import sys
import termios
import time
import tty

KEYS={'e':'arm','r':'ready','n':'lower','o':'open','c':'close','u':'lift','p':'pickup',
      'l':'release','v':'walk','w':'forward','s':'backward','a':'left','d':'right','x':'halt',
      'q':'stop','\x03':'stop','\x1b':'stop'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True,help='Existing SSH alias or user@Pi hostname')
    p.add_argument('--directory',default='microduck-phase1',help='Bundle directory relative to Pi home')
    p.add_argument('--supported',action='store_true');p.add_argument('--max-seconds',type=int,default=120)
    a=p.parse_args()
    if a.host.startswith('-') or not sys.stdin.isatty():p.error('Require an SSH host and an interactive Mac terminal')
    remote='cd "$HOME"/'+shlex.quote(a.directory)+' && exec .venv/bin/python phase1.py run --max-seconds '+str(a.max_seconds)
    if a.supported:remote+=' --supported'
    child=subprocess.Popen(['ssh','-T','-o','BatchMode=yes','-o','ServerAliveInterval=1',
                            '-o','ServerAliveCountMax=2',a.host,remote],stdin=subprocess.PIPE,text=True)
    print('e arm; r ready; n lower; o/c jaw; u lift; p pickup; l release; v prepare gait; w forward jog; x halt; q STOP',flush=True)
    old=termios.tcgetattr(sys.stdin);seq=0;next_send=0
    try:
        tty.setcbreak(sys.stdin.fileno())
        while child.poll() is None:
            action='heartbeat'
            ready,_,_=select.select([sys.stdin],[],[],max(0,next_send-time.monotonic()))
            if ready:
                ch=os.read(sys.stdin.fileno(),1).decode(errors='ignore')
                if not ch:action='stop'
                else:action=KEYS.get(ch.lower(),'heartbeat')
            if ready or time.monotonic()>=next_send:
                child.stdin.write(json.dumps({'seq':seq,'action':action})+'\n');child.stdin.flush()
                seq+=1;next_send=time.monotonic()+.1
            if action=='stop':break
    finally:
        termios.tcsetattr(sys.stdin,termios.TCSADRAIN,old)
        try:
            child.stdin.write(json.dumps({'seq':seq,'action':'stop'})+'\n');child.stdin.flush();child.stdin.close()
        except (BrokenPipeError,ValueError):pass
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:child.terminate()
    if child.returncode not in (0,2,None):raise SystemExit(child.returncode)

if __name__=='__main__':main()
