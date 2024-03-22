$ = require 'jquery'

###
default_setup =
    listener_position: [0, 0, 0]
    sources: [{
        type: "Microphone"
        name: "Microphone"
        dry: 0
        wet: 0
        position: "listener"
    }, {
        type: "impulse"
        name: "impulse"
        dry: 1
        wet: 1
        }
        ]
###

speed_of_sound = 331 # Zero degrees. TODO: Make customizable

EchoSource = (ctx, pos, decayTime) ->
    # TODO: Decay
    listener = ctx.listener

    dx = listener.positionX - pos[0]
    dy = listener.positionY - pos[1]
    dz = listener.positionZ - pos[2]
    delay = ctx.createDelay()
    
    panner = ctx.createPanner()
    panner.setPosition pos[0], pos[1], pos[2]



    delay.connect(panner)
    
    input: delay
    output: panner
    delay: delay
    panner: panner

mediaDevices = navigator.mediaDevices
start = ->
    console.log "Stating"
    ctx = new AudioContext()

    ctx.listener.setPosition 40, 0, 0
    #ctx.listener.setOrientation 0, 1, 0, 0, 1, 0

    sources = new GainNode(ctx)
    output = ctx.destination

    mic_dev = await mediaDevices.getUserMedia(
        audio:
            latency: 0
            echoCancellation: false
            noiseSupression: false
            autoGainControl: false
    )
    mic_raw = ctx.createMediaStreamSource(mic_dev)
    mic = mic_raw.connect(ctx.createChannelMerger(1))
    mic.connect sources

    echo = EchoSource ctx, [0, 0, 0], 0.1
    sources.connect(echo.input)
    echo.output.connect(output)
    
    echo = EchoSource ctx, [120, 0, 0], 0.1
    sources.connect(echo.input)
    echo.output.connect(output)



    console.log("Started")
    
    

$(document).one "click keypress", start