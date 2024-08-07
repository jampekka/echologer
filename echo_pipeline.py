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
        line = line.split("#",1)[0]
        if not line.strip(): continue
        out.append(line)
        #if line.strip().startswith('#'): continue
        #out.append(line)
    
    print('\n'.join(out))
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
    
    jack_format = 'audio/x-raw,channels=4,rate=(int)48000,format=F32LE,layout=interleaved,channel-mask=(bitmask)0x0'
    webrtc_format = 'audio/x-raw,channels=4,rate=(int)48000,format=F32LE,layout=non-interleaved,channel-mask=(bitmask)0x0'
    mono_format = 'audio/x-raw,channels=1,rate=(int)48000,format=F32LE,layout=interleaved'
    
    lag = 0.25 # TODO: measure and reduce!
    
    def channel_echo(delay, decay=None, wet=None):
        true_delay = max(0, min(5, delay - lag))
        if decay is None:
            decay = min(15.0, max((1 + delay)**3, 0.4))
        if wet is None:
            wet = 1/(1 + delay*3)**2
            if wet < 0.1: wet = 0.0
        
        print(dict(delay=delay, wet=wet, decay=decay))
        return f"""
            ladspa-delay-so-delay-5s dry-wet-balance=1 delay={true_delay} ! audioconvert
            ! calf-sourceforge-net-plugins-Reverb diffusion=1  amount={wet} decay-time={decay} dry={1 - wet} on=true ! audioconvert
            """

    full = f"""
        jackaudiosrc port-names="system:capture_1,system:capture_2,system:capture_3,system:capture_4" connect=explicit name=inputs client-name=echosim ! {jack_format} ! tee name=audiosrc

        ! audioconvert ! {webrtc_format} ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=true extended-filter=true noise-suppression=true echo-suppression-level=high echo-cancel=true
        ! audioconvert ! {jack_format} ! deinterleave name=mic
        
        interleave channel-positions-from-input=false name=out

        # We seem to need queues here or the pipeline stalls. Could try
        # to find a nicer place for this. Now we ramp up four threads
        #mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.25 - lag} ! out.sink_0
        #mic.src_1 ! volume volume=0.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.25 - lag} ! out.sink_1
        #mic.src_2 ! volume volume=0.2 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.50 - lag} ! out.sink_2
        #mic.src_3 ! volume volume=0.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.25 - lag} ! out.sink_3
        
        #mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! {channel_echo(0.25, 0.4, 0.1)} ! out.sink_0
        #mic.src_1 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.6, 3, 1.0)} ! out.sink_1
        #mic.src_2 ! volume volume=0.1 ! queue ! audioconvert ! {channel_echo(0.5, 0.6, 0.5)} ! out.sink_2
        #mic.src_3 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.7, 3, 1.0)} ! out.sink_3
        
        #mic.src_0 ! volume volume=0.1 ! queue ! audioconvert ! {channel_echo(0.5, 0.6, 0.5)} ! out.sink_0
        #mic.src_1 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.6, 3, 1.0)} ! out.sink_1
        #mic.src_2 ! volume volume=1.0 ! queue ! audioconvert ! {channel_echo(0.25, 0.4, 0.1)} ! out.sink_2
        #mic.src_3 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.7, 3, 1.0)} ! out.sink_3
        
        #mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! {channel_echo(0.0, 0.4, 0.0)} ! out.sink_0
        #mic.src_1 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 3, 0.0)} ! out.sink_1
        #mic.src_2 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 0.6, 0.0)} ! out.sink_2
        #mic.src_3 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 3, 0.0)} ! out.sink_3
        


        

        out.src ! audioconvert ! {jack_format}
        ! volume volume=0.5 name=mixed

        ! audioconvert mix-matrix="<
            <0.5, 0.0, 0.0, 0.5>,
            <0.5, 0.5, 0.0, 0.0>,
            <0.0, 0.5, 0.5, 0.0>,
            <0.0, 0.0, 0.5, 0.5>>"

        ! audioconvert ! {webrtc_format} ! webrtcechoprobe
        
        ! audioconvert ! {jack_format} ! jackaudiosink sync=true name=speakers
    """
    
    zerolagger = "ladspa-delay-so-delay-5s dry-wet-balance=0.5 delay=0.0 ! audioconvert ! calf-sourceforge-net-plugins-Reverb diffusion=1  amount=0.0 decay-time=3 dry=1.0 on=true ! audioconvert"

    lagtest = f"""
        jackaudiosrc port-names="system:capture_1,system:capture_2,system:capture_3,system:capture_4" connect=explicit name=inputs client-name=echosim ! {jack_format}

        ! audioconvert ! queue ! {webrtc_format} ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=false noise-suppression=false echo-suppression-level=high echo-cancel=true
        ! audioconvert ! {jack_format} ! deinterleave name=mic
        
        interleave channel-positions-from-input=false name=out

        # We seem to need queues here or the pipeline stalls. Could try
        # to find a nicer place for this. Now we ramp up four threads
        
        mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! {channel_echo(0.0, 0.4, 0.0)} ! out.sink_0
        mic.src_1 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 3, 0.0)} ! out.sink_1
        mic.src_2 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 0.6, 0.0)} ! out.sink_2
        mic.src_3 ! volume volume=0.0 ! queue ! audioconvert ! {channel_echo(0.0, 3, 0.0)} ! out.sink_3
        


        #mic.src_0 ! volume volume=1.0 ! queue ! {zerolagger} ! out.sink_0
        #mic.src_1 ! volume volume=0.0 ! queue ! {zerolagger} ! out.sink_1
        #mic.src_2 ! volume volume=0.0 ! queue ! {zerolagger} ! out.sink_2
        #mic.src_3 ! volume volume=0.0 ! queue ! {zerolagger} ! out.sink_3
        

        out.src ! audioconvert ! {jack_format}
        ! volume volume=0.5 name=mixed

        ! audioconvert mix-matrix="<
            <0.5, 0.0, 0.0, 0.5>,
            <0.5, 0.5, 0.0, 0.0>,
            <0.0, 0.5, 0.5, 0.0>,
            <0.0, 0.0, 0.5, 0.5>>"

        ! audioconvert ! {webrtc_format} ! webrtcechoprobe
        
        ! audioconvert ! {jack_format} ! jackaudiosink sync=true name=speakers
    """

    full = f"""
        jackaudiosrc port-names="system:capture_1,system:capture_2,system:capture_3,system:capture_4" connect=explicit name=inputs client-name=echosim ! {jack_format}

        ! audioconvert ! queue ! {webrtc_format} ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=false noise-suppression=false echo-suppression-level=high echo-cancel=true
        ! audioconvert ! {jack_format} ! deinterleave name=mic
        
        interleave channel-positions-from-input=false name=out

        # We seem to need queues here or the pipeline stalls. Could try
        # to find a nicer place for this. Now we ramp up four threads
        
        mic.src_0 ! volume volume=0.1 ! queue ! audioconvert ! {channel_echo(0.5, 0.6, 0.5)} ! out.sink_0
        mic.src_1 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.6, 3, 1.0)} ! out.sink_1
        mic.src_2 ! volume volume=1.0 ! queue ! audioconvert ! {channel_echo(0.25, 0.4, 0.1)} ! out.sink_2
        mic.src_3 ! volume volume=0.01 ! queue ! audioconvert ! {channel_echo(0.7, 3, 1.0)} ! out.sink_3
        
        out.src ! audioconvert ! {jack_format}
        ! volume volume=0.5 name=mixed

        ! audioconvert mix-matrix="<
            <0.5, 0.0, 0.0, 0.5>,
            <0.5, 0.5, 0.0, 0.0>,
            <0.0, 0.5, 0.5, 0.0>,
            <0.0, 0.0, 0.5, 0.5>>"

        ! audioconvert ! {webrtc_format} ! webrtcechoprobe
        
        ! audioconvert ! {jack_format} ! jackaudiosink sync=true name=speakers
    """



    
    pre_delay = 0.1
    

    stream_format = 'audio/x-raw,rate=48000,layout=interleaved,format=S16LE'
    mono_format = 'audio/x-raw,rate=48000,layout=interleaved,format=F32LE,channels=1'
    webrtc_format = 'audio/x-raw,rate=48000,layout=interleaved,format=S16LE'
    stereo = f"""
        autoaudiosrc ! {stream_format}
        ! audioconvert ! {webrtc_format} ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=true noise-suppression=false echo-suppression-level=low echo-cancel=true
        ! audioconvert ! {stream_format} ! deinterleave name=mic
        
        interleave name=out

        #mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.25 - pre_delay} ! out.sink_0
        #mic.src_1 ! volume volume=0.1 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time={0.5 - pre_delay} ! out.sink_1
        
        mic.src_0 ! audioconvert ! {mono_format} ! queue ! out.sink_0
        mic.src_1 ! audioconvert ! {mono_format} ! queue ! out.sink_1

        out.src
        #! calf-sourceforge-net-plugins-Reverb amount=0.1 dry=0.5 decay-time=0.5 on=true
        ! audioconvert ! volume volume=0.1

        ! audioconvert ! audio/x-raw,layout=non-interleaved ! webrtcechoprobe
        
        ! autoaudiosink

    """

    stereo_jack = f"""
        jackaudiosrc low-latency=true port-names="system:capture_1,system:capture_3" connect=explicit name=inputs client-name=echosim
        #! audioconvert input-channels-reorder-mode=force
        #alsasrc device={device} ! audio/x-raw,channels=4
        #autoaudiosrc ! audio/x-raw,channels=4
        #audiotestsrc ! audio/x-raw,channels=4,channel-mask=0x0000000000000033

        ! queue ! audioconvert !  audio/x-raw,layout=non-interleaved ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=true extended-filter=true noise-suppression=false echo-suppression-level=moderate echo-cancel=true
        ! audioconvert ! deinterleave name=mic
        
        interleave name=out

        mic.src_0 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 ! out.sink_0
        mic.src_1 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 ! out.sink_1
        #mic.src_2 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 ! out.sink_2
        #mic.src_3 ! volume volume=1.0 ! queue ! audioconvert ! ladspa-delay-1898-so-delay-c delay-time=0.25 ! out.sink_3
        
        out.src ! volume volume=0.1 name=mixed

        #! audioconvert mix-matrix="<
        #    <0.5, 0.5, 0.0, 0.0>,
        #    <0.0, 0.5, 0.5, 0.0>,
        #    <0.0, 0.0, 0.5, 0.5>,
        #    <0.5, 0.0, 0.0, 0.5>>"
        
        ! audioconvert name=to_probe ! audio/x-raw,layout=non-interleaved ! webrtcechoprobe ! queue ! audioconvert
        
        #! autoaudiosink filter-caps=audio/x-raw,channels=4 name=dst
        # ! alsasink device={device}
        ! jackaudiosink name=speakers
        #! audioconvert ! pipewiresink mode=default
        #! audioconvert ! jackaudiosink
        #! audioconvert ! alsasink
    """

    unecho = f"""
        jackaudiosrc port-names="system:capture_1,system:capture_3" connect=explicit name=inputs client-name=echosim
        #alsasrc 
        #jackaudiosrc name=inputs client-name=echosim ! queue
        
        ! audioconvert ! audio/x-raw,layout=non-interleaved ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=false noise-suppression=false echo-suppression-level=moderate echo-cancel=true
        #! audioconvert ! audio/x-raw,layout=non-interleaved ! webrtcdsp gain-control=false high-pass-filter=false delay-agnostic=false extended-filter=false noise-suppression=false echo-suppression-level=moderate echo-cancel=false
        ! audioconvert ! volume volume=0.1
        ! audioconvert ! audio/x-raw,layout=non-interleaved ! webrtcechoprobe
        #! queue ! audioconvert ! alsasink name=speakers
        ! audioconvert ! jackaudiosink name=speakers
       #! tee name=unecho
        
        #audiotestsrc ! dst.

        #! dst.
        #! audioconvert ! audio/x-raw,layout=non-interleaved ! webrtcechoprobe ! audioconvert ! dst.
        
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
        jackaudiosrc ! audio/x-raw,channels=4,format=F32LE,channel-mask=(bitmask)0x0
        ! volume volume=0.1 ! jackaudiosink
    """

    #(bitmask)0x0000000000000107
    pipeline = Gst.parse_launch(stripcomments(full))
    #pipeline.set_property('async-handling', True)
    #pipeline.set_property('delay', 1000)
    
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
    except:
        pass

    Gst.debug_bin_to_dot_file(pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
    # cleanup
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main(sys.argv))

