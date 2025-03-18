meta:
  id: bnk
  file-extension: bnk
  ks-opaque-types: true
  endian: le
  bit-endian: be
seq:
  - id: magic
    contents: [BNKl]
  - id: version
    type: u2
  - id: num_sounds
    type: u2
  - id: first_sound_offset
    type: u4
  - id: sound_data_size
    type: u4
    if: version == 4
  - id: unknown
    type: u4
    if: version == 4
  - id: sounds
    type: sound_entry(_root._io.pos, _index == (num_sounds - 1))
    repeat: expr
    repeat-expr: num_sounds
types:
  sound_entry:
    params:
      - id: pos
        type: u4
      - id: is_last
        type: bool
    seq:
      - id: offset
        type: u4
    instances:
      body:
        pos: body_offset
        type: sound_data
        if: offset > 0
      body_offset:
        value: pos + offset
  sound_data:
    seq:
      - id: magic
        contents: [PT, 0, 0]
      - id: header
        type: header(false)
  header:
    params:
      - id: is_subheader
        type: bool
    seq:
      - id: tlvs
        type: pt_header_tlv
        repeat: until
        repeat-until: _.is_terminator or (is_subheader and _.is_subheader_terminator)
  pt_header_tlv:
    seq:
      - id: type
        type: u1
        enum: tv_type
      - id: value
        type:
          switch-on: type
          cases:
            'tv_type::subheader': header(true)
            'tv_type::terminator': empty_value
            'tv_type::data_start': data_start
            _: tlv_value
    instances:
      is_terminator:
        value: type == tv_type::terminator
      is_subheader_terminator:
        value: type == tv_type::subheader_terminator
  tlv_value:
    seq:
      - id: size
        type: u1
      - id: value
        size: size
        if: size > 0 and size < 5
        type:
          switch-on: size
          cases:
            1: b8
            2: b16
            3: b24
            4: b32
            _: b8
  empty_value:
    seq:
      - id: value
        size: 0
  data_start:
    seq:
      - id: size
        type: u1
      - id: value
        size: size
        type:
          switch-on: size
          cases:
            1: b8
            2: b16
            3: b24
            4: b32
            _: b8
    instances:
      body:
        pos: value
        type: bnk_audio_stream(_parent._parent._parent._parent) # Get the main header
        # size: 100 # FIXME: Correct size needed here
  # bnk_audio_stream:
  #   seq:
  #     - id: num_samples
  #       type: u4
  #     - id: samples
  #       type: u2
  #       repeat: expr
  #       repeat-expr: num_samples
enums:
  tv_type:
    0x80: revision
    0x82: channels
    0x83: compression_type
    0x84: sample_rate
    0x85: num_samples
    0x86: loop_offset
    0x87: loop_length
    0x88: data_start
    0x8a: subheader_terminator
    0x92: bytes_per_sample
    0xa0: revision2
    0xfd: subheader
    0xff: terminator
    0x07: pitch_unknown0
    0x0a: pitch_unknown1
    0x10: pitch_unknown2
