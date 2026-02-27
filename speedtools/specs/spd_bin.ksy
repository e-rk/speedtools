meta:
    id: spd_bin
    file-extension: bin
    license: CC0-1.0
    endian: le
params:
    - id: num_road_blocks
      type: u4
seq:
    - id: speed
      type: u1
      repeat: expr
      repeat-expr: (num_road_blocks + 1) / 2
    - id: lane
      type: u1
      repeat: expr
      repeat-expr: num_road_blocks
    - id: offset
      type: f4
      repeat: expr
      repeat-expr: num_road_blocks
