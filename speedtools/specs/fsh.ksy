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
  - id: num_resources
    type: u4
    doc: Number of resources
  - id: directory_id_string
    contents: [GIMX]
  - id: resources
    type: resource(_index, _index == (num_resources - 1))
    repeat: expr
    repeat-expr: num_resources
types:
  resource:
    params:
      - id: index
        type: s4
      - id: is_last
        type: bool
    seq:
      - id: name
        type: str
        size: 4
        doc: Resource name
      - id: offset
        type: u4
        doc: Offset of the resource data in file
    instances:
      body:
        pos: offset
        type: resource_body
        size: body_size
      body_size:
        value: 'not is_last ? _parent.resources[index + 1].offset - offset : _root._io.size - offset'
  resource_body:
    seq:
      - id: blocks
        type: data_block
        repeat: until
        repeat-until: _.extra_offset == 0
  data_block:
    seq:
      - id: code
        type: u1
        enum: data_type
        doc: Data block type
      - id: extra_offset
        type: b24le
        doc: Offset of the next data block since the start of this data block
      - id: width
        type: u2
        doc: Width of the bitmap or length of text data
      - id: height
        type: u2
        doc: Height of the bitmap
      - id: data
        type:
          switch-on: code
          cases:
            data_type::text: strz
            _: bitmap
        size: 'is_last ? (_parent._io.size - _parent._io.pos) : (extra_offset - 8)'
    instances:
      is_last:
        value: extra_offset == 0
  bitmap:
    seq:
      - id: unknown
        type: u4
      - id: x_pos
        type: u2
      - id: y_pos
        type: u2
      - id: data
        type:
          switch-on: _parent.code
          cases:
            data_type::bitmap8: u1
            data_type::bitmap32: pixel_32_element
            data_type::palette: palette_element
        repeat: expr
        repeat-expr: _parent.width * _parent.height
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
  data_type:
    0x7b: bitmap8
    0x7d: bitmap32
    0x2d: palette
    0x6f: text
