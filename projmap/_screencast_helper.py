#!/usr/bin/python3
"""Mutter ScreenCast helper — streams a capture as raw RGB frames to stdout.

Run with the SYSTEM python3 (needs PyGObject `gi`, which projmap's venv lacks).
The D-Bus ScreenCast session must stay alive for the duration, so this process
holds it and spawns a child `gst-launch` that writes raw RGB (W*H*3 per frame)
to *this* process's stdout (fd 1). Status lines go to stderr.

Usage:
  _screencast_helper.py list                       # print monitors as JSON, exit
  _screencast_helper.py virtual W H FPS            # capture a NEW blank virtual monitor
  _screencast_helper.py monitor W H FPS CONNECTOR  # mirror a REAL output (e.g. DP-1)
"""
import sys
import json
import signal
import subprocess

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib  # noqa: E402


def _list_monitors():
    """Print real monitors as JSON via org.gnome.Mutter.DisplayConfig."""
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    dc = Gio.DBusProxy.new_sync(
        bus, Gio.DBusProxyFlags.NONE, None,
        'org.gnome.Mutter.DisplayConfig', '/org/gnome/Mutter/DisplayConfig',
        'org.gnome.Mutter.DisplayConfig', None)
    _serial, monitors, logical_monitors, _props = dc.call_sync(
        'GetCurrentState', None, Gio.DBusCallFlags.NONE, -1, None).unpack()

    # connector -> (width, height) from each monitor's current mode
    res = {}
    for (connector, _vendor, _product, _mserial), modes, _mprops in monitors:
        for _mode_id, w, h, _refresh, _pscale, _scales, mprops in modes:
            if mprops.get('is-current'):
                res[connector] = (w, h)
                break

    out = []
    for x, y, scale, _transform, primary, lm_monitors, _lprops in logical_monitors:
        for connector, _v, _p, _s in lm_monitors:
            w, h = res.get(connector, (0, 0))
            out.append({
                'connector': connector, 'primary': bool(primary),
                'x': x, 'y': y, 'scale': scale, 'width': w, 'height': h,
            })
    print(json.dumps(out))


mode = sys.argv[1]
if mode == 'list':
    _list_monitors()
    sys.exit(0)

W, H, FPS = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
sc = Gio.DBusProxy.new_sync(
    bus, Gio.DBusProxyFlags.NONE, None,
    'org.gnome.Mutter.ScreenCast', '/org/gnome/Mutter/ScreenCast',
    'org.gnome.Mutter.ScreenCast', None)
session_path = sc.call_sync(
    'CreateSession', GLib.Variant('(a{sv})', ({},)),
    Gio.DBusCallFlags.NONE, -1, None).unpack()[0]
sess = Gio.DBusProxy.new_sync(
    bus, Gio.DBusProxyFlags.NONE, None,
    'org.gnome.Mutter.ScreenCast', session_path,
    'org.gnome.Mutter.ScreenCast.Session', None)

props = {'cursor-mode': GLib.Variant('u', 1)}
if mode == 'virtual':
    stream_path = sess.call_sync(
        'RecordVirtual', GLib.Variant('(a{sv})', (props,)),
        Gio.DBusCallFlags.NONE, -1, None).unpack()[0]
elif mode == 'monitor':
    connector = sys.argv[5]
    stream_path = sess.call_sync(
        'RecordMonitor', GLib.Variant('(sa{sv})', (connector, props)),
        Gio.DBusCallFlags.NONE, -1, None).unpack()[0]
else:
    sys.stderr.write(f'unknown mode: {mode}\n')
    sys.exit(2)

gst = {'proc': None}


def _on_node(node_id):
    # No videorate: the Mutter stream is damage-driven (variable rate, buffers
    # without durations), which makes videorate assert. pipewiresrc already only
    # emits on change, so it's naturally rate-limited.
    pipeline = (
        f'pipewiresrc path={node_id} do-timestamp=true ! '
        f'videoscale ! video/x-raw,width={W},height={H} ! '
        f'videoconvert ! video/x-raw,format=RGB ! '
        f'fdsink fd=1'
    )
    # gst inherits our stdout (fd 1) and writes raw RGB frames there.
    gst['proc'] = subprocess.Popen(['gst-launch-1.0', '-q'] + pipeline.split())
    sys.stderr.write(f'NODE {node_id}\n')
    sys.stderr.flush()


def _cb(conn, sender, path, iface, sig, params):
    if sig == 'PipeWireStreamAdded':
        _on_node(params.unpack()[0])


bus.signal_subscribe(
    'org.gnome.Mutter.ScreenCast', 'org.gnome.Mutter.ScreenCast.Stream',
    'PipeWireStreamAdded', stream_path, None, Gio.DBusSignalFlags.NONE, _cb)
sess.call_sync('Start', None, Gio.DBusCallFlags.NONE, -1, None)

loop = GLib.MainLoop()


def _cleanup(*_a):
    if gst['proc'] is not None:
        gst['proc'].terminate()
    try:
        sess.call_sync('Stop', None, Gio.DBusCallFlags.NONE, -1, None)
    except Exception:
        pass
    loop.quit()


signal.signal(signal.SIGTERM, _cleanup)
signal.signal(signal.SIGINT, _cleanup)
loop.run()
