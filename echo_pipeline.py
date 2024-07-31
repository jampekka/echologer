#!/usr/bin/env python

import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GstAudio', '1.0')
from gi.repository import GLib, Gst, GstAudio

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s\n" % (err, debug))
        loop.quit()
    return True

def set_props(element, props):
    for p, v in props.items():
        element.set_property(p, v)

def element(name, props={}):
    el = Gst.ElementFactory.make(name, None)
    set_props(el, props)
    return el

def stripcomments(txt):
    out = []
    for line in txt.split('\n'):
        out.append(line.split("#",1)[0])
        #if line.strip().startswith('#'): continue
        #out.append(line)
    
    print(' '.join(out))
    out = '\n'.join(out)
    
    return out
def main(args):
    Gst.init(None)
    
    
    """
    pipeline = element('pipeline')
    src = element('autoaudiosrc')
    
    delay = element('ladspa-delay-1898-so-delay-c', {'delay-time': 0.25})
    #delay.set_property("delay-time", 0.25)
    
    sink = element('autoaudiosink')
    
    echo_cancel = element('webrtcdsp', {
                    'gain-control': False,
                    'high-pass-filter': False,
                    'delay-agnostic': True,
                    'extended-filter': True,
                    'noise-suppression': True,
                    'echo-suppression-level': 'high',
                    'echo-cancel': True
                })
    echo_probe = element('webrtcechoprobe')
    
    pipeline.add(src, delay, sink, echo_cancel, echo_probe)
    Gst.Element.link_many(src, echo_cancel, delay, sink, echo_probe)
    """
    
    device = "hw:CARD=US4x4HR,DEV=0"

    full = f"""
        alsasrc device={device} ! audio/x-raw,channels=4
        #autoaudiosrc ! audio/x-raw,channels=4
        #audiotestsrc ! audio/x-raw,channels=4,channel-mask=0x0000000000000033

        ! audioconvert ! webrtcdsp
            gain-control=false
            high-pass-filter=false
            delay-agnostic=true
            extended-filter=true
            noise-suppression=true
            echo-suppression-level=moderate
            echo-cancel=true
        ! deinterleave name=mic
        
        interleave name=out

        mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 !  out.sink_0
        mic.src_1 ! volume volume=0.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 !  out.sink_1
        mic.src_2 ! volume volume=0.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 !  out.sink_2
        mic.src_3 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.5 !  out.sink_3
        
        out.src ! volume volume=1.0

        ! audioconvert mix-matrix="<
            <0.5, 0.5, 0.0, 0.0>,
            <0.0, 0.5, 0.5, 0.0>,
            <0.0, 0.0, 0.5, 0.5>,
            <0.5, 0.0, 0.0, 0.5>>"
        
        ! audioconvert ! webrtcechoprobe
        
        ! autoaudiosink filter-caps=audio/x-raw,channels=4 name=dst
        alsasink device={device}
        #! audioconvert ! pipewiresink mode=default
        #! audioconvert ! jackaudiosink
        #! audioconvert ! alsasink
    """
    
    pre_delay = 0.1
    stereo = f"""
        #alsasrc device={device} ! audio/x-raw,channels=4
        autoaudiosrc

        ! audioconvert ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=true noise-suppression=false echo-suppression-level=low echo-cancel=true
        ! deinterleave name=mic
        
        interleave name=out

        mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.25 - pre_delay} !  out.sink_0
        mic.src_1 ! volume volume=0.1 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.5 - pre_delay} !  out.sink_1
        #mic.src_2 ! volume volume=0.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 !  out.sink_2
        #mic.src_3 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.5 !  out.sink_3
        
        out.src
        ! calf-sourceforge-net-plugins-Reverb amount=0.1 dry=0.5 decay-time=0.5 on=true
        ! volume volume=1.0

        #! audioconvert mix-matrix="<
        #    <0.5, 0.5, 0.0, 0.0>,
        #    <0.0, 0.5, 0.5, 0.0>,
        #    <0.0, 0.0, 0.5, 0.5>,
        #    <0.5, 0.0, 0.0, 0.5>>"
        
        ! audioconvert ! webrtcechoprobe
        
        #! autoaudiosink filter-caps=audio/x-raw,channels=4 name=dst
        ! audioconvert ! autoaudiosink
        #! alsasink device={device}
        #! audioconvert ! pipewiresink mode=default
        #! audioconvert ! jackaudiosink
        #! audioconvert ! alsasink
    """

    testsrc = f"""
        audiotestsrc ! audio/x-raw,channels=4#,channel-mask=0x0000000000000033
        ! deinterleave keep-positions=true name=mic
        
        interleave name=out

        mic.src_0 ! audioconvert ! volume volume=0.0 ! queue !  out.sink_0
        mic.src_1 ! audioconvert ! volume volume=0.0 ! queue !  out.sink_1
        mic.src_2 ! audioconvert ! volume volume=1.0 ! queue !  out.sink_2
        mic.src_3 ! audioconvert ! volume volume=0.0 ! queue !  out.sink_3


        out.src ! volume volume=0.0001

        ! audio/x-raw,channels=4,channel-mask=0x0000000000000033 ! audioconvert ! alsasink device={device}
    """
    
    minimal = f"""
        alsasrc device={device} ! audio/x-raw,rate=48000,channels=4 ! volume volume=0.01 ! alsasink device={device}
    """

    #(bitmask)0x0000000000000107
    pipeline = Gst.parse_launch(stripcomments(stereo))
    
    """
    out = pipeline.get_by_name('out')
    out.set_property("channel-positions", [
        GstAudio.AudioChannelPosition.FRONT_LEFT,
        GstAudio.AudioChannelPosition.FRONT_RIGHT,
        GstAudio.AudioChannelPosition.REAR_LEFT,
        GstAudio.AudioChannelPosition.REAR_RIGHT,
        ])
    """
    """
    out.set_property("channel-positions", [
        GstAudio.AudioChannelPosition.MONO,
        GstAudio.AudioChannelPosition.MONO,
        GstAudio.AudioChannelPosition.MONO,
        GstAudio.AudioChannelPosition.MONO,
        ])
    """
    
    #print(GstAudio.audio_channel_positions_from_mask(4, 0x0000000000000107))
    # create and event loop and feed gstreamer bus mesages to it
    loop = GLib.MainLoop()
    
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)


    try:
        loop.run()
    except e:
        pass

    Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
    # cleanup
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
