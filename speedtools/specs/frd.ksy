meta:
  id: frd
  file-extension: frd
  license: CC0-1.0
  endian: le
seq:
  - id: unknown
    size: 28
  - id: num_segments
    type: u4
  - id: num_road_blocks
    type: u4
  - id: road_blocks
    type: road_block
    repeat: expr
    repeat-expr: num_road_blocks
  - id: segment_headers
    type: segment_header
    repeat: expr
    repeat-expr: num_segments + 1
  - id: segment_data
    type: segment_data
    parent: segment_headers[_index]
    repeat: expr
    repeat-expr: num_segments + 1
  - id: num_global_objects
    type: u4
  - id: global_objects
    type: object_chunk(num_global_objects)
types:
  float3:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4
  int3:
    seq:
      - id: x
        type: s4
      - id: y
        type: s4
      - id: z
        type: s4
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
  short3:
    seq:
      - id: x
        type: s2
      - id: y
        type: s2
      - id: z
        type: s2
  road_block:
    seq:
      - id: location
        type: float3
        doc: Road block node location
      - id: normal
        type: float3
        doc: Normal vector of the road plane
      - id: forward
        type: float3
        doc: Unit vector pointing forwards
      - id: right
        type: float3
        doc: Unit vector pointing right
      - id: left_wall
        type: f4
        doc: Distance to the left wall
      - id: right_wall
        type: f4
        doc: Distance to the right wall
      - id: unknown1
        size: 8
      - id: neighbors
        type: u2
        repeat: expr
        repeat-expr: 2
        doc: Neighboring nodes
      - id: unknown2
        size: 16
  segment_header:
    seq:
      - id: num_polygons
        type: u4
        repeat: expr
        repeat-expr: 11
        doc: Number of polygons in each chunk
      - id: unused1
        size: 44
        doc: Empty space
      - id: num_vertices
        type: u4
        doc: Number of vertices in the track segment
      - id: num_high_res_vertices
        type: u4
        doc: Number of high-resolution vertices in the track segment
      - id: num_low_res_vertices
        type: u4
        doc: Number of low-resolution vertices in the track segment
      - id: num_medium_res_vertices
        type: u4
        doc: Number of medium-resolution vertices in the track segment
      - id: num_vertices_dup
        type: u4
        doc: Number of vertices in the track segment
      - id: num_object_vertices
        type: u4
        doc: Number of vertices used by off-road track objects
      - id: unused2
        size: 8
        doc: Empty space
      - id: location
        type: float3
        doc: Center location of the track segment
      - id: bounding_points
        type: float3
        repeat: expr
        repeat-expr: 4
        doc: Coordinates of the points delimiting the segment boundary
      - id: neighbors
        type: neighbor
        repeat: expr
        repeat-expr: 300
        doc: List of segment numbers neighboring with this segment
      - id: num_objects_per_chunks
        type: num_objects_per_chunk
        repeat: expr
        repeat-expr: 4
        doc: Number of road objects stored in each object chunk.
      - id: num_driveable_polygons
        type: u4
        doc: Number of driveable track polygon attributes
      - id: min_point
        type: float3
        doc: Minimum vertex coordinate for driveable track polygon
      - id: max_point
        type: float3
        doc: Maximum vertex coordinate for diriveable track polygon
      - id: unused3
        size: 4
        doc: Empty space
      - id: num_road_blocks
        type: u4
        doc: Number of road blocks associated with this segment
      - id: num_road_objects
        type: u4
        doc: Number of non-animated road objects
      - id: unused4
        size: 4
        doc: Empty space
      - id: num_polygon_objects
        type: u4
        doc: Number of off-road polygon objects
      - id: unused5
        size: 4
        doc: Empty space
      - id: num_sound_sources
        type: u4
        doc: Number of sound sources
      - id: unused6
        size: 4
        doc: Empty space
      - id: num_light_sources
        type: u4
        doc: Number of light sources
      - id: unused7
        size: 4
        doc: Empty space
      - id: neighbor_segments
        type: u4
        repeat: expr
        repeat-expr: 8
        doc: List of segments in direct contact with this segment
  neighbor:
    seq:
      - id: block
        type: s2
        doc: Identifier of the neighboring block
      - id: unknown
        type: s2
  num_objects_per_chunk:
    seq:
      - id: num_objects
        type: u4
      - id: unknown
        size: 4
  segment_data:
    seq:
      - id: vertices
        type: float3
        repeat: expr
        repeat-expr: _parent.num_vertices
        doc: Vertice coordinates
      - id: vertice_shadings
        type: color
        repeat: expr
        repeat-expr: _parent.num_vertices
        doc: Vertice shading color
      - id: driveable_polygons
        type: driveable_polygon
        repeat: expr
        repeat-expr: _parent.num_driveable_polygons
        doc: Additional attributes for driveable track polygons
      - id: object_attributes
        type: object_attribute
        repeat: expr
        repeat-expr: _parent.num_road_objects
        doc: Additional attributes for track objects
      - id: second_object_attributes
        type: object_attribute_2_padded(_parent.num_polygon_objects)
        size: 20 * _parent.num_polygon_objects
        doc: Additional attributes for polygon and some track objects
      - id: sound_sources
        type: source_type
        repeat: expr
        repeat-expr: _parent.num_sound_sources
        doc: Sound source data
      - id: light_sources
        type: source_type
        repeat: expr
        repeat-expr: _parent.num_light_sources
        doc: Light source data
      - id: chunks
        type: track_polygon(_parent.num_polygons[_index])
        repeat: expr
        repeat-expr: 11
        doc: Polygon data chunks
      - id: object_chunks
        type: object_chunk(_parent.num_objects_per_chunks[_index].num_objects)
        repeat: expr
        repeat-expr: 4
        doc: Object data chunks
  driveable_polygon:
    seq:
      - id: min_y
        type: u1
        doc: Minimum value of the Y coordinate
      - id: max_y
        type: u1
        doc: Maximum value of the Y coordinate
      - id: min_x
        type: u1
        doc: Minimum value of the X coordinate
      - id: max_x
        type: u1
        doc: Maximum value of the X coordinate
      - id: front_edge
        type: u1
        doc: Front edge flags
      - id: left_edge
        type: u1
        doc: Left edge flags
      - id: back_edge
        type: u1
        doc: Back edge flags
      - id: right_edge
        type: u1
        doc: Right edge flags
      - id: collision_flags
        type: u1
        doc: Polygon collision flags
      - id: unknown
        size: 1
      - id: polygon
        type: u2
        doc: Index of the polygon in high-resolution track chunk described by this structure
      - id: normal
        type: short3
      - id: forward
        type: short3
    instances:
      road_effect:
        value: collision_flags & 0x0f
        enum: road_effect
    enums:
      road_effect:
        0: not_driveable
        1: driveable1
        2: gravel
        3: driveable2
        4: leaves1
        5: dust1
        6: driveable3
        7: driveable4
        8: driveable5
        9: snow1
        10: driveable6
        11: leaves2
        12: driveable7
        13: dust2
        14: driveable8
        15: snow2
  object_attribute:
    seq:
      - id: location
        type: int3
        doc: Coordinate of the object reference point
      - id: unknown1
        size: 2
      - id: identifier
        type: u2
        doc: Unique identifier of the object
      - id: unknown2
        size: 3
      - id: collision_type
        type: u1
        enum: collision_type
        doc: Collision type of the object
    enums:
      collision_type:
        0x00: none
        0x01: static
        0x02: rigid
        0x03: unknown
  object_attribute_2_padded:
    params:
      - id: num_attributes
        type: u4
    seq:
      - id: attributes
        type: object_attribute_2
        repeat: expr
        repeat-expr: num_attributes
  object_attribute_2:
    seq:
      - id: unknown1
        size: 2
        doc: Unknown use
      - id: type
        type: u1
        enum: attribute_type
        doc: Object attribute type
      - id: identifier
        type: u1
        doc: Object identifier number
      - id: location
        type: int3
        doc: Object location
      - id: cross_index
        type: u1
        doc: Unknown use
        if: type != attribute_type::polygon_object
      - id: unknown2
        size: 3
        if: type != attribute_type::polygon_object
    enums:
      attribute_type:
        0x01: polygon_object
        0x02: road_object1
        0x03: road_object2
        0x04: road_object3
        0x06: special
  source_type:
    seq:
      - id: location
        type: int3
        doc: Source location
      - id: type
        type: u4
        doc: Source type
  track_polygon:
    params:
      - id: num_polygons
        type: u4
    seq:
      - id: polygons
        type: polygon
        repeat: expr
        repeat-expr: num_polygons
        doc: Sequence of polygons
  polygon:
    seq:
      - id: face
        type: u2
        repeat: expr
        repeat-expr: 4
        doc: Indices of the vertices building the polygon
      - id: texture
        type: u2
        doc: Texture data
      - id: flags
        type: u2
        doc: Polygon flags
      - id: animation
        type: u1
        doc: Texture animation data
    instances:
      backface_culling:
        value: (flags & 0x8000) == 0
      mirror_y:
        value: (flags & 0x0020) != 0
      mirror_x:
        value: (flags & 0x0010) != 0
      invert:
        value: (flags & 0x0008) != 0
      rotate:
        value: (flags & 0x0004) != 0
      lane:
        value: (texture & 0x0800) != 0
      texture_id:
        value: (texture & 0x07FF)
  object_chunk:
    params:
      - id: num_objects
        type: u4
    seq:
      - id: objects
        type: object_header
        repeat: expr
        repeat-expr: num_objects
      - id: object_extras
        type: object_data
        parent: objects[_index]
        repeat: expr
        repeat-expr: objects.size
  object_header:
    seq:
      - id: type
        type: u4
        enum: object_type
        doc: Object type
      - id: attribute_index
        type: u4
        doc: Index od the additional object attribute data
      - id: unknown
        size: 4
      - id: location
        type: float3
        doc: Location of the object
      - id: specific_data_size
        type: u4
        doc: Size of the object specific data
      - id: unused1
        size: 4
      - id: num_vertices
        type: u4
        doc: Number of vertices in object geometry
      - id: unused2
        size: 8
      - id: num_polygons
        type: u4
        doc: Number of polygons in object geometry
      - id: unused3
        size: 4
    enums:
      object_type:
        0x02: normal1
        0x03: animated
        0x04: normal2
        0x06: special
  object_data:
    seq:
      - id: animation
        type: animation
        if: _parent.type == object_header::object_type::animated
        doc: Animation data
      - id: vertices
        type: float3
        repeat: expr
        repeat-expr: _parent.num_vertices
        doc: Vertice coordinates
      - id: vertice_shadings
        type: color
        repeat: expr
        repeat-expr: _parent.num_vertices
        doc: Vertice shading color
      - id: polygons
        type: polygon
        repeat: expr
        repeat-expr: _parent.num_polygons
        doc: Object polygons
  animation:
    seq:
      - id: head
        type: u2
        doc: Head value with unknown use
      - id: type
        type: u1
        doc: Type value with unknown use
      - id: identifier
        type: u1
        doc: Unique identifier
      - id: num_keyframes
        type: u2
        doc: Number of keyframes in the animation
      - id: delay
        type: u2
        doc: Initial delay of the animation
      - id: keyframes
        type: keyframe
        repeat: expr
        repeat-expr: num_keyframes
        doc: Animation keyframes
  keyframe:
    seq:
      - id: location
        type: int3
        doc: Object location at keyframe
      - id: quaternion
        type: short4
        doc: Object rotation at keyframe
  color:
    seq:
      - id: red
        type: u1
        doc: Red color channel
      - id: green
        type: u1
        doc: Green color channel
      - id: blue
        type: u1
        doc: Blue color channel
      - id: alpha
        type: u1
        doc: Alpha color channel
