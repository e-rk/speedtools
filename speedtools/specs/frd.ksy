meta:
  id: frd
  file-extension: frd
  endian: le
seq:
  - id: header
    type: frd_header
  - id: road_blocks
    type: frd_road_block
    repeat: expr
    repeat-expr: header.pos
  - id: track_blocks
    type: frd_track_block
    repeat: expr
    repeat-expr: header.blocks + 1
  - id: track_block_data
    type: frd_track_block_data(track_blocks[_index])
    repeat: expr
    repeat-expr: header.blocks + 1
  - id: nobj
    type: u4
  - id: global_objects
    type: xobjs(nobj)
types:
  frd_header:
    seq:
      - id: unknown
        size: 28
      - id: blocks
        type: u4
      - id: pos
        type: u4
  frd_road_block:
    seq:
      - id: ref
        type: point
      - id: normal
        type: point
      - id: forward
        type: point
      - id: right
        type: point
      - id: left_wall
        type: f4
      - id: right_wall
        type: f4
      - id: unknown
        size: 28
  point:
    seq:
      - id: x
        type: f4
      - id: y
        type: f4
      - id: z
        type: f4
  frd_track_block:
    seq:
      - id: block
        type: u4
        repeat: expr
        repeat-expr: 7
      - id: obj
        type: u4
        repeat: expr
        repeat-expr: 4
      - id: unknown
        size: 44
      - id: vertices
        type: u4
      - id: hi_res_vert
        type: u4
      - id: lo_res_vert
        type: u4
      - id: med_res_vert
        type: u4
      - id: vertices_dup
        type: u4
      - id: object_vert
        type: u4
      - id: unknown1
        size: 8
      - id: centre
        type: point
      - id: bounding
        type: point
        repeat: expr
        repeat-expr: 4
      - id: neighbouring_blocks
        type: neighbor_block
        repeat: expr
        repeat-expr: 300
      - id: nobj
        type: nobj_type
        repeat: expr
        repeat-expr: 4
      - id: nvroad
        type: u4
      - id: pt_min
        type: point
      - id: pt_max
        type: point
      - id: unknown3
        size: 4
      - id: positions
        type: u4
      - id: nxobj
        type: u4
      - id: unknown4
        size: 4
      - id: npolyobj
        type: u4
      - id: unknown5
        size: 4
      - id: nsoundsrc
        type: u4
      - id: unknown6
        size: 4
      - id: nlightsrc
        type: u4
      - id: unknown7
        size: 4
      - id: hs_neighbors
        type: u4
        repeat: expr
        repeat-expr: 8
  neighbor_block:
    seq:
      - id: block
        type: s2
      - id: unknown
        type: s2
  nobj_type:
    seq:
      - id: nobj
        type: u4
      - id: unknown
        size: 4
  frd_track_block_data:
    params:
      - id: header
        type: frd_track_block
    seq:
      - id: vertices
        type: point
        repeat: expr
        repeat-expr: header.vertices
      - id: unknown
        type: u4
        repeat: expr
        repeat-expr: header.vertices
      - id: vroad
        type: nvroad_type
        repeat: expr
        repeat-expr: header.nvroad
      - id: xobj
        type: refxobj
        repeat: expr
        repeat-expr: header.nxobj
      - id: unknown1
        size: 20
        repeat: expr
        repeat-expr: header.npolyobj
      - id: soundsrc
        type: source_type
        repeat: expr
        repeat-expr: header.nsoundsrc
      - id: lightsrc
        type: source_type
        repeat: expr
        repeat-expr: header.nlightsrc
      - id: polydata
        type: track_polygon(header.block[_index])
        repeat: expr
        repeat-expr: 7
      - id: polydata_obj
        type: track_polygon(header.obj[_index])
        repeat: expr
        repeat-expr: 4
      - id: objs
        type: xobjs(header.nobj[_index].nobj)
        repeat: expr
        repeat-expr: 4
  nvroad_type:
    seq:
      - id: hs_minmax
        size: 4
      - id: hs_orphan
        size: 4
      - id: unknown
        size: 2
      - id: count
        type: u2
      - id: data
        type: vroad_data
  vroad_data:
    seq:
      - id: norm
        type: u2_vector
      - id: forw
        type: u2_vector
  u2_vector:
    seq:
      - id: x
        type: u2
      - id: y
        type: u2
      - id: z
        type: u2
  s4_vector:
    seq:
      - id: x
        type: s4
      - id: y
        type: s4
      - id: z
        type: s4
  refxobj:
    seq:
      - id: pt
        type: s4_vector
      - id: unknown
        size: 2
      - id: global_no
        type: u2
      - id: unknown1
        size: 2
      - id: cross_index
        size: 1
      - id: unknown2
        size: 1
  source_type:
    seq:
      - id: pt
        type: s4_vector
      - id: type
        type: u4
  track_polygon:
    params:
      - id: count
        type: u4
    seq:
      - id: data
        type: polydata
        repeat: expr
        repeat-expr: count
  polydata:
    seq:
      - id: vertex
        type: u2
        repeat: expr
        repeat-expr: 4
      - id: texture
        type: u2
      - id: hs_texflags
        type: u2
      - id: flags
        size: 1
  xobjs:
    params:
      - id: nobj
        type: u4
    seq:
      - id: objdata
        type: xobjdata
        repeat: expr
        repeat-expr: nobj
      - id: extra
        type: xobjdata_extra(objdata[_index])
        repeat: expr
        repeat-expr: nobj
  xobjdata:
    seq:
      - id: cross_type
        type: u4
      - id: cross_no
        type: u4
      - id: unknown
        size: 4
      - id: ref
        type: point
        if: cross_type == 1 or cross_type == 2 or cross_type == 4
      - id: unknown1
        size: 12
        if: cross_type == 3
      - id: anim
        type: u4
      - id: unknown2
        size: 4
      - id: nvertices
        type: u4
      - id: unknown3
        size: 8
      - id: npolygons
        type: u4
      - id: unknown4
        size: 4
  xobjdata_extra:
    params:
      - id: objdata
        type: xobjdata
    seq:
      - id: anim
        type: xobjdata_anim
        if: objdata.cross_type == 3
      - id: vertices
        type: point
        repeat: expr
        repeat-expr: objdata.nvertices
      - id: unknown
        type: u4
        repeat: expr
        repeat-expr: objdata.nvertices
      - id: polygons
        type: track_polygon(objdata.npolygons)
  xobjdata_anim:
    seq:
      - id: unknown
        size: 2
      - id: type
        size: 1
      - id: objno
        size: 1
      - id: anim_length
        type: u2
      - id: anim_delay
        type: u2
      - id: anim_data
        type: anim_data_type
        repeat: expr
        repeat-expr: anim_length
  anim_data_type:
    seq:
      - id: pt
        type: s4_vector
      - id: x
        type: s2
      - id: y
        type: s2
      - id: z
        type: s2
      - id: w
        type: s2
