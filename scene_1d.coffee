#!/usr/bin/env coffee

# TODO: Split to library and node.js executable

waa = require 'node-web-audio-api'
{AudioContext, mediaDevices, GainNode, DelayNode, AudioDestinationNode} = waa

speed_of_sound = 331 # 0⁰C

is_webaudio_node = (node) ->
    # A hack to check if an object is an AudioNode
    # Can't just check with instanceof because node-web-audio-api
    # breaks the spec
    # https://github.com/ircam-ismm/node-web-audio-api/issues/97
    return true if Object.getPrototypeOf(node.constructor).name == "AudioNode"
    return true if node instanceof AudioDestinationNode

    return false
    console.log Object.getPrototypeOf(node.constructor).name
    Object.getPrototypeOf(node.constructor).name == "AudioNode"

connect = (source, nodes...) ->
    for target in nodes
        if (is_webaudio_node source) and (is_webaudio_node target)
            source.connect target
        else if is_webaudio_node target
            source.output.connect target
        else if is_webaudio_node source
            source.connect target.input
        source = target
    return source

get_reflector = (ctx, {listener, position, decay}) ->
    rel_pos = position - listener
    length = Math.abs(rel_pos)*2
    
    # Hacky supergain
    gain = 500/(1 + length)**2
    delay = length/speed_of_sound
    panning = Math.sign(rel_pos)

    get_echo ctx, gain: gain, delay: delay, panning: panning

get_echo = (ctx, {gain, delay, panning}) ->
    gainer = ctx.createGain()
    gainer.gain.value = gain
    delayer = ctx.createDelay()
    delayer.delayTime.value = delay
    panner = ctx.createStereoPanner()
    panner.pan.value = panning

    input = gainer
    output = input
    .connect delayer
    .connect panner

    input: input
    output: output

get_microphone = (ctx, mediaDevices) ->
    mic_dev = await mediaDevices.getUserMedia audio: true
    mic_raw = ctx.createMediaStreamSource mic_dev
    mic = ctx.createChannelMerger 1
    mic_raw.connect mic

get_graph = (ctx, config) ->
    input = ctx.createGain()
    output = ctx.createGain()

    for reflector in config.reflectors
            reflector.listener ?= config.listener
            node = get_reflector(ctx, reflector)
            connect input, node, output

    input: input
    output: output


main = () ->
    fs = require 'fs'
    CSON = require 'cson'

    ctx = new AudioContext()

    config = fs.readFileSync process.stdin.fd, 'utf-8'
    config = CSON.parse config

    graph = get_graph ctx, config

    input = await get_microphone ctx, mediaDevices
    output = ctx.destination

    connect input, graph, output
    connect input, output
    console.log "Connected"
    

if require? and require.main == module
    main()