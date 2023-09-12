meta:
  id: cam
  file-extension: cam
  license: CC0-1.0
  endian: le
seq:
  - id: num_cameras
    type: u4
  - id: cameras
    type: camera
    repeat: expr
    repeat-expr: num_cameras
types:
  camera:
    seq:
      - id: type
        type: u4
      - id: location
        type: float3
      - id: transform
        type: f4
        repeat: expr
        repeat-expr: 9
      - id: unknown1
        type: f4
      - id: start_road_block
        type: u4
      - id: unknown2
        size: 4
      - id: end_road_block
        type: u4
  float3:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4
