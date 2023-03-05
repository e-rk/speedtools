meta:
  id: fsh
  file-extension: fsh
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
      - id: elem
        type: u4
    instances:
      red: 
        value: elem & 0xff
      green:
        value: (elem >> 8) & 0xff
      blue:
        value: (elem >> 16) & 0xff
      alpha:
        value: (elem >> 24) & 0xff
      color: 
        value: 'blue + green * 0x100 + red * 0x10000 + alpha * 0x1000000'
  palette_element:
    seq:
      - id: elem
        type: u2
    instances:
      red: 
        value: (elem & 0x1f) * 8
      green:
        value: ((elem >> 5) & 0x1f) * 8
      blue:
        value: ((elem >> 10) & 0x1f) * 8
      alpha:
        value: '(elem & 0x8000) != 0 ? 0xff : 0'
      color: 
        value: 'blue + green * 0x100 + red * 0x10000 + alpha * 0x1000000'
enums:
  bitmap_code:
    0x7b: bitmap_8
    0x7d: bitmap_32
    0x2d: palette
    0x6f: text