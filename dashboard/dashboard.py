"""
EV ADAS Python Dashboard — Phase 9 (Minimalist HUD Redesign)
Reads UART telemetry from STM32 Blue Pill / PICSimLab
Run: python dashboard.py --port COM3
     python dashboard.py --demo        (no hardware needed)
"""

import argparse
import serial
import threading
import time
import re
import collections
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Wedge
import matplotlib.animation as animation
import numpy as np

# ── Palette (minimalist HUD / mono + purple accent) ───────────────────
BG        = '#050506'
PANEL     = '#0d0d10'
TRACK     = '#1f1f24'
TEXT      = '#f5f5f7'
TEXT_DIM  = '#9a9aa3'
TEXT_MUTE = '#57575f'
PURPLE    = '#8b5cf6'
CYAN      = '#22d3ee'
AMBER     = '#fbbf24'
RED       = '#ef4444'
ALARM_COLORS = [PURPLE, AMBER, '#fb923c', RED]

# ── Shared state ─────────────────────────────────────────────────────
state = {
    'speed': 0.0, 'soc': 80.0, 'torque': 0.0,
    'temp': 25.0,  'range': 2666.0,
    'accel': 0.0,  'brake': 0.0,
    'front': 400.0,'left':  400.0, 'right': 400.0,
    'ttc':   99.9, 'col':   0,
    'bsd_l': 0,    'bsd_r': 0,
    'alarm': 0,    'fault': 0,
    'drive_mode': 1,
    'connected': False,
}

spd_history = collections.deque([0.0]*60, maxlen=60)

# ── Parse one UART line ───────────────────────────────────────────────
def parse_line(line):
    line = line.strip()

    m = re.search(
        r'SPD:(\d+)\.(\d+)\s+SOC:(\d+)\.(\d+)\s+TRQ:(-?\d+)'
        r'\s+TMP:(\d+)\.(\d+)\s+RNG:(\d+)\s+ACC:(\d+)\s+BRK:(\d+)', line)
    if m:
        g = m.groups()
        state['speed']  = float(g[0]) + float(g[1])/10
        state['soc']    = float(g[2]) + float(g[3])/10
        state['torque'] = float(g[4])
        state['temp']   = float(g[5]) + float(g[6])/10
        state['range']  = float(g[7])
        state['accel']  = float(g[8])
        state['brake']  = float(g[9])
        spd_history.append(state['speed'])
        return

    m = re.search(
        r'F:(\d+)\s+L:(\d+)\s+R:(\d+)\s+TTC:(\d+)\.(\d+)s?\s+'
        r'COL:(\d+)\s+BSD:(\d)(\d)\s+ALM:(\d+)\s+FLT:([0-9A-Fa-f]+)', line)
    if m:
        g = m.groups()
        state['front'] = float(g[0])
        state['left']  = float(g[1])
        state['right'] = float(g[2])
        state['ttc']   = float(g[3]) + float(g[4])/10
        state['col']   = int(g[5])
        state['bsd_l'] = int(g[6])
        state['bsd_r'] = int(g[7])
        state['alarm'] = int(g[8])
        state['fault'] = int(g[9], 16)

# ── Serial reader thread ──────────────────────────────────────────────
def serial_reader(port, baud):
    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                state['connected'] = True
                print(f"[UART] Connected: {port} @ {baud}")
                while True:
                    line = ser.readline().decode('ascii', errors='replace')
                    if line:
                        parse_line(line)
        except Exception as e:
            state['connected'] = False
            print(f"[UART] {e} — retry in 2s")
            time.sleep(2)

# ── Demo mode — animate without hardware ─────────────────────────────
_t = 0.0
def demo_tick():
    global _t
    _t += 0.1
    state['speed']  = 60 + 40 * np.sin(_t * 0.3)
    state['soc']    = max(5, 80 - _t * 0.3)
    state['torque'] = 80 * abs(np.sin(_t * 0.5))
    state['temp']   = 25 + 40 * (1 - np.exp(-_t * 0.05))
    state['range']  = state['soc'] / 100 * 60000 / 18
    state['accel']  = 50 + 30 * np.sin(_t * 0.4)
    state['brake']  = 0
    state['front']  = 100 + 80 * np.sin(_t * 0.2)
    state['left']   = 200 + 180 * np.sin(_t * 0.15)
    state['right']  = 200 + 180 * np.cos(_t * 0.15)
    state['ttc']    = state['front']/100 / max(state['speed']/3.6, 0.1)
    state['col']    = 2 if state['front']<20 else 1 if state['front']<50 else 0
    state['bsd_l']  = 1 if state['left']<30 and state['speed']>20 else 0
    state['bsd_r']  = 1 if state['right']<30 and state['speed']>20 else 0
    state['alarm']  = state['col']
    state['fault']  = 1 if state['temp'] > 90 else 0
    state['connected'] = True
    spd_history.append(state['speed'])

# ── Dashboard layout ──────────────────────────────────────────────────
fig = plt.figure(figsize=(13, 8), facecolor=BG)
fig.canvas.manager.set_window_title('EV ADAS Dashboard — Blue Pill')

gs = fig.add_gridspec(4, 3, height_ratios=[0.18, 1.5, 0.28, 1.15],
                       hspace=0.30, wspace=0.28,
                       left=0.04, right=0.96, top=0.96, bottom=0.05)

ax_header = fig.add_subplot(gs[0, :])
ax_speed  = fig.add_subplot(gs[1, :])
ax_seg    = fig.add_subplot(gs[2, :])
ax_batt   = fig.add_subplot(gs[3, 0])
ax_adas   = fig.add_subplot(gs[3, 1])
ax_info   = fig.add_subplot(gs[3, 2])

for ax in fig.get_axes():
    ax.set_facecolor(BG)

MODES = ['ECO', 'NORMAL', 'SPORT']
MODE_COLORS = [PURPLE, CYAN, AMBER]

# ── Header ─────────────────────────────────────────────────────────────
def draw_header(ax, alarm_idx):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    ax.text(0.0, 0.5, 'EV / ADAS', transform=ax.transAxes, color=TEXT_DIM,
            fontsize=10, fontweight='bold', va='center', family='monospace')

    alarm_str = ['NOMINAL', 'ADVISORY', 'WARNING', 'CRITICAL'][alarm_idx]
    alarm_col = ALARM_COLORS[alarm_idx]
    ax.text(1.0, 0.5, f'\u25cf {alarm_str}', transform=ax.transAxes, color=alarm_col,
            fontsize=10, fontweight='bold', va='center', ha='right', family='monospace')

    sig_col = PURPLE if state['connected'] else RED
    sig_str = 'LINK OK' if state['connected'] else 'LINK LOST'
    ax.text(0.5, 0.5, sig_str, transform=ax.transAxes, color=sig_col,
            fontsize=9, va='center', ha='center', family='monospace')

    ax.plot([0, 1], [0.0, 0.0], color=TRACK, linewidth=1, transform=ax.transAxes)

# ── Big center speed ─────────────────────────────────────────────────
def draw_speed(ax, speed, rng, mode_idx):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    ax.text(0.5, 0.62, f'{speed:.0f}', ha='center', va='center',
            transform=ax.transAxes, color=TEXT, fontsize=95, fontweight='bold',
            family='monospace')
    ax.text(0.5, 0.20, 'KM/H', ha='center', va='center', transform=ax.transAxes,
            color=TEXT_MUTE, fontsize=13, family='monospace')

    ax.text(0.14, 0.62, MODES[mode_idx], ha='center', va='center',
            transform=ax.transAxes, color=MODE_COLORS[mode_idx],
            fontsize=11, fontweight='bold', family='monospace')
    ax.text(0.86, 0.62, f'{rng:.0f} KM', ha='center', va='center',
            transform=ax.transAxes, color=TEXT_DIM,
            fontsize=11, fontweight='bold', family='monospace')

# ── Segmented speed bar ─────────────────────────────────────────────
def draw_seg(ax, speed):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    n_seg = 40
    frac = min(speed / 200.0, 1.0)
    lit = int(frac * n_seg)
    gap = 0.004
    seg_w = (1.0 - gap * (n_seg - 1)) / n_seg

    for i in range(n_seg):
        x = i * (seg_w + gap)
        f = i / n_seg
        if i < lit:
            c = PURPLE if f < 0.55 else (AMBER if f < 0.8 else RED)
        else:
            c = TRACK
        ax.add_patch(patches.Rectangle((x, 0.25), seg_w, 0.5, facecolor=c,
                                        edgecolor='none', transform=ax.transAxes))

# ── Battery panel (linear) ──────────────────────────────────────────
def draw_batt(ax, soc, mode_idx):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.0, 0.94, 'BATTERY', transform=ax.transAxes, color=TEXT_MUTE,
            fontsize=9, fontweight='bold', family='monospace')

    col = PURPLE if soc > 30 else AMBER if soc > 10 else RED
    ax.text(0.0, 0.72, f'{soc:.0f}%', transform=ax.transAxes, color=TEXT,
            fontsize=30, fontweight='bold', family='monospace')

    n_seg = 20
    lit = int(min(soc, 100) / 100 * n_seg)
    gap = 0.008
    seg_w = (1.0 - gap * (n_seg - 1)) / n_seg
    for i in range(n_seg):
        x = i * (seg_w + gap)
        c = col if i < lit else TRACK
        ax.add_patch(patches.Rectangle((x, 0.42), seg_w, 0.14, facecolor=c,
                                        edgecolor='none', transform=ax.transAxes))

    ax.text(0.0, 0.22, f'MODE: {MODES[mode_idx]}', transform=ax.transAxes,
            color=MODE_COLORS[mode_idx], fontsize=9.5, fontweight='bold',
            family='monospace')
    ax.text(0.0, 0.06, f'{state["temp"]:.1f}\u00b0C MOTOR', transform=ax.transAxes,
            color=RED if state['temp'] > 80 else TEXT_MUTE, fontsize=8.5,
            family='monospace')

# ── ADAS radar sweep ─────────────────────────────────────────────────
def draw_adas(ax):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.axis('off')
    ax.text(-1.25, 1.18, 'ADAS RADAR', color=TEXT_MUTE, fontsize=9,
            fontweight='bold', family='monospace')

    for r in (0.4, 0.75, 1.05):
        ax.add_patch(Circle((0, 0), r, fill=False, edgecolor=TRACK, linewidth=1))

    col_col = [TRACK, AMBER, RED][min(state['col'], 2)]

    dist_m = state['front'] / 100.0
    fr = max(0.0, 1.0 - min(dist_m, 10.0) / 10.0)
    if dist_m < 10.0:
        r = 1.05 * (1 - fr) + 0.15
        ax.add_patch(Wedge((0, 0), r, 60, 120, width=0.06,
                            facecolor=col_col if state['col'] else CYAN,
                            edgecolor='none'))
        ax.text(0, r + 0.12, f'{state["front"]:.0f}cm', ha='center',
                color=TEXT_DIM, fontsize=7.5, family='monospace')

    if state['bsd_l']:
        ax.add_patch(Wedge((0, 0), 0.55, 150, 210, width=0.06,
                            facecolor=AMBER, edgecolor='none'))
    if state['bsd_r']:
        ax.add_patch(Wedge((0, 0), 0.55, -30, 30, width=0.06,
                            facecolor=AMBER, edgecolor='none'))

    ax.add_patch(patches.FancyBboxPatch((-0.16, -0.28), 0.32, 0.56,
                                         boxstyle='round,pad=0.02,rounding_size=0.05',
                                         facecolor='#1a1030', edgecolor=PURPLE, linewidth=1.3))
    ax.text(0, 0, 'EV', ha='center', va='center', color=TEXT, fontsize=9,
            fontweight='bold')

    ttc_col = RED if state['ttc'] < 3 else AMBER if state['ttc'] < 6 else PURPLE
    ax.text(0, -1.22, f'TTC {state["ttc"]:.1f}s', ha='center', color=ttc_col,
            fontsize=9.5, fontweight='bold', family='monospace')

# ── Stat tiles ────────────────────────────────────────────────────────
def draw_info(ax):
    ax.cla(); ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0.0, 0.94, 'TELEMETRY', transform=ax.transAxes, color=TEXT_MUTE,
            fontsize=9, fontweight='bold', family='monospace')

    fault_col = RED if state['fault'] else PURPLE
    rows = [
        ('TORQUE', f'{state["torque"]:.0f} Nm', TEXT),
        ('ACCEL',  f'{state["accel"]:.0f}%', CYAN),
        ('BRAKE',  f'{state["brake"]:.0f}%', AMBER if state['brake'] > 0 else TEXT_MUTE),
        ('FAULT',  f'0x{state["fault"]:02X}', fault_col),
    ]
    for i, (lbl, val, col) in enumerate(rows):
        y = 0.72 - i * 0.22
        ax.text(0.0, y, lbl, transform=ax.transAxes, color=TEXT_MUTE,
                fontsize=8.5, family='monospace')
        ax.text(1.0, y, val, transform=ax.transAxes, color=col, ha='right',
                fontsize=10.5, fontweight='bold', family='monospace')

# ── Animation update ──────────────────────────────────────────────────
IS_DEMO = False

def animate(frame):
    if IS_DEMO:
        demo_tick()

    alarm = min(state['alarm'], 3)

    if alarm == 3:
        fig.patch.set_facecolor('#1a0000' if int(time.time()*2) % 2 else BG)
    else:
        fig.patch.set_facecolor(BG)

    draw_header(ax_header, alarm)
    draw_speed(ax_speed, state['speed'], state['range'], state['drive_mode'])
    draw_seg(ax_seg, state['speed'])
    draw_batt(ax_batt, state['soc'], state['drive_mode'])
    draw_adas(ax_adas)
    draw_info(ax_info)

    return []

# ── Entry point ───────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EV ADAS Dashboard')
    parser.add_argument('--port',  default=None, help='Serial port (COM3 / /dev/ttyUSB0)')
    parser.add_argument('--baud',  type=int, default=115200)
    parser.add_argument('--demo',  action='store_true', help='Demo mode — no hardware needed')
    args = parser.parse_args()

    if args.demo or args.port is None:
        IS_DEMO = True
        print("[INFO] Demo mode — no serial port required")
        print("[INFO] Run with --port COM3 to connect to hardware")
    else:
        IS_DEMO = False
        t = threading.Thread(target=serial_reader,
                             args=(args.port, args.baud), daemon=True)
        t.start()

    ani = animation.FuncAnimation(
        fig, animate, interval=100, blit=False, cache_frame_data=False)
    plt.show()
