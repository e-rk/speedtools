meta:
  id: ctb
  file-extension: ctb
  license: CC0-1.0
  endian: le
  encoding: ASCII
seq:
  - id: id
    type: u4
  - id: ver
    type: u1
  - id: resolved
    type: u1
  - id: startevent
    type: u1
  - id: controllerpercent
    type: u1
  - id: lowrandomtargetlevel
    type: u2
  - id: lowrandomtargetrange
    type: u2
  - id: lowrandomattacktime
    type: s4
  - id: lowrandomattackrange
    type: s4
  - id: highrandomtargetlevel
    type: u2
  - id: highrandomtargetrange
    type: u2
  - id: highrandomattacktime
    type: s4
  - id: highrandomattackrange
    type: s4
  - id: patchnum
    type: s1
    repeat: expr
    repeat-expr: 8
  - id: event
    type: audioeng_event
    repeat: expr
    repeat-expr: 16
  - id: volume
    type: table(0x128)
    repeat: expr
    repeat-expr: 8
  - id: pitch
    type: table(0x148)
    repeat: expr
    repeat-expr: 8
types:
  audioeng_event:
    seq:
      - id: use
        type: u1
      - id: patnum
        type: u1
      - id: pad1
        type: u1
      - id: pad2
        type: u1
      - id: delta
        type: s2
      - id: max
        type: s2
      - id: attackdelta
        type: s4
      - id: decaydelta
        type: s4
  table:
    params:
      - id: offset_start
        type: u4
    seq:
      - id: offset
        type: u4
    instances:
      value:
        type: s1
        repeat: expr
        repeat-expr: 512
        pos: offset_start + offset
        if: offset > 0
