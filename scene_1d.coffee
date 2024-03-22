#!/usr/bin/env coffee

# TODO: Split to library and node.js executable

waa = require 'node-web-audio-api'
{AudioContext,
mediaDevices,
GainNode,
DelayNode,
AudioDestinationNode,
AudioBufferSourceNode,
OfflineAudioContext} = waa
fs = require 'fs'
CSON = require 'cson'
toWav = require 'audiobuffer-to-wav'

speed_of_sound = 331 # 0⁰C

log = (args...) ->
    console.error args...

is_webaudio_node = (node) ->
    # A hack to check if an object is an AudioNode
    # Can't just check with instanceof because node-web-audio-api
    # breaks the spec
    # https://github.com/ircam-ismm/node-web-audio-api/issues/97
    return true if Object.getPrototypeOf(node.constructor).name == "AudioNode"
    return true if node instanceof AudioDestinationNode
    return true if node instanceof AudioBufferSourceNode

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
    gain = 200/(1 + length)**2
    delay = length/speed_of_sound
    panning = Math.sign(rel_pos)
    console.log delay
    get_echo ctx, gain: gain, delay: delay, panning: panning

get_echo = (ctx, {gain, delay, panning=0.0}) ->
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

    output.gain.value = config.wet ? 1

    for reflector in config.reflectors ? []
            reflector.listener ?= config.listener
            node = get_reflector(ctx, reflector)
            connect input, node, output

    for echo in config.echos ? []
        # Negative gains are interpreted as decibels.
        # Quite hacky, but makes things simpler.
        if echo.gain <= 0
            # TODO: Find out once for all if this should be
            # squared (i.e. factor 20) or not (i.e. factor 10).
            echo.gain = 10**(echo.gain/10)
        node = get_echo ctx, echo
        connect input, node, output

    
    input: input
    output: output

load_audio_buffer = (ctx, path) ->
    data = fs.readFileSync(path).buffer
    await ctx.decodeAudioData data
    
main = () ->

    input_file = process.argv[2]

    interactive = process.stdout.isTTY

    if not interactive and not input_file
        throw "Output file rendering currently requires an input file"

    ctx = online_ctx = new AudioContext()
        
    if input_file
        input_data = await load_audio_buffer online_ctx, input_file
    else
        input = await get_microphone ctx, mediaDevices
    

    if not interactive
        # TODO: Could be smarter about the length padding
        sr = input_data.sampleRate
        len = input_data.length
        ctx = new OfflineAudioContext(
            numberOfChannels: 2
            length: len + sr*3, # 3 seconds padding, could infer from graph latency
            sampleRate: sr
        )
        online_ctx.close()
    
    if input_data
        input = ctx.createBufferSource()
        input.buffer = input_data
        input.start()

    output = ctx.destination

    config = fs.readFileSync process.stdin.fd, 'utf-8'
    config = CSON.parse config

    graph = get_graph ctx, config


    dry_gain = new GainNode ctx
    dry_gain.gain.value = config.dry ? 1

    connect input, graph, output
    connect input, dry_gain, output

    if not interactive
        outdata = await ctx.startRendering()
        
        wav = toWav outdata

        # TODO: Writing to file descriptor produces garbage,
        # so using /dev/stdout. Not sure why.
        fs.writeFileSync "/dev/stdout", Buffer.from(wav)
        # The offline context can't be closed apparently, and the
        # process doesn't exit if its not
        # ctx.close()
        process.exit()
    

if require? and require.main == module
    main()
