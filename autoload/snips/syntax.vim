func! snips#syntax#define_props()
  call prop_type_add('snips_keyword', {'highlight': 'Keyword'})
  call prop_type_add('snips_comment', {'highlight': 'Comment'})
  call prop_type_add('snips_description', {'highlight': 'String'})
  call prop_type_add('snips_trigger', {'highlight': 'Identifier'})
  call prop_type_add('snips_option', {'highlight': 'PreProc'})
  call prop_type_add('snips_placeholder', {'highlight': 'Special'})
endfunc


func! snips#syntax#hi() abort
  let groups = snips#_gen_hi_groups()

  for g in groups
    call prop_add(g.line + 1, g.column + 1, {'length': g.length, 'type': g.group})
  endfor
endfunc
