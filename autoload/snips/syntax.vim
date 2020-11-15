func! snips#syntax#define_props()
  hi default snipsInterpolation guifg=#605454

  call prop_type_add('snips_keyword', {'highlight': 'Keyword'})
  call prop_type_add('snips_comment', {'highlight': 'Comment'})
  call prop_type_add('snips_description', {'highlight': 'String'})
  call prop_type_add('snips_trigger', {'highlight': 'Identifier'})
  call prop_type_add('snips_option', {'highlight': 'PreProc'})
  call prop_type_add('snips_placeholder', {'highlight': 'Special'})
  call prop_type_add('snips_interpolation', {'highlight': 'snipsInterpolation', 'priority': 1})
endfunc


func! snips#syntax#hi() abort
  let groups = snips#_gen_hi_groups()

  for g in groups
    call prop_add(g.line + 1, g.column + 1, s:to_options(g))
  endfor
endfunc


func! s:to_options(g)
  let opt = {'type': a:g.group}

  if has_key(a:g, 'length')
    let opt.length = a:g.length
  else
    let opt.end_lnum = a:g.end_line + 1
    let opt.end_col = a:g.end_column + 1
  endif

  return opt
endfunc
