meta:
    id: bnk
    file-extension: bnk
    ks-opaque-types: true
    license: CC0-1.0
    endian: le
    bit-endian: be
doc: |
    Sound bank file.

    The file consists of the header, a table of patch offsets, the patch section (one "PT" tag
    list per patch) and the sample data. A patch describes one or more timbres (layers played
    together). Each timbre lists its playback parameters, followed by a sample header that points
    into the sample data.
seq:
    - id: magic
      contents: [BNKl]
    - id: version
      type: u1
      doc: Bank version (2 or 4). The game only distinguishes version 4 from the older banks.
    - id: reserved
      type: u1
    - id: num_sounds
      type: u2
      doc: Number of entries in the patch offset table.
    - id: first_sound_offset
      type: u4
      doc: |
          Size of the header, the offset table and the patch section, i.e. the offset of the sample
          data.
    - id: sound_data_size
      type: u4
      if: version == 4
      doc: Size of the sample data. `first_sound_offset + sound_data_size` is the size of the bank.
    - id: unknown
      type: u4
      if: version == 4
      doc: Always 0xffffffff.
    - id: sounds
      type: sound_entry(_root._io.pos, _index == (num_sounds - 1))
      repeat: expr
      repeat-expr: num_sounds
      doc: Patch offset table.
types:
    sound_entry:
        params:
            - id: pos
              type: u4
            - id: is_last
              type: bool
        seq:
            - id: offset
              type: u4
              doc: Offset of the patch relative to this entry. Zero marks an empty slot.
        instances:
            body:
                pos: body_offset
                type: sound_data
                if: offset > 0
            body_offset:
                value: pos + offset
    sound_data:
        doc: |
            Patch. The timbres are separated with `tv_type::separator`. Each timbre lists its
            playback parameters (tags below 0x26), then `tv_type::subheader` and the sample header.
            The playback parameters are reset to their defaults for every timbre, except the
            patch-level tags.
        seq:
            - id: magic
              contents: [PT]
            - id: reserved
              type: u1
            - id: flags
              type: u1
              doc: |
                  Bit 1 - a 4-byte field precedes the tags. Bit 0 is set by the game once the sound
                  buffers of the patch are created. Zero in all banks.
            - id: extension
              type: u4
              if: (flags & 2) != 0
            - id: header
              type: header(false)
    header:
        doc: |
            Tag list. The patch tag list ends with `tv_type::terminator`. The sample header
            (`is_subheader`) is parsed up to `tv_type::sample_data_pointer`, which every sample header
            contains exactly once. The game reads the sample header until the next separator or
            terminator, so the `tv_type::hw_buffer` slot that follows ends up in the enclosing list.
        params:
            - id: is_subheader
              type: bool
        seq:
            - id: tlvs
              type: pt_header_tlv
              repeat: until
              repeat-until: _.is_terminator or (is_subheader and _.ends_sample_header)
    pt_header_tlv:
        doc: |
            Tag-length-value entry. `padding`, `subheader`, `separator` and `terminator` have no
            length byte.
        seq:
            - id: type
              type: u1
              enum: tv_type
            - id: value
              if: type != tv_type::padding and type != tv_type::separator
              type:
                  switch-on: type
                  cases:
                      "tv_type::subheader": header(true)
                      "tv_type::terminator": empty_value
                      "tv_type::data_start": data_start
                      _: tlv_value
        instances:
            is_terminator:
                value: type == tv_type::terminator
            ends_sample_header:
                value: type == tv_type::sample_data_pointer
    tlv_value:
        doc: Length-prefixed big-endian payload.
        seq:
            - id: len_short
              type: u1
            - id: len_long
              type: u4be
              if: len_short == 0xff
              doc: Extended payload length.
            - id: data
              size: len_data
        instances:
            len_data:
                value: "len_short == 0xff ? len_long : len_short"
            value:
                value: >-
                    len_data == 0 ? 0 :
                    len_data == 1 ? data[0] - ((data[0] & 0x80) << 1) :
                    len_data == 2 ? ((data[0] << 8) | data[1]) - ((data[0] & 0x80) << 9) :
                    len_data == 3 ? ((data[0] << 16) | (data[1] << 8) | data[2]) - ((data[0] & 0x80) << 17) :
                    ((data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]) - ((data[0] & 0x80) << 25)
                if: len_data <= 4
                doc: |
                    Two's complement big-endian integer. Longer payloads are opaque to the game and
                    have no value.
    empty_value:
        seq:
            - id: value
              size: 0
    data_start:
        doc: Offset of the sample data relative to the start of the bank.
        seq:
            - id: size
              type: u1
            - id: value
              size: size
              type:
                  switch-on: size
                  cases:
                      1: b8
                      2: b16
                      3: b24
                      4: b32
                      _: b8
        instances:
            body:
                pos: value
                type: bnk_audio_stream(_parent._parent) # Get the sample header
    # bnk_audio_stream: # For debugging
    #   seq:
    #     - id: debug
    #       type: u1
enums:
    tv_type:
        0x00:
            id: play_mode
            doc: |
                Patch-level. Selects the decoder variant. 1 (default) plays the sample once, or loops
                it when it has a loop end. 2 streams the sample without looping.
        0x01:
            id: velocity_low
            doc: Lowest note velocity that plays the timbre. Default 0.
        0x02:
            id: velocity_high
            doc: Highest note velocity that plays the timbre. Default 127.
        0x03:
            id: key_low
            doc: Lowest note that plays the timbre. Default 0.
        0x04:
            id: key_high
            doc: Highest note that plays the timbre. Default 127.
        0x05:
            id: unknown_05
            doc: Default -1.
        0x06:
            id: priority
            doc: Voice stealing priority, 0..100. Default 0.
        0x07:
            id: root_key
            doc: Note (MIDI number) at which the sample plays at its recorded rate. Default 60.
        0x08:
            id: unknown_08
            doc: Default -1.
        0x09:
            id: unknown_09
            doc: Default 1.
        0x0a:
            id: pitch_bend_range
            doc: Pitch change at full pitch bend, in semitones. Default 0.
        0x0b:
            id: num_voices
            doc: Number of hardware voices allocated for the timbre. Default 1.
        0x0c:
            id: pan
            doc: Pan, 0..127 with the centre at 64. Combined with the requested pan. Default 64.
        0x0d:
            id: pan_random_range
            doc: A random offset in [-value, value) is added to the pan on each play. Default 0.
        0x0e:
            id: volume
            doc: Volume, 0..127, scaled by the note velocity. Default 127.
        0x0f:
            id: volume_random_range
            doc: A random offset in [-value, value) is added to the volume on each play. Default 0.
        0x10:
            id: detune
            doc: Pitch offset in cents. Default 0.
        0x11:
            id: detune_random_range
            doc: A random offset in [-value, value) cents is added to the pitch on each play. Default 0.
        0x12:
            id: volume_curve
            doc: Offset (relative to the value) of a volume lookup table. Default none.
        0x13:
            id: effect_send
            doc: Effect (reverb) send level, 0..127. Default 0.
        0x15:
            id: pan_curve
            doc: Offset (relative to the value) of a pan lookup table. Default none.
        0x17:
            id: pitch_bend_curve
            doc: Offset (relative to the value) of a pitch bend lookup table. Default none.
        0x19:
            id: envelope
            doc: Offset (relative to the value) of the envelope. Defaults to a built-in envelope.
        0x1b:
            id: unknown_1b
            doc: Patch-level. Default 15.
        0x1c:
            id: envelope_initial_level
            doc: Initial envelope level, 0..127. Default 127.
        0x1d:
            id: volume_mod_table
            doc: Offset (relative to the value) of a volume modulation table. Default none.
        0x1e:
            id: volume_mod_length
            doc: Number of entries in the volume modulation table.
        0x1f:
            id: volume_mod_random_phase
            doc: Non-zero starts the volume modulation at a random entry.
        0x20:
            id: pitch_mod_table
            doc: Offset (relative to the value) of a pitch modulation table. Default none.
        0x21:
            id: pitch_mod_length
            doc: Number of entries in the pitch modulation table.
        0x22:
            id: pitch_mod_depth
            doc: Pitch modulation depth in cents.
        0x23:
            id: pitch_mod_random_phase
            doc: Non-zero starts the pitch modulation at a random entry.
        0x24:
            id: patch_detune_random_range
            doc: |
                Patch-level. A random offset in [-value, value) cents, drawn once per play and applied
                to every timbre of the patch.
        0x25:
            id: pan_scale
            doc: Multiplier applied to the requested pan. Default 1.
        0x80:
            id: revision
            doc: Not read by the game.
        0x81:
            id: bits_per_sample
            doc: PCM sample size in bits. Default 16.
        0x82:
            id: channels
            doc: Number of interleaved channels. Default 1.
        0x83:
            id: compression_type
            doc: 0 - PCM (default), 7 - ADPCM, 9 - MicroTalk 10:1.
        0x84:
            id: sample_rate
            doc: Default 22050.
        0x85:
            id: num_samples
        0x86:
            id: loop_start
            doc: First sample of the loop. Default -1.
        0x87:
            id: loop_end
            doc: |
                Last sample of the loop (inclusive). The sample loops only when the value is greater
                than 0. Default -1.
        0x88:
            id: data_start
            doc: Offset of the sample data relative to the start of the bank.
        0x8a:
            id: sample_data_pointer
            doc: 4-byte slot for the address of the sample data, filled in by the game. Zero in files.
        0x91:
            id: resampler_quality
            doc: Resampling quality, 0..100. Below 26 the game picks the low quality mixer.
        0x92:
            id: spatialization
            doc: |
                0 - 2D software voice (default), 1 - 3D software voice, 2 - DirectSound3D buffer
                created when the bank is loaded (the game sets the value to 3 once the buffer exists).
        0x93:
            id: hw_buffer
            doc: 4-byte slot for the DirectSound3D buffer handle, filled in by the game. Zero in files.
        0xa0:
            id: revision2
            doc: Not read by the game.
        0xfc:
            id: padding
            doc: Padding byte, skipped.
        0xfd:
            id: subheader
            doc: Start of the sample header. No length byte.
        0xfe:
            id: separator
            doc: Start of the next timbre. No length byte.
        0xff:
            id: terminator
            doc: End of the patch. No length byte.
