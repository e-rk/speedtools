meta:
    id: fedata
    title: Front end data
    file-extension:
        - eng
        - bri
        - fre
        - ger
        - ita
        - spa
        - swe
        - jap
    license: CC0-1.0
    endian: le
    encoding: ISO-8859-1
seq:
    - id: header
      type: u2
    - id: unknown0
      size: 796
    - id: serial
      type: s4
      doc: Serial number of the car
    - id: unknown1
      size: 88
    - id: flags
      type: u1
    - id: unknown2
      size: 7
    - id: car_class
      type: s4
      enum: car_class
    - id: unknown3
      size: 2
    - id: format
      type: u1
    - id: unknown4
      size: 50
    - id: engine_location
      type: u1
      enum: engine_location
    - id: unknown5
      size: 2
    - id: num_strings
      type: u2
      doc: Number of the localized strings
    - id: strings
      type: string_entry
      repeat: expr
      repeat-expr: num_strings
      doc: Localized strings
instances:
    police:
        value: (flags & 0x10) != 0
types:
    string_entry:
        seq:
            - id: offset
              type: u4
              doc: Offset of the string from the start of the file
        instances:
            value:
                io: _root._io
                pos: offset
                type: strz
enums:
    car_class:
        0: aaa
        1: aa
        2: a
        3: b
    engine_location:
        0: front
        1: mid
        2: rear
