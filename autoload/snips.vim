let s:py = has('python3') ? 'py3' : 'py'
let s:pyeval = function(has('python3') ? 'py3eval' : 'pyeval')
let s:timer = -1
let s:current_line = -1
let s:expand_end_line = -1
let s:pos = {}


func! s:err(message)
  echohl Error
  echo a:message
  echohl None
endfunc

func! snips#import() abort
  try
    exe s:py 'import vim, snips, completor_snips'
  catch /^Vim(py\(thon\|3\)):/
    call s:err('Fail to import completor_snips')
    return
  endtry

  try
    exe s:py 'import completor, completers.common'
  catch /^Vim(py\(thon\|3\)):/
    call s:err('Fail to import completor')
    return
  endtry

  try
    exe s:py 'completor.get("common").hooks.append(completor_snips.Snips.filetype)'
    call s:set_snippets_dirs()
  catch /^Vim(py\(thon\|3\)):/
    call s:err('Fail to add snips hook')
  endtry
endfunc


func! s:render(res, lnum) abort
  if empty(a:res.content)
    let lines = []
    let current = ''
    let remain_lines = []
  else
    let lines = split(a:res.content, "\n", v:true)
    let current = lines[0]
    let remain_lines = lines[1:]
  endif

  call setline(a:lnum, current)
  if s:expand_end_line >= a:lnum + 1
    call deletebufline('', a:lnum+1, s:expand_end_line)
  endif

  call append(a:lnum, remain_lines)

  let s:expand_end_line = a:lnum+len(remain_lines)
  let s:current_line = a:lnum

  if empty(a:res.pos)
    let s:pos = {}

    if len(lines) == 0
      let s:pos.line = a:lnum
    else
      let s:pos.line = a:lnum + len(lines) - 1
    endif

    if a:res.end_col > 0
      let s:pos.col = a:res.end_col + 1
    else
      let s:pos.col = col([s:pos.line, '$'])
    endif

    let s:pos.orig_col = col('.')
    call cursor(s:pos.line, s:pos.col)
    call timer_start(0, {t -> s:end_expand()})
  else
    let p = a:res.pos
    let s:pos = #{
          \ line: a:lnum+p.start_line,
          \ col: p.edit_column+1,
          \ end_line: a:lnum+p.end_line,
          \ end_column: p.end_column+1,
          \ orig_col: p.start_column+1
          \ }
    call s:select(s:pos)
  endif

  call timer_start(0, {t -> s:enable_text_change()})
  return ''
endfunc

" Expand the snippet.
func! snips#expand() abort
  call s:end_expand()

  let [_, lnum, column, _, _ ] = getcurpos()
  let line = getline('.')

  let res = s:expand(lnum, column, line)
  if empty(res)
    return ''
  endif

  let v = s:render(res, lnum)
  call timer_start(0, {t -> s:setup_expand()})
  return v
endfunc

func! snips#jump_next() abort
  if s:current_line == -1
    return ''
  endif
  let m = mode()
  if m != 's' && m != 'i'
    return ''
  endif
  let res = s:jump('forward')
  if empty(res)
    return ''
  endif

  let pos = res.pos

  if empty(pos)
    return ''
  endif

  let lnum = s:current_line
  let s:pos = #{
        \ line: lnum+pos.start_line,
        \ col: pos.edit_column+1,
        \ orig_col: pos.start_column+1,
        \ end_line: lnum+pos.end_line,
        \ end_column: pos.end_column+1,
        \ }
  call cursor(s:pos.line, s:pos.col)
  call s:select(s:pos)
  return ''
endfunc


func! s:setup_expand()
  smap <expr> <c-s> snips#jump_next()
  imap <expr> <c-s> snips#jump_next()

  " Set up ticker.
  let s:timer = timer_start(300, function('s:on_expand_tick'), #{repeat: -1})
endfunc

imap <leader>z <C-R>=snips#expand()<CR>


func! s:enable_text_change()
  augroup snips_text_change
    autocmd!
    autocmd TextChanged * :call s:on_text_change()
    autocmd TextChangedI * :call s:on_text_change()
  augroup END
endfunc


func! s:disable_text_change()
  augroup snips_text_change
    autocmd!
  augroup END
endfunc


func! s:on_expand_tick(timer)
  if s:current_line == -1
    return
  endif

  let m = mode()
  if m == 's' || m == 'i'
    return
  endif
  " Clear ticker.
  call s:end_expand()
endfunc


func s:end_expand()
  call timer_stop(s:timer)
  call s:teardown_expand()
endfunc


func s:teardown_expand()
  let s:expand_end_line = -1

  if s:current_line == -1
    return
  endif

  call s:disable_text_change()

  sunmap <expr> <c-s>
  iunmap <expr> <c-s>
  call s:reset_jump()
  let s:current_line = -1
  let s:current_col = -1
endfunc

func! s:on_text_change() abort
  call s:disable_text_change()

  let current = col('.')
  let c = current - 2
  let l = line('.')
  let line_diff = l - s:pos.line

  if line_diff != 0 || current < s:pos.orig_col
    call timer_start(0, {_ -> s:end_expand()})
    return
  endif

  let col_pos = c + 1
  if line_diff < 0
    let lines = []
  else
    let lines = getline(s:pos.line, l)
  endif

  let col = s:pos.orig_col

  if len(lines) <= 1
    if c < col - 1
      let lines = []
    elseif line_diff >= 0
      let lines[0] = lines[0][col-1:c]
    endif
  else
    let lines[0] = lines[0][col-1:]
    let lines[-1] = lines[-1][:c]
  endif

  let content = join(lines, "\n")
  let res = s:rerender(content)
  if empty(res)
    return
  endif

  call timer_start(0, {t -> s:render(res, s:current_line)})
endfunc

func! s:select(pos)
  if a:pos.line == a:pos.end_line && a:pos.end_column == a:pos.col
    let start = virtcol([a:pos.line, a:pos.col - 1])
    let action = 'i'
    if start != 0
      let action = 'a'
    endif
    call feedkeys("\<ESC>" .. a:pos.line ..'G' .. start .. '|' .. action)
    return
  endif

  let start = virtcol([a:pos.line, a:pos.col])
  let end = virtcol([a:pos.end_line, a:pos.end_column-1])

  call feedkeys("\<ESC>v" .. a:pos.end_line .. 'G' .. end .. '|o' .. a:pos.line .. 'G' .. start .."|o\<C-G>")
endfunc

func! s:expand(lnum, column, line) abort
  let tabstop = &softtabstop

  if tabstop == 0
    let tabstop = &tabstop
  elseif tabstop < 0
    let tabstop = &shiftwidth
  endif

  let context = #{
        \ fname: expand("%:t"),
        \ fpath: expand("%"),
        \ ftype: &ft,
        \ lnum: a:lnum - 1,
        \ column: a:column - 1,
        \ text: a:line,
        \ tabstop: tabstop,
        \ expandtab: &expandtab,
        \ shiftwidth: &shiftwidth,
        \ indent: indent('.'),
        \ }

  let s:context = context

  exe s:py 'res = snips.expand(vim.eval("context"))'
  return s:pyeval('res')
endfunc

func! s:jump(direction) abort
  exe s:py 'res = snips.jump(vim.eval("&ft"), vim.eval("a:direction"))'
  return s:pyeval('res')
endfunc

func! s:rerender(content) abort
  exe s:py 'res = snips.rerender(vim.eval("a:content"))'
  return s:pyeval('res')
endfunc

func! s:reset_jump() abort
  exe s:py 'snips.reset_jump(vim.eval("&ft"))'
endfunc

func! s:set_snippets_dirs() abort
  exe s:py 'snips.set_snippets_dirs(vim.eval("g:snips_snippets_dirs"))'
endfunc

func! snips#_gen_hi_groups() abort
  exe s:py 'res = snips.gen_highlight_groups(vim.current.buffer[:])'
  return s:pyeval('res')
endfunc
