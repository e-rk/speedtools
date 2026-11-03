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
    - id: runtime_links
      size: 16
      doc: Run time only, not meaningful
    - id: runtime_display_name
      size: 256
      doc: Run time only, not meaningful
    - id: car_id
      type: strz
      size: 256
      doc: ID of the car, normally the name of its folder.
    - id: runtime_folder_names
      size: 268
      doc: Run time only, not meaningful
    - id: serial
      type: s4
      doc: |
          Serial number of the car. Stock cars use 0-49 and are identified by
          it everywhere, e.g. in the career save files.
    - id: runtime_manufacturer_index
      type: s4
      doc: Run time only, not meaningful
    - id: runtime_player_options
      size: 8
      doc: Run time only, not meaningful
    - id: runtime_colors
      size: 76
      doc: Run time only, not meaningful
    - id: flags
      type: car_flags
    - id: runtime_header
      type: u4
      doc: Run time only, not meaningful
    - id: car_class
      type: s4
      enum: car_class
    - id: interior_scroll_x
      type: u2
      doc: |
          Initial horizontal scroll, in pixels, of the interior panorama
          (IN<id>.fsh) in the 320x192 showcase interior view.
    - id: version
      type: u1
      doc: Must be 10, otherwise the game skips the car.
    - id: acceleration
      type: rating
    - id: top_speed
      type: rating
    - id: handling
      type: rating
    - id: braking
      type: rating
    - id: overall
      type: rating
      doc: |
          Overall rating. The career mode uses it to pick opponents of a
          similar strength.
    - id: padding0
      size: 1
    - id: price
      type: u4
      doc: Purchase price in the career mode, in US dollars.
    - id: upgrade_prices
      type: u4
      repeat: expr
      repeat-expr: 3
      doc: Price of each of the three upgrade stages, in US dollars.
    - id: runtime_half_sizes
      size: 12
      doc: Run time only, not meaningful
    - id: unknown
      type: u1
      doc: Unknown, unused field.
    - id: engine_location
      type: u1
      enum: engine_location
    - id: padding1
      size: 2
    - id: num_strings
      type: u2
      doc: Number of the localized strings
    - id: strings
      type: string_entry
      repeat: expr
      repeat-expr: num_strings
      doc: |
          Localized strings. The showcase uses them by index:
          0 manufacturer, 1 model, 2 full car name, 3 price, 4 status,
          5 weight, 6 weight distribution (front/rear), 7 length, 8 width,
          9 height, 10 engine type, 11 displacement, 12 horsepower, 13 torque,
          14 maximum engine speed, 15 brakes (front/rear),
          16 tires (front/rear), 17 special feature, 18 top speed, 19 0-60 mph time,
          20 0-100 mph time, 21 transmission type, 22 number of gears,
          23 title of the manufacturer history, 24-30 history entries,
          31-40 color names.
instances:
    police:
        value: flags.police
types:
    car_flags:
        meta:
            bit-endian: le
        seq:
            - id: locked
              type: b1
              doc: Bonus car, hidden until it is unlocked.
            - id: unknown0
              type: b1
              doc: Unknown field, unused
            - id: own_fe_art
              type: b1
              doc: |
                  The front end art is loaded from the car folder and named
                  after `car_id` instead of coming from FeArt. The game also
                  sends such cars to the network peers.
            - id: network_temp
              type: b1
              doc: Run time only, not meaningful
            - id: police
              type: b1
              doc: Police car
            - id: no_pursuit
              type: b1
              doc: Not available in the pursuit mode.
            - id: addon
              type: b1
              doc: |
                  Car that other players may not have. The game sends its files
                  to the network peers and keeps it out of some multiplayer car
                  lists.
            - id: no_wreck_smoke
              type: b1
              doc: A wrecked car does not smoke or burn.
            - id: convertible
              type: b1
              doc: The roof can be opened.
            - id: removable_hardtop
              type: b1
              doc: |
                  Like `convertible`, but with a removable hardtop. Takes
                  precedence over `convertible`.
            - id: has_history_art
              type: b1
              doc: Run time only, not meaningful.
            - id: has_showcase_art
              type: b1
              doc: Run time only, not meaningful.
            - id: has_interior_art
              type: b1
              doc: Run time only, not meaningful.
            - id: has_slides
              type: b1
              doc: Run time only, not meaningful.
            - id: no_upgrades
              type: b1
              doc: |
                  The car cannot be upgraded. Without this flag the game raises
                  the acceleration, top speed, handling and braking ratings so
                  that they never drop with an upgrade.
            - id: fixed_paint
              type: b1
              doc: |
                  The car always uses its first color instead of the one closest
                  to the requested color.
            - id: unused
              type: b16
    rating:
        doc: Performance rating on a 0-20 scale.
        seq:
            - id: levels
              type: u1
              repeat: expr
              repeat-expr: 4
              doc: Rating of the stock car followed by the rating after each upgrade stage.
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
        255: none
    engine_location:
        0: front
        1: mid
        2: rear
