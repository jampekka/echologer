#!/usr/bin/env coffee

# TODO: Split to library and node.js executable

jsEnv = require 'browser-or-node'

# Use for conditional requires for node.js so that
# esbuild doesn't try to find them
hackrequire = (lib) -> require lib

if jsEnv.isNode
    waa = hackrequire 'node-web-audio-api'
    {AudioContext,
    mediaDevices,
    GainNode,
    DelayNode,
    AudioDestinationNode,
    AudioBufferSourceNode,
    OfflineAudioContext,
    AudioNode} = waa
    fs = hackrequire 'fs'
else
    {AudioContext,
    mediaDevices,
    GainNode,
    DelayNode,
    AudioDestinationNode,
    AudioBufferSourceNode,
    OfflineAudioContext,
    AudioNode} = window
    mediaDevices = navigator.mediaDevices

toWav = require 'audiobuffer-to-wav'

speed_of_sound = 331 # 0⁰C

log = (args...) ->
    console.error args...


is_webaudio_node = (node) ->
    # A hack to check if an object is an AudioNode
    # Can't just check with instanceof because node-web-audio-api
    # breaks the spec
    # https://github.com/ircam-ismm/node-web-audio-api/issues/97
    return true if node instanceof AudioNode
    #return true if Object.getPrototypeOf(node.constructor).name == "AudioNode"
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

get_reflector = (ctx, {listener, position, decay, gain=1.0}) ->
    rel_pos = position - listener
    length = Math.abs(rel_pos)*2
    
    # Hacky supergain
    #gain = 200/(1 + length)**2
    console.log gain
    gain = (1/(1 + length)**2)*gain
    delay = length/speed_of_sound
    panning = Math.sign(rel_pos)
    console.log "Echo", delay, gain
    get_echo ctx, gain: gain, delay: delay, panning: panning

get_echo = (ctx, {gain, delay, panning=0.0}) ->
    gainer = ctx.createGain()
    gainer.gain.value = gain
    delayer = ctx.createDelay()

    # Try to compensate for loopback latency
    console.log ctx.outputLatency
    #delay = delay - ctx.outputLatency * 2

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
    mic_dev = await mediaDevices.getUserMedia
        audio:
        #    channelCount: 1
            echoCancellation: false
            noiseSupression: false
            autoGainControl: false
            #latency: 0
    
    mic_raw = ctx.createMediaStreamSource mic_dev
    # Using merged microphone for now, as no implementation
    # seems to support 4 channels
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


run_config = (config) ->
    # TODO: Fix rendering to file
    #input_file = process.argv[2]
    #interactive = process.stdout.isTTY
    interactive = true
    #if not interactive and not input_file
    #    throw "Output file rendering currently requires an input file"

    ctx = online_ctx = new AudioContext()

    #if input_file
    #    input_data = await load_audio_buffer online_ctx, input_file
    #else
    #    input = await get_microphone ctx, mediaDevices
    input_data = null
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
    
    console.log ctx
    output = ctx.destination
    output.channelCount = output.maxChannelCount

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

module.exports = {run_config}