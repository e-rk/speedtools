meta:
  id: viv
  file-extension: viv
  endian: be
  encoding: ASCII
seq:
  - id: magic
    contents: [BIGF]
  - id: size
    type: u4
  - id: num_entries
    type: u4
  - id: unknown
    size: 4
  - id: entries
    type: directory_entry
    repeat: expr
    repeat-expr: num_entries
types:
  directory_entry:
    seq:
      - id: offset
        type: u4
      - id: length
        type: u4
      - id: name
        type: strz
    instances:
      body:
        pos: offset
        type:
          switch-on: name
          cases:
            '"carp.txt"': text_data
            '"car.fce"': mesh_data
        size: length
  directory_item:
    seq:
      - id: test
        type: u4
  text_data:
    seq:
      - id: text
        type: str
        size-eos: true
  mesh_data:
    seq:
      - id: magic
        contents: [0x14, 0x10, 0x10, 0]
      - id: unknown
        size: 4
      - id: num_triangles
        type: u4le
      - id: num_vertices
        type: u4le
      - id: num_arts
        type: u4le
      - id: vertice_table_offset
        type: u4le
      - id: normals_table_offset
        type: u4le
      - id: triangles_table_offset
        type: u4le
      - id: unknown2
        size: 12
      - id: undamaged_vertices_offset
        type: u4le
      - id: undamaged_normals_offset
        type: u4le
      - id: damaged_vertices_offset
        type: u4le
      - id: damaged_normals_offset
        type: u4le
      - id: unknown3
        size: 4
      - id: driver_movement_offset
        type: u4le
      - id: unknown4
        size: 8
      - id: half_sizes
        type: f4le
        repeat: expr
        repeat-expr: 3
      - id: num_light_sources
        type: u4le
      - id: light_sources
        type: point
        repeat: expr
        repeat-expr: num_light_sources
      - id: unused_light_sources
        type: point
        repeat: expr
        repeat-expr: 16 - num_light_sources
      - id: num_parts
        type: u4le
      - id: parts
        type: point
        repeat: expr
        repeat-expr: num_parts
      - id: unused_parts
        type: point
        repeat: expr
        repeat-expr: 64 - num_parts
      - id: part_vertex_index
        type: u4le
        repeat: expr
        repeat-expr: num_parts
      - id: unused_part_vertex_index
        type: u4le
        repeat: expr
        repeat-expr: 64 - num_parts
      - id: part_num_vertices
        type: u4le
        repeat: expr
        repeat-expr: num_parts
      - id: unused_part_num_vertices
        type: u4le
        repeat: expr
        repeat-expr: 64 - num_parts
      - id: part_triangle_index
        type: u4le
        repeat: expr
        repeat-expr: num_parts
      - id: unused_part_triangle_index
        type: u4le
        repeat: expr
        repeat-expr: 64 - num_parts
      - id: part_num_triangles
        type: u4le
        repeat: expr
        repeat-expr: num_parts
      - id: unused_part_num_triangles
        type: u4le
        repeat: expr
        repeat-expr: 64 - num_parts
      - id: num_primary_colors
        type: u4le
      - id: primary_colors
        type: primary_color
        repeat: expr
        repeat-expr: num_primary_colors
      - id: unused_primary_colors
        type: primary_color
        repeat: expr
        repeat-expr: 16 - num_primary_colors
      - id: interior_colors
        type: primary_color
        repeat: expr
        repeat-expr: num_primary_colors
      - id: unused_interior_colors
        type: primary_color
        repeat: expr
        repeat-expr: 16 - num_primary_colors
      - id: secondary_colors
        type: primary_color
        repeat: expr
        repeat-expr: num_primary_colors
      - id: unused_secondary_colors
        type: primary_color
        repeat: expr
        repeat-expr: 16 - num_primary_colors
      - id: driver_colors
        type: primary_color
        repeat: expr
        repeat-expr: num_primary_colors
      - id: unused_driver_colors
        type: primary_color
        repeat: expr
        repeat-expr: 16 - num_primary_colors
      - id: unknown5
        size: 260
      - id: unknown6
        size: 64 * 16  # TODO: ???
      - id: unknown7
        size: 64 * 64  # TODO: ???
      - id: unknown8
        size: 528  # TODO: ???
    instances:
      vertices:
        pos: 8248 + vertice_table_offset
        type: point
        repeat: expr
        repeat-expr: num_vertices
      normals:
        pos: 8248 + normals_table_offset
        type: point
        repeat: expr
        repeat-expr: num_vertices
      polygons:
        pos: 8248 + triangles_table_offset
        type: polygon
        repeat: expr
        repeat-expr: num_triangles
  point:
    seq:
      - id: x
        type: f4le
      - id: y
        type: f4le
      - id: z
        type: f4le
  primary_color:
    seq:
      - id: hue
        type: u4le
      - id: saturation
        type: u4le
      - id: brightness
        type: u4le
      - id: unknown
        size: 4
  polygon:
    seq:
      - id: texture
        type: u4le
      - id: vertices
        type: u4le
        repeat: expr
        repeat-expr: 3
      - id: unknown
        # contents: [00, ff, 00, ff, 00, ff, 00, ff, 00, ff, 00, ff]
        size: 2
        repeat: expr
        repeat-expr: 6
      - id: smoothing
        type: u4
      - id: u
        type: f4le
        repeat: expr
        repeat-expr: 3
      - id: v
        type: f4le
        repeat: expr
        repeat-expr: 3
