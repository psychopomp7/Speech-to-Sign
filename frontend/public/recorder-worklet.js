class RecorderProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const channelData = input[0]; // Float32Array
      const buffer = new Int16Array(channelData.length);
      for (let i = 0; i < channelData.length; i++) {
        buffer[i] = Math.max(-1, Math.min(1, channelData[i])) * 0x7fff;
      }
      this.port.postMessage(buffer.buffer);
    }
    return true;
  }
}

registerProcessor("recorder-processor", RecorderProcessor);
