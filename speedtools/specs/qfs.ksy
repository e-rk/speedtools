meta:
  id: qfs
  file-extension: qfs
  endian: be
  imports:
    - fsh
seq:
  - id: flags
    type: u1
  - id: magic
    contents: [0xFB]
  - id: expanded_length
    type: b24
  - id: data
    size-eos: true
    process: speedtools.refpack(expanded_length)
    type: fsh