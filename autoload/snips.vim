let s:py = has('python3') ? 'py3' : 'py'
let s:pyeval = function(has('python3') ? 'py3eval' : 'pyeval')

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
  catch /^Vim(py\(thon\|3\)):/
    call s:err('Fail to add snips hook')
  endtry
endfunc

let s:current_line = -1
let s:pos = {}

" Expand the snippet.
func! snips#expand() abort
  let [_, lnum, column, _, _ ] = getcurpos()
  let text = getline('.')[:column-1]
  let last = split(text, '\s\+', 1)[-1]
  if empty(last)
    return ''
  endif
  let res = s:expand(last)
  if empty(res)
    return ''
  endif

  let lines = split(res.content, "\n")
  let remain = len(text) - len(last)
  if remain > 0
    let current = text[:remain] . lines[0]
  else
    let current = lines[0]
  endif
  call setline(lnum, current)
  call append(lnum, lines[1:])
  let s:current_line = lnum
  if res.lnum == -1
    let s:pos = #{line: lnum+len(lines)-1}
    let s:pos.col = col([s:pos.line, '$'])
    call cursor(s:pos.line, s:pos.col)
  else
    let s:pos = #{line: lnum+res.lnum, col: res.col+1}
    call cursor(s:pos.line, s:pos.col)
    call s:select(s:pos.line, s:pos.col, res.length)
  endif
  call timer_start(0, {t -> s:setup_expand()})
  return ''
endfunc

func! snips#jump_next() abort
  call Log("jump")
  if s:current_line == -1
    return ''
  endif
  let m = mode()
  call Log(string(m))
  if m != 's' && m != 'i'
    return ''
  endif
  call Log("call jump")
  let res = s:jump('forward')
  call Log(string(res))
  if empty(res)
    return ''
  endif
  if res.lnum == -1
    return ''
  endif
  call Log(string([res]))
  let lnum = s:current_line
  let s:pos = #{line: lnum+res.lnum, col: res.col+1}
  call cursor(s:pos.line, s:pos.col)
  call s:select(s:pos.line, s:pos.col, res.length)
  return ''
endfunc

func! s:setup_expand()
  smap <expr> <c-s> snips#jump_next()
  imap <expr> <c-s> snips#jump_next()

  " Set up ticker.
  call timer_start(300, function('s:on_expand_tick'), #{repeat: -1})

  let s:callback_id = listener_add(function('s:callback'))
endfunc

imap <leader>z <C-R>=snips#expand()<CR>

func! s:on_expand_tick(timer)
  let m = mode()
  if m == 's' || m == 'i'
    return
  endif
  call listener_remove(s:callback_id)

  " Clear ticker.
  call timer_stop(a:timer)
  call Log("teardown")
  sunmap <expr> <c-s>
  iunmap <expr> <c-s>
  call s:reset_jump()
  let s:current_line = -1
  let s:current_col = -1
endfunc

func! s:callback(bufnr, start, end, added, changes)
  call s:on_text_change()
endfunc

func! s:on_text_change() abort
  let c = col('.') - 2
  let l = line('.')
  let line_diff = l - s:pos.line
  let col_pos = c + 1
  if line_diff < 0
    let lines = []
  else
    let lines = getline(s:pos.line, l)
  endif
  call Log(string(lines).'|'.string(s:pos.line))
  if len(lines) <= 1
    call Log(string([s:pos.col-1, c]))
    if c < s:pos.col - 1
      let lines = []
    elseif line_diff >= 0
      let lines[0] = lines[0][s:pos.col-1:c]
    endif
  else
    let lines[0] = lines[0][s:pos.col-1:]
    let lines[-1] = lines[-1][:c]
  endif
  let content = join(lines, "\n")
  call Log(string(content).'|'.string(lines))
  call Log(string(s:pos))
  let res = s:update_placeholder(content, line_diff, col_pos)
  if empty(res)
    return
  endif
  call Log(string(res.updates))
  call timer_start(0, {t -> s:update_text(res)})
endfunc

func! s:update_text(res) abort
  call listener_remove(s:callback_id)
  try
    call Log("before updates")
    for u in a:res.updates
      call s:set_text(s:current_line, u)
    endfor
    call Log(string(["after updates", a:res.lnum]))
    let s:pos.line = s:current_line + a:res.lnum
    let s:pos.col = a:res.col + 1
    call s:select(s:pos.line, s:pos.col, 0)
  finally
    let s:callback_id = listener_add(function('s:callback'))
  endtry
endfunc

func! s:set_text(base_line, item) abort
  let lnum = a:base_line + a:item.line_offset
  let text = getline(lnum)
  call Log(string([lnum, text, a:item, string(a:item.content)]))
  if a:item.col_offset == 0
    let prefix = ''
  else
    let prefix = text[:a:item.col_offset-1]
  endif
  let suffix = text[a:item.col_offset+a:item.length:]
  let lines = split(a:item.content, "\n", 1)
  call Log(string(["line replace", prefix, suffix, lines]))
  if len(lines) > 1
    if a:item.col_offset == 0 && a:item.length == 0
      call append(lnum - 1, lines[0])
    else
      call setline(lnum, prefix . lines[0])
    endif
    if len(lines) > 2
      call append(lnum, lines[1:-2])
    endif
    if empty(lines[-1])
      return
    endif
    if suffix == '' && a:item.length == 0
      call append(lnum + len(lines) - 2, lines[-1])
    else
      call setline(lnum + len(lines) - 1, lines[-1] . suffix)
    endif
  elseif len(lines) == 1
    call Log(string([lnum, prefix, lines[0], suffix]))
    if prefix == '' && suffix == '' && a:item.length == 0
      call append(lnum - 1 , lines[0])
    else
      call setline(lnum, prefix . lines[0] . suffix)
    endif
  else
    call setline(lnum, prefix . suffix)
    call Log(string(["aa", lnum, prefix, suffix]))
  endif
endfunc

func! s:add_text(lnum, prefix, suffix, text)
  if a:prefix == '' && a:suffix == ''
    call append(a:lnum, text)
  endif
  return a:lnum + 1
endfunc

func! s:select(lnum, start, length)
  if a:length == 0
    let end = a:start
  else
    let end = a:start + a:length - 1
  endif
  call Log(string([a:start, end]))
  if a:start == end
    let start = virtcol([a:lnum, a:start - 1])
    call Log("aaa".string(start))
    let action = 'i'
    if start != 0
      let action = 'a'
    endif
    call feedkeys("\<ESC>".a:lnum.'G'.start.'|'.action)
    return
  endif
  let start = virtcol([a:lnum, a:start])
  let end = virtcol([a:lnum, end])
  call feedkeys("\<ESC>v".a:lnum.'G'.end.'|o'.a:lnum.'G'.start."|o\<C-G>")
endfunc

func! s:expand(trigger) abort
  let fn = expand("%:t")
  exe s:py 'res = snips.expand(vim.eval("fn"), vim.eval("&ft"), vim.eval("a:trigger"))'
  return s:pyeval('res')
endfunc

func! s:jump(direction) abort
  exe s:py 'res = snips.jump(vim.eval("&ft"), vim.eval("a:direction"))'
  return s:pyeval('res')
endfunc

func! s:reset_jump() abort
  exe s:py 'snips.reset_jump(vim.eval("&ft"))'
endfunc

func! s:update_placeholder(content, line, col) abort
  let fn = expand("%:t")
  exe s:py 'res = snips.update_placeholder(vim.eval("fn"), vim.eval("&ft"), vim.eval("a:content"), vim.eval("a:line"), vim.eval("a:col"))'
  return s:pyeval('res')
endfunc
