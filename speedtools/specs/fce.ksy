meta:
  id: fce
  file-extension: fce
  license: CC0-1.0
  endian: le
  encoding: ASCII
seq:
  - id: magic
    contents: [0x14, 0x10, 0x10, 0]
  - id: unknown
    size: 4
  - id: num_polygons
    type: u4
    doc: Number of polygons in the entire model
  - id: num_vertices
    type: u4
    doc: Number of vertices in the entire model
  - id: num_arts
    type: u4
    doc: Number of color presets
  - id: vertice_table_offset
    type: u4
    doc: Offset of the vertice table in bytes after the FCE header
  - id: normals_table_offset
    type: u4
    doc: Offset of the vertice normal table in bytes after the FCE header
  - id: polygon_table_offset
    type: u4
    doc: Offset of the polygon table in bytes after the FCE header
  - id: unknown2
    size: 12
  - id: undamaged_vertices_offset
    type: u4
    doc: Offset of the undamaged vertices in bytes after the FCE header
  - id: undamaged_normals_offset
    type: u4
    doc: Offset of the undamaged normals in bytes after the FCE header
  - id: damaged_vertices_offset
    type: u4
    doc: Offset of the damaged vertices in bytes after the FCE header
  - id: damaged_normals_offset
    type: u4
    doc: Offset of the damaged normals in bytes after the FCE header
  - id: damage_weights_offset
    type: u4
  - id: driver_movement_offset
    type: u4
    doc: Offset of the driver movement data in bytes after the FCE header
  - id: unknown4
    size: 8
  - id: half_sizes
    type: float3
    doc: Car half-sizes
  - id: num_light_sources
    type: u4
    doc: Number of light source dummies
  - id: light_sources
    type: float3
    repeat: expr
    repeat-expr: num_light_sources
    doc: Light source dummies
  - id: unused_light_sources
    type: float3
    repeat: expr
    repeat-expr: 16 - num_light_sources
  - id: num_car_parts
    type: u4
    doc: Number of car parts
  - id: part_locations
    type: float3
    repeat: expr
    repeat-expr: num_car_parts
    doc: Car part locations
  - id: unused_parts
    type: float3
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: part_vertex_index
    type: u4
    repeat: expr
    repeat-expr: num_car_parts
    doc: Index of the first vertice of the part in the vertice table
  - id: unused_part_vertex_index
    type: u4
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: part_num_vertices
    type: u4
    repeat: expr
    repeat-expr: num_car_parts
    doc: Number of vertices used by the part
  - id: unused_part_num_vertices
    type: u4
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: part_polygon_index
    type: u4
    repeat: expr
    repeat-expr: num_car_parts
    doc: Index of the first polygon of the part in the polygon table
  - id: unused_part_polygon_index
    type: u4
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: part_num_polygons
    type: u4
    repeat: expr
    repeat-expr: num_car_parts
    doc: Number of polygons used by the part
  - id: unused_part_num_polygons
    type: u4
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: num_colors
    type: u4
    doc: Number of car colors
  - id: primary_colors
    type: color
    repeat: expr
    repeat-expr: num_colors
    doc: Car primary colors
  - id: unused_primary_colors
    type: color
    repeat: expr
    repeat-expr: 16 - num_colors
  - id: interior_colors
    type: color
    repeat: expr
    repeat-expr: num_colors
    doc: Car interior colors
  - id: unused_interior_colors
    type: color
    repeat: expr
    repeat-expr: 16 - num_colors
  - id: secondary_colors
    type: color
    repeat: expr
    repeat-expr: num_colors
    doc: Car secondary colors
  - id: unused_secondary_colors
    type: color
    repeat: expr
    repeat-expr: 16 - num_colors
  - id: driver_colors
    type: color
    repeat: expr
    repeat-expr: num_colors
    doc: Driver colors
  - id: unused_driver_colors
    type: color
    repeat: expr
    repeat-expr: 16 - num_colors
  - id: unknown5
    size: 260
  - id: dummies
    type: dummy
    # size: 64 * 16  # TODO: ???
    size: 64
    repeat: expr
    repeat-expr: 16
  - id: part_strings
    type: part
    size: 64
    repeat: expr
    repeat-expr: num_car_parts
  - id: unused_part_strings
    type: part
    size: 64
    repeat: expr
    repeat-expr: 64 - num_car_parts
  - id: unknown8
    size: 528  # TODO: ???
instances:
  vertices:
    pos: 8248 + vertice_table_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Vertice table
  normals:
    pos: 8248 + normals_table_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Normal table
  polygons:
    pos: 8248 + polygon_table_offset
    type: polygon
    repeat: expr
    repeat-expr: num_polygons
    doc: Polygon table
  undamaged_vertices:
    pos: 8248 + undamaged_vertices_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Undamaged vertice table
  undamaged_normals:
    pos: 8248 + undamaged_normals_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Undamaged normal table
  damaged_vertices:
    pos: 8248 + damaged_vertices_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Damaged vertice table
  damaged_normals:
    pos: 8248 + damaged_normals_offset
    type: float3
    repeat: expr
    repeat-expr: num_vertices
    doc: Damaged normal table
  vertex_damage_weights:
    pos: 8248 + damage_weights_offset
    type: f4
    repeat: expr
    repeat-expr: num_vertices
    doc: Vertex damage weights
  movement_data:
    pos: 8248 + driver_movement_offset
    type: u4
    repeat: expr
    repeat-expr: num_vertices
    doc: Vertex movement data
types:
  float3:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4
  color:
    seq:
      - id: hue
        type: u1
      - id: saturation
        type: u1
      - id: brightness
        type: u1
      - id: unknown
        size: 1
  polygon:
    seq:
      - id: texture
        type: u4
        doc: Texture data
      - id: face
        type: u4
        repeat: expr
        repeat-expr: 3
        doc: Polygon face
      - id: unknown
        # contents: [00, ff, 00, ff, 00, ff, 00, ff, 00, ff, 00, ff]
        size: 2
        repeat: expr
        repeat-expr: 6
      - id: flags
        type: u4
        doc: Polygon flags
      - id: u
        type: f4
        repeat: expr
        repeat-expr: 3
        doc: U texture coordinate
      - id: v
        type: f4
        repeat: expr
        repeat-expr: 3
        doc: V texture coordinate
    instances:
        non_reflective:
            value: (flags & 0x0001) != 0
        highly_reflective:
            value: (flags & 0x0002) != 0
        backface_culling:
            value: (flags & 0x0004) == 0
        transparent:
            value: (flags & 0x0008) != 0
  dummy:
    seq:
      - id: magic
        type: str
        size: 1
      - id: color
        type: str
        size: 1
      - id: type
        type: str
        size: 1
      - id: breakable
        type: str
        size: 1
      - id: flashing
        type: str
        size: 1
      - id: intensity
        type: str
        size: 1
      - id: time_on
        type: str
        size: 1
      - id: time_off
        type: str
        size: 1
  part:
    seq:
      - id: value
        type: strz
        repeat: eos
