meta:
  id: qfs
  file-extension: qfs
  license: CC0-1.0
  imports:
    - fsh
  endian: be
seq:
  - id: magic
    contents: [0x10, 0xFB]
    doc: Pack code indicating LZ77-compressed file
  - id: expanded_length
    type: b24
    doc: Data length after decompression
  - id: data
    size-eos: true
    process: speedtools.refpack(expanded_length)
    type: fsh
    doc: Data compressed with LZ77 algorithm (RefPack)
