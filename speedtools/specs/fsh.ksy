meta:
  id: fsh
  file-extension: fsh
  license: CC0-1.0
  endian: le
  encoding: ASCII
seq:
  - id: magic
    contents: [SHPI]
  - id: length
    type: u4
  - id: num_objects
    type: u4
  - id: directory_id_string
    contents: [GIMX]
  - id: objects
    type: directory_entry
    repeat: expr
    repeat-expr: num_objects
types:
  directory_entry:
    seq:
      - id: identifier
        type: str
        size: 4
      - id: offset
        type: u4
    instances:
      body:
        pos: offset
        type: bitmap
      aux:
        pos: offset + body.block_size
        type: bitmap
  bitmap:
    seq:
      - id: code
        type: u1
        enum: bitmap_code
      - id: block_size
        type: b24le
      - id: width
        type: u2
      - id: height
        type: u2
      - id: unknown
        type: u4
      - id: x_pos
        type: u2
      - id: y_pos
        type: u2
      - id: data
        type:
          switch-on: code
          cases:
            bitmap_code::bitmap_8: u1
            bitmap_code::bitmap_32: pixel_32_element
            bitmap_code::palette: palette_element
        repeat: expr
        repeat-expr: width * height
  pixel_32_element:
    seq:
      - id: value
        type: u4
        doc: Raw 32-bit pixel value
    instances:
      red:
        value: value & 0xff
      green:
        value: (value >> 8) & 0xff
      blue:
        value: (value >> 16) & 0xff
      alpha:
        value: (value >> 24) & 0xff
      color:
        value: 'blue + green * 0x100 + red * 0x10000 + alpha * 0x1000000'
        doc: ARGB color value
  palette_element:
    seq:
      - id: value
        type: u2
        doc: Raw palette value
    instances:
      red:
        value: (value & 0x1f) * 8
      green:
        value: ((value >> 5) & 0x1f) * 8
      blue:
        value: ((value >> 10) & 0x1f) * 8
      alpha:
        value: '(value & 0x8000) != 0 ? 0xff : 0'
      color:
        value: 'blue + green * 0x100 + red * 0x10000 + alpha * 0x1000000'
        doc: ARGB color value
enums:
  bitmap_code:
    0x7b: bitmap_8
    0x7d: bitmap_32
    0x2d: palette
    0x6f: text
