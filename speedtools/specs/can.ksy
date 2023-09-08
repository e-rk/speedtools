meta:
  id: can
  file-extension: can
  license: CC0-1.0
  endian: le
seq:
  - id: head
    type: u2
  - id: type
    type: u1
  - id: identifier
    type: u1
  - id: num_keyframes
    type: u2
  - id: delay
    type: u2
  - id: keyframes
    type: keyframe
    repeat: expr
    repeat-expr: num_keyframes
types:
  keyframe:
    seq:
      - id: location
        type: int3
      - id: quaternion
        type: short4
  int3:
    seq:
      - id: ix
        type: s4
      - id: iy
        type: s4
      - id: iz
        type: s4
    instances:
      x:
        value: ix * 0.7692307692307693 / 65536
      y:
        value: iy * 0.7692307692307693 / 65536
      z:
        value: iz * 0.7692307692307693 / 65536
  short4:
    seq:
      - id: x
        type: s2
      - id: y
        type: s2
      - id: z
        type: s2
      - id: w
        type: s2
