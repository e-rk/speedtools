meta:
  id: viv
  file-extension: viv
  license: CC0-1.0
  imports:
    - fce
  endian: be
  encoding: ASCII
seq:
  - id: magic
    contents: [BIGF]
  - id: size
    type: u4
    doc: Size of the entire file
  - id: num_entries
    type: u4
    doc: Number of directory entries
  - id: unknown
    size: 4
  - id: entries
    type: directory_entry
    repeat: expr
    repeat-expr: num_entries
    doc: Directory entries
types:
  directory_entry:
    seq:
      - id: offset
        type: u4
        doc: Absolute offset of associated data in file
      - id: length
        type: u4
        doc: Length of the associated data
      - id: name
        type: strz
        doc: Name of the directory entry
    instances:
      body:
        pos: offset
        type:
          switch-on: name
          cases:
            '"carp.txt"': strz
            '"car.fce"': fce
            '"dash.fce"': fce
        size: length
